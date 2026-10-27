#!/usr/bin/env python3
"""V9 physical roles, actual equipment cavities, service metadata and clearances.

These are static XML/OBB checks, not a Roblox Studio physics or avatar test.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from audit_v8_geometry import Box, load, sat_penetration
from v7_common import name
from v9_collision_policy import PRIMARY_NAMES

ROOT=Path(__file__).resolve().parents[1]
SOLID={'structure','housing','panel','walkable'}
ROLES=SOLID|{'detail','internal','control'}
BASE={'Part','Seat','SpawnLocation','MeshPart','WedgePart','UnionOperation','TrussPart'}

# Standing body corridors, not a complete navigation mesh. Room boundaries
# are deliberately avoided so closed main entry leaves are not treated as bugs.
PASSAGES={
    'E03_south_approach':((-1.25,1.25),(-63.0,-58.5),(-22,-7)),
    'E06_central_route':((58.6,61.4),(-63.0,-58.5),(-68.3,-47.7)),
    'E07_working_aisle':((-39.65,-36.25),(-63.0,-58.5),(-54.8,-44.5)),
    'E10_central_route':((152.6,155.4),(-63.0,-58.5),(-33.8,33.8)),
    'E16_entry_approach':((-1.35,1.35),(-63.0,-58.5),(52.5,61.0)),
}


def items(root):
    entries=list(root.iter('Item'))
    indexed={e.get('referent'):e for e in entries}
    assert len(indexed)==len(entries),'Duplicate referents'
    parents={child.get('referent'):p.get('referent') for p in entries for child in p.findall('Item')}
    return indexed,parents


def boolprop(item,key,default=False):
    return item.findtext(f"Properties/bool[@name='{key}']",str(default).lower())=='true'


def box_for_bounds(label,bounds):
    center=np.array([(lo+hi)/2 for lo,hi in bounds])
    half=np.array([(hi-lo)/2 for lo,hi in bounds])
    return Box(label,label,label,'Part',center,half,np.eye(3),half,0,False,False,'block')


def ancestors(ref,parents):
    while ref in parents:
        ref=parents[ref]
        yield ref


def path_of(ref,indexed,parents):
    return '/'.join(reversed([name(indexed[ref])]+[name(indexed[a]) for a in ancestors(ref,parents)]))


def rotation(axis,angle):
    a=math.radians(angle);c,s=math.cos(a),math.sin(a)
    return {
        'X':np.array([[1,0,0],[0,c,-s],[0,s,c]]),
        'Y':np.array([[c,0,s],[0,1,0],[-s,0,c]]),
        'Z':np.array([[c,-s,0],[s,c,0],[0,0,1]]),
    }[axis]


def validate(source,target,manifest_path,original_path):
    manifest=json.loads(manifest_path.read_text())
    oldroot=ET.parse(source).getroot();root=ET.parse(target).getroot();base_root=ET.parse(original_path).getroot()
    before,before_parents=items(oldroot);current,parents=items(root);original,original_parents=items(base_root)
    _,all_boxes=load(target)
    boxes={b.ref:b for b in all_boxes}
    _,old_boxes=load(source)
    old_box_index={b.ref:b for b in old_boxes}
    roles=manifest.get('roles',manifest.get('new_roles',manifest.get('newroles',{})))
    assert isinstance(roles,dict) and roles,'Missing physical role manifest'
    assert set(roles.values())<=ROLES,'Unknown physical role'
    broken=[ref.text for ref in root.iter('Ref') if ref.text not in (None,'null','nil') and ref.text not in current]
    assert not broken,('Broken references',broken)

    # The architectural shell, main doors and all pre-existing script sources
    # must survive; equipment upgrades are intentionally allowed elsewhere.
    protected=[]
    for ref,item in original.items():
        path=path_of(ref,original,original_parents)
        if '/B2_Architecture/' in path or '/Doors/' in path or item.get('class') in ('Script','LocalScript','ModuleScript'):
            protected.append(ref)
            assert ref in current,('Protected original deleted',path)
            assert ET.tostring(item.find('Properties'))==ET.tostring(current[ref].find('Properties')),('Protected original modified',path)
            assert original_parents.get(ref)==parents.get(ref),('Protected original reparented',path)

    errors=[]
    for ref,role in roles.items():
        if ref not in current:
            # A module can deliberately replace a part built earlier in the
            # same construction pass; removed entries are reported separately.
            continue
        part=current[ref]
        if part.get('class') not in BASE:
            errors.append(f'Role assigned to nonpart: {ref}');continue
        expected_solid=role in SOLID
        expected_query=expected_solid or role=='control'
        if boolprop(part,'CanCollide')!=expected_solid or boolprop(part,'CanQuery')!=expected_query:
            errors.append(f'Role flags differ: {path_of(ref,current,parents)} / {role}')
        if not boolprop(part,'Anchored'):
            errors.append(f'Unanchored authored equipment: {path_of(ref,current,parents)}')
        if boolprop(part,'CanTouch'):
            errors.append(f'Unexpected touch sensor: {path_of(ref,current,parents)}')
        if expected_solid and float(part.findtext("Properties/float[@name='Transparency']",'0'))>=.95:
            errors.append(f'Invisible primary solid: {path_of(ref,current,parents)}')

    # Retained large V7/V8 additions should not keep the old all-decorative flags.
    legacy=[]
    for ref,item in before.items():
        if ref in original or item.get('class')!='Part' or ref not in current:continue
        if name(item) in PRIMARY_NAMES:
            if not boolprop(current[ref],'CanCollide') or not boolprop(current[ref],'CanQuery'):
                errors.append(f'Retained primary addition is still pass-through: {path_of(ref,current,parents)}')
            legacy.append(ref)

    active_roles={ref:role for ref,role in roles.items() if ref in current}
    solid_refs={ref for ref,role in active_roles.items() if role in SOLID}
    assert len(solid_refs)>=50,'V9 needs real primary collision geometry'

    # Every declared cavity must have a real internal assembly in its physical
    # volume. Thin shelves crossing the center are valid; full filled proxies
    # are rejected by coverage AND volume, not merely center intersection.
    cavities=manifest.get('cavities',[])
    assert cavities,'No equipment cavities registered'
    cavity_results=[]
    for cavity in cavities:
        model=cavity['model'];assert model in current,('Missing cavity model',model)
        center=np.array(cavity['center'],dtype=float)
        outer=np.array(cavity['size'],dtype=float)
        thickness=float(cavity.get('thickness',.12))
        matrix=np.array(cavity.get('matrix',np.eye(3)),dtype=float)
        assert np.allclose(matrix.T@matrix,np.eye(3),atol=1e-6)
        half=outer/2-thickness
        assert (half>0).all()
        scopes=[model]
        if model in parents:scopes.append(parents[model])
        inside=[];filled=[];scope_used=model
        for scope in scopes:
            descendants={e.get('referent') for e in current[scope].iter('Item')}
            found=[]
            for ref in descendants:
                if ref not in boxes or roles.get(ref)!='internal':continue
                point=matrix.T@(boxes[ref].center-center)
                if np.all(np.abs(point)<=half+.02):found.append(ref)
            if found:
                inside=found;scope_used=scope;break
        # Check all scene solids in the inner volume, not only that model's
        # descendants, so a retained filled V8 block cannot hide inside a shell.
        for ref in solid_refs:
            box=boxes[ref]
            point=matrix.T@(box.center-center)
            extent=np.abs(matrix.T@box.rotation)@box.half
            overlap=np.maximum(0,np.minimum(point+extent,half)-np.maximum(point-extent,-half))
            coverage=overlap/(2*half)
            actual_volume=float(np.prod(2*box.half))
            inner_volume=float(np.prod(2*half))
            if min(coverage)>=.75 and actual_volume/inner_volume>=.5:
                filled.append(ref)
        if not inside:errors.append(f'Cavity has no spatially contained internal assembly: {path_of(model,current,parents)}')
        if filled:errors.append(f'Cavity filled by solid volume: {path_of(model,current,parents)} / {filled}')
        cavity_results.append({'model':model,'path':path_of(model,current,parents),
                               'internal_scope':scope_used,'internal_parts_inside':len(inside),
                               'filled_collision_proxies':filled})

    # Service metadata must refer to actual panel/mover parts and actual
    # ProximityPrompts; this catches attractive but non-opening fake covers.
    services=manifest.get('services',[]);assert services,'No service panel registrations'
    seen_movers=set();sweep_collisions=[];inward_panels=[]
    arch=[box for box in all_boxes if '/B2_Architecture/' in box.path and boolprop(current[box.ref],'CanCollide',True)]
    arch_centers=np.array([b.center for b in arch]);arch_extents=np.array([b.extent for b in arch])
    for entry in services:
        ref=entry['panel'];assert ref in current and ref in boxes,('Missing service panel',ref)
        panel=current[ref]
        assert roles.get(ref)=='panel',('Service panel role missing',ref)
        prompts=[e for e in panel.findall('Item') if e.get('class')=='ProximityPrompt']
        assert len(prompts)==1,('Missing service prompt',path_of(ref,current,parents))
        prompt=prompts[0]
        assert boolprop(prompt,'RequiresLineOfSight') and boolprop(prompt,'Enabled')
        assert 0<float(prompt.findtext("Properties/float[@name='MaxActivationDistance']",'0'))<=10
        assert entry['axis'] in ('X','Y','Z','Slide') and 0<abs(float(entry['angle']))<=150
        pivot=np.array(entry['pivot'],dtype=float);assert np.isfinite(pivot).all()
        slide=np.array(entry.get('delta',(0,0,0)),dtype=float)
        if entry['axis']=='Slide':
            assert np.isfinite(slide).all() and float(np.linalg.norm(slide))>0,('Invalid slide travel',ref)
        moving=entry['moving'];assert moving and ref in moving and len(moving)==len(set(moving))
        assert not seen_movers.intersection(moving),'A part is controlled by multiple service hinges'
        seen_movers.update(moving)
        # Infer the actual closed face from panel location rather than the
        # cavity's nominal front: a fixed-front tank may open at its top.
        cavity_by_model={c['model']:c for c in cavities}
        owner=next((cavity_by_model[a] for a in ancestors(ref,parents) if a in cavity_by_model),None)
        if owner is not None and entry['axis']!='Slide':
            cc=np.array(owner['center'],dtype=float);rr=np.array(owner.get('matrix',np.eye(3)),dtype=float)
            hh=np.array(owner['size'],dtype=float)/2
            local=rr.T@(boxes[ref].center-cc)
            face_axis=int(np.argmax(np.abs(local)/hh));face_sign=1 if local[face_axis]>=0 else -1
            inner=hh-float(owner.get('thickness',.12))
            if abs(local[face_axis])/hh[face_axis]>.7:
                for fraction in np.linspace(.125,1,8):
                    q=rotation(entry['axis'],float(entry['angle'])*float(fraction))
                    posed=rr.T@(pivot+q@(boxes[ref].center-pivot)-cc)
                    if face_sign*posed[face_axis] < inner[face_axis]-.03 and np.all(np.abs(posed)<=inner+.03):
                        inward_panels.append({'panel':ref,'path':path_of(ref,current,parents),'fraction':float(fraction),'cavity_model':owner['model']})
                        break
        for mover in moving:
            assert mover in boxes,('Invalid moving part',mover)
            # Sample covers and attached physical structures only; tiny labels
            # can slightly protrude intentionally and are not avatar obstacles.
            if not boolprop(current[mover],'CanCollide'):continue
            start=boxes[mover]
            for fraction in np.linspace(0,1,9):
                angle=float(entry['angle'])*float(fraction)
                if entry['axis']=='Slide':
                    pos=start.center+slide*float(fraction);rot=start.rotation
                else:
                    q=rotation(entry['axis'],float(angle))
                    pos=pivot+q@(start.center-pivot);rot=q@start.rotation
                extent=np.abs(rot)@start.half
                posed=replace(start,center=pos,rotation=rot,extent=extent)
                broad=np.where(np.all(np.abs(arch_centers-pos)<arch_extents+extent-.04,axis=1))[0]
                for index in broad:
                    obstacle=arch[int(index)]
                    depth=sat_penetration(posed,obstacle,.04)
                    if depth is not None:
                        sweep_collisions.append({'panel':ref,'mover':mover,'angle':round(float(angle),3),
                                                 'obstacle':obstacle.ref,'path':obstacle.path,'overlap':round(depth,5)})
    if sweep_collisions:errors.append(f'Service cover sweep intersects original architecture: {len(sweep_collisions)} sampled candidates')
    if inward_panels:errors.append(f'Service cover opens into its own cavity: {len(inward_panels)} panels')

    # Sampled standing-body passage volumes. These are static geometric bounds,
    # not claims about Humanoid step height or dynamic pathfinding.
    all_solids=[box for box in all_boxes if boolprop(current[box.ref],'CanCollide',True)]
    centers=np.array([b.center for b in all_solids]);extents=np.array([b.extent for b in all_solids])
    route_results=[]
    for label,bounds in PASSAGES.items():
        corridor=box_for_bounds(label,bounds)
        broad=np.where(np.all(np.abs(centers-corridor.center)<extents+corridor.extent-.025,axis=1))[0]
        obstructions=[]
        for index in broad:
            box=all_solids[int(index)]
            depth=sat_penetration(corridor,box,.025)
            if depth is not None:obstructions.append({'ref':box.ref,'path':box.path,'overlap':round(depth,5)})
        if obstructions:errors.append(f'Standing-body corridor obstructed: {label}')
        route_results.append({'name':label,'bounds':bounds,'obstructions':obstructions})

    # Preserve access to all original click targets by checking that no new
    # physical volume fills their target itself; raycast behavior still needs
    # real Studio testing because opening panels changes visibility dynamically.
    clicks=[box for box in old_boxes if box.interactive and box.ref in original]
    new_solids=[boxes[ref] for ref in solid_refs if ref not in original]
    control_overlaps=[]
    if new_solids:
        ncenters=np.array([box.center for box in new_solids]);nextents=np.array([box.extent for box in new_solids])
        for target_box in clicks:
            broad=np.where(np.all(np.abs(ncenters-target_box.center)<nextents+target_box.extent-.025,axis=1))[0]
            for index in broad:
                box=new_solids[int(index)]
                depth=sat_penetration(target_box,box,.025)
                if depth is not None:control_overlaps.append({'target':target_box.describe(),'solid':box.describe(),'overlap':round(depth,5)})
    if control_overlaps:errors.append(f'Primary solids intersect existing click targets: {len(control_overlaps)}')

    before_added=[e for ref,e in before.items() if ref not in original and e.get('class') in BASE]
    changed_refs=[ref for ref,e in before.items() if ref in current and ET.tostring(e.find('Properties'))!=ET.tostring(current[ref].find('Properties'))]
    removed_refs=set(before)-set(current)
    return {
        'result':'PASS' if not errors else 'REVIEW_REQUIRED',
        'validation':'Static XML and conservative OBB checks; no Roblox Studio physics/rendering/avatar execution',
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'target_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'legacy_addon_parts_before':len(before_added),'legacy_addon_collidable_before':sum(boolprop(e,'CanCollide') for e in before_added),
        'protected_architecture_door_and_script_instances':len(protected),
        'retained_legacy_primary_parts_checked':len(legacy),'modified_existing_instances':len(changed_refs),
        'removed_existing_instances':len(removed_refs),'authored_part_roles':dict(Counter(active_roles.values())),
        'authored_primary_collision_parts':len(solid_refs),'registered_cavities':len(cavities),
        'cavities':cavity_results,'service_panels':len(services),'service_sweep_samples_per_mover':9,
        'service_sweep_architecture_candidates':sweep_collisions,'service_panels_opening_into_own_cavity':inward_panels,'standing_body_corridors':route_results,
        'original_click_targets_checked':len(clicks),'new_solid_vs_original_click_target_candidates':control_overlaps,
        'limitations':['Corridor boxes are representative routes, not a full Humanoid navigation test.',
                       'Click-target checks detect volume overlap, not line-of-sight changes during animation.',
                       'Cylinders and meshes use conservative oriented bounding boxes.'],
        'errors':errors,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'artifacts/PROJECT_NULL_EXPERIMENTAL_V8.rbxlx')
    parser.add_argument('--target',type=Path,default=ROOT/'artifacts/PROJECT_NULL_ENGINEERING_V9.rbxlx')
    parser.add_argument('--manifest',type=Path,default=ROOT/'artifacts/V9_MANIFEST.json')
    parser.add_argument('--original',type=Path,default=ROOT/'source/PROJECT_NULL_INTERIORS_V6.rbxlx')
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/PHYSICS_AUDIT_V9.json')
    args=parser.parse_args()
    result=validate(args.source,args.target,args.manifest,args.original)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key not in ('cavities','service_sweep_architecture_candidates','standing_body_corridors','new_solid_vs_original_click_target_candidates')},ensure_ascii=False,indent=2))
    if result['result']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
