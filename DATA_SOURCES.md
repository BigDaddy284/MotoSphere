# Data sources

This document records discovered sources, their access methods, licences,
restrictions and collection status.

## Current state

No sources have been registered yet.

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
