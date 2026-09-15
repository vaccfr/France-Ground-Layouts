# AVISO runtime settings

Airport settings are flat files: `Settings/LFPG.json`, `Settings/LFPO.json`,
etc. There are no per-airport folders or separate feature files.

- <ICAO>.json: styles, groups, backgrounds, zoom levels and runway settings.
- Optional `features` inside <ICAO>.json: toggle-group assignments keyed by feature IDs or `folder:<KMZ folder name>`.
- common.json: reusable runtime settings referenced with {"$ref": "name"}.

Editable colors are named definitions in `Colours.sct` in this folder, layered over
the unchanged native ../Colours.sct. BACKGROUND_COLOR is the shared
default; LFPG and LFPO Real use REAL_LFPG_BACKGROUND_COLOR and
REAL_LFPO_BACKGROUND_COLOR respectively. TEXT_COLOR and TEXT_HALO_COLOR
are used only for text. Other roles retain their own color references, even
when their initial RGB values match. Original COLOR_* names remain compatible
with upstream native layouts. DARK_*, LIGHT_* and REAL_<ICAO>_* describe AVISO
palette roles. Undefined references are errors.
Light styles reference native COLOR_* definitions directly when the role and
value match. Separate LIGHT_* entries are retained for distinct overrides.

$ref objects recursively merge local overrides over common settings. Lists
replace inherited lists.

The optional `features` object inside each airport JSON contains only group assignments:

```json
{
  "features": {
    "folder:LFPG Groundlayout East Arrows": {
      "vsmr_group_ids": ["ground-layout-east"]
    }
  }
}
```

Only LFPG currently needs the `features` object, for the East/West arrow folders. Other
features need no entries. Styles are inferred from native color names, geometry
kind and label file categories. Geometry roles follow the selected style;
no per-feature style or rendering overrides are stored or accepted.

GNG, KMZ and native Colours.sct remain unchanged. Appearance belongs in Settings.
LFPO uses `metadata.exclude_features` to omit its obsolete background rectangle
from generated output without editing either source file. The list contains
source feature IDs; an ID absent from a later pack is harmless.
