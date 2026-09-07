# Vendored 3DHOP viewer -- provenance

This folder is a trimmed copy of the `minimal/` package from
[`cnr-isti-vclab/3DHOP`](https://github.com/cnr-isti-vclab/3DHOP), pinned at
tag `4.3` (commit `a8c145ddc575df5291e073a377d942ff77c34901`, 2020-06-18).
Vendored 2026-09-07 (PRIMER.md S6) -- offline per this repo's own rule that
network access stays confined to the `fetch` step (PRIMER.md A3); `bundle`
copies this folder into every `dist/<slug>.zip` as-is.

**Licence: GNU GPLv3** (`LICENSE.txt` in this folder, copied verbatim from
upstream). It ships inside every `dist/<slug>.zip` this repo produces
(`viewer/LICENSE.txt`) -- not optional, GPLv3 requires the licence to
travel with the distributed code.

## What was trimmed and why

Upstream's own `minimal/` folder is ~9.8 MB, almost all of it their demo
model (`models/gargo.nxz`, 7.1 MB) and five toolbar skin themes we don't
need. This folder keeps only what `3DHOP_no_tools.html` (renamed
`index.html` here) actually loads, ~970 KB total:

- **`index.html`**: upstream's `minimal/3DHOP_no_tools.html`, unchanged
  except one line -- the mesh URL points at `../data/model/model.nxz`
  (this package's own model, at the fixed path `bundle` always writes it
  to) instead of upstream's `models/gargo.nxz`. Chosen over
  `3DHOP_all_tools.html` deliberately: this is a presentation viewer
  shipped inside a citable data package, not an editing workbench --
  measurement/section tools aren't needed and only add surface area.
- **`js/`**: exactly the 10 scripts `index.html`'s `<script>` tags load
  (`spidergl`, `jquery`, `presenter`, `nexus`, `ply`, the four
  `trackball_*` variants actually instantiated or switchable, `init`),
  plus `corto.js`/`corto.em.js` -- `nexus.js` loads these as a Web Worker
  at runtime (`path.replace('nexus.js', 'corto.em.js')`, not a `<script>`
  tag) whenever a mesh node is corto-compressed, which is the codec
  `nxscompress` (this repo's own `nexus` step, S4) is expected to use.
  `meco.js` (the older, corto-predecessor codec, same lazy-Worker
  mechanism) is kept too even though S4 has never produced a meco-flagged
  `.nxz` in this project so far -- 26 KB is cheap insurance against an
  untested nxsbuild/nxscompress version doing so, versus a broken viewer
  if it's missing. `ply.js` is *not* actually needed (we only ship
  `.nxz`, never raw `.ply`) but stays since `index.html` loads it
  unconditionally and dropping it means also editing the html, for 29 KB.
- **`skins/`**: only the 7 dark-toolbar icons `index.html` actually
  references by `src` (`home`, `zoomin`, `zoomout`, `lightcontrol`,
  `lightcontrol_on`, `full`, `full_on`) and the one `backgrounds/light.jpg`
  it sets via inline style -- not the other five skin themes (`light`,
  `minimal_dark`, `minimal_light`, `transparent_dark`, `transparent_light`)
  or the icons only `3DHOP_all_tools.html` uses (measure/sections/pick/
  pin/color/normals/orthographic/...). **Korrigiert 2026-09-07 (Nachtrag,
  echter Lauf bei Flo):** the two light-control icons were first vendored
  under the wrong filenames -- `index.html`'s `id="light"`/`id="light_on"`
  attributes read as if the files were `light.png`/`light_on.png`, but the
  actual `src` values (and the files 3DHOP ships) are
  `lightcontrol.png`/`lightcontrol_on.png` -- a *different* icon pair in
  the same folder (`light.png`/`light_on.png`/`light_off.png` exist too,
  for an unrelated purpose upstream). Fixed by vendoring the two correct
  files instead.
- **`stylesheet/`**: `3dhop.css` only, not `3dhop_panels.css` (that's for
  `3DHOP_all_tools.html`'s tool panels).

Not trimmed further on purpose: `jquery.js` (88 KB) and `spidergl.js`
(186 KB) are the two biggest files kept, both hard dependencies of
`presenter.js`/`nexus.js` with no smaller drop-in replacement upstream
ships -- shrinking further would mean patching 3DHOP's own JS, which this
repo's A3 rule (copied code keeps its guards, i.e. stays recognisably
upstream) argues against.

## Updating this vendored copy

By hand, same pattern as `schemas/md_cff/MD.cff-schema.yaml`: re-clone
`cnr-isti-vclab/3DHOP` at the tag/commit to pin, redo the trim above
against the new `minimal/3DHOP_no_tools.html`, redo the one-line mesh URL
edit, update the pin note at the top of this file. Not automated, not
live-fetched at `bundle` time -- see PRIMER.md A3.
