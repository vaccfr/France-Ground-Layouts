# AVISO converter

Double-click **Convert AVISO.cmd** on Windows. Select local source (Enter/1) or
the original official GitHub source (2). Python 3.10+ is required.

For unattended conversion:

```powershell
python Script/aviso_converter.py --local
python Script/aviso_converter.py --github
python Script/aviso_converter.py --source "path/to/folder-or.zip"
```

No arguments means local source; it never contacts GitHub. Explicit GitHub
selection downloads vaccfr/France-Ground-Layouts master and reports network
errors without silently using another source. Local input accepts a checkout,
an extracted outer repository folder, or a ZIP with GNG/, KMZ/ and Colours.sct.
The root source is preferred, then equivalent inputs under Input/.

GeoJSON/ is generated output. All products are validated before writing files.
An explicit source selection overwrites the existing GeoJSON output; official
source may contain different airports and geometry from a customized checkout.
No reports, summaries or cached downloads are generated.

Settings/ is the only place for editable vSMR customization: palettes,
backgrounds, groups, zoom levels and runway settings. Settings/Colours.sct
contains palette additions/overrides; the pack's root Colours.sct stays intact.
Colors in Settings take precedence over the selected pack's native definitions.

## Official sources are read-only

GNG/, KMZ/ and root Colours.sct are based on the official pack at
[vaccfr commit 134b865](https://github.com/vaccfr/France-Ground-Layouts/commit/134b8659885665721f415e1e2bf482f54bf10840).
Native files remain unchanged, including KMZ imagery, folder structure and
coordinate formatting. Update them only from the official pack.

LFPO Settings omit the obsolete background rectangle using
`metadata.exclude_features` and set the Real background to #6C6A68. This is
an output-only setting: it never rewrites GNG or KMZ. The converter also works
if that rectangle is later removed from the official sources.

The converter reads geometry from KMZ and labels from GNG. Airports without
KMZ geometry use their GNG geometry. GNG geometry is ignored when KMZ supplies
it, and KMZ point placemarks are ignored, so the two representations do not
duplicate features in GeoJSON. Both original formats remain stored unchanged.
Only airports present in the selected pack generate output.

Missing or duplicate feature IDs receive deterministic output IDs without
writing them back. LFPG arrow groups use KMZ folder selectors in Settings/LFPG.json.
Conversion writes only GeoJSON; source/settings directories are rejected as
output destinations. All changes to appearance belong in Settings/.

## Verification

```powershell
python Script/verify_converter.py
python Script/verify_upstream.py
```

The full regression check compares regenerated output with GeoJSON/, verifies
native geometry/text selection and checks that every source/settings file stays
byte-identical after conversion. The upstream check validates deterministic
conversion and independent color controls. Neither check edits the pack.
