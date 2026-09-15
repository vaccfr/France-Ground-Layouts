"""Offline checks that also work on unmodified official GNG layouts."""
import copy
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import aviso_converter as c


def main():
    source = c.load_source(c.ROOT)
    c.require_native_ids(source)
    settings = c.load_settings()
    colors = c.palette_colors()
    changed = c.load_settings(dict(colors, TEXT_COLOR='#123456', TEXT_HALO_COLOR='#654321'))
    for code, recipe in settings['recipes'].items():
        old = recipe['document']
        new = copy.deepcopy(changed['recipes'][code]['document'])
        for key, style in old['styles'].items():
            for prop in ('text-color', 'text-halo-color'):
                if prop in style['paint']:
                    assert new['styles'][key]['paint'][prop] == ('#123456' if prop == 'text-color' else '#654321')
                    new['styles'][key]['paint'][prop] = style['paint'][prop]
        assert new == old, 'Text controls changed non-text rendering: ' + code
    changed = c.load_settings(dict(colors, BACKGROUND_COLOR='#123456'))
    for code, recipe in changed['recipes'].items():
        for mode, color in recipe['document']['metadata']['background_colors'].items():
            assert color == ({('LFPG', 'real'): '#6F6F6F', ('LFPO', 'real'): '#6C6A68'}.get((code, mode), '#123456'))
    with patch.object(c, 'github_source', side_effect=AssertionError('Local mode contacted GitHub')):
        assert c.choose_source() == source
    with patch.object(c, 'github_source', return_value=source), patch.object(c, 'local_source', side_effect=AssertionError('GitHub mode used local source')):
        assert c.choose_source('github') == source
    with tempfile.TemporaryDirectory(prefix='aviso-upstream-') as temporary:
        output = Path(temporary)
        c.run(c.ROOT, output)
        first = {p.name: p.read_bytes() for p in output.glob('*.geojson')}
        assert len(first) == len(source['airports']) and first
        for name, data in first.items():
            doc = json.loads(data)
            c.validate(name[:4], doc)
            assert doc['metadata']['geometry_source'] == 'local GNG'
        c.run(c.ROOT, output)
        assert first == {p.name: p.read_bytes() for p in output.glob('*.geojson')}
    print('PASS: deterministic conversion, explicit sources, isolated text controls and background exceptions.')


if __name__ == '__main__':
    main()
