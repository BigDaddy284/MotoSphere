"""Tests that the models and the migrations describe the same store, with real SQLite files.

The first test holds the real models to the real migrations. The others
prove that the comparison can fail: two models of the tests' own, kept in
a schema of their own (``Proof.metadata``), and migrations written by hand
that build the same tables or differ from them in one way.
"""

from pathlib import Path

import pytest
from sqlalchemy import (
    CheckConstraint,
    Connection,
    Engine,
    ForeignKey,
    Index,
    MetaData,
    UniqueConstraint,
)
from sqlalchemy.dialects import sqlite
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import CreateIndex, CreateTable

from motosphere.db.base import Base
from motosphere.db.compare import differences
from motosphere.db.migrations import Migration, migrate
from motosphere.db.models import SCHEMA
from motosphere.db.store import open_store
from motosphere.db.texts import NotEmpty


class Proof(Base):
    """Models of the tests' own, in a schema apart from the real one."""

    __abstract__ = True
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)


class ProofMaker(Proof):
    __tablename__ = "maker"

    name: Mapped[NotEmpty] = mapped_column(unique=True)


class ProofBike(Proof):
    __tablename__ = "bike"
    __table_args__ = (
        UniqueConstraint("maker_id", "number"),
        CheckConstraint("number > 0", name="number_positive"),
        CheckConstraint("model != 'Not Known'", name="model_known"),
        Index(None, "model", "weight"),
    )

    maker_id: Mapped[int] = mapped_column(ForeignKey("maker.id"))
    number: Mapped[int]
    model: Mapped[str] = mapped_column(index=True)
    weight: Mapped[float | None]
    # A name that is a word of SQL.
    group: Mapped[str | None]


NOT_EMPTY = (
    "trim(name, char(9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760, 8192, 8193, 8194, "
    "8195, 8196, 8197, 8198, 8199, 8200, 8201, 8202, 8232, 8233, 8239, 8287, 12288)) != ''"
)
# The statements of a migration written by hand that builds what the two models say.
MAKER = f"""
    CREATE TABLE maker (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        CONSTRAINT uq_maker_name UNIQUE (name),
        CONSTRAINT ck_maker_name_not_empty CHECK ({NOT_EMPTY})
    ) STRICT
"""
BIKE = """
    CREATE TABLE bike (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        maker_id INTEGER NOT NULL,
        number INTEGER NOT NULL,
        model TEXT NOT NULL,
        weight REAL,
        "group" TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        CONSTRAINT uq_bike_maker_id_number UNIQUE (maker_id, number),
        CONSTRAINT ck_bike_number_positive CHECK (number > 0),
        CONSTRAINT ck_bike_model_known CHECK (model != 'Not Known'),
        CONSTRAINT fk_bike_maker_id_maker FOREIGN KEY(maker_id)
            REFERENCES maker (id)
    ) STRICT
"""
BY_MODEL = "CREATE INDEX ix_bike_model ON bike (model)"
BY_MODEL_AND_WEIGHT = "CREATE INDEX ix_bike_model_weight ON bike (model, weight)"
AS_THE_MODELS = [MAKER, BIKE, BY_MODEL, BY_MODEL_AND_WEIGHT]

NOT_THE_SAME = (
    "The {} is not the same in both. Where they first differ, "
    "the models say `{}` and the migrations say `{}`."
)


def running(*statements: str) -> Migration:
    """A migration that runs the statements, in order."""

    def migration(connection: Connection) -> None:
        for statement in statements:
            connection.exec_driver_sql(statement)

    return migration


@pytest.fixture
def models(tmp_path: Path) -> Engine:
    """A second store of the test's own, with the tables of the two models made in it."""
    engine = open_store(tmp_path / "models.sqlite3")
    with engine.begin() as connection:
        Proof.metadata.create_all(connection)
    return engine


def test_the_models_and_the_migrations_agree(store: Engine, tmp_path: Path) -> None:
    from_the_models = open_store(tmp_path / "models.sqlite3")
    with from_the_models.begin() as connection:
        SCHEMA.create_all(connection)
    migrate(store)

    found = differences(models=from_the_models, migrated=store)

    assert not found, "\n".join(found)


def test_a_migration_written_by_hand_builds_what_the_models_say(
    store: Engine, models: Engine
) -> None:
    migrate(store, [running(*AS_THE_MODELS)])

    assert differences(models=models, migrated=store) == []


def test_the_statements_sqlalchemy_writes_for_the_models_build_the_same_as_text(
    store: Engine, models: Engine
) -> None:
    tables = Proof.metadata.sorted_tables
    as_text = [
        *(str(CreateTable(table).compile(dialect=sqlite.dialect())) for table in tables),
        *(
            str(CreateIndex(index).compile(dialect=sqlite.dialect()))
            for table in tables
            for index in sorted(table.indexes, key=lambda index: str(index.name))
        ),
    ]
    assert len(as_text) == 4

    migrate(store, [running(*as_text)])

    assert differences(models=models, migrated=store) == []


@pytest.mark.parametrize(
    "maker",
    [
        " ".join(MAKER.split()).replace("( ", "(").replace(" )", ")").replace(", ", ","),
        MAKER.replace("    ", "\t").replace("\n", "\r\n"),
        MAKER.lower(),
        MAKER.replace("maker (", '"maker" (').replace(" name", ' "name"'),
        MAKER.replace(" name", " `name`").replace("(name", "([name]"),
        MAKER.replace("        name ", '        "NAME" '),
        MAKER.replace("NOT NULL,", "NOT NULL, -- it must be there,\n", 1),
        MAKER.replace("UNIQUE (name)", "UNIQUE /* no two,\n (alike */ (name) /* at all */"),
    ],
    ids=[
        "on one line, with no more spaces than needed",
        "with tabs and the line ends of Windows",
        "in small letters",
        "with names in double quotes",
        "with names in quotes of the other two kinds",
        "with a name in other letters, large for small",
        "with a comment to the end of a line",
        "with two comments between words, one over two lines",
    ],
)
def test_how_a_statement_is_written_makes_no_difference(
    store: Engine, models: Engine, maker: str
) -> None:
    assert maker != MAKER

    migrate(store, [running(maker, BIKE, BY_MODEL, BY_MODEL_AND_WEIGHT)])

    assert differences(models=models, migrated=store) == []


def test_a_table_that_was_given_its_name_later_is_the_same_table(
    store: Engine, models: Engine
) -> None:
    # SQLite then keeps the statement with the name in quotes.
    made_under_another_name = MAKER.replace("TABLE maker", "TABLE builder")
    migrate(
        store,
        [
            running(made_under_another_name),
            running("ALTER TABLE builder RENAME TO maker"),
            running(BIKE, BY_MODEL, BY_MODEL_AND_WEIGHT),
        ],
    )

    with store.connect() as connection:
        kept = connection.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE name = 'maker'"
        ).scalar_one()
    assert str(kept).split("(")[0].split() == ["CREATE", "TABLE", '"maker"']
    assert differences(models=models, migrated=store) == []


@pytest.mark.parametrize(
    ("one", "other", "found"),
    [
        (
            "CREATE VIEW said AS SELECT 'a''b'",
            "CREATE VIEW said AS SELECT 'a' 'b'",
            NOT_THE_SAME.format(
                "view said",
                "create view said as select 'a''b'",
                "create view said as select 'a' 'b'",
            ),
        ),
        (
            'CREATE TABLE said ("a""b" TEXT)',
            'CREATE TABLE said ("a" "b" TEXT)',
            NOT_THE_SAME.format("table said", 'a""b text )', "a b text )"),
        ),
        (
            "CREATE TABLE said (`a``b` TEXT)",
            "CREATE TABLE said (`a` `b` TEXT)",
            NOT_THE_SAME.format("table said", "a``b text )", "a b text )"),
        ),
    ],
    ids=["in text", "in a name in double quotes", "in a name in the quotes that lean back"],
)
def test_a_quote_written_twice_inside_quotes_does_not_end_them(
    store: Engine, tmp_path: Path, one: str, other: str, found: str
) -> None:
    # SQLite takes both: the first is one text or one name with a quote in it,
    # the second two that stand side by side.
    with_one = open_store(tmp_path / "models.sqlite3")
    with with_one.begin() as connection:
        connection.exec_driver_sql(one)
    migrate(store, [running(other)])

    assert differences(models=with_one, migrated=store) == [found]


MAKER_TABLE = "table maker"
BIKE_TABLE = "table bike"


@pytest.mark.parametrize(
    ("statements", "found"),
    [
        (
            [*AS_THE_MODELS, "CREATE TABLE more (id INTEGER)"],
            ["Only the migrations have the table more."],
        ),
        (
            [MAKER],
            [
                "Only the models have the index ix_bike_model.",
                "Only the models have the index ix_bike_model_weight.",
                "Only the models have the table bike.",
            ],
        ),
        (
            [],
            [
                "Only the models have the index ix_bike_model.",
                "Only the models have the index ix_bike_model_weight.",
                "Only the models have the table bike.",
                "Only the models have the table maker.",
            ],
        ),
        (
            [MAKER, BIKE, BY_MODEL],
            ["Only the models have the index ix_bike_model_weight."],
        ),
        (
            [*AS_THE_MODELS, "CREATE INDEX ix_bike_number ON bike (number)"],
            ["Only the migrations have the index ix_bike_number."],
        ),
        (
            [*AS_THE_MODELS, "CREATE VIEW names AS SELECT name FROM maker"],
            ["Only the migrations have the view names."],
        ),
        (
            [*AS_THE_MODELS, "CREATE TRIGGER told AFTER INSERT ON maker BEGIN SELECT 1; END"],
            ["Only the migrations have the trigger told."],
        ),
        (
            ["CREATE VIEW maker AS SELECT 1 AS id", BIKE, BY_MODEL, BY_MODEL_AND_WEIGHT],
            ["Only the models have the table maker.", "Only the migrations have the view maker."],
        ),
        (
            [*AS_THE_MODELS, "CREATE TABLE sqlites (id INTEGER)"],
            ["Only the migrations have the table sqlites."],
        ),
    ],
    ids=[
        "a table only the migrations have",
        "a table only the models have, with its indexes",
        "all the models have, where the migrations build nothing",
        "an index only the models have",
        "an index only the migrations have",
        "a view only the migrations have",
        "a trigger only the migrations have",
        "a view where the models have a table",
        "a table whose name only begins like those SQLite keeps for itself",
    ],
)
def test_what_only_one_of_the_two_has_is_named(
    store: Engine, models: Engine, statements: list[str], found: list[str]
) -> None:
    migrate(store, [running(*statements)])

    assert differences(models=models, migrated=store) == found


@pytest.mark.parametrize(
    ("old", "new", "found"),
    [
        (
            "weight REAL,",
            "weight REAL, colour TEXT,",
            NOT_THE_SAME.format(
                BIKE_TABLE, "group text , created_at text not ...", "colour text , group text , ..."
            ),
        ),
        (
            '"group" TEXT,',
            "",
            NOT_THE_SAME.format(
                BIKE_TABLE,
                "group text , created_at text not ...",
                "created_at text not null , updated_at ...",
            ),
        ),
        (
            "number INTEGER NOT NULL,",
            "number REAL NOT NULL,",
            NOT_THE_SAME.format(
                BIKE_TABLE,
                "number integer not null , model text ...",
                "number real not null , model text ...",
            ),
        ),
        (
            "model TEXT NOT NULL,",
            "model TEXT,",
            NOT_THE_SAME.format(
                BIKE_TABLE,
                "model text not null , weight real , ...",
                "model text , weight real , group text ...",
            ),
        ),
        (
            "weight REAL,",
            "weight REAL NOT NULL,",
            NOT_THE_SAME.format(
                BIKE_TABLE,
                "weight real , group text , created_at text ...",
                "weight real not null , group text , ...",
            ),
        ),
        (
            "weight REAL,",
            "weight REAL DEFAULT 0,",
            NOT_THE_SAME.format(
                BIKE_TABLE,
                "weight real , group text , created_at text ...",
                "weight real default 0 , group text , ...",
            ),
        ),
        (
            "PRIMARY KEY AUTOINCREMENT,",
            "PRIMARY KEY,",
            NOT_THE_SAME.format(
                BIKE_TABLE,
                "id integer not null primary key autoincrement , maker_id integer not null ...",
                "id integer not null primary key , maker_id integer not null , ...",
            ),
        ),
        (
            "number INTEGER NOT NULL,\n        model TEXT NOT NULL,",
            "model TEXT NOT NULL,\n        number INTEGER NOT NULL,",
            NOT_THE_SAME.format(
                BIKE_TABLE,
                "number integer not null , model ...",
                "model text not null , number ...",
            ),
        ),
        (
            "CONSTRAINT uq_bike_maker_id_number UNIQUE (maker_id, number),",
            "",
            NOT_THE_SAME.format(
                BIKE_TABLE,
                "constraint uq_bike_maker_id_number unique ( maker_id , number ...",
                "constraint ck_bike_number_positive check ( number > 0 ...",
            ),
        ),
        (
            "UNIQUE (maker_id, number)",
            "UNIQUE (number, maker_id)",
            NOT_THE_SAME.format(
                BIKE_TABLE,
                "maker_id , number ) , constraint ...",
                "number , maker_id ) , constraint ...",
            ),
        ),
        (
            "CONSTRAINT uq_bike_maker_id_number UNIQUE",
            "CONSTRAINT uq_bike_number UNIQUE",
            NOT_THE_SAME.format(
                BIKE_TABLE,
                "constraint uq_bike_maker_id_number unique ( maker_id , number ...",
                "constraint uq_bike_number unique ( maker_id , number ...",
            ),
        ),
        (
            "CHECK (number > 0)",
            "CHECK (number >= 0)",
            NOT_THE_SAME.format(
                BIKE_TABLE,
                "number > 0 ) , constraint ck_bike_model_known ...",
                "number >= 0 ) , constraint ck_bike_model_known ...",
            ),
        ),
        (
            "'Not Known'",
            "'not known'",
            NOT_THE_SAME.format(
                BIKE_TABLE,
                "model != 'Not Known' ) , constraint fk_bike_maker_id_maker foreign ...",
                "model != 'not known' ) , constraint fk_bike_maker_id_maker foreign ...",
            ),
        ),
        (
            "'Not Known'",
            "'Not  Known'",
            NOT_THE_SAME.format(
                BIKE_TABLE,
                "model != 'Not Known' ) , constraint fk_bike_maker_id_maker foreign ...",
                "model != 'Not  Known' ) , constraint fk_bike_maker_id_maker foreign ...",
            ),
        ),
        (
            "REFERENCES maker (id)",
            "REFERENCES maker (id) ON DELETE CASCADE ON UPDATE CASCADE",
            NOT_THE_SAME.format(
                BIKE_TABLE, "id ) ) strict", "id ) on delete cascade on update cascade ..."
            ),
        ),
        (
            ",\n        CONSTRAINT fk_bike_maker_id_maker FOREIGN KEY(maker_id)\n"
            "            REFERENCES maker (id)",
            "",
            NOT_THE_SAME.format(
                BIKE_TABLE,
                "model != 'Not Known' ) , constraint fk_bike_maker_id_maker foreign key ( ...",
                "model != 'Not Known' ) ) strict",
            ),
        ),
        (
            ") STRICT",
            ")",
            NOT_THE_SAME.format(BIKE_TABLE, "id ) ) strict", "id ) )"),
        ),
        (
            "CREATE INDEX ix_bike_model ON bike (model)",
            "CREATE UNIQUE INDEX ix_bike_model ON bike (model)",
            NOT_THE_SAME.format(
                "index ix_bike_model",
                "create index ix_bike_model on bike ( model ...",
                "create unique index ix_bike_model on bike ( ...",
            ),
        ),
        (
            "ON bike (model, weight)",
            "ON bike (weight, model)",
            NOT_THE_SAME.format(
                "index ix_bike_model_weight", "model , weight )", "weight , model )"
            ),
        ),
        (
            "ON bike (model, weight)",
            "ON bike (model, weight) WHERE weight BETWEEN 1 AND 2",
            NOT_THE_SAME.format(
                "index ix_bike_model_weight",
                "weight )",
                "weight ) where weight between 1 and 2",
            ),
        ),
    ],
    ids=[
        "a column only the migrations have",
        "a column only the models have",
        "a column of another type",
        "a column that may be without a value in the migrations only",
        "a column that may be without a value in the models only",
        "a column with a value of its own in the migrations",
        "a key that may be given twice",
        "two columns the other way round",
        "a constraint only the models have",
        "a constraint over the same columns the other way round",
        "a constraint of another name",
        "a check that says something else",
        "text in single quotes in other letters, small for large",
        "text in single quotes with another space",
        "a foreign key that does more",
        "a foreign key only the models have",
        "a table that is not strict",
        "an index that lets no two rows be alike",
        "an index over the same columns the other way round",
        "an index over some rows only",
    ],
)
def test_a_table_or_an_index_that_differs_is_named_with_the_place(
    store: Engine, models: Engine, old: str, new: str, found: str
) -> None:
    as_the_models = "\n;\n".join([BIKE, BY_MODEL, BY_MODEL_AND_WEIGHT])
    assert as_the_models.count(old) == 1

    migrate(store, [running(MAKER, *as_the_models.replace(old, new).split("\n;\n"))])

    assert differences(models=models, migrated=store) == [found]


def test_a_column_added_to_a_table_later_does_not_stand_where_the_models_have_it(
    store: Engine, models: Engine
) -> None:
    without_the_weight = BIKE.replace("weight REAL,", "")
    assert without_the_weight != BIKE

    migrate(
        store,
        [
            running(MAKER, without_the_weight, BY_MODEL),
            running("ALTER TABLE bike ADD COLUMN weight REAL", BY_MODEL_AND_WEIGHT),
        ],
    )

    assert differences(models=models, migrated=store) == [
        NOT_THE_SAME.format(
            BIKE_TABLE, "weight real , group text , ...", "group text , created_at text not ..."
        )
    ]


def test_the_differences_come_kind_by_kind_and_name_by_name(store: Engine, models: Engine) -> None:
    migrate(
        store,
        [
            running(
                MAKER.replace(") STRICT", ")"),
                "CREATE TABLE also (id INTEGER)",
                "CREATE INDEX ix_also_id ON also (id)",
            )
        ],
    )

    assert differences(models=models, migrated=store) == [
        "Only the migrations have the index ix_also_id.",
        "Only the models have the index ix_bike_model.",
        "Only the models have the index ix_bike_model_weight.",
        "Only the migrations have the table also.",
        "Only the models have the table bike.",
        NOT_THE_SAME.format(MAKER_TABLE, "12288 ) ) != '' ) ) strict", "12288 ) ) != '' ) )"),
    ]


def test_the_tables_sqlite_keeps_for_itself_are_not_compared(store: Engine, models: Engine) -> None:
    migrate(store, [running(*AS_THE_MODELS)])
    with store.begin() as connection:
        connection.exec_driver_sql("ANALYZE")

    with store.connect() as connection, models.connect() as other:
        kept = "SELECT count(*) FROM sqlite_master WHERE name LIKE 'sqlite~_stat%' ESCAPE '~'"
        assert connection.exec_driver_sql(kept).scalar_one() > 0
        assert other.exec_driver_sql(kept).scalar_one() == 0
    assert differences(models=models, migrated=store) == []


def test_comparing_writes_to_neither_store(store: Engine, models: Engine) -> None:
    migrate(store, [running(MAKER)])
    files = [Path(str(engine.url.database)) for engine in (models, store)]
    before = [file.read_bytes() for file in files]

    assert len(differences(models=models, migrated=store)) == 3

    assert [file.read_bytes() for file in files] == before
