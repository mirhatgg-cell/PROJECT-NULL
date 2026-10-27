#!/usr/bin/env python3
"""Build the narrative and playable-procedure pass on the unchanged V9 place."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from v7_common import name
from v9_common import Builder9
import v10_world
import v10_feedback

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'Narrative_Gameplay_V10'


def lua_literal(value):
    """Serialize only JSON data, without evaluating user-controlled source."""
    if value is None:
        return 'nil'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        # JSON UTF-8 strings use the same escapes as Lua for this content.
        # Encode the two JSON-only control escapes as decimal Lua escapes.
        return json.dumps(value, ensure_ascii=False).replace('\\b', '\\008').replace('\\f', '\\012')
    if isinstance(value, list):
        return '{' + ','.join(lua_literal(v) for v in value) + '}'
    if isinstance(value, dict):
        return '{' + ','.join('[' + lua_literal(str(k)) + ']=' + lua_literal(v)
                              for k, v in value.items()) + '}'
    raise TypeError(type(value))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'artifacts/PROJECT_NULL_GAMEPLAY_V10.rbxlx')
    args = parser.parse_args()
    source = ROOT / 'artifacts/PROJECT_NULL_ENGINEERING_V9.rbxlx'
    tree = ET.parse(source)
    root = tree.getroot()
    before = {e.get('referent'): e for e in root.iter('Item')}
    equipment = next(e for e in root.iter('Item')
                     if e.get('class') == 'Model' and name(e) == 'Equipment')
    assert not any(name(e) == MODEL for e in equipment.findall('Item'))
    builder = Builder9(root)
    addition = builder.model(equipment, MODEL)
    builder.note(addition, 'README',
                 'V10: local documentary narrative, five playable laboratory procedures, '
                 'physical supply/medical/cooling stations and staff. V9 physical equipment '
                 'and all legacy scripts are retained. The nature of NULL is not resolved.')
    world = v10_world.build(builder, addition, root)
    feedback = v10_feedback.build(builder, addition, root)
    content = json.loads((ROOT / 'tools/v10_content.json').read_text())
    ids = [d['id'] for d in content['documents']]
    assert len(ids) == len(set(ids)), 'Duplicate document IDs'
    assert all(d.get('title') and d.get('body') and d.get('room') for d in content['documents'])

    def service(cls, label):
        found = next((e for e in root.findall('Item') if e.get('class') == cls), None)
        return found if found is not None else builder.item(root, cls, label)

    server_service = service('ServerScriptService', 'ServerScriptService')
    server_folder = builder.item(server_service, 'Folder', 'ProjectNullV10')
    scripts = {}

    def script(parent, cls, label, code, source_path=None):
        item = builder.item(parent, cls, label)
        builder.prop(item, 'ProtectedString', 'Source', code)
        if cls != 'ModuleScript':
            builder.prop(item, 'bool', 'Disabled', False)
        scripts[label] = {'referent': item.get('referent'), 'class': cls,
                          'source': source_path,
                          'sha256': hashlib.sha256(code.encode()).hexdigest()}
        return item

    script(server_folder, 'ModuleScript', 'ExperimentCore',
           (ROOT / 'src/ExperimentCore_V10.luau').read_text(), 'src/ExperimentCore_V10.luau')
    script(server_folder, 'ModuleScript', 'Content',
           '-- Generated from tools/v10_content.json; server-only evidence.\nreturn ' + lua_literal(content) + '\n',
           'tools/v10_content.json')
    script(server_folder, 'Script', 'ProjectNullServer_V10',
           (ROOT / 'src/ProjectNullServer_V10.server.luau').read_text(),
           'src/ProjectNullServer_V10.server.luau')

    replicated = service('ReplicatedStorage', 'ReplicatedStorage')
    remote_folder = builder.item(replicated, 'Folder', 'ProjectNullV10')
    for label in ('Request', 'Push'):
        builder.item(remote_folder, 'RemoteEvent', label)

    starter = service('StarterPlayer', 'StarterPlayer')
    player_scripts = next((e for e in starter.findall('Item')
                           if e.get('class') == 'StarterPlayerScripts'), None)
    if player_scripts is None:
        player_scripts = builder.item(starter, 'StarterPlayerScripts', 'StarterPlayerScripts')
    script(player_scripts, 'LocalScript', 'ProjectNullClient_V10',
           (ROOT / 'src/ProjectNullClient_V10.client.luau').read_text(),
           'src/ProjectNullClient_V10.client.luau')

    args.output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(args.output, encoding='utf-8', xml_declaration=True)
    current = {e.get('referent'): e for e in root.iter('Item')}
    assert set(before) <= set(current), 'V10 may not delete the V9 baseline'
    new = [e for ref, e in current.items() if ref not in before]
    base_classes = {'Part', 'Seat', 'SpawnLocation', 'MeshPart', 'WedgePart', 'UnionOperation'}
    parts = [e for e in new if e.get('class') in base_classes]
    manifest = {
        'version': 10, 'source': str(source.relative_to(ROOT)),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'output_sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
        'new_classes': dict(Counter(e.get('class') for e in new)),
        'new_parts': len(parts),
        'new_collidable_parts': sum(e.findtext("Properties/bool[@name='CanCollide']") == 'true'
                                    for e in parts),
        'roles': builder.roles, 'services': builder.services,
        'cavities': builder.cavities, 'world': world, 'feedback': feedback, 'scripts': scripts,
        'documents': ids,
    }
    args.output.with_name('V10_MANIFEST.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: manifest[key] for key in
                      ('version', 'new_classes', 'new_parts', 'new_collidable_parts')},
                     ensure_ascii=False, indent=2))
    print('Documents:', len(ids), 'service accesses:', len(builder.services),
          'cavities:', len(builder.cavities))


if __name__ == '__main__':
    main()
