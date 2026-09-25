# AVISO runtime settings

Airport settings are flat files: `Settings/LFPG.json`, `Settings/LFPO.json`,
etc. There are no per-airport folders or separate feature files.

- <ICAO>.json: styles, groups, backgrounds, zoom levels and runway settings.
- Optional `features` inside <ICAO>.json: toggle-group assignments keyed by feature IDs or `file:<GNG filename without extension>`.
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
    "file:LFPG Groundlayout East Arrows": {
      "vsmr_group_ids": ["ground-layout-east"]
    }
  }
}
```

Only LFPG currently needs the `features` object, for optional East/West arrow GNG files. Empty groups are hidden. Other
features need no entries. Styles are inferred from native color names, geometry
kind and label file categories. Geometry roles follow the selected style;
no per-feature style or rendering overrides are stored or accepted.

GNG, KMZ and native Colours.sct remain unchanged from the official pack.
Make appearance changes here, not in the native source files. Geometry and labels are read exclusively from GNG; KMZ files are ignored. Keep IDs stable only for
features explicitly assigned to toggle groups. Ordinary feature IDs are an
output detail, not a mapping that needs manual maintenance. Official GitHub
layouts may differ from the customized local ones.
