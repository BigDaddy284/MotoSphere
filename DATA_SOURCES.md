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
