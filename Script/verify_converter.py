"""Offline conversion and native-format regression checks (standard library only)."""
import copy
import collections
import io
import hashlib
import json
import re
from pathlib import Path
import tempfile
from unittest.mock import patch
import zipfile

import aviso_converter as c


def main():
    root = c.ROOT
    def input_hashes():
        paths = [root / 'Colours.sct']
        for folder in ('GNG', 'KMZ', 'Settings'):
            paths.extend(p for p in (root / folder).rglob('*') if p.is_file())
        return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    original_inputs = input_hashes()
    source = c.load_source(root)
    c.require_native_ids(source)
    for path in (root / 'Settings').rglob('*.json'):
        assert not re.search(r'"#[0-9A-Fa-f]{6}"', path.read_text(encoding='utf-8')), 'Palette literals belong in Settings/Colours.sct'
    changed_colors = dict(source['colors'], BACKGROUND_COLOR='#123456')
    changed_settings = c.load_settings(changed_colors)
    assert changed_settings['recipes']['LFPG']['document']['metadata']['background_colors']['dark'] == '#123456'
    assert changed_settings['recipes']['LFPG']['document']['metadata']['background_colors']['real'] == '#6F6F6F'
    lfpo = changed_settings['recipes']['LFPO']['document']
    assert lfpo['metadata']['color_palettes'] == ['dark', 'light', 'real']
    assert lfpo['metadata']['background_colors']['real'] == '#6C6A68'
    assert not any(k.startswith('polygon.terrain2.') for k in lfpo['styles'])
    assert not any(r['color'] == 'COLOR_Terrain2' for r in source['airports']['LFPO'])
    for path in (root / 'GNG' / 'LFFF' / 'LFPO').glob('*.txt'):
        assert not any(r['color'] == 'COLOR_Terrain2' for r in c.parse_gng(path.as_posix(), path.read_bytes()))
    for code, recipe in changed_settings['recipes'].items():
        for mode, color in recipe['document']['metadata']['background_colors'].items():
            if (code, mode) not in (('LFPG', 'real'), ('LFPO', 'real')):
                assert color == '#123456', (code, mode)
    text_settings = c.load_settings(dict(source['colors'], TEXT_COLOR='#123456'))
    for recipe in text_settings['recipes'].values():
        for style in recipe['document']['styles'].values():
            if 'text-color' in style['paint']:
                assert style['paint']['text-color'] == '#123456'
    missing_colors = dict(source['colors'])
    del missing_colors['BACKGROUND_COLOR']
    try:
        c.load_settings(missing_colors)
        raise AssertionError('Undefined palette color accepted')
    except ValueError as error:
        assert 'Undefined palette color' in str(error)
    try:
        c.read_colors(b'#define DARK_TEST 0\n#define DARK_TEST 1\n')
        raise AssertionError('Duplicate palette definition accepted')
    except ValueError as error:
        assert 'Duplicate color' in str(error)
    expected_files = {p.name: p.read_bytes() for p in (root / 'GeoJSON').glob('*.geojson')}
    assert expected_files, 'Generate GeoJSON before running the checks'
    for name, data in expected_files.items():
        doc = json.loads(data)
        allowed = {'ground-layout-east', 'ground-layout-west'} if name == 'LFPG.geojson' else set()
        assert {g['id'] for g in doc.get('vsmr_groups', [])} <= allowed
        for feature in doc['features']:
            assert set(feature['properties'].get('vsmr_group_ids', [])) <= allowed
    with tempfile.TemporaryDirectory(prefix='vsmr-aviso-tests-') as scratch:
        scratch = Path(scratch)
        c.run(root, scratch / 'GeoJSON')
        actual_files = {p.name:p.read_bytes() for p in (scratch / 'GeoJSON').iterdir()}
        assert actual_files == expected_files, 'Committed GeoJSON is not current: regenerate from local source'
        # Every output geometry and label comes from GNG, with no KMZ contribution.
        native = collections.defaultdict(list)
        for path in (root / 'GNG').rglob('*.txt'):
            native[path.parent.name].extend(c.parse_gng(path.relative_to(root).as_posix(), path.read_bytes()))
        for code in list(native):
            published = {Path(r['file']).name for r in native[code]}
            for name, records in c.additional_gng(code).items():
                if name not in published:
                    native[code].extend(records)
        def geometry_counts(records):
            return collections.Counter(c.packed(r['geometry']) for r in records)
        for code, records in source['airports'].items():
            assert geometry_counts(records) == geometry_counts(native[code]), code
            output = json.loads(actual_files[code + '.geojson'])
            assert geometry_counts(output['features']) == geometry_counts(records), code
            assert collections.Counter((r['name'], c.packed(r['geometry'])) for r in records if r['kind'] == 'label') == collections.Counter((r['name'], c.packed(r['geometry'])) for r in native[code] if r['kind'] == 'label'), code
            used = {g for f in output['features'] for g in f['properties']['vsmr_group_ids']}
            assert {g['id'] for g in output['vsmr_groups']} == used

        lfpg = json.loads(actual_files['LFPG.geojson'])
        arrows = [f for f in lfpg['features'] if f['properties']['geometry_role'] == 'directional_arrows']
        assert len(arrows) == 6
        for group in ('ground-layout-east', 'ground-layout-west'):
            grouped = [f for f in arrows if group in f['properties']['vsmr_group_ids']]
            assert len(grouped) == 3
            assert {f['properties']['style_id'].rsplit('.', 1)[-1] for f in grouped} == {'centerline', 'brown', 'green'}
        with patch.object(c, 'additional_gng', return_value={}):
            plain_source = c.load_source(root)
        for code, records in source['airports'].items():
            if code != 'LFPG':
                assert records == plain_source['airports'][code]
        assert len(source['airports']['LFPG']) == len(plain_source['airports']['LFPG']) + 6
        assert c.additional_gng('ZZZZ') == {}
        with patch.object(Path, 'read_text', return_value='{"additional_gng": ["../LFPG outside.txt"]}'):
            try:
                c.additional_gng('LFPG')
                raise AssertionError('Escaping supplemental GNG path accepted')
            except ValueError:
                pass

        # No file from KMZ may be opened, even when present beside the input.
        read_bytes = Path.read_bytes
        def guarded_read(path):
            assert 'KMZ' not in path.parts, 'Converter opened a KMZ file'
            return read_bytes(path)
        with patch.object(Path, 'read_bytes', guarded_read):
            assert c.load_source(root) == source

        # Live GNG edits and deterministic IDs do not depend on another format.
        label = c.parse_gng('GNG/LFFF/TEST/TEST Gates.txt', b'N049.00.00.000 E002.00.00.000 GATE\n')[0]
        shape = dict(file='GNG/LFFF/TEST/TEST Groundlayout.txt', kind='line', color='COLOR_Taxiway', name='line',
                     geometry=dict(type='LineString', coordinates=[[2,49],[2.1,49.1]]))
        gng = {'text': ('TEST', [label, shape])}
        selected = c.assemble_sources(gng)['TEST']
        assert [r['kind'] for r in selected] == ['label', 'line']
        assert c.assemble_sources({}) == {}
        edited = copy.deepcopy(gng)
        edited['text'][1][1]['geometry']['coordinates'][0][0] += 0.01
        assert c.assemble_sources(edited)['TEST'][1]['geometry'] == edited['text'][1][1]['geometry']
        edited['text'][1].append(copy.deepcopy(shape))
        added = c.assemble_sources(edited)['TEST']
        assert len(added) == 3 and len({r['source_id'] for r in added}) == 3
        assert added == c.assemble_sources(edited)['TEST']

        # Protected output paths must fail before creating or modifying any files.
        for destination in (root, root / 'GNG', root / 'KMZ' / 'output', root / 'Settings'):
            try:
                c.run(root, destination)
                raise AssertionError('Source overwrite accepted')
            except ValueError as error:
                assert 'protected source/settings' in str(error)

        # Only GNG and Colours.sct are required in folder and ZIP inputs.
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name in ('GNG', 'Colours.sct'):
                path = root / name
                for file in sorted(path.rglob('*')) if path.is_dir() else [path]:
                    if file.is_file():
                        archive.writestr('France-Ground-Layouts-master/' + file.relative_to(root).as_posix(), file.read_bytes())
        buffer.seek(0)
        assert c.load_source(buffer) == source
        plain = scratch / 'gng-only'
        with zipfile.ZipFile(buffer) as archive:
            archive.extractall(plain)
        assert c.load_source(plain) == source
        assert not list(plain.rglob('KMZ'))
        with zipfile.ZipFile(buffer, 'a') as archive:
            archive.writestr('France-Ground-Layouts-master/KMZ/ZZZZ broken.kmz', b'not a KMZ')
            archive.writestr('France-Ground-Layouts-master/KMZ/Colours.sct', b'invalid, must not be read')
            archive.writestr('France-Ground-Layouts-master/Settings/Colours.sct', b'not the native source colours')
        buffer.seek(0)
        zip_read = zipfile.ZipFile.read
        def guarded_zip_read(archive, name, *args, **kwargs):
            filename = name.filename if isinstance(name, zipfile.ZipInfo) else name
            assert '/KMZ/' not in filename and not filename.startswith('KMZ/'), 'Converter opened KMZ ZIP entry'
            return zip_read(archive, name, *args, **kwargs)
        with patch.object(zipfile.ZipFile, 'read', guarded_zip_read):
            assert c.load_source(buffer) == source
        with patch.object(c, 'github_source', side_effect=AssertionError('Local conversion contacted GitHub')):
            assert c.choose_source() == source
        with patch.object(c, 'github_source', return_value=source), patch.object(c, 'local_source', side_effect=AssertionError('GitHub selection used local input')):
            assert c.choose_source('github') == source
        with patch.object(c, 'github_source', side_effect=OSError('simulated offline')):
            try:
                c.choose_source('github')
                raise AssertionError('Explicit GitHub failure silently changed source')
            except OSError:
                pass

        # Source text/coordinates remain live. Added labels inherit the same settings.
        saved = c.load_settings()
        original = source['airports']['LFPG']
        edited = copy.deepcopy(original)
        gate = next(r for r in edited if r['kind']=='label' and r['name']=='I04')
        gate['name'] = 'RENAMED'
        gate['geometry']['coordinates'][0] += 0.0001
        new_gate = copy.deepcopy(gate)
        new_gate.update(source_id='LFPG-regression-new', name='NEW-GATE')
        edited.append(new_gate)
        deleted = next(r['source_id'] for r in edited if r['kind']=='label' and r['name']=='I05')
        edited = [r for r in edited if r['source_id'] != deleted]
        doc = c.convert_airport('LFPG', saved['recipes']['LFPG'], edited, source['colors'])
        result = {f['id']:f for f in doc['features']}
        assert deleted not in result
        assert result[gate['source_id']]['properties']['text-field']=='RENAMED'
        assert result[gate['source_id']]['geometry']==gate['geometry']
        assert result['LFPG-regression-new']['properties']['style_id']==result[gate['source_id']]['properties']['style_id']
        assert result['LFPG-regression-new']['properties']['vsmr_group_ids']==result[gate['source_id']]['properties']['vsmr_group_ids']

        # Runtime customizations still apply independently of native geometry.
        recipe = copy.deepcopy(saved['recipes']['LFPG'])
        recipe['document']['metadata']['background_colors']['dark'] = '#123456'
        recipe['document']['styles']['label.gates']['paint']['zoomLevel'] = 11
        custom = c.convert_airport('LFPG', recipe, original, source['colors'])
        assert custom['metadata']['background_colors']['dark']=='#123456'
        assert custom['styles']['label.gates']['paint']['zoomLevel']==11
        assert [f['geometry'] for f in custom['features']]==[r['geometry'] for r in original]

        broken = scratch / 'broken.zip'
        broken.write_bytes(b'not a zip')
        try:
            c.run(broken, scratch / 'GeoJSON')
            raise AssertionError('Malformed ZIP accepted')
        except zipfile.BadZipFile:
            pass
        assert {p.name:p.read_bytes() for p in (scratch / 'GeoJSON').iterdir()} == actual_files
        assert not list(scratch.rglob('Conversion report.json'))
        assert not list(scratch.rglob('Conversion summary.txt'))
    assert input_hashes() == original_inputs, 'Conversion modified official sources or settings'
    print(f'PASS: {len(expected_files)} GeoJSON files; {sum(len(r) for r in source["airports"].values())} native features; GNG-only inputs, ignored KMZ and unchanged sources; source edits; palettes/groups; explicit local/GitHub selection.')


if __name__ == '__main__':
    main()
