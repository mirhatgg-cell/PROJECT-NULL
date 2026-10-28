#!/usr/bin/env python3
"""Extend the V10 place into a connected ocean vessel without replacing its labs."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from build_v10 import lua_literal
from v7_common import name
from v9_common import Builder9, setprop
import v11_hull
import v11_interiors
import v11_npcs

ROOT = Path(__file__).resolve().parents[1]
BASE_CLASSES = {'Part', 'Seat', 'SpawnLocation', 'MeshPart', 'WedgePart', 'UnionOperation'}
LOWER_ROOMS = [
    ('E01','Подготовка / передача смены',(-15.5,15.5,-65,-38,-75.5,-48.5)),
    ('E02','Шлюз лабораторий',(-7.5,7.5,-65,-38,-46.5,-25.5)),
    ('E03','Камера погружения',(-23.5,23.5,-65,-36,-23.5,23.5)),
    ('E04','Операторская',(-63.5,-24.5,-65,-38,-11.5,11.5)),
    ('E05','Восстановление',(40.5,79.5,-65,-38,-23.5,7.5)),
    ('E06','Медицинский пост',(46.5,73.5,-65,-38,-69.5,-46.5)),
    ('E07','Калибровка и независимый журнал',(-57.5,-30.5,-65,-38,-59.5,-36.5)),
    ('E08','Чистые расходники',(46.5,77.5,-65,-38,51.5,78.5)),
    ('E09','Снятое оборудование',(-51.5,-32.5,-65,-38,54.5,69.5)),
    ('E10','Физический зал',(126.5,181.5,-65,-38,-35.5,35.5)),
    ('E11','Подготовка физического зала',(138.5,169.5,-65,-38,-75.5,-48.5)),
    ('E12','Управление физическим залом',(186.5,217.5,-65,-38,-11.5,11.5)),
    ('E13','Архив поколений оборудования',(134.5,173.5,-65,-38,56.5,87.5)),
    ('E16','Аппаратная',(-15.5,15.5,-65,-38,51.5,74.5)),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts/PROJECT_NULL_OCEAN_V11.rbxlx')
    args = parser.parse_args()
    source = ROOT/'artifacts/PROJECT_NULL_GAMEPLAY_V10.rbxlx'
    tree = ET.parse(source)
    root = tree.getroot()
    before = {e.get('referent'): e for e in root.iter('Item')}
    old_properties = {r: ET.tostring(e.find('Properties')) for r,e in before.items()}
    old_parents = {c.get('referent'): p.get('referent') for p in root.iter('Item') for c in p.findall('Item')}
    b = Builder9(root)
    facility = b.find('PROJECT_NULL_ARCH_P01', cls='Model')
    assert facility is not None and b.find('Ocean_Complex_V11') is None
    addition = b.model(facility, 'Ocean_Complex_V11')
    b.note(addition, 'README', 'V11 extends the existing laboratories into an ocean vessel. '
           'Scene dimensions and waterline are implementation choices, not a canon depth. '
           'Existing protocols, incident chronology and save keys are retained.')
    hull = v11_hull.build(b, addition, root)
    interiors = v11_interiors.build(b, addition, root)
    npcs = v11_npcs.build(b, addition, root)
    # All new service access uses F; E keeps its original gameplay meaning.
    for service in b.services:
        panel = next(e for e in root.iter('Item') if e.get('referent') == service['panel'])
        prompt = b.find('V9_ServicePrompt', under=panel, cls='ProximityPrompt')
        if prompt is not None: setprop(prompt, 'token', 'KeyboardKeyCode', 102)

    server = b.find('ProjectNullV10', under=next(e for e in root.findall('Item') if e.get('class')=='ServerScriptService'), cls='Folder')
    network = b.find('ProjectNullV10', under=next(e for e in root.findall('Item') if e.get('class')=='ReplicatedStorage'), cls='Folder')
    content = json.loads((ROOT/'tools/v11_content.json').read_text())
    old_content = json.loads((ROOT/'tools/v10_content.json').read_text())
    old_docs = {d['id']:d for d in old_content['documents']}
    docs = {d['id']:d for d in content['documents']}
    assert len(docs)==len(content['documents'])
    assert all(k in docs and all(docs[k].get(field) == value for field,value in v.items())
               for k,v in old_docs.items()), 'Original document fields must be retained'
    rooms = [{'id':i,'label':label,'bounds':bounds,'deck':'Лабораторная палуба'} for i,label,bounds in LOWER_ROOMS]
    rooms.extend(interiors.get('rooms', []))
    rooms.append({'id':'BRIDGE','label':'Ходовой мостик','bounds':(215,255,-29,-7,-40,40),'deck':'Верхняя палуба'})
    # Authoring metadata can use tuples; Lua modules contain JSON-shaped data.
    rooms = json.loads(json.dumps(rooms, ensure_ascii=False))
    ship_config = json.loads(json.dumps({'water': hull.get('water',{}), 'rooms': rooms}, ensure_ascii=False))
    scripts = {}
    def source_item(parent, cls, label, code, path=None, existing=None):
        item = existing if existing is not None else b.item(parent,cls,label)
        setprop(item,'ProtectedString','Source',code)
        if cls!='ModuleScript': setprop(item,'bool','Disabled',False)
        scripts[label]={'referent':item.get('referent'),'class':cls,'source':path,
                        'sha256':hashlib.sha256(code.encode()).hexdigest()}
        return item
    for label, filename in [('ProjectNullServer_V10','ProjectNullServer_V10.server.luau'),
                            ('ProjectNullClient_V10','ProjectNullClient_V10.client.luau')]:
        existing=b.find(label,cls='Script' if 'Server' in label else 'LocalScript')
        source_item(server,existing.get('class'),label,(ROOT/'src'/filename).read_text(),
                    'src/'+filename,existing)
    source_item(server,'ModuleScript','Content','-- V11 server-only narrative data.\nreturn '+lua_literal(content)+'\n',
                'tools/v11_content.json',b.find('Content',under=server,cls='ModuleScript'))
    for label, filename in [('Dialogue','Dialogue_V11.luau'),('NPCDirector','NPCDirector_V11.luau'),('OceanEnvironment','OceanEnvironment_V11.luau')]:
        source_item(server,'ModuleScript',label,(ROOT/'src'/filename).read_text(),'src/'+filename)
    source_item(server,'ModuleScript','ShipConfig','return '+lua_literal(ship_config)+'\n')
    source_item(network,'ModuleScript','WorldConfig','return '+lua_literal({'rooms':rooms})+'\n')
    args.output.parent.mkdir(exist_ok=True,parents=True)
    tree.write(args.output,encoding='utf-8',xml_declaration=True)
    current={e.get('referent'):e for e in root.iter('Item')}
    modified=[r for r in before if r in current and old_properties[r]!=ET.tostring(current[r].find('Properties'))]
    removed=sorted(set(before)-set(current))
    new=[e for r,e in current.items() if r not in before]
    parts=[e for e in new if e.get('class') in BASE_CLASSES]
    manifest={'version':11,'source':str(source.relative_to(ROOT)),
              'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'output_sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),
              'new_classes':dict(Counter(e.get('class') for e in new)),
              'new_parts':len(parts),'new_collidable_parts':sum(e.findtext("Properties/bool[@name='CanCollide']")=='true' for e in parts),
              'roles':b.roles,'services':b.services,'cavities':b.cavities,
              'hull':hull,'interiors':interiors,'npcs':npcs,'scripts':scripts,
              'modified_refs':modified,'removed_refs':removed,
              'modification_reasons':{'portal':'One west outer wall is split to connect the laboratory gallery to the new stairs.',
                    'npcs':'The two existing named staff models are upgraded to articulated R6 rigs; obsolete rigid joints/appearance are replaced.',
                    'sources':'The existing server, client and content module are extended in place; existing remotes and save key are retained.'},
              'documents':list(docs),'rooms':rooms}
    args.output.with_name('V11_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('version','new_parts','new_collidable_parts','new_classes')},ensure_ascii=False,indent=2))
    print('New services:',len(b.services),'cavities:',len(b.cavities),'documents:',len(docs),'rooms:',len(rooms))


if __name__=='__main__':main()
