"""How far a collected record can be trusted: the two lists that say it.

Everything MotoSphere collects keeps with it where it came from and how
far it can be trusted (DESIGN.md 8). Two different questions are asked of
a record, and each has a list of its own:

- how sure it is that the record says what its source says. That is its
  confidence, :class:`Confidence`, and it is about the reading: a value
  taken from a field made for it is surer than one worked out from a
  sentence;
- what standing the source's word has. That is its verification status,
  :class:`VerificationStatus`, and it is about the publishing: what the
  organiser of a race published about it is official, whoever read it
  and however surely.

Neither answers the other. A result read without doubt from a fan's
website is of high confidence and independent; a date worked out from an
official notice is official and of low confidence.

Each list is said once, here. Its values are the texts that are stored,
and a column of the list (:class:`motosphere.db.lists.OneOf`) refuses
every other text. The texts are in small letters, with one space between
two words. Both lists go from what can be trusted most to what can be
trusted least. No table has a column of them yet: they come with the
columns every collected record has (DAT-008). Once a table has one, a
text of that list is changed or taken away only by a migration, because
the table's check names the texts and rows hold them.
"""

from enum import StrEnum

__all__ = ["Confidence", "VerificationStatus"]


class Confidence(StrEnum):
    """How sure it is that a record says what its source says (DESIGN.md 8)."""

    # The source gives the value in a place made for it, such as a field of
    # a feed or a cell under its heading, and it was taken as it stands.
    HIGH = "high"
    # The value was read out of a page or a document made for people, by a
    # rule written for that source. It is wrong where the page is not as
    # the rule expects it.
    MEDIUM = "medium"
    # The value was worked out from what stands around it, or the source is
    # unclear about it or says two things.
    LOW = "low"


class VerificationStatus(StrEnum):
    """What standing the word of a record's source has (DESIGN.md 6, in its order)."""

    # Published by whoever is answerable for what the record says: the body
    # that ran the race or the championship, or the track about itself.
    OFFICIAL = "official"
    # Published by somebody else, such as a news publication, a results
    # database or a community website.
    INDEPENDENT = "independent"
    # Put together afterwards from what is left, where nothing published at
    # the time is at hand. It is never shown as an official record.
    RECONSTRUCTED = "reconstructed"
    # A mention that has not been checked against anything.
    UNVERIFIED = "unverified"
