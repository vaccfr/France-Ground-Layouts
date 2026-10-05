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
an extracted outer repository folder, or a ZIP with GNG/ and Colours.sct.
The root source is preferred, then equivalent inputs under Input/.

GeoJSON/ is generated output. All products are validated before writing files.
An explicit source selection overwrites the existing GeoJSON output; official
source may contain different airports and geometry from a customized checkout.
No reports, summaries or cached downloads are generated.

Settings/ is the only place for editable vSMR customization: palettes,
backgrounds, groups, zoom levels and runway settings. Settings/Colours.sct
contains palette additions/overrides; conversion leaves root Colours.sct intact.
Colors in Settings take precedence over the selected pack's native definitions.

## Official sources are read-only

GNG/, KMZ/ and root Colours.sct are based on the official pack at
[vaccfr commit ed923f4](https://github.com/vaccfr/France-Ground-Layouts/commit/ed923f4b8ce11bbf1a0998597fd46595287b4d4c).
Conversion leaves all native source files unchanged. The LFPO background rectangle removal
was already merged upstream in PR #196. LFPO's Real background is configured
as #6C6A68 in Settings/Colours.sct.

Local source updates include LFBO gate categories and LFLL geometry/labels imported
from edited AVISO files. LFLL's KMZ retains its folder structure; new native color
names describe stand entry lines, surface markings and red taxiway markings.
Use local mode to retain these additions until they are available upstream.

LFBO's Real palette includes grass outlines. LFSB has an airport-specific Real
palette with grass outlines and no outlines on runways or hard surfaces.
These appearance settings do not modify native GNG/KMZ geometry or Dark/Light.

The converter reads all geometry and text exclusively from GNG. KMZ files
remain in the repository for the upstream workflow, but are neither required,
opened nor parsed. Folder inputs may omit KMZ entirely, and any KMZ entries in
ZIP inputs are ignored. Colours.sct and Settings supply rendering configuration.
Only airports with GNG records generate output.

KMZ archives are based on official commit
[2f61d769](https://github.com/vaccfr/France-Ground-Layouts/commit/2f61d769d970e0574d37feccbbc51dc4b234cd8e)
with geometry corrections limited to 29 archives that differ spatially from
this checkout's GNG. Native folders, styles and bundled assets are retained.
33 archives are byte-identical to upstream; coordinate rounding, formatting,
style aliases and line packaging alone do not warrant rewriting them.
LFRB and the LFXX reference template receive only Point annotation removal,
preserving their geometry and other XML content. No KMZ contains Point text
annotations; text remains in GNG only. The 29 corrected archives use exact
current GNG coordinates and native color tokens, including its omissions.
LFLG, LFMU, LFPM and LFRK currently have text-only GNG, so their KMZ contain no
geometry. The regional coastline and reference template have no airport GNG
counterparts; their geometry is retained and checked for absence of text.

Feature IDs are deterministic output details and are never written back.
Optional group assignments use `file:<GNG filename without extension>` or an
exact feature ID. Groups with no assigned output feature are hidden; objects
available only in KMZ are not imported.
Conversion writes only GeoJSON; source/settings directories are rejected as
output destinations. All changes to appearance belong in Settings/.

## Verification

```powershell
python Script/verify_converter.py
python Script/verify_upstream.py
python Script/verify_kmz_geometry.py
```

The full regression check compares regenerated output with GeoJSON/, verifies
GNG geometry/text selection and KMZ isolation and checks that every source/settings file stays
byte-identical after conversion. The upstream check validates deterministic
conversion and independent color controls. Neither check edits the pack.
Palette regressions also check LFBO grass outlines, LFSB runway/apron outline
suppression and isolation of airport-specific Real color edits.

The KMZ check exports geometry to temporary GNG and parses it back. Corrected
archives match coordinates, native colors and geometry multiplicities exactly.
Preserved upstream geometry is compared at native GNG coordinate precision
(three decimal places of DMS seconds, allowing half a unit plus floating-point
rounding). Unmatched vertices still fail. Original style aliases and repeated
line segments do not affect this spatial check; polygon counts are preserved.
The output reports exact matches separately from native-precision matches.
Polygon starting vertices/winding and line direction/packaging do not affect
geometry. The check does not reproduce comments, whitespace, file splits or GNG
text. Repeated directed segments are exported into separate temporary GNG files
to preserve multiplicities where the exact comparison applies. All 64 KMZ are
checked for valid XML, complete active style references and absence of Point
annotations. Unused legacy styles are left untouched.
