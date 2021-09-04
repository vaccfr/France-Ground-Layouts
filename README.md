<p align="center"><img src="https://i.imgur.com/n17WHdO.png" width="auto"></p>

<p align="center"><br>Official repository for the ground layouts of the French Sector File<br>
<a href="https://www.vatsim.fr/fr" target="_blank">https://vatsim.fr/fr</a> <i>(Version française)</i><br>
<a href="https://www.vatsim.fr/gb" target="_blank">https://vatsim.fr/gb</a> <i>(English version)</i>
</p>

---



# Standard de design

- Un rectangle doit être définie en fond de carte qui couvre toute la platforme, plus une marge de 10nm de chaque coté. La couleur de cette zone est COLOR_GrasSurface4
- Les pistes doivent être définies en polygones à part, couleur COLOR_RunwayConcrete
- Les taxiways doivent être définies en polygones à part, couleur COLOR_HardSurface2
- Les aprons doivent être définis en polygones à part, couleur COLOR_HardSurface3
- Les zones d'herbes doivent être définies en polygones à part, couleur COLOR_GrasSurface
- Les batiments doivent être définis en polygones à part, couleur COLOR_Building
- Les points d'attente CAT I doivent être définis en polygones à part, couleur COLOR_ProhibitedArea
- Les points d'attente CAT III doivent être définis en polygones à part, couleur COLOR_TaxiwayOrange
- Les zones désafectées doivent être définies en polygones à part, couleur COLOR_HardSurface4
- Les zones chevrons doivent être définis en polygones à part, couleur COLOR_HardSurface4
- Les lignes médianes des portes et parkings doivent être définis en 'paths' (rubrique [GEO]) à part, couleur COLOR_Taxiway
- Le moins de points possible doit être utilisé, afin de conserver les performances d'EuroScope
