"""Round-trip native KMZ geometry to temporary GNG; compare with current GNG.

Polygon starting vertices, winding and line direction/packaging do not change
geometry. Updated archives match coordinates, colors and multiplicities exactly.
Preserved upstream archives are compared spatially at native GNG precision,
without rewriting their coordinates, style aliases or duplicate line packaging.
Text stays exclusively in GNG; KMZ files are never read by the production converter.
"""
from __future__ import annotations

import collections
from decimal import Decimal, localcontext
import math
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile

import aviso_converter as c

NS = 'http://www.opengis.net/kml/2.2'
# GNG coordinates normally use three decimal places of DMS seconds. Permit
# half that unit plus floating-point rounding in the spatial comparison only.
NATIVE_EPSILON = .00051 / 3600


def tag(name):
    return '{' + NS + '}' + name


def points(element):
    if element is None or not element.text:
        raise ValueError('Missing KML coordinates')
    result = []
    for item in element.text.split():
        values = item.split(',')
        if len(values) not in (2, 3):
            raise ValueError('Invalid KML coordinate: ' + item)
        result.append([float(values[0]), float(values[1])])
    return result


def read_kmz(path):
    records = []
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError(str(path) + ': corrupt archive')
        for name in archive.namelist():
            if not name.lower().endswith('.kml'):
                continue
            root = ET.fromstring(archive.read(name))
            ids = {element.attrib['id']: element for element in root.iter() if 'id' in element.attrib}
            checked = set()

            def check_style(reference):
                if not reference or not reference.startswith('#') or reference in checked:
                    return
                checked.add(reference)
                if reference[1:] not in ids:
                    raise ValueError(str(path) + ': missing active style ' + reference)
                for nested in ids[reference[1:]].iter(tag('styleUrl')):
                    check_style(nested.text)

            if list(root.iter(tag('Point'))):
                raise ValueError(str(path) + ': text/point annotation remains')
            for placemark in root.iter(tag('Placemark')):
                check_style(placemark.findtext(tag('styleUrl')))
                color = placemark.findtext(tag('name'), '')
                for polygon in placemark.iter(tag('Polygon')):
                    if polygon.find(tag('innerBoundaryIs')) is not None:
                        raise ValueError(str(path) + ': polygon holes cannot be represented by native GNG')
                    ring = points(polygon.find(tag('outerBoundaryIs') + '/' + tag('LinearRing') + '/' + tag('coordinates')))
                    records.append(dict(kind='polygon', color=color, geometry=dict(type='Polygon', coordinates=[ring])))
                for line in placemark.iter(tag('LineString')):
                    records.append(dict(kind='line', color=color, geometry=dict(type='LineString', coordinates=points(line.find(tag('coordinates'))))))
    return records


def ring_key(ring):
    ring = tuple(map(tuple, ring))
    if ring and ring[-1] == ring[0]:
        ring = ring[:-1]
    if not ring:
        raise ValueError('Empty polygon')
    # Starting vertex and winding do not affect the native filled surface.
    return min(sequence[index:] + sequence[:index]
               for sequence in (ring, ring[::-1])
               for index, point in enumerate(sequence) if point == min(ring))


def inventory(records):
    result = collections.Counter()
    for record in records:
        kind, color, geometry = record['kind'], record['color'], record['geometry']
        if kind == 'label':
            continue
        if kind == 'polygon':
            result[('polygon', color, ring_key(geometry['coordinates'][0]))] += 1
        else:
            paths = [geometry['coordinates']] if geometry['type'] == 'LineString' else geometry['coordinates']
            for path in paths:
                for start, end in zip(path, path[1:]):
                    if start != end:
                        result[('segment', color, tuple(sorted((tuple(start), tuple(end)))))] += 1
    return result


def spatial_inventory(records, native):
    """Compare legacy KMZ at GNG precision, ignoring style aliases/line repeats.

    Only vertices within half a native coordinate unit snap to an existing GNG
    vertex. Unmatched vertices remain distinct; real spatial changes still fail.
    Polygon counts are preserved, while native per-file line deduplication and
    segment direction/packaging do not affect the comparison.
    """
    buckets = collections.defaultdict(set)

    def paths(record):
        geometry = record['geometry']
        return [geometry['coordinates']] if geometry['type'] == 'LineString' else geometry['coordinates']

    def cell(point):
        return tuple(math.floor(value / NATIVE_EPSILON) for value in point)

    for record in native:
        if record['kind'] != 'label':
            for line in paths(record):
                for point in line:
                    buckets[cell(point)].add(tuple(point))

    def snap(point):
        x, y = cell(point)
        candidates = [candidate
                      for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                      for candidate in buckets.get((x + dx, y + dy), ())
                      if max(abs(a - b) for a, b in zip(point, candidate)) <= NATIVE_EPSILON]
        return min(candidates, key=lambda candidate: (sum((a - b) ** 2 for a, b in zip(point, candidate)), candidate)) if candidates else tuple(point)

    normalized = []
    for record in records:
        if record['kind'] == 'label':
            continue
        lines = [[snap(point) for point in line] for line in paths(record)]
        normalized.append(dict(kind=record['kind'], color='*', geometry=dict(
            type=record['geometry']['type'],
            coordinates=lines[0] if record['geometry']['type'] == 'LineString' else lines)))
    result = inventory(normalized)
    return collections.Counter({key: 1 if key[0] == 'segment' else count for key, count in result.items()})


def verify_spatial_precision():
    """Rounding is acceptable; a change beyond native precision is not."""
    def line(start, end, color='COLOR_Taxiway'):
        return dict(kind='line', color=color, geometry=dict(type='LineString', coordinates=[start, end]))

    native = [line([2, 49], [2.001, 49.001])]
    rounded = [line([2 + NATIVE_EPSILON * .9, 49], [2.001, 49.001], 'COLOR_Legacy')]
    shifted = [line([2 + NATIVE_EPSILON * 2, 49], [2.001, 49.001])]
    expected = spatial_inventory(native, native)
    assert spatial_inventory(rounded, native) == expected
    assert spatial_inventory(shifted, native) != expected


def dms(value, latitude):
    # Sufficient decimal precision to preserve the parsed binary float exactly.
    with localcontext() as context:
        context.prec = 60
        seconds = abs(Decimal(str(value))) * 3600
        degree = int(seconds // 3600)
        seconds -= degree * 3600
        minute = int(seconds // 60)
        seconds -= minute * 60
        hemisphere = ('N' if value >= 0 else 'S') if latitude else ('E' if value >= 0 else 'W')
        return f'{hemisphere}{degree:03d}.{minute:02d}.{seconds:028.25f}'


def row(point):
    return dms(point[1], True) + ' ' + dms(point[0], False)


def export_gng(records):
    rows = []
    for record in records:
        color, geometry = record['color'], record['geometry']
        if not re.fullmatch(c.COLOR_TOKEN + r'|\d+', color):
            raise ValueError('Not a native GNG color token: ' + color)
        if record['kind'] == 'polygon':
            rows.append(color)
            rows.extend(row(point) for point in geometry['coordinates'][0])
            rows.append('')
        else:
            for start, end in zip(geometry['coordinates'], geometry['coordinates'][1:]):
                if start != end:
                    rows.append(row(start) + ' ' + row(end) + ' ' + color)
    return ('\n'.join(rows) + '\n').encode('utf-8')


def export_groups(records):
    """Keep repeated native segments in separate files, as GNG requires."""
    groups = []
    seen = []
    for record in records:
        geometry = record['geometry']
        keys = set()
        if record['kind'] == 'line':
            keys = {(record['color'], tuple(start), tuple(end))
                    for start, end in zip(geometry['coordinates'], geometry['coordinates'][1:]) if start != end}
        index = next((index for index, existing in enumerate(seen) if not keys & existing), len(groups))
        if index == len(groups):
            groups.append([])
            seen.append(set())
        groups[index].append(record)
        seen[index].update(keys)
    return groups


def main():
    verify_spatial_precision()
    airports = archives = annotations_only = exact = legacy = 0
    with tempfile.TemporaryDirectory(prefix='kmz-gng-roundtrip-') as directory:
        for path in sorted((c.ROOT / 'KMZ').glob('*.kmz')):
            records = read_kmz(path)
            archives += 1
            code = path.name[:4]
            files = sorted((c.ROOT / 'GNG').glob('*/' + code + '/*.txt'))
            if not files:
                # Regional coastline and reference template have no airport GNG.
                assert path.name in ('LFMM Region Coastline.kmz', 'LFXX reference.kmz'), path.name
                continue
            native = [record for file in files for record in c.parse_gng(file.relative_to(c.ROOT).as_posix(), file.read_bytes())]
            expected, actual = inventory(native), inventory(records)
            strict = actual == expected
            if strict:
                exact += 1
            else:
                expected_spatial = spatial_inventory(native, native)
                actual_spatial = spatial_inventory(records, native)
                assert actual_spatial == expected_spatial, f'{path.name}: {sum((expected_spatial-actual_spatial).values())} missing / {sum((actual_spatial-expected_spatial).values())} extra spatial items'
                legacy += 1
            converted = []
            for index, group in enumerate(export_groups(records)):
                generated = Path(directory) / (path.stem + f'-{index}.txt')
                generated.write_bytes(export_gng(group))
                converted.extend(c.parse_gng(generated.name, generated.read_bytes()))
            if strict:
                assert inventory(converted) == expected, path.name + ': KMZ -> GNG round trip changed coordinates, colors or multiplicities'
            else:
                assert spatial_inventory(converted, native) == expected_spatial, path.name + ': KMZ -> GNG round trip changed geometry beyond native precision'
            assert all(record['kind'] != 'label' for record in converted)
            airports += 1
            annotations_only += not bool(expected)
    print(f'PASS: {archives} text-free KMZ; {airports} airport archives match GNG geometry ({exact} exact including colors/counts, {legacy} spatial at native precision); KMZ -> GNG round trip verified; {annotations_only} have text-only GNG. Coastline/reference checked separately.')


if __name__ == '__main__':
    main()
