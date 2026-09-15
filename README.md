<p align="center"><img src="https://i.imgur.com/n17WHdO.png" width="auto"></p>

<p align="center"><br>Official repository for the ground layouts of the French Sector File<br>
<a href="https://www.vatsim.fr/fr" target="_blank">https://vatsim.fr/fr</a> <i>(Version française)</i><br>
<a href="https://www.vatsim.fr/gb" target="_blank">https://vatsim.fr/gb</a> <i>(English version)</i>
</p>

---

## French vACC AVISO Map  

A map displaying the available, work-in-progress and planned airports is available [here](https://www.google.com/maps/d/viewer?mid=1BH-EmsmISqlP5sPrPS61wtXdW6Of-q0y&usp=sharing)  

# Design standard  

## General guidelines  

- As few points as possible should be used to maintain EuroScope's performance while ensuring a sufficient level of accuracy (smooth curves, etc.).
- Only “drivable” areas should be drawn. Consequently, shoulders will not be drawn as aprons, taxiways, or runways.
- To optimize the number of polygons, overlapping polygons should be preferred.
- The associated freetext (taxiways, VFR points and gates) should be updated consequently

## Colors  

- **Runways** must be defined as separate polygons, color **COLOR_RunwayConcrete**
- **Grass runways** must be defined as separate polygons, color **COLOR_RunwayGrass**
- **Taxiways** must be defined as separate polygons, with the color **COLOR_HardSurface2**
- **Grass taxiways** must be defined as separate polygons, with the color **COLOR_GrassSurface2**
- **Aprons** must be defined as separate polygons, with the color **COLOR_HardSurface3**
- **Grass areas** must be defined as separate polygons, color **COLOR_GrasSurface**
- **Buildings** must be defined as separate polygons, color **COLOR_Building**
- **CAT I holding points** must be defined as separate polygons, color **COLOR_Stopbar**
- **CAT III holding points** must be defined as separate polygons, color **COLOR_TaxiwayOrange**
- **Unusable paved areas** must be defined as separate polygons, color **COLOR_HardSurface4**
- **Gate centerlines** must be defined as separate lines (under the [GEO] section), using the color **COLOR_Taxiway**
- **Intermediate holding points** must be defined as dashed lines, using the color **COLOR_TaxiwayOrange**
  
If you have any questions or issues regarding the creation or updating of an AVISO, please visit the French vACC Discord server.


## Optional vSMR AVISO conversion

GNG, KMZ and Colours.sct remain unchanged from the official pack.
LFPO uses a Real background setting following the upstream rectangle removal.
The converter reads geometry and text only from GNG, without rewriting it.
KMZ files are not opened or parsed.
Customize vSMR only through Settings/, including Settings/Colours.sct for colors.

On Windows, double-click **Script/Convert AVISO.cmd** and choose:

1. **Local** (default): use this checkout's GNG and Colours.sct.
2. **Official GitHub**: download original source from vaccfr/France-Ground-Layouts.

Python 3.10+ is required. Conversion writes GeoJSON into `GeoJSON/`. No reports or
summaries are produced. An explicit GitHub failure is reported; it does not
silently switch to different source data.

`Settings/` holds runtime styles, groups, zoom levels and airport settings. Colors
are customized in Settings/Colours.sct over the native Colours.sct. Text/background defaults are shared; unrelated
geometry roles remain independently editable even when RGB values match.
See [converter usage](Script/README.md) and [runtime settings](Settings/README.md).
