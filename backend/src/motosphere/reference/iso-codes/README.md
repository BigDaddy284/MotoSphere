# What was taken from iso-codes

The two other files of this folder are from the project **iso-codes**,
which keeps the lists of several ISO standards in one place
(<https://salsa.debian.org/iso-codes-team/iso-codes>). Both are
**unchanged**: each is, byte for byte, the file of release **4.20.1** of
2026-01-01.

| File here | File of the release | SHA-256 |
|---|---|---|
| `iso_3166-1.json` | `data/iso_3166-1.json` | `f01b812b57fba9f31ff621bf33e7c7570a01964dbeb5be2167e94decf538c89f` |
| `LGPL-2.1-or-later.txt` | `LICENSES/LGPL-2.1-or-later.txt` | `5749785c8bdefafcb5d798270ed0a967036fe2ca63dcedade1627565dfef81d2` |

`iso_3166-1.json` is the list of the countries of ISO 3166-1: 249
entries, each with its code of two letters, its code of three letters, its
number and its name in English, and some with an official name, a common
name and a flag.

## Licence

The release says of its files `data/*json` (in its `REUSE.toml`):

    SPDX-FileCopyrightText = "2016 Dr. Tobias Quathamer <toddy@debian.org>"
    SPDX-License-Identifier = "LGPL-2.1-or-later"

That is the GNU Lesser General Public License, version 2.1 or, at the
choice of whoever passes the file on, any later version. Its text is
`LGPL-2.1-or-later.txt`, beside this file. It permits copying and passing
on the file. It asks that every copy keeps this notice and comes with
the licence, and that a changed copy says that it was changed and when.

## Where the files were fetched from

The release as its makers published it, `iso-codes_4.20.1.orig.tar.xz`
(4 702 640 bytes, SHA-256
`5d551f3ddb32548c4321e9011720fd97751af0107592f79ebffc939bd32f2268`),
fetched on 2026-11-27 from the Ubuntu archive
(<https://archive.ubuntu.com/ubuntu/pool/main/i/iso-codes/>). The
description of the source package there (`iso-codes_4.20.1-1.dsc`) names
that same SHA-256 for it.

## Taking a newer release

Replace both files with those of the newer release, unchanged; write the
release, its date and the new SHA-256 values here; and change the two
values in `backend/tests/unit/test_reference_countries.py`, where the
number of the countries is held too. Write the release, its day and its
address in `backend/src/motosphere/reference/countries_load.py` as well:
they are what the rows of the store say of where they came from. Nothing
in this folder is edited by hand.

A store that was loaded from the older file keeps its rows. The loading
adds the countries that are new, and names those the newer file says
something else of. What the newer file says of them is put to the review
queue; no country is changed without a person's decision.
