"""Tests of the country a source is of, as the model says it. They need no store."""

from graphlib import TopologicalSorter

from sqlalchemy import ForeignKeyConstraint, Integer

from motosphere.db.base import broken_rules
from motosphere.db.models import SCHEMA, Source
from motosphere.db.models.provenance_rule import NOT_COLLECTED, broken_provenance

# The table as the whole schema has it, and the column.
TABLE = SCHEMA.tables["source"]
COLUMN = TABLE.columns["country_id"]


def test_the_column_is_the_last_thing_a_source_says_of_itself() -> None:
    assert Source.__table__ is TABLE
    assert [column.name for column in TABLE.columns][-4:] == [
        "switched_on",
        "country_id",
        "created_at",
        "updated_at",
    ]


def test_a_source_may_be_of_no_country_and_the_model_gives_it_none() -> None:
    assert isinstance(COLUMN.type, Integer)
    assert COLUMN.nullable is True
    assert COLUMN.default is None
    assert COLUMN.server_default is None
    assert Source(name="Example Federation").country_id is None


def test_the_column_points_to_the_key_of_a_country_and_nothing_is_done_when_that_goes() -> None:
    keys = [one for one in TABLE.constraints if isinstance(one, ForeignKeyConstraint)]

    assert [
        (str(key.name), key.column_keys, [part.target_fullname for part in key.elements])
        for key in keys
    ] == [("fk_source_country_id_country", ["country_id"], ["country.id"])]
    assert [(key.ondelete, key.onupdate) for key in keys] == [(None, None)]


def test_the_table_has_this_one_index_and_it_lets_two_sources_be_of_one_country() -> None:
    assert [
        (str(index.name), [column.name for column in index.columns], bool(index.unique))
        for index in TABLE.indexes
    ] == [("ix_source_country_id", ["country_id"], False)]


def test_only_the_sources_and_the_countries_point_to_each_other() -> None:
    points_to = {
        table.name: {key.column.table.name for key in table.foreign_keys} - {table.name}
        for table in SCHEMA.tables.values()
    }
    each_other = sorted(
        (one, other)
        for one, others in points_to.items()
        for other in others
        if one < other and one in points_to[other]
    )

    assert each_other == [("country", "source")]
    # Without that one pointer the tables can be put in an order in which
    # each comes after those it points to: nothing else goes round.
    points_to["source"] = points_to["source"] - {"country"}
    in_order = list(TopologicalSorter(points_to).static_order())
    assert sorted(in_order) == sorted(SCHEMA.tables)
    assert in_order.index("source") < in_order.index("country")


def test_the_schema_with_the_column_keeps_every_rule() -> None:
    assert broken_rules(SCHEMA) == []
    assert broken_provenance(SCHEMA, NOT_COLLECTED) == []
    assert "source" in NOT_COLLECTED
