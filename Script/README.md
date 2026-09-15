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
contains palette additions/overrides; the pack's root Colours.sct stays intact.
Colors in Settings take precedence over the selected pack's native definitions.

## Official sources are read-only

GNG/, KMZ/ and root Colours.sct are based on the official pack at
[vaccfr commit ed923f4](https://github.com/vaccfr/France-Ground-Layouts/commit/ed923f4b8ce11bbf1a0998597fd46595287b4d4c).
All native source files remain unchanged. The LFPO background rectangle removal
was already merged upstream in PR #196. LFPO's Real background is configured
as #6C6A68 in Settings/Colours.sct.

Do not reformat coordinates, remove content, rename or reorganize native files,
or rebuild KMZ archives. Update sources only from the official pack.

The converter reads all geometry and text exclusively from GNG. KMZ files
remain in the repository for the upstream workflow, but are neither required,
opened nor parsed. Folder inputs may omit KMZ entirely, and any KMZ entries in
ZIP inputs are ignored. Colours.sct and Settings supply rendering configuration.
Only airports with GNG records generate output.

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
```

The full regression check compares regenerated output with GeoJSON/, verifies
GNG geometry/text selection and KMZ isolation and checks that every source/settings file stays
byte-identical after conversion. The upstream check validates deterministic
conversion and independent color controls. Neither check edits the pack.
