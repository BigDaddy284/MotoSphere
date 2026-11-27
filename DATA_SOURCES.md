# Data sources

This document records discovered sources, their access methods, licences,
restrictions and collection status.

## Current state

No source is registered in the store yet. One source has been found, its
licence read, and its file taken into the repository: the list of the
countries, from the project iso-codes (DAT-012, below).

## How a source is described

A source is described by its kind and by the way it is collected from,
each from a list in the code (`motosphere.db.models.source`, DAT-039).
`DATABASE.md` ("The information sources") has both lists with what each
text means. The columns "Category" and "Collection method" of the
registry below hold those texts.

The store keeps every source in its table `source` (DAT-006,
`DATABASE.md`): its name, its website, the two texts above, how often it
is scanned, where its terms are, its licence, what its terms ask for or
forbid, and when a person last read them. A source is registered switched
off. It is switched on only after a person has read its terms, and the
store refuses a source that is switched on and does not say when they
were read. The registry below names the same sources for a reader.

What a source offers is one or more of nine kinds of information, from a
third list in the code (`InformationType`, DAT-040; `DATABASE.md` has it
with what each text means): `tracks`, `events`, `championships`,
`results`, `standings`, `riders`, `teams`, `news` and `reference data`.
The column "Information types" of the registry below holds those texts,
and the store keeps them in its table `source_offer`, a row for each kind
a source offers.

When a source was last scanned, when that last worked, what last went
wrong and how it is doing are not written down anywhere, here or in the
store: they are read from the record of its collection runs whenever
somebody asks (DAT-041; `DATABASE.md`, "How a source is doing"). A source
is `not yet scanned`, `healthy`, `failing` or `interrupted`. A
reliability score comes later, with the task that can tell one from
records that were checked (COL-009).

Three ways of collecting are permitted only on a condition (DESIGN.md
§7.2 and §14), and a source is registered with one of them only after the
condition was checked and written down in its row here:

- `html extraction`: the site's terms and its robots.txt permit it.
- `json endpoint`: the source authorises the use of the endpoint.
- `search engine discovery`: the search engine permits it.

A `social media page` is a source only where that network permits
collecting.

## Source registry

| Name | Website | Country | Category | Information types | Collection method | Licence / terms | Restrictions | Status |
|---|---|---|---|---|---|---|---|---|
| iso-codes | <https://salsa.debian.org/iso-codes-team/iso-codes> | – (of no one country) | `reference list` | `reference data` | `public dataset` | LGPL-2.1-or-later, © 2016 Dr. Tobias Quathamer; read in release 4.20.1 on 2026-11-27 | Every copy keeps the notice and comes with the licence; a changed copy says that it was changed and when; a work that takes over part of the list is passed on under the same licence | File in the repository, unchanged (DAT-012). Not in the store yet |

## The countries: iso-codes

**What it is.** iso-codes is a project of Debian that keeps the lists of
several ISO standards in one place, "rather than repeated in many
programs throughout the system" (its `README.md`). Its file
`data/iso_3166-1.json` is the list of ISO 3166-1, the international
standard for the names of countries: 249 entries, each with its code of
two letters, its code of three letters, its number and its name in
English.

**What MotoSphere takes.** That one file, unchanged, from release 4.20.1
of 2026-01-01, with the licence of the release beside it and a note that
says where both came from
(`backend/src/motosphere/reference/iso-codes/`). A test holds both files
to the release, byte for byte. MotoSphere reads the two codes of letters
and the name of each entry, and nothing else. Nothing is fetched while
the pipeline runs: a newer release is taken by a person, as the note
beside the files says.

**Its licence, as read.** The release says of its files `data/*json`, in
its `REUSE.toml`: copyright 2016 Dr. Tobias Quathamer, licence
`LGPL-2.1-or-later`, the GNU Lesser General Public License, version 2.1
or any later version. The text of the licence comes with the release and
is in the repository beside the file. It permits copying the file and
passing it on. It asks three things, which every task that passes the
list on has to keep:

- every copy keeps the notice of copyright and comes with the licence;
- a changed copy says that it was changed, and when;
- a work that takes over the list, or part of it, is passed on under the
  same licence, free of charge.

The file in the repository is an unchanged copy with its notice and its
licence, so the first is kept and the second does not arise. The third
matters once the countries are published with the site's data: the
published file then names iso-codes and this licence. That is for the
task that publishes them (PUB-003).

**How it was fetched.** The release as its makers published it,
`iso-codes_4.20.1.orig.tar.xz`, from the Ubuntu archive
(<https://archive.ubuntu.com/ubuntu/pool/main/i/iso-codes/>), once, on
2026-11-27. Its SHA-256 is the one the description of the source package
there names for it. The project's own server could not be reached from
where the planner works.

**What was checked.** The file is JSON with one list of 249 entries. No
two entries have one code of two letters, one code of three letters, one
number or one name. Every code of two letters is two capitals of the 26
letters, and every code of three is three. Every one of the 249 entries
has the same code of three letters and the same number as Unicode's
Common Locale Data Repository gives for its code of two letters
(`territoryCodes` in `common/supplemental/supplementalData.xml`, as it
stood on 2026-11-27): a second list, kept by other people, agrees with
all of it.

**The names are the standard's.** A name is the short name of the
standard in English, as iso-codes writes it. Most read as one expects
("New Zealand", "Türkiye"). Fifteen are written with a comma
("Korea, Republic of"), and some are not what a visitor would call the
place. iso-codes has a second, common name for eleven of them ("South
Korea"). MotoSphere stores the name as the source writes it. Which name
the site shows is decided where countries are first shown.

**What else was looked at.**

- **Unicode's Common Locale Data Repository** (Unicode License v3, read
  in its repository). Its list of regions is not the list of ISO 3166-1:
  it has 257 regions in ordinary use, the 249 of the standard and eight
  more (AC, CP, CQ, DG, EA, IC, TA, XK), and nothing in it says which are
  which. Its English names are its own. It is used here as the check
  above and for nothing else; nothing of it is in the repository.
- **ISO itself.** The page of the standard could not be read from where
  the planner works, so nothing is said here about its terms. The list
  is not taken from ISO.
- **Not looked into:** GeoNames (its server could not be reached), the
  United Nations' list of countries and areas, Wikidata and Natural
  Earth. None was needed once a source was found that has the list
  itself under a licence that allows passing it on.

**Its category.** The design describes a source by one of twelve kinds
(`SourceCategory`, DAT-039), each a kind of website of the sport: a
governing body, a championship, a track, a club and so on. A project
that keeps the lists of a standard is none of them, and it is not put
under one that does not fit. The list has a thirteenth kind for it,
`reference list`, which is this project's own (DAT-058; `DATABASE.md`,
"A kind of source that is not of the sport"). The source is registered
in the store with DAT-059.
