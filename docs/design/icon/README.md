# MotoSphere icon

The two designs of the MotoSphere icon. They are the source of every icon
file the application serves. Planning documents: only the planner changes
this folder.

| File | What it is | Used for |
|---|---|---|
| `motosphere-icon.svg` | The full design, approved by the owner on 2026-11-17 | 64 pixels and larger |
| `motosphere-icon-small.svg` | The small design, a reduction of the full one; shown to the owner at every size on 2026-11-17, who acknowledged it and asked for no change | Smaller than 64 pixels |

## The full design

A 1024 × 1024 drawing in the owner's Sky Classic style
(`../sky-classic-icon/`):

- A rounded charcoal tile, `#34363b` at the top to `#1e1f22` at the bottom,
  with a border of `#45484f`.
- One globe, drawn as an outline in the sky-blue gradient, `#3d8bff` to
  `#8cc4ff`, with a soft glow. The outer circle is the outline of the globe.
  It breaks at the top for the word MOTO and at the bottom for SPHERE, both
  curved along the circle.
- The lettering is Orbitron, weight 800 (SIL Open Font License), converted
  to outlines, so no font is needed to show it.
- The grid of the globe is one group at 45% opacity, so the crossings stay
  even.

The file is kept exactly as the owner approved it, including the
provenance record in its `metadata` element. Do not edit it by hand.

## The small design

Below about 64 pixels the lettering cannot be read and the fine grid turns
into a smudge, so small sizes use a reduction of the same drawing. Nothing is
added; parts are taken away and what remains is made bolder:

- The tile fills the whole square and has no border (at 16 pixels the margin
  and the border are less than half a pixel).
- The lettering is left out, and the two arcs of the outline are extended
  until they meet, giving a full circle.
- The grid keeps its two straight lines and one of its curved pairs. It is
  drawn at 70% opacity instead of 45%, because thin lines lose contrast when
  they are only a pixel wide.
- There is no glow: at this size it only blurs the outline.
- The same two gradients, with the same colours and the same direction.

The numbers are chosen for a 16 pixel grid (64 units to a pixel): the grid
lines are one pixel wide and the curved pair falls on whole pixels.

## Rules for changes

The owner's preferences, from the design rounds:

- Make a change by extending what is already there, not by adding new
  elements.
- Review every result yourself, at every size it is used, before showing it.

And for the files:

- Only the colours listed above. No script, no link, no embedded image and
  no outside address: the icon must be safe to open anywhere. The browser
  tests check this.
- The files the application serves are generated from these two designs and
  never edited by hand. After a design changes, run `npm run icons` in
  `frontend/` and commit the result.

## Generated files

`npm run icons` (in `frontend/`) writes these into `frontend/public/`:

| File | From | Content |
|---|---|---|
| `favicon.svg` | small design | A copy, byte for byte. Browser tabs. |
| `favicon.ico` | small design | 16, 32 and 48 pixel images, for software that cannot use the SVG. |
| `apple-touch-icon.png` | full design | 180 pixels, on a `#1e1f22` background, because phones show see-through corners as black. |

## Interface icons

Icons inside the application (buttons, markers, panels) follow the same
style when they are added: an outline glyph with round joins and round caps,
in the sky-blue gradient or the theme's accent colour, on the theme's
surfaces. They are drawn as SVG, hold no text and no outside reference, and
are tested the same way as the application icon.
