#!/usr/bin/env python3
"""V9 engineering rework: physical equipment, interiors, service access and motion."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from v7_common import name
from v9_common import Builder9
from v9_collision_policy import should_collide
import v9_metrology
import v9_experimental
import v9_thermal
import v9_immersion_medical

ROOT=Path(__file__).resolve().parents[1]
MODEL='Engineering_Rework_V9'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/PROJECT_NULL_ENGINEERING_V9.rbxlx')
    args=parser.parse_args()
    source=ROOT/'artifacts/PROJECT_NULL_EXPERIMENTAL_V8.rbxlx'
    tree=ET.parse(source);root=tree.getroot()
    before={e.get('referent'):e for e in root.iter('Item')}
    equipment=next(e for e in root.iter('Item') if e.get('class')=='Model' and name(e)=='Equipment')
    assert not any(name(e)==MODEL for e in equipment.findall('Item'))
    b=Builder9(root)
    addition=b.model(equipment,MODEL)
    b.note(addition,'README','V9 engineering rework: physical main structures, hollow cases, modeled internals, service doors/drawers, maintenance access and working NIF amplifier cutoff. Original main architecture and three legacy controllers are retained; V7/V8 prototype equipment is deliberately rebuilt.')
    for module in (v9_metrology,v9_experimental,v9_thermal,v9_immersion_medical):
        module.build(b,addition,root)
    # Upgrade every surviving older addon according to explicit part roles.
    legacy=[]
    for old_name in ('Visual_Detail_V7','Experimental_Equipment_V8'):
        old=b.find(old_name,under=equipment)
        if old is None:continue
        for part in old.iter('Item'):
            if part.get('class')!='Part':continue
            ref=part.get('referent')
            if ref in b.roles:continue
            if should_collide(part):
                b.role(part,'structure');legacy.append(ref)
            else:b.roles[ref]='detail'
    server=next(e for e in root.findall('Item') if e.get('class')=='ServerScriptService')
    controller=b.item(server,'Script','ServiceController_V9')
    b.prop(controller,'ProtectedString','Source',(ROOT/'src/ServiceController_V9.server.luau').read_text())
    b.prop(controller,'bool','Disabled',False)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    tree.write(args.output,encoding='utf-8',xml_declaration=True)
    current={e.get('referent'):e for e in root.iter('Item')}
    new=[e for ref,e in current.items() if ref not in before]
    baseclasses={'Part','Seat','SpawnLocation','MeshPart','WedgePart','UnionOperation'}
    newparts=[e for e in new if e.get('class') in baseclasses]
    counts=Counter(e.get('class') for e in new)
    manifest={
        'version':9,'source':str(source.relative_to(ROOT)),'output':str(args.output),
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'output_sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),
        'new_classes':dict(counts),'new_parts':len(newparts),
        'new_collidable_parts':sum(e.findtext("Properties/bool[@name='CanCollide']")=='true' for e in newparts),
        'legacy_physicalized':legacy,'removed':b.removed,
        'removed_refs':sorted(set(before)-set(current)),
        'roles':{ref:role for ref,role in b.roles.items() if ref in current},
        'services':b.services,'cavities':b.cavities,
        'groups':{name(e):sum(p.get('class')=='Part' for p in e.iter('Item')) for e in addition.findall('Item') if e.get('class')=='Model'},
        'controller_ref':controller.get('referent'),
    }
    manifest_path=args.output.with_name('V9_MANIFEST.json')
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('new_classes','new_parts','new_collidable_parts','groups')},indent=2,ensure_ascii=False))
    print('Services:',len(b.services),'cavities:',len(b.cavities),'legacy structures physicalized:',len(legacy))


if __name__=='__main__':main()
