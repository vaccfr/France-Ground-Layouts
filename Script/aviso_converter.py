"""France Ground Layouts -> vSMR shared-geometry AVISO. Standard library only."""
from __future__ import annotations

import collections
import argparse
import copy
import ctypes
import hashlib
from decimal import Decimal
import io
import json
import math
import os
from pathlib import Path
import re
import sys
import time
import traceback
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
GITHUB_URL = 'https://codeload.github.com/vaccfr/France-Ground-Layouts/zip/refs/heads/master'
COORD = re.compile(r'([NSEW])(\d{2,3})[. :](\d{2})[. :](\d{2}(?:\.\d+)?)', re.IGNORECASE)
DEFAULT_STYLES = {}
COLOR_TOKEN = r'(?:(?:COLOR_|DARK_|LIGHT_|REAL_)[A-Za-z0-9_-]+|BACKGROUND_COLOR|TEXT_COLOR|TEXT_HALO_COLOR)'


def packed(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def decode(data):
    try:
        return data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return data.decode('cp1252')


def dms(match):
    h, deg, minute, sec = match.groups()
    h = h.upper()
    fraction_digits = len(sec.partition('.')[2])
    deg, minute, sec = int(deg), int(minute), Decimal(sec)
    # The supplied sector data sometimes uses 60 seconds after rounding.
    if minute > 59 or sec > 60 or deg > (90 if h in 'NS' else 180):
        raise ValueError('Invalid coordinate: ' + match.group())
    value = float((Decimal(deg) + Decimal(minute) / 60 + sec / 3600) * (-1 if h in 'SW' else 1))
    return round(value, 9) if fraction_digits <= 3 else value


def pairs(matches):
    if len(matches) % 2:
        raise ValueError('Unpaired latitude/longitude')
    result = []
    for lat, lon in zip(matches[::2], matches[1::2]):
        if lat[1].upper() not in 'NS' or lon[1].upper() not in 'EW':
            raise ValueError('Expected latitude followed by longitude')
        result.append([dms(lon), dms(lat)])
    return result


def record(file, kind, color, name, geometry):
    return dict(file=file, kind=kind, color=color, name=name, geometry=geometry)


def parse_gng(file, data):
    text = decode(data)
    records, polygon, color = [], [], None
    lines = collections.defaultdict(list)
    stem = Path(file).stem

    def flush():
        nonlocal polygon
        if polygon:
            if len(set(map(tuple, polygon))) < 3:
                raise ValueError(f'{file}: polygon has fewer than three points')
            if polygon[-1] != polygon[0]:
                polygon.append(polygon[0][:])
            records.append(record(file, 'polygon', color, stem,
                                  dict(type='Polygon', coordinates=[polygon])))
            polygon = []

    for number, raw in enumerate(text.splitlines(), 1):
        text = raw.split(';')[0].strip()
        if not text or text.startswith('//'):
            continue
        if re.fullmatch(COLOR_TOKEN, text):
            flush()
            color = text
            continue
        matches = list(COORD.finditer(text))
        if len(matches) == 4:
            flush()
            pts = pairs(matches)
            token = text[matches[-1].end():].strip()
            if not re.fullmatch(COLOR_TOKEN + r'|\d+', token):
                raise ValueError(f'{file}:{number}: unsupported line color {token!r}')
            lines[token].append(pts)
        elif len(matches) == 2:
            pts = pairs(matches)
            label = text[matches[-1].end():].strip()
            if label:
                flush()
                records.append(record(file, 'label', '', label, dict(type='Point', coordinates=pts[0])))
            elif color:
                polygon.append(pts[0])
            else:
                raise ValueError(f'{file}:{number}: coordinate without polygon color')
        else:
            raise ValueError(f'{file}:{number}: unsupported data: {text[:100]}')
    flush()
    for token, segments in lines.items():
        paths = []
        seen = set()
        for start, end in segments:
            key = (tuple(start), tuple(end))
            if start == end or key in seen:
                continue
            seen.add(key)
            if paths and paths[-1][-1] == start:
                paths[-1].append(end)
            else:
                paths.append([start, end])
        if paths:
            geometry = dict(type='LineString', coordinates=paths[0]) if len(paths) == 1 else dict(type='MultiLineString', coordinates=paths)
            records.append(record(file, 'line', token, stem, geometry))
    return records


def source_archive(path):
    if hasattr(path, 'read'):
        return zipfile.ZipFile(path)
    path = Path(path)
    if path.is_file():
        return zipfile.ZipFile(path)
    if not path.is_dir():
        raise ValueError('Source does not exist: ' + str(path))
    candidates = [path] if all((path / n).exists() for n in ('GNG', 'Colours.sct')) else [p.parent for p in path.rglob('Colours.sct') if (p.parent / 'GNG').is_dir()]
    if len(candidates) != 1:
        raise ValueError('Expected one folder containing GNG/ and Colours.sct')
    folder = candidates[0]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name in ('GNG', 'Colours.sct'):
            item = folder / name
            paths = sorted(item.rglob('*')) if item.is_dir() else [item]
            for file in paths:
                if file.is_file() and not file.is_symlink():
                    archive.writestr(file.relative_to(folder).as_posix(), file.read_bytes())
    buffer.seek(0)
    return zipfile.ZipFile(buffer)


def read_colors(data):
    colors = {}
    for name, number in re.findall(r'#define\s+([\w-]+)\s+(\d+)', decode(data)):
        if name in colors:
            raise ValueError('Duplicate color definition: ' + name)
        value = int(number)
        if not 0 <= value <= 0xFFFFFF:
            raise ValueError('Invalid color value: ' + name)
        colors[name] = '#%02X%02X%02X' % (value & 255, (value >> 8) & 255, (value >> 16) & 255)
    return colors


def palette_colors(native=None):
    """Apply editable vSMR palettes without changing the pack's color definitions."""
    colors = read_colors((ROOT / 'Colours.sct').read_bytes()) if native is None else dict(native)
    colors.update(read_colors((ROOT / 'Settings' / 'Colours.sct').read_bytes()))
    return colors


def additional_gng(code):
    """Optional GNG supplements live with airport settings, never in the pack."""
    folder = ROOT / 'Settings'
    settings = folder / (code + '.json')
    if not settings.is_file():
        return {}
    names = json.loads(settings.read_text(encoding='utf-8-sig')).get('additional_gng', [])
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        raise ValueError(code + ': additional_gng must be a list of GNG filenames')
    result = {}
    for name in names:
        path = folder / name
        if path.resolve().parent != folder.resolve() or not name.startswith(code + ' ') or path.suffix.lower() != '.txt':
            raise ValueError(code + ': additional GNG must be an airport TXT file inside Settings')
        if name in result:
            raise ValueError(code + ': duplicate additional GNG filename')
        result[name] = parse_gng('Settings/' + name, path.read_bytes())
    return result


def load_source(path):
    airports = collections.defaultdict(list)
    inventory, gng, extras = set(), {}, {}
    with source_archive(path) as archive:
        entries = [(i, i.filename.replace('\\', '/')) for i in archive.infolist() if not i.is_dir()]
        names = {name for _, name in entries}
        roots = {m.group(1) for _, name in entries
                 if (m := re.fullmatch(r'((?:.*/)?)GNG/.*\.txt', name, re.IGNORECASE))
                 and m.group(1) + 'Colours.sct' in names}
        if len(roots) != 1:
            raise ValueError('Expected one source folder containing GNG/ and Colours.sct')
        prefix = roots.pop()
        members = [(i, name[len(prefix):]) for i, name in entries
                   if name == prefix + 'Colours.sct'
                   or (name.startswith(prefix + 'GNG/') and name.lower().endswith('.txt'))]
        if sum(i.file_size for i, _ in members) > 512 * 1024 * 1024:
            raise ValueError('Source ZIP is larger than 512 MB uncompressed')
        for member, file in members:
            data = archive.read(member)
            if file in inventory:
                raise ValueError('Duplicate source path: ' + file)
            inventory.add(file)
            if file.startswith('GNG/') and file.lower().endswith('.txt'):
                code = Path(file).parent.name.upper()
                if not re.fullmatch('[A-Z]{4}', code):
                    raise ValueError('Invalid airport directory: ' + file)
                gng[file] = (code, parse_gng(file, data))
            elif file == 'Colours.sct':
                extras['colors'] = read_colors(data)
        published = {(code, Path(file).name) for file, (code, _) in gng.items()}
        for code in sorted({code for code, _ in published}):
            for name, records in additional_gng(code).items():
                if (code, name) not in published:
                    gng['Settings/' + name] = (code, records)
        airports = assemble_sources(gng)
    if not gng or not extras.get('colors'):
        raise ValueError('Expected GNG/ and a valid Colours.sct')
    extras['colors'] = palette_colors(extras['colors'])
    return dict(airports=dict(airports), **extras)


def assemble_sources(gng):
    """Build all geometry and text exclusively from GNG records."""
    airports = collections.defaultdict(list)
    for _, (code, records) in sorted(gng.items()):
        airports[code].extend(copy.deepcopy(records))
    for code, records in airports.items():
        seen = set()
        for item in records:
            identifier = item.get('source_id')
            if not identifier or identifier in seen:
                base = code + '-' + hashlib.sha256(packed(item)).hexdigest()[:20]
                identifier, suffix = base, 1
                while identifier in seen:
                    suffix += 1
                    identifier = base + '-' + str(suffix)
            item['source_id'] = identifier
            seen.add(identifier)
    return {code: records for code, records in airports.items() if records}


def coordinates(geometry):
    def walk(value):
        if value and isinstance(value[0], (float, int)):
            yield value
        else:
            for child in value:
                yield from walk(child)
    yield from walk(geometry['coordinates'])


def load_settings(colors=None):
    if colors is None:
        colors = palette_colors()
    folder = ROOT / 'Settings'
    common = json.loads((folder / 'common.json').read_text(encoding='utf-8-sig'))
    def merge(base, changes):
        for key, value in changes.items():
            if isinstance(base.get(key), dict) and isinstance(value, dict):
                merge(base[key], value)
            else:
                base[key] = value
        return base
    def resolve(value, stack=()):
        if isinstance(value, list):
            return [resolve(v, stack) for v in value]
        if isinstance(value, str) and re.fullmatch(COLOR_TOKEN, value):
            if value not in colors:
                raise ValueError('Undefined palette color: ' + value)
            return colors[value]
        if not isinstance(value, dict):
            return value
        reference = value.get('$ref')
        base = {}
        if reference is not None:
            if reference in stack:
                raise ValueError('Circular customization reference: ' + reference)
            base = resolve(common[reference], stack + (reference,))
        for key, child in value.items():
            if key != '$ref':
                merge(base, {key: resolve(child, stack)})
        return base
    recipes = {}
    for airport in sorted(folder.glob('*.json')):
        if not re.fullmatch('[A-Z]{4}', airport.stem):
            continue
        document = json.loads(airport.read_text(encoding='utf-8-sig'))
        document.pop('additional_gng', None)
        overrides = document.pop('features', {})
        if not isinstance(overrides, dict):
            raise ValueError(str(airport) + ': features must be a group-assignment object')
        settings = resolve(document)
        for feature_id, options in overrides.items():
            if not isinstance(options, dict) or set(options) != {'vsmr_group_ids'}:
                raise ValueError(str(airport) + ': only group assignments are allowed in features')
        recipes[airport.stem] = dict(document=settings, overrides=overrides)
    return dict(recipes=recipes)


def serialize_document(doc):
    return packed(doc) + b'\n'


def label_category(file):
    value = Path(file).stem[5:]
    return 'TORA' if 'TORA' in value.upper() else value or 'Labels'


def infer_style(item, doc, colors):
    kind = item['kind']
    if kind == 'line' and Path(item['file']).stem.endswith(('East Arrows', 'West Arrows')):
        suffix = {'COLOR_Centerlines': 'centerline', 'COLOR_TaxiwayGreen': 'green', 'COLOR_TaxiwayBrown': 'brown'}.get(item['color'])
        arrow_style = 'line.ground_layout_arrows.' + (suffix or '')
        if arrow_style in doc['styles']:
            return arrow_style
    token = re.sub(r'^(?:COLOR_|LIGHT_|DARK_|REAL_[A-Z]{4}_)', '', item['color']).lower()
    prefix = ('label.' + re.sub('[^a-z0-9]+', '-', label_category(item['file']).lower()).strip('-')) if kind == 'label' else kind + '.' + token + '.'
    candidates = list(doc['styles']) + [k for k in DEFAULT_STYLES if k not in doc['styles']]
    matches = []
    def normalized(value):
        value = re.sub(r'(?:[._-])[a-fA-F0-9]{6}(?=$|[._-])', '', value)
        return re.sub(r'[^a-z0-9]', '', value.lower())
    if kind == 'label':
        category = normalized(Path(item['file']).stem[5:])
        if not category and 'airport.reference' in doc['styles']:
            matches = ['airport.reference']
        else:
            matches = [k for k in candidates if k.startswith('label.') and normalized(k[6:]) == category]
            if not matches and category == 'labels' and 'label.text.label.labels' in candidates:
                matches = ['label.text.label.labels']
    else:
        role = re.sub(r'_[0-9]+$', '', token) if token.startswith(kind + '_') else kind + '_' + token
        matches = [k for k in candidates if normalized(k) == normalized(role)]
        if kind == 'line' and 'gate' in item['name'].lower():
            stands = [k for k in candidates if k.endswith('.stands') and normalized(k[:-7]) == normalized(role)]
            matches = stands or matches
    if not matches:
        matches = [k for k in candidates if k == prefix or k.startswith(prefix)]
    if matches:
        paint_key = 'fill' if kind == 'polygon' else 'stroke'
        def rank(key):
            style = doc['styles'].get(key, DEFAULT_STYLES.get(key))
            paint = style['paint']
            light = paint.get('palette-overrides', {}).get('light', {}).get(paint_key, paint.get(paint_key))
            return (light != colors.get(item['color']), key not in doc['styles'], len(key))
        key = min(matches, key=rank)
        if key not in doc['styles']:
            doc['styles'][key] = copy.deepcopy(DEFAULT_STYLES[key])
        return key
    style_id = prefix.rstrip('.')
    color = colors['TEXT_COLOR'] if kind == 'label' else colors.get(item['color'], colors['TEXT_COLOR'])
    category = label_category(item['file']) if kind == 'label' else token
    layer = {'label': 'Labels', 'line': 'Guidance lines', 'polygon': 'Airfield surfaces'}[kind]
    paint = {'text-color': color, 'text-font': 'Arial', 'text-size': 12, 'text-halo-color': colors['TEXT_HALO_COLOR'], 'text-halo-width': 1, 'text-anchor': 'center', 'zoomLevel': 9 if 'gate' in category.lower() else 7} if kind == 'label' else {'stroke': color, 'stroke-width': 1, 'stroke-opacity': 1} if kind == 'line' else {'fill': color, 'fill-opacity': 1}
    doc['styles'][style_id] = dict(name=category, layer=layer, object_type={'label': 'Label', 'line': 'Line', 'polygon': 'Area'}[kind], paint=paint)
    return style_id


def update_counts(doc):
    features = doc['features']
    pts = [p for f in features for p in coordinates(f['geometry'])]
    if pts:
        doc['bbox'] = [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)]
    metadata = doc['metadata']
    metadata['feature_count'] = len(features)
    metadata['style_count'] = len(doc['styles'])
    for key in ('layer', 'category'):
        metadata[key + '_counts'] = dict(sorted(collections.Counter(f['properties'].get(key, '') for f in features).items()))
    counts = collections.Counter(f['properties'].get('style_id') for f in features)
    for key, style in doc['styles'].items():
        style['feature_count'] = counts[key]


def convert_airport(code, recipe, records, colors):
    doc = dict(type=recipe['document']['type'], name=recipe['document']['name'], bbox=[],
               **copy.deepcopy({k: v for k, v in recipe['document'].items() if k not in ('type', 'name', 'bbox')}))
    overrides = recipe['overrides']
    features = []
    excluded = set(doc['metadata'].pop('exclude_features', []))
    for item in records:
        feature_id = item['source_id']
        if feature_id in excluded:
            continue
        options = {}
        options.update(copy.deepcopy(overrides.get('file:' + Path(item['file']).stem, {})))
        options.update(copy.deepcopy(overrides.get(feature_id, {})))
        style_id = infer_style(item, doc, colors)
        style = doc['styles'][style_id]
        props = dict(airport=code, name=item['name'], layer=style['layer'], category=style['name'], object_type=style['object_type'],
                     style_id=style_id, source_group=Path(item['file']).stem if item['kind']=='label' else item['name'],
                     vsmr_group_ids=[], geometry_role={'polygon':'filled_region','line':'linework','label':'text_label'}[item['kind']])
        if item['kind'] == 'label':
            props['text-field'] = item['name']
        if style_id == 'airport.reference':
            props['geometry_role'] = 'airport_reference_point'
        if style_id.startswith('line.ground_layout_arrows.'):
            props['geometry_role'] = 'directional_arrows'
            props.pop('source_group', None)
        if style_id == 'label.text.label.labels':
            props.pop('source_group', None)
        props.update(options)
        props = {k:v for k,v in props.items() if v is not None}
        features.append(dict(type='Feature', id=feature_id, properties=props, geometry=copy.deepcopy(item['geometry'])))
    doc['features'] = features
    used_groups = {group for feature in features for group in feature['properties'].get('vsmr_group_ids', [])}
    doc['vsmr_groups'] = [group for group in doc.get('vsmr_groups', []) if group['id'] in used_groups]
    return doc


def validate(code, doc):
    if doc.get('type') != 'FeatureCollection' or doc['metadata'].get('geometry_mode') != 'shared':
        raise ValueError(code + ': expected a shared-geometry FeatureCollection')
    ids = set()
    for feature in doc['features']:
        if feature['id'] in ids:
            raise ValueError(code + ': duplicate feature ID ' + feature['id'])
        ids.add(feature['id'])
        if feature['properties']['style_id'] not in doc['styles']:
            raise ValueError(code + ': missing style')
        for point in coordinates(feature['geometry']):
            if len(point) < 2 or not all(math.isfinite(v) for v in point[:2]) or not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
                raise ValueError(code + ': invalid coordinates')


def enable_color():
    if os.name == 'nt':
        kernel = ctypes.windll.kernel32
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_uint()
        if kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel.SetConsoleMode(handle, mode.value | 4)
    return sys.stdout.isatty()


COLOR = False


def say(text='', color='36'):
    print(f'\033[{color}m{text}\033[0m' if COLOR else text, flush=True)


def github_source():
    request = urllib.request.Request(GITHUB_URL, headers={'User-Agent': 'vSMR-AVISO-Converter/2'})
    with urllib.request.urlopen(request, timeout=10) as response:
        data = response.read(64 * 1024 * 1024 + 1)
    if len(data) > 64 * 1024 * 1024:
        raise ValueError('GitHub ZIP exceeds 64 MB')
    source = load_source(io.BytesIO(data))
    require_native_ids(source)
    return source


def require_native_ids(source):
    for code, records in source['airports'].items():
        ids = [r.get('source_id') for r in records]
        if any(not i for i in ids) or len(ids) != len(set(ids)):
            raise ValueError(code + ': source feature identifiers are missing or duplicated')


def local_source():
    candidates = []
    if all((ROOT / name).exists() for name in ('GNG', 'Colours.sct')):
        candidates.append(ROOT)
    folder = ROOT / 'Input'
    if folder.is_dir():
        if all((folder / name).exists() for name in ('GNG', 'Colours.sct')):
            candidates.append(folder)
        candidates.extend(sorted(p for p in folder.iterdir() if p.is_dir() and all((p / name).exists() for name in ('GNG', 'Colours.sct'))))
        candidates.extend(sorted(folder.glob('*.zip'), key=lambda p: p.stat().st_mtime, reverse=True))
    errors = []
    for candidate in candidates:
        try:
            source = load_source(candidate)
            require_native_ids(source)
            say('        Local source: ' + str(candidate), '90')
            return source
        except Exception as error:
            errors.append(str(candidate) + ': ' + str(error))
    raise ValueError('No usable local source. Put GNG/ and Colours.sct beside Script/, or put them, an extracted repository folder, or its ZIP in Input/. ' + '; '.join(errors))


def choose_source(mode='local'):
    if mode == 'github':
        say('        Using official GitHub master', '92')
        return github_source()
    if mode != 'local':
        raise ValueError('Unknown source mode: ' + mode)
    return local_source()


def run(source_path=None, output=None, source_mode='local'):
    start = time.perf_counter()
    output = Path(output) if output is not None else ROOT / 'GeoJSON'
    source_roots = [ROOT]
    if isinstance(source_path, (str, Path)) and Path(source_path).is_dir():
        source_roots.append(Path(source_path))
    for source_root in source_roots:
        for name in ('GNG', 'KMZ', 'Settings', 'Colours.sct'):
            protected = (source_root / name).resolve()
            destination = output.resolve()
            if destination == protected or protected in destination.parents or destination in protected.parents:
                raise ValueError('Output overlaps protected source/settings: ' + str(output))
    say('\n  +----------------------------------------------------------+')
    say('  |                  vSMR AVISO CONVERTER                     |')
    say('  |      France Ground Layouts / GNG source              |')
    say('  +----------------------------------------------------------+\n')
    say('  [1/4] Reading official GitHub...' if source_mode == 'github' else '  [1/4] Reading local source...', '37')
    source = choose_source(source_mode) if source_path is None else load_source(source_path)
    require_native_ids(source)
    say('  [2/4] Applying palettes, groups and runtime settings...', '37')
    saved = load_settings(source['colors'])
    votes = collections.defaultdict(collections.Counter)
    for recipe in saved['recipes'].values():
        for key, original_style in recipe['document']['styles'].items():
            style = copy.deepcopy(original_style)
            style.get('paint', {}).get('palette-overrides', {}).pop('real', None)
            votes[key][packed(style)] += 1
    DEFAULT_STYLES.clear()
    DEFAULT_STYLES.update({key: json.loads(choices.most_common(1)[0][0]) for key, choices in votes.items()})
    products = {}
    all_codes = sorted(source['airports'])
    for n, code in enumerate(all_codes, 1):
        recipe = saved['recipes'].get(code)
        if recipe is None:
            recipe = dict(document=dict(type='FeatureCollection', name=code + ' AVISO', bbox=[], metadata=dict(schema='vSMR AVISO', schema_version=2, geometry_mode='shared', airport=code, coordinate_reference_system='WGS84', coordinate_order='longitude, latitude', default_color_palette='dark', color_palettes=['dark','light'], background_colors={'dark':source['colors']['BACKGROUND_COLOR'],'light':source['colors']['BACKGROUND_COLOR']}), styles={}, vsmr_groups=[]), overrides={})
        doc = convert_airport(code, recipe, source['airports'][code], source['colors'])
        update_counts(doc)
        doc['metadata'].update(geometry_source='vaccfr/France-Ground-Layouts' if source_mode == 'github' else 'local GNG', geometry_source_url='https://github.com/vaccfr/France-Ground-Layouts' if source_mode == 'github' else '', geometry_license='GPL-3.0')
        validate(code, doc)
        products[code + '.geojson'] = serialize_document(doc)
        if n % 50 == 0 or n == len(all_codes):
            say(f'        [{"#" * (n * 24 // len(all_codes)):<24}] {n:3}/{len(all_codes)} airports', '90')
    say('  [3/4] Geometry, style references and coordinates validated.', '37')
    say('  [4/4] Writing GeoJSON files...', '37')
    output.mkdir(parents=True, exist_ok=True)
    for filename, data in products.items():
        path = output / filename
        temp = path.with_suffix(path.suffix + '.tmp')
        temp.write_bytes(data)
        os.replace(temp, path)
    for path in output.glob('????.geojson'):
        if re.fullmatch(r'[A-Z]{4}\.geojson', path.name) and path.name not in products:
            path.unlink()
    say(f'\n  DONE  |  {len(all_codes)} airports  |  {time.perf_counter() - start:.1f} seconds', '92')
    say(f'  Output: {output}', '37')
    say('  Finished automatically. You can close this window.\n', '90')
    return dict(airport_count=len(all_codes))


if __name__ == '__main__':
    COLOR = enable_color()
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        inputs = parser.add_mutually_exclusive_group()
        inputs.add_argument('--local', action='store_true', help='Convert this checkout before committing local source edits')
        inputs.add_argument('--source', type=Path, help='Convert an explicit repository folder or ZIP')
        inputs.add_argument('--github', action='store_true', help='Download original data from vaccfr/France-Ground-Layouts')
        arguments = parser.parse_args()
        run(ROOT if arguments.local else arguments.source, source_mode='github' if arguments.github else 'local')
    except Exception as error:
        say('\n  CONVERSION FAILED: ' + str(error), '91')
        traceback.print_exc()
        sys.exit(1)
