"""Tests of the table of the review queue, against a real SQLite file.

The store of every test is built by the migrations, as a real store is.
What the table must refuse is also written past the model.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, delete, select
from sqlalchemy.exc import IntegrityError

from motosphere.db.models import ReviewItem, Source
from motosphere.db.models.review_item import ReviewKind, ReviewState
from motosphere.db.models.source import CollectionMethod, SourceCategory
from motosphere.db.work import unit_of_work

MOMENT = "2026-11-26T09:00:00.000000+00:00"
DECIDED = datetime(2026, 11, 26, 12, 30, tzinfo=UTC)
DECIDED_AS_TEXT = "2026-11-26T12:30:00.000000+00:00"
ADDRESS = "https://federation.example/tracks/7"
BROKEN_KEY = "FOREIGN KEY constraint failed"
CHECK = "CHECK constraint failed: ck_review_item_"
# A row written past the model: every column but the key, in the table's order.
PAST_THE_MODEL = (
    "INSERT INTO review_item (kind, record_table, record_id, other_record_id, field, "
    "source_id, source_address, source_value, reason, state, decided_by, decided_at, note, "
    "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)
WHAT_IT_HOLDS = (
    "SELECT kind, record_table, record_id, other_record_id, field, source_id, source_address, "
    "source_value, reason, state, decided_by, decided_at, note FROM review_item ORDER BY id"
)
# The two kinds that are about what a source says of a field.
OF_A_FIELD = ["sources disagree", "value outside its rules"]
# What goes with those two kinds, and with them alone.
WITH_A_FIELD = ["field", "source_id", "source_address", "source_value"]


@contextmanager
def refused(why: str) -> Iterator[None]:
    """SQLite refuses what the block writes, and says exactly this."""
    with pytest.raises(IntegrityError) as refusal:
        yield
    assert str(refusal.value.orig) == why


def a_source(store: Engine, name: str = "Example Federation") -> int:
    """Store a source, and give its key."""
    source = Source(
        name=name,
        website="https://federation.example",
        category=SourceCategory.GOVERNING_BODY,
        collection_method=CollectionMethod.RSS,
    )
    with unit_of_work(store) as work:
        work.add(source)
    return source.id


def a_duplicate(**given: object) -> dict[str, object]:
    """A possible duplicate that nobody has decided, as a row, but for what is given."""
    row: dict[str, object] = {
        "kind": "possible duplicate",
        "record_table": "track",
        "record_id": 7,
        "other_record_id": 12,
        "field": None,
        "source_id": None,
        "source_address": None,
        "source_value": None,
        "reason": "The two tracks have one name and lie 140 metres apart.",
        "state": "open",
        "decided_by": None,
        "decided_at": None,
        "note": None,
    }
    assert set(given) <= set(row)
    row.update(given)
    return row


def of_a_field(kind: str = "sources disagree", **given: object) -> dict[str, object]:
    """An item about what the first source says of a field, as a row, but for what is given."""
    return a_duplicate(
        **{
            "kind": kind,
            "other_record_id": None,
            "field": "length_in_metres",
            "source_id": 1,
            "source_address": ADDRESS,
            "source_value": "1750",
            "reason": "The record says 1600.",
            **given,
        }
    )


def write(store: Engine, row: dict[str, object]) -> None:
    """Write an item past the model, as plain SQL."""
    with store.begin() as connection:
        connection.exec_driver_sql(PAST_THE_MODEL, (*row.values(), MOMENT, MOMENT))


def held(store: Engine) -> list[tuple[object, ...]]:
    """What the table holds, as SQLite holds it, by the key, without the two times."""
    with store.connect() as connection:
        return [tuple(row) for row in connection.exec_driver_sql(WHAT_IT_HOLDS)]


def test_in_the_file_the_table_is_as_the_model_says_it(newest: Engine) -> None:
    with newest.connect() as connection:
        columns = [
            (name, kind, bool(must), bool(key))
            for _, name, kind, must, _, key in connection.exec_driver_sql(
                "PRAGMA table_info(review_item)"
            )
        ]
        refers = [
            (to, here, there, on_update, on_delete)
            for _, _, to, here, there, on_update, on_delete, _ in connection.exec_driver_sql(
                "PRAGMA foreign_key_list(review_item)"
            )
        ]
        indexes = [
            (name, unique, made_by, partial)
            for _, name, unique, made_by, partial in connection.exec_driver_sql(
                "PRAGMA index_list(review_item)"
            )
        ]
        indexed = [
            name
            for _, _, name in connection.exec_driver_sql(
                "PRAGMA index_info(ix_review_item_source_id)"
            )
        ]
        strict = connection.exec_driver_sql(
            "SELECT strict FROM pragma_table_list WHERE name = 'review_item'"
        ).scalar_one()
        written = str(
            connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE name = 'review_item'"
            ).scalar_one()
        )

    assert columns == [
        ("id", "INTEGER", True, True),
        ("kind", "TEXT", True, False),
        ("record_table", "TEXT", True, False),
        ("record_id", "INTEGER", True, False),
        ("other_record_id", "INTEGER", False, False),
        ("field", "TEXT", False, False),
        ("source_id", "INTEGER", False, False),
        ("source_address", "TEXT", False, False),
        ("source_value", "TEXT", False, False),
        ("reason", "TEXT", True, False),
        ("state", "TEXT", True, False),
        ("decided_by", "TEXT", False, False),
        ("decided_at", "TEXT", False, False),
        ("note", "TEXT", False, False),
        ("created_at", "TEXT", True, False),
        ("updated_at", "TEXT", True, False),
    ]
    assert refers == [("source", "source_id", "id", "NO ACTION", "NO ACTION")]
    # The index over the source: two rows can be alike in it, a statement
    # made it, and it is over all rows. The two others are those of one
    # doubt, and test_review_item_one_doubt.py has their tests.
    assert sorted(indexes) == [
        ("ix_review_item_record_table_record_id_field_source_id_source_value", 1, "c", 1),
        ("ix_review_item_record_table_record_id_other_record_id", 1, "c", 1),
        ("ix_review_item_source_id", 0, "c", 0),
    ]
    assert indexed == ["source_id"]
    assert strict == 1
    assert "AUTOINCREMENT" in written
    in_one_line = " ".join(written.split())
    for name, check in {
        "record_id_positive": "(record_id > 0)",
        "other_record_id_after_record_id": "(other_record_id > record_id)",
        "other_record_id_when_possible_duplicate": (
            "((other_record_id IS NULL) = (kind != 'possible duplicate'))"
        ),
        "field_unless_possible_duplicate": "((field IS NULL) = (kind = 'possible duplicate'))",
        "source_id_unless_possible_duplicate": (
            "((source_id IS NULL) = (kind = 'possible duplicate'))"
        ),
        "source_address_unless_possible_duplicate": (
            "((source_address IS NULL) = (kind = 'possible duplicate'))"
        ),
        "source_value_unless_possible_duplicate": (
            "((source_value IS NULL) = (kind = 'possible duplicate'))"
        ),
        "decided_by_when_decided": "((decided_by IS NULL) = (state = 'open'))",
        "decided_at_when_decided": "((decided_at IS NULL) = (state = 'open'))",
        "state_one_of": "(state IN ('open', 'accepted', 'rejected'))",
    }.items():
        assert f"CONSTRAINT ck_review_item_{name} CHECK {check}" in in_one_line
    assert (
        "CONSTRAINT ck_review_item_kind_one_of CHECK (kind IN ( "
        "'possible duplicate', 'sources disagree', 'value outside its rules' ))" in in_one_line
    )
    for column in ("record_table", "field", "reason", "decided_by", "note"):
        assert f"CONSTRAINT ck_review_item_{column}_not_empty CHECK (trim({column}," in (
            in_one_line
        )
    assert "CONSTRAINT ck_review_item_source_address_web_address CHECK (" in in_one_line
    # The nine of the table, the two of the lists, the five of the texts
    # that are not empty, and that of the web address.
    assert in_one_line.count("CONSTRAINT ck_review_item_") == 17


def test_a_possible_duplicate_is_stored_and_read_back(
    newest: Engine, clock: list[datetime]
) -> None:
    with unit_of_work(newest) as work:
        work.add(
            ReviewItem(
                kind=ReviewKind.POSSIBLE_DUPLICATE,
                record_table="track",
                record_id=7,
                other_record_id=12,
                reason="The two tracks have one name and lie 140 metres apart.",
            )
        )

    with unit_of_work(newest) as work:
        found = work.execute(select(ReviewItem)).scalar_one()
    assert found.id == 1
    assert found.kind is ReviewKind.POSSIBLE_DUPLICATE
    assert (found.record_table, found.record_id, found.other_record_id) == ("track", 7, 12)
    assert (found.field, found.source_id, found.source_address, found.source_value) == (
        None,
        None,
        None,
        None,
    )
    assert found.reason == "The two tracks have one name and lie 140 metres apart."
    # Nobody has decided an item that is new: the model says so by itself.
    assert found.state is ReviewState.OPEN
    assert (found.decided_by, found.decided_at, found.note) == (None, None, None)
    assert found.created_at == found.updated_at == clock[-1]
    assert held(newest) == [tuple(a_duplicate().values())]


@pytest.mark.parametrize(
    "kind", [ReviewKind.SOURCES_DISAGREE, ReviewKind.VALUE_OUTSIDE_ITS_RULES], ids=OF_A_FIELD
)
def test_an_item_about_what_a_source_says_of_a_field_is_stored_and_read_back(
    newest: Engine, kind: ReviewKind
) -> None:
    source = a_source(newest)

    with unit_of_work(newest) as work:
        work.add(
            ReviewItem(
                kind=kind,
                record_table="track",
                record_id=7,
                field="length_in_metres",
                source_id=source,
                source_address=ADDRESS,
                source_value="1750",
                reason="The record says 1600.",
            )
        )

    with unit_of_work(newest) as work:
        found = work.execute(select(ReviewItem)).scalar_one()
    assert found.kind is kind
    assert (found.record_table, found.record_id, found.other_record_id) == ("track", 7, None)
    assert (found.field, found.source_id, found.source_address, found.source_value) == (
        "length_in_metres",
        source,
        ADDRESS,
        "1750",
    )
    assert found.state is ReviewState.OPEN
    assert held(newest) == [tuple(of_a_field(kind.value).values())]


@pytest.mark.parametrize("state", [ReviewState.ACCEPTED, ReviewState.REJECTED], ids=lambda s: s)
def test_an_item_that_was_decided_says_how_by_whom_and_when(
    newest: Engine, state: ReviewState
) -> None:
    with unit_of_work(newest) as work:
        work.add(
            ReviewItem(
                kind=ReviewKind.POSSIBLE_DUPLICATE,
                record_table="track",
                record_id=7,
                other_record_id=12,
                reason="The two tracks have one name and lie 140 metres apart.",
                state=state,
                decided_by="Jo Example",
                decided_at=DECIDED,
                note="Asked the club. Kept for the next time the two come up.",
            )
        )

    with unit_of_work(newest) as work:
        found = work.execute(select(ReviewItem)).scalar_one()
    assert found.state is state
    assert (found.decided_by, found.decided_at) == ("Jo Example", DECIDED)
    assert found.note == "Asked the club. Kept for the next time the two come up."
    assert held(newest) == [
        tuple(
            a_duplicate(
                state=state.value,
                decided_by="Jo Example",
                decided_at=DECIDED_AS_TEXT,
                note="Asked the club. Kept for the next time the two come up.",
            ).values()
        )
    ]


def test_an_open_item_is_decided_afterwards_and_can_have_a_note_before(newest: Engine) -> None:
    write(newest, a_duplicate(note="Waiting for the club to answer."))

    with unit_of_work(newest) as work:
        item = work.execute(select(ReviewItem)).scalar_one()
        item.state = ReviewState.REJECTED
        item.decided_by = "Jo Example"
        item.decided_at = DECIDED

    assert held(newest) == [
        tuple(
            a_duplicate(
                state="rejected",
                decided_by="Jo Example",
                decided_at=DECIDED_AS_TEXT,
                note="Waiting for the club to answer.",
            ).values()
        )
    ]


@pytest.mark.parametrize("column", ["kind", "state"])
@pytest.mark.parametrize("word", ["", "Open", "duplicate", "decided"])
def test_a_kind_and_a_state_are_of_their_lists(newest: Engine, column: str, word: str) -> None:
    a_source(newest)
    # A word that is not on its list is not the kind of a possible duplicate
    # and not the state of an open item. So the row is one that breaks no
    # other rule then: it is about a field, and it was decided.
    row = of_a_field(state="accepted", decided_by="Jo Example", decided_at=DECIDED_AS_TEXT)
    row[column] = word

    with refused(f"{CHECK}{column}_one_of"):
        write(newest, row)

    assert held(newest) == []


@pytest.mark.parametrize("column", ["kind", "record_table", "record_id", "reason", "state"])
def test_an_item_says_its_kind_its_record_why_and_its_state(newest: Engine, column: str) -> None:
    with refused(f"NOT NULL constraint failed: review_item.{column}"):
        write(newest, a_duplicate(**{column: None}))

    assert held(newest) == []


@pytest.mark.parametrize("column", ["kind", "record_table", "record_id", "reason"])
def test_an_item_without_its_kind_its_record_or_why_is_refused_through_the_model(
    newest: Engine, column: str
) -> None:
    # The state is not among them: the model gives a new item its state.
    said: dict[str, object] = {
        "kind": ReviewKind.POSSIBLE_DUPLICATE,
        "record_table": "track",
        "record_id": 7,
        "reason": "The two tracks have one name.",
    }
    del said[column]

    with (
        refused(f"NOT NULL constraint failed: review_item.{column}"),
        unit_of_work(newest) as work,
    ):
        work.add(ReviewItem(other_record_id=12, **said))

    assert held(newest) == []


@pytest.mark.parametrize("column", ["record_table", "field", "reason", "decided_by", "note"])
@pytest.mark.parametrize("text", ["", " ", "\t\n"], ids=["empty", "a space", "a tab and a line"])
def test_a_text_of_an_item_is_not_empty(newest: Engine, column: str, text: str) -> None:
    a_source(newest)
    # An item that may say every one of the five: about a field, and decided.
    row = of_a_field(
        state="accepted", decided_by="Jo Example", decided_at=DECIDED_AS_TEXT, note="Checked."
    )
    row[column] = text

    with refused(f"{CHECK}{column}_not_empty"):
        write(newest, row)

    assert held(newest) == []


@pytest.mark.parametrize("key", [0, -1, -7])
def test_the_key_of_a_record_is_above_nothing(newest: Engine, key: int) -> None:
    a_source(newest)

    with refused(f"{CHECK}record_id_positive"), unit_of_work(newest) as work:
        work.add(
            ReviewItem(
                kind=ReviewKind.SOURCES_DISAGREE,
                record_table="track",
                record_id=key,
                field="length_in_metres",
                source_id=1,
                source_address=ADDRESS,
                source_value="1750",
                reason="The record says 1600.",
            )
        )
    with refused(f"{CHECK}record_id_positive"):
        write(newest, of_a_field(record_id=key))

    assert held(newest) == []


def test_a_possible_duplicate_names_the_other_record(newest: Engine) -> None:
    with (
        refused(f"{CHECK}other_record_id_when_possible_duplicate"),
        unit_of_work(newest) as work,
    ):
        work.add(
            ReviewItem(
                kind=ReviewKind.POSSIBLE_DUPLICATE,
                record_table="track",
                record_id=7,
                reason="The two tracks have one name.",
            )
        )
    with refused(f"{CHECK}other_record_id_when_possible_duplicate"):
        write(newest, a_duplicate(other_record_id=None))

    assert held(newest) == []


@pytest.mark.parametrize("other", [7, 6, 1], ids=["itself", "the key before", "the first key"])
def test_the_other_record_of_a_possible_duplicate_has_the_greater_key(
    newest: Engine, other: int
) -> None:
    with refused(f"{CHECK}other_record_id_after_record_id"), unit_of_work(newest) as work:
        work.add(
            ReviewItem(
                kind=ReviewKind.POSSIBLE_DUPLICATE,
                record_table="track",
                record_id=7,
                other_record_id=other,
                reason="The two tracks have one name.",
            )
        )
    with refused(f"{CHECK}other_record_id_after_record_id"):
        write(newest, a_duplicate(other_record_id=other))

    assert held(newest) == []


@pytest.mark.parametrize("column", WITH_A_FIELD)
def test_a_possible_duplicate_names_no_field_no_source_and_nothing_a_source_says(
    newest: Engine, column: str
) -> None:
    a_source(newest)

    with refused(f"{CHECK}{column}_unless_possible_duplicate"):
        write(newest, a_duplicate(**{column: of_a_field()[column]}))

    assert held(newest) == []


@pytest.mark.parametrize("kind", OF_A_FIELD)
@pytest.mark.parametrize("column", WITH_A_FIELD)
def test_an_item_about_a_field_names_the_field_the_source_where_and_what_it_says(
    newest: Engine, kind: str, column: str
) -> None:
    a_source(newest)

    with refused(f"{CHECK}{column}_unless_possible_duplicate"):
        write(newest, of_a_field(kind, **{column: None}))

    assert held(newest) == []


@pytest.mark.parametrize("kind", OF_A_FIELD)
def test_an_item_about_a_field_names_no_other_record(newest: Engine, kind: str) -> None:
    source = a_source(newest)

    with (
        refused(f"{CHECK}other_record_id_when_possible_duplicate"),
        unit_of_work(newest) as work,
    ):
        work.add(
            ReviewItem(
                kind=ReviewKind(kind),
                record_table="track",
                record_id=7,
                other_record_id=12,
                field="length_in_metres",
                source_id=source,
                source_address=ADDRESS,
                source_value="1750",
                reason="The record says 1600.",
            )
        )
    with refused(f"{CHECK}other_record_id_when_possible_duplicate"):
        write(newest, of_a_field(kind, other_record_id=12))

    assert held(newest) == []


def test_the_source_of_an_item_is_one_that_exists(newest: Engine) -> None:
    source = a_source(newest)

    with refused(BROKEN_KEY), unit_of_work(newest) as work:
        work.add(
            ReviewItem(
                kind=ReviewKind.SOURCES_DISAGREE,
                record_table="track",
                record_id=7,
                field="length_in_metres",
                source_id=source + 1,
                source_address=ADDRESS,
                source_value="1750",
                reason="The record says 1600.",
            )
        )
    with refused(BROKEN_KEY):
        write(newest, of_a_field(source_id=source + 1))

    assert held(newest) == []


def test_a_source_that_an_item_names_cannot_be_deleted_and_one_that_none_names_can(
    newest: Engine,
) -> None:
    source = a_source(newest)
    other = a_source(newest, "Example Club")
    write(newest, of_a_field(source_id=source))

    with refused(BROKEN_KEY), unit_of_work(newest) as work:
        work.execute(delete(Source).where(Source.id == source))
    with refused(BROKEN_KEY), newest.begin() as connection:
        connection.exec_driver_sql("DELETE FROM source WHERE id = ?", (source,))
    with refused(BROKEN_KEY), newest.begin() as connection:
        connection.exec_driver_sql("UPDATE source SET id = 99 WHERE id = ?", (source,))
    with unit_of_work(newest) as work:
        work.execute(delete(Source).where(Source.id == other))

    with newest.connect() as connection:
        assert connection.exec_driver_sql("SELECT id FROM source").all() == [(source,)]
    assert held(newest) == [tuple(of_a_field(source_id=source).values())]


def test_sqlite_looks_for_the_items_of_a_source_by_the_index(newest: Engine) -> None:
    source = a_source(newest)
    write(newest, of_a_field(source_id=source))

    with newest.connect() as connection:
        plan = [
            str(step[3])
            for step in connection.exec_driver_sql(
                "EXPLAIN QUERY PLAN DELETE FROM source WHERE id = ?", (source,)
            )
        ]

    assert [step for step in plan if "review_item" in step] == [
        "SEARCH review_item USING COVERING INDEX ix_review_item_source_id (source_id=?)"
    ]
    # Nor is any other table that refers to a source read whole.
    assert [step for step in plan if step.startswith("SCAN")] == []


@pytest.mark.parametrize(
    "address",
    ["federation.example/tracks/7", "ftp://federation.example", "https://", "https://a b"],
    ids=["no beginning", "another beginning", "no site", "a space"],
)
def test_where_the_source_says_it_is_a_web_address(newest: Engine, address: str) -> None:
    a_source(newest)

    with refused(f"{CHECK}source_address_web_address"):
        write(newest, of_a_field(source_address=address))

    assert held(newest) == []


@pytest.mark.parametrize(
    ("state", "column", "given", "check"),
    [
        ("open", "decided_by", "Jo Example", "decided_by_when_decided"),
        ("open", "decided_at", DECIDED_AS_TEXT, "decided_at_when_decided"),
        ("accepted", "decided_by", None, "decided_by_when_decided"),
        ("accepted", "decided_at", None, "decided_at_when_decided"),
        ("rejected", "decided_by", None, "decided_by_when_decided"),
        ("rejected", "decided_at", None, "decided_at_when_decided"),
    ],
    ids=[
        "open, and somebody decided",
        "open, and decided at a moment",
        "accepted by nobody",
        "accepted at no moment",
        "rejected by nobody",
        "rejected at no moment",
    ],
)
def test_who_decided_and_when_go_with_a_decision_and_with_nothing_else(
    newest: Engine, state: str, column: str, given: str | None, check: str
) -> None:
    decision: dict[str, object] = {"state": state}
    if state != "open":
        decision.update(decided_by="Jo Example", decided_at=DECIDED_AS_TEXT)
    decision[column] = given

    with refused(f"{CHECK}{check}"):
        write(newest, a_duplicate(**decision))

    assert held(newest) == []


def test_a_decision_without_who_and_when_is_refused_through_the_model(newest: Engine) -> None:
    with refused(f"{CHECK}decided_by_when_decided"), unit_of_work(newest) as work:
        work.add(
            ReviewItem(
                kind=ReviewKind.POSSIBLE_DUPLICATE,
                record_table="track",
                record_id=7,
                other_record_id=12,
                reason="The two tracks have one name.",
                state=ReviewState.ACCEPTED,
            )
        )

    assert held(newest) == []


@pytest.mark.parametrize(
    ("column", "given", "why"),
    [
        ("record_id", "seven", "cannot store TEXT value in INTEGER column"),
        ("record_id", 7.5, "cannot store REAL value in INTEGER column"),
        ("other_record_id", "twelve", "cannot store TEXT value in INTEGER column"),
        ("source_id", "the first", "cannot store TEXT value in INTEGER column"),
        ("source_value", b"1750", "cannot store BLOB value in TEXT column"),
        ("reason", b"The record says 1600.", "cannot store BLOB value in TEXT column"),
    ],
    ids=[
        "a key in words",
        "a key with a fraction",
        "another record in words",
        "a source in words",
        "what a source says, as bytes",
        "a reason of bytes",
    ],
)
def test_the_table_is_strict(newest: Engine, column: str, given: object, why: str) -> None:
    a_source(newest)
    row = a_duplicate() if column == "other_record_id" else of_a_field()
    row[column] = given

    with refused(f"{why} review_item.{column}"):
        write(newest, row)

    assert held(newest) == []


@pytest.mark.parametrize(
    "said",
    ["", " 1750 ", "1750.0", "<script>alert(1)</script>", "'); DROP TABLE review_item; --"],
    ids=["empty text", "spaces around it", "a fraction", "markup", "a statement"],
)
def test_what_a_source_says_is_kept_as_the_text_it_was(newest: Engine, said: str) -> None:
    # It is what a source said, and nothing is done with it but to keep it:
    # empty text is kept too, because a source can say it of a field.
    source = a_source(newest)

    with unit_of_work(newest) as work:
        work.add(
            ReviewItem(
                kind=ReviewKind.VALUE_OUTSIDE_ITS_RULES,
                record_table="track",
                record_id=7,
                field="length_in_metres",
                source_id=source,
                source_address=ADDRESS,
                source_value=said,
                reason="A length is a whole number above nothing.",
            )
        )

    with unit_of_work(newest) as work:
        assert work.execute(select(ReviewItem.source_value)).scalar_one() == said
    with newest.connect() as connection:
        assert connection.exec_driver_sql("SELECT count(*) FROM review_item").scalar_one() == 1


def test_a_number_given_for_what_a_source_says_is_kept_as_its_text(newest: Engine) -> None:
    a_source(newest)
    write(newest, of_a_field(source_value=1750))

    with newest.connect() as connection:
        found = connection.exec_driver_sql(
            "SELECT source_value, typeof(source_value) FROM review_item"
        ).all()
    assert found == [("1750", "text")]


def test_the_table_does_not_hold_an_item_to_records_that_exist(newest: Engine) -> None:
    # A reference is to one table, and an item can be about a record of
    # any: the code that opens an item is what holds it to its records.
    row = a_duplicate(record_table="no such table", record_id=987654321, other_record_id=987654322)

    write(newest, row)

    assert held(newest) == [tuple(row.values())]


def test_the_table_holds_one_doubt_to_one_item(newest: Engine) -> None:
    # The same doubt a second time is refused, and the first item is as it
    # was. What the same doubt is has its tests in
    # test_review_item_one_doubt.py.
    write(newest, a_duplicate())

    with refused(
        "UNIQUE constraint failed: review_item.record_table, review_item.record_id, "
        "review_item.other_record_id"
    ):
        write(newest, a_duplicate())

    assert held(newest) == [tuple(a_duplicate().values())]


def test_the_table_keeps_a_decision(newest: Engine) -> None:
    # A decided item is neither put back to open nor deleted: the store
    # itself refuses it. The tests of that are in
    # test_review_item_decision_kept.py.
    accepted = a_duplicate(state="accepted", decided_by="Jo Example", decided_at=MOMENT)
    rejected = a_duplicate(
        record_id=8, state="rejected", decided_by="Jo Example", decided_at=MOMENT
    )
    write(newest, accepted)
    write(newest, rejected)

    with (
        refused("A decided review item (review_item) is never edited."),
        newest.begin() as connection,
    ):
        connection.exec_driver_sql(
            "UPDATE review_item SET state = 'open', decided_by = NULL, decided_at = NULL "
            "WHERE id = 1"
        )
    with (
        refused("A decided review item (review_item) is never deleted."),
        newest.begin() as connection,
    ):
        connection.exec_driver_sql("DELETE FROM review_item WHERE id = 2")

    assert held(newest) == [tuple(accepted.values()), tuple(rejected.values())]
