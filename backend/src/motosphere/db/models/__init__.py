"""The models: one class for each table of the data store.

Every model is named here, and so loading this package, or any module of
it, loads them all. ``SCHEMA`` is what they say together: every table the
store has. Whoever needs the whole schema takes it from here.
"""

from typing import Final

from sqlalchemy import MetaData

from motosphere.db.base import Base
from motosphere.db.models.collection_run import CollectionRun
from motosphere.db.models.country import Country
from motosphere.db.models.record_change import RecordChange
from motosphere.db.models.region import Region
from motosphere.db.models.review_item import ReviewItem
from motosphere.db.models.source import Source, SourceOffer

__all__ = [
    "SCHEMA",
    "CollectionRun",
    "Country",
    "RecordChange",
    "Region",
    "ReviewItem",
    "Source",
    "SourceOffer",
]

# Every table of the store, as the models say them. A test holds the
# migrations to it, and another proves that no model anywhere in the code
# is missing from it.
SCHEMA: Final[MetaData] = Base.metadata
