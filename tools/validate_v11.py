#!/usr/bin/env python3
"""Audit the integrated V11 XML, articulated rigs and conservative geometry.

This is not a Roblox physics, navigation, animation, rendering or live-network
test. Cylinders and mesh-like parts are represented by oriented part bounds.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import numpy as np

from audit_v8_geometry import load, sat_penetration
from validate_v10 import (ADDITIONAL_PASSAGES, ALLOWED_ACTIONS, arrays, broadphase,
                          cavity_check, child, ray_entry, sha, swept_box, value)
from validate_v9_physics import (PASSAGES, ROLES, SOLID, boolprop, box_for_bounds,
                                 items, path_of)
from v7_common import name

ROOT = Path(__file__).resolve().parents[1]


def refs(entries):
    if isinstance(entries, dict):
        return set(entries)
    return {e if isinstance(e, str) else e.get('referent', e.get('ref')) for e in entries or []}


def frame(item, key='CFrame'):
    node = item.find(f"Properties/CoordinateFrame[@name='{key}']")
    if node is None:
        return None
    point = np.array([float(node.findtext(k)) for k in 'XYZ'])
    matrix = np.array([[float(node.findtext(f'R{i}{j}')) for j in range(3)] for i in range(3)])
    return point, matrix


def standing_approach(target, solids, queryable, floors=(-64, -28), max_distance=9):
    """Find one grounded body and a first-hit ray, on a known deck level."""
    sc, se = arrays(solids)
    qc, qe = arrays(queryable)
    failures = Counter()
    trials = 0
    for floor in floors:
        if abs(target.center[1] - (floor+4.65)) > max_distance:
            continue
        for distance in (2.8, 4, 5.5, 7):
            for angle in np.linspace(0, 2*np.pi, 32, endpoint=False):
                origin = np.array([target.center[0]+np.cos(angle)*distance,
                                   floor+4.65, target.center[2]+np.sin(angle)*distance])
                if np.linalg.norm(origin-target.center) > max_distance:
                    continue
                trials += 1
                body = box_for_bounds('standing approach', ((origin[0]-.85, origin[0]+.85),
                                       (floor+.15, floor+5.4), (origin[2]-.85, origin[2]+.85)))
                blocked = [b for b in broadphase(body, solids, sc, se)
                           if sat_penetration(body, b, .04) is not None]
                if blocked:
                    failures['body:'+blocked[0].path] += 1
                    continue
                origin_floor = np.array([origin[0], floor+.25, origin[2]])
                end_floor = np.array([origin[0], floor-.5, origin[2]])
                supported = [(ray_entry(origin_floor, end_floor, b), b.ref) for b in solids
                             if abs(b.center[0]-origin[0]) < b.extent[0]+.02
                             and abs(b.center[2]-origin[2]) < b.extent[2]+.02
                             and b.center[1]-b.extent[1] < floor+.25
                             and b.center[1]+b.extent[1] > floor-.5]
                supported = [(t, r) for t, r in supported if t is not None]
                if not supported:
                    failures['no floor support'] += 1
                    continue
                midpoint = (origin+target.center)/2
                extent = abs(origin-target.center)/2+.0001
                ray_box = replace(target, center=midpoint, half=extent, extent=extent, rotation=np.eye(3))
                hits = [(ray_entry(origin, target.center, b), b.ref, b.path)
                        for b in broadphase(ray_box, queryable, qc, qe, -.0001)]
                hits = sorted(h for h in hits if h[0] is not None)
                if hits and hits[0][1] == target.ref:
                    return {'reachable': True, 'floor': floor, 'head': origin.tolist(),
                            'support': min(supported)[1], 'trials': trials}
                failures['ray:'+(hits[0][2] if hits else 'no hit')] += 1
    return {'reachable': False, 'trials': trials, 'blockers': dict(failures.most_common(8))}


def validate(source, target, manifest_path):
    manifest = json.loads(manifest_path.read_text())
    oldroot, root = ET.parse(source).getroot(), ET.parse(target).getroot()
    old, oldparents = items(oldroot)
    current, parents = items(root)
    _, geometry = load(target)
    boxes = {b.ref: b for b in geometry}
    new = set(current)-set(old)
    roles = manifest.get('roles', {})
    errors, warnings = [], []
    assert manifest['source_sha256'] == sha(source), 'V10 baseline hash mismatch'
    assert manifest['output_sha256'] == sha(target), 'V11 artifact hash mismatch'
    npc = manifest.get('npcs', {})
    interiors = manifest.get('interiors', {})
    hull = manifest.get('hull', {})
    if not npc and isinstance(manifest.get('groups'), dict):
        npc = manifest['groups'].get('npcs', {})
        interiors = manifest['groups'].get('interiors', {})
        hull = manifest['groups'].get('hull', {})
    movable = refs(npc.get('movable_refs', []))
    # The builder reports changes, but cannot approve its own arbitrary edits.
    # Limit exceptions to the one connection wall, the two existing staff rigs
    # and the three established source instances extended in place.
    def in_old_staff(ref):
        trail = path_of(ref, old, oldparents)
        return any('/Staff_'+staff in trail for staff in ('TECH', 'MEDIC'))
    source_names = {'ProjectNullServer_V10', 'ProjectNullClient_V10', 'Content'}
    source_refs = {r for r,e in old.items() if e.get('class') in ('Script','LocalScript','ModuleScript') and name(e) in source_names}
    wall_refs = {r for r,e in old.items() if name(e) == 'OuterWall' and r in boxes
                 and np.allclose(frame(e)[0], (-93,-51,-5))}
    assert len(wall_refs) == 1, 'The intended original west connection wall is ambiguous'
    permitted_modified = source_refs | wall_refs | {r for r in old if in_old_staff(r)}
    permitted_removed = {r for r,e in old.items() if in_old_staff(r) and e.get('class') == 'WeldConstraint'}
    scripts = manifest.get('scripts', {})
    for script in scripts.values() if isinstance(scripts, dict) else scripts:
        if isinstance(script, dict) and script.get('referent') in old:
            if script['referent'] not in source_refs:
                errors.append('Manifest attempts to replace an unrelated old script: '+name(old[script['referent']]))
    changes = {'modified': [], 'removed': [], 'reparented': []}
    for ref, item in old.items():
        trail = path_of(ref, old, oldparents)
        if ref not in current:
            changes['removed'].append({'ref': ref, 'path': trail})
            if ref not in permitted_removed:
                errors.append('Unapproved V10 deletion: '+trail)
            continue
        if ET.tostring(item.find('Properties')) != ET.tostring(current[ref].find('Properties')):
            changes['modified'].append({'ref': ref, 'path': trail})
            if ref not in permitted_modified:
                errors.append('Unapproved V10 property change: '+trail)
            else:
                oldprops = {p.get('name'):ET.tostring(p) for p in item.find('Properties')}
                newprops = {p.get('name'):ET.tostring(p) for p in current[ref].find('Properties')}
                changed = {key for key in set(oldprops)|set(newprops) if oldprops.get(key) != newprops.get(key)}
                if ref in source_refs and changed-{'Source','Disabled'}:
                    errors.append('Source extension changes unrelated properties: '+trail)
                if ref in wall_refs and changed-{'CFrame','size','Size'}:
                    errors.append('Portal split changes unrelated wall properties: '+trail)
                if in_old_staff(ref) and item.get('class') in ('ProximityPrompt','StringValue','Folder'):
                    errors.append('Existing staff interaction identity changed: '+trail)
        if oldparents.get(ref) != parents.get(ref):
            changes['reparented'].append({'ref': ref, 'path': trail})
            if not in_old_staff(ref):
                errors.append('Unapproved V10 reparenting: '+trail)
    broken = [e.text for e in root.iter('Ref') if e.text not in (None, 'null', 'nil') and e.text not in current]
    if broken:
        errors.append('Broken XML references: '+repr(broken[:12]))
    for ref,item in current.items():
        if ref not in new and ref not in permitted_modified:
            continue
        properties=[p.get('name') for p in item.find('Properties')]
        if len(properties) != len(set(properties)):
            errors.append('Duplicate serialized property: '+path_of(ref,current,parents))
    assert set(roles.values()) <= ROLES, 'Unknown authoring roles'
    newparts = new & set(boxes)
    if newparts-set(roles):
        errors.append(f'{len(newparts-set(roles))} new BaseParts have no explicit physical role')
    for ref, role in roles.items():
        if ref not in boxes:
            errors.append('Role references absent BasePart: '+str(ref))
            continue
        item = current[ref]
        if ref not in movable:
            if boolprop(item, 'CanCollide') != (role in SOLID) or boolprop(item, 'CanQuery') != (role in SOLID or role == 'control'):
                errors.append('Physical-role flags differ: '+boxes[ref].path)
            if not boolprop(item, 'Anchored') or boolprop(item, 'CanTouch'):
                errors.append('Unexpected dynamic/touch-enabled equipment: '+boxes[ref].path)
        if role in SOLID and boxes[ref].transparency >= .95:
            errors.append('Invisible primary collider: '+boxes[ref].path)
    statics = [b for b in geometry if b.ref not in movable and boolprop(current[b.ref], 'CanCollide', True)]
    added_solids = [b for b in statics if b.ref in new]
    sc, se = arrays(statics)
    ac, ae = arrays(added_solids)
    queryable = [b for b in geometry if boolprop(current[b.ref], 'CanQuery', True) or boolprop(current[b.ref], 'CanCollide', True)]
    cavities = [cavity_check(c, current, parents, boxes, roles, statics) for c in manifest.get('cavities', [])]
    for cavity in cavities:
        if not cavity['internal_parts_inside'] or cavity['filled_collision_proxies']:
            errors.append('Empty or collision-filled authored case: '+cavity['path'])

    routes = []
    known_routes = {**PASSAGES, **ADDITIONAL_PASSAGES,
                    'V11_west_gallery_portal': ((-98,-88),(-63.85,-58.6),(-3,3)),
                    'V11_upper_central_corridor': ((-94,214),(-27.85,-22.6),(-4,4))}
    for label, bounds in known_routes.items():
        body = box_for_bounds(label, bounds)
        blockers = [{'ref': b.ref, 'path': b.path} for b in broadphase(body, statics, sc, se)
                    if sat_penetration(body, b, .04) is not None]
        if blockers:
            errors.append('Standing-body route obstructed: '+label)
        routes.append({'name': label, 'bounds': bounds, 'blockers': blockers})
    old_targets = [b for b in geometry if b.ref in old and any(c.get('class') == 'ClickDetector' for c in current[b.ref].findall('Item'))]
    blocked_clicks = []
    for target_box in old_targets:
        for obstacle in broadphase(target_box, added_solids, ac, ae):
            if sat_penetration(target_box, obstacle, .025) is not None:
                blocked_clicks.append({'target': target_box.ref, 'obstacle': obstacle.ref, 'path': obstacle.path})
    if blocked_clicks:
        errors.append(f'New geometry blocks {len(blocked_clicks)} original click-target volumes')
    old_statics = [b for b in statics if b.ref in old]
    oc, oe = arrays(old_statics)
    structural_contacts = []
    for added in added_solids:
        for original in broadphase(added, old_statics, oc, oe, .12):
            overlap = sat_penetration(added, original, .12)
            if overlap is None:
                continue
            reason = None
            if (added.name == 'LowerStairHallFloor' and original.name == 'SectionedFloorSlab'
                    and abs((added.center[1]+added.extent[1])-(-64)) < .001
                    and abs((original.center[1]+original.extent[1])-(-64)) < .001
                    and added.center[0]+added.extent[0] <= -92.49
                    and original.center[0]-original.extent[0] >= -93.01):
                reason = 'Half-stud threshold floor lap joins the new stair hall to the unchanged laboratory slab at equal floor height.'
            elif (added.name == 'WestGalleryPortalNorthPier'
                    and '/LAB_Crew_Stair_Tower/' in added.path
                    and np.allclose(added.center, (-93,-51,46))
                    and (original.name == 'OuterWall' and np.allclose(original.center, (4,-51,85))
                         or original.name == 'ServiceGalleryCeiling' and np.allclose(original.center, (4,-39,39)))):
                reason = 'The restored west wall strip retains its original wall plane and laps the unchanged north perimeter corner/ceiling edge by half a stud; the portal remains clear.'
            structural_contacts.append({'new': added.ref, 'new_path': added.path,
                                        'existing': original.ref, 'existing_path': original.path,
                                        'overlap': float(overlap), 'reason': reason})
    unreviewed = [c for c in structural_contacts if c['reason'] is None]
    if unreviewed:
        errors.append(f'New structures intersect existing laboratory geometry: {len(unreviewed)}')

    stair_results = []
    for flight in interiors.get('stairs', []):
        treads = [boxes[r] for r in flight.get('treads', []) if r in boxes]
        if len(treads) != 20:
            errors.append('Stair flight needs twenty physical treads: '+flight['id'])
            continue
        heights = [t.center[1]+t.extent[1] for t in treads]
        rises = np.diff(heights)
        pitches = [float(np.linalg.norm((b.center-a.center)[[0,2]])) for a,b in zip(treads,treads[1:])]
        if not np.allclose(rises, .6, atol=.001) or not np.allclose(pitches, 1.05, atol=.001):
            errors.append('Stair rise/run differs from safe authored dimensions: '+flight['id'])
        obstructions = []
        for tread, top in zip(treads, heights):
            # Above the step-up envelope, sample a centerline head/torso volume;
            # lower adjacent risers are intentionally stepped over by Humanoid.
            head = box_for_bounds('stair headroom', ((tread.center[0]-.75,tread.center[0]+.75),
                                  (top+2.2,top+6), (tread.center[2]-.75,tread.center[2]+.75)))
            for obstruction in broadphase(head, statics, sc, se, .035):
                if sat_penetration(head, obstruction, .035) is not None:
                    obstructions.append({'tread': tread.ref, 'obstacle': obstruction.ref, 'path': obstruction.path})
        if obstructions:
            errors.append('Stair flight has insufficient sampled headroom: '+flight['id'])
        stair_results.append({'id': flight['id'], 'treads': len(treads), 'rise': rises.tolist(),
                              'pitch': pitches, 'headroom_obstructions': obstructions})
    if len(stair_results) != 3:
        errors.append('Three connected stair flights were not declared')

    connected_routes = []
    for route in interiors.get('routes', []):
        points = route.get('points', [])
        blockers = []
        for start,end in zip(points,points[1:]):
            start,end=np.asarray(start,dtype=float),np.asarray(end,dtype=float)
            distance=float(np.linalg.norm(end-start))
            for fraction in np.linspace(0,1,max(2,int(distance/.75)+1)):
                point=start+(end-start)*fraction
                # Route metadata describes a smooth rise, whereas the actual
                # surface is stepped. Resolve only nearby walkable supports
                # within the authored .6-stud riser plus .05 tolerance. This
                # does not exempt stairs from torso/head obstruction checks.
                support_high = point + np.array([0,.65,0])
                support_low = point - np.array([0,.65,0])
                support_heights = []
                for support in statics:
                    if roles.get(support.ref) != 'walkable':
                        continue
                    if (abs(support.center[0]-point[0]) > support.extent[0]+.001
                            or abs(support.center[2]-point[2]) > support.extent[2]+.001
                            or abs(support.rotation[1,1]) < .999):
                        continue
                    entry = ray_entry(support_high,support_low,support)
                    if entry is not None:
                        support_heights.append(float((support_high+(support_low-support_high)*entry)[1]))
                if support_heights:
                    point = point.copy();point[1] = max(support_heights)
                lower=2.2 if abs(start[1]-end[1])>.1 else .15
                body=box_for_bounds('connected route sample',((point[0]-.75,point[0]+.75),
                                    (point[1]+lower,point[1]+5.4),(point[2]-.75,point[2]+.75)))
                for obstacle in broadphase(body,statics,sc,se,.04):
                    if sat_penetration(body,obstacle,.04) is not None:
                        blockers.append({'point':point.tolist(),'obstacle':obstacle.ref,'path':obstacle.path})
        if blockers:
            errors.append('Declared physical connection route obstructed: '+route['id'])
        connected_routes.append({'id':route['id'],'points':points,'blockers':blockers})

    # Terrain FillBlock is axis-aligned in the initializer. Reject any water
    # section crossing the inhabited laboratory envelope. The tapered bow may
    # legitimately have water inside its broad rectangular bounding box.
    water = hull.get('water', {})
    envelope = hull.get('hull', {}).get('old_laboratory_envelope',
                    {'x':[-93,227], 'y':[-67.3,-37], 'z':[-95,97]})
    dry = box_for_bounds('retained inhabited laboratory envelope', tuple(envelope[k] for k in ('x','y','z')))
    water_results = []
    for index, region in enumerate(water.get('fill_boxes', [])):
        center, size = np.asarray(region['center']), np.asarray(region['size'])
        if not np.isfinite(center).all() or not np.isfinite(size).all() or np.any(size <= 0):
            errors.append('Invalid native ocean fill bounds: '+str(index))
            continue
        bounds = tuple((float(c-s/2),float(c+s/2)) for c,s in zip(center,size))
        fill = box_for_bounds('ocean section '+str(index), bounds)
        enters_lab = sat_penetration(fill,dry,.001) is not None
        if enters_lab:
            errors.append('Native ocean water crosses the retained dry laboratories: '+str(index))
        water_results.append({'index':index,'center':center.tolist(),'size':size.tolist(),'crosses_laboratories':enters_lab})
    if not water_results or water.get('placement_is_canon_depth') is not False:
        errors.append('Native ocean fill metadata or scene/canon distinction is missing')

    # Detect all tagged interactions in the final XML, including retained ones.
    interactions = []
    content_path = ROOT/'tools/v11_content.json'
    content = json.loads(content_path.read_text())
    doc_by_id = {d['id']: d for d in content['documents']}
    for config in root.iter('Item'):
        if config.get('class') != 'Folder' or name(config) != 'V10_Interact':
            continue
        ref = parents[config.get('referent')]
        if ref not in boxes:
            errors.append('Interaction has no physical target')
            continue
        action_item, arg_item = child(config, 'Action'), child(config, 'Argument')
        action, argument = value(action_item), value(arg_item)
        prompt = child(current[ref], 'V10_Prompt', 'ProximityPrompt')
        if action not in ALLOWED_ACTIONS or prompt is None:
            errors.append('Invalid interaction metadata: '+boxes[ref].path)
            continue
        if not boolprop(current[ref], 'CanQuery') or not boolprop(prompt, 'Enabled') or not boolprop(prompt, 'RequiresLineOfSight'):
            errors.append('Interaction query/visibility disabled: '+boxes[ref].path)
        if action == 'document' and argument not in doc_by_id:
            errors.append('Physical document missing authored content: '+str(argument))
        if action == 'npc' and argument not in content['staff']:
            errors.append('Physical NPC missing authored dialogue: '+str(argument))
        approach = standing_approach(boxes[ref], statics, queryable)
        if not approach['reachable']:
            errors.append('No grounded interaction approach: '+boxes[ref].path)
        interactions.append({'ref': ref, 'action': action, 'argument': argument,
                             'path': boxes[ref].path, **approach})
    physical_docs = {e['argument'] for e in interactions if e['action'] == 'document'}
    if set(doc_by_id)-physical_docs:
        errors.append('Documents have no physical placement: '+repr(sorted(set(doc_by_id)-physical_docs)))
    previous_content = json.loads((ROOT/'tools/v10_content.json').read_text())
    for previous in previous_content['documents']:
        after = doc_by_id.get(previous['id'], {})
        if any(after.get(key) != value for key,value in previous.items()):
            errors.append('Existing V10 evidence changed: '+previous['id'])

    # V9/V10 covers may not acquire a new obstacle; new covers are checked
    # against the complete static scene. Every recorded transform is compared
    # with the actual runtime metadata before its motion is trusted.
    services = []
    for version in (9,10):
        services += [(True, s) for s in json.loads((ROOT/f'artifacts/V{version}_MANIFEST.json').read_text())['services']]
    services += [(False, s) for s in manifest.get('services', [])]
    sweeps, sweep_collisions = [], []
    for legacy, service in services:
        panel = current.get(service['panel'])
        if panel is None:
            errors.append('Service panel removed: '+service['panel'])
            continue
        config = child(panel, 'V9_Service')
        if config is None:
            errors.append('Service runtime metadata absent: '+service['panel'])
            continue
        actual_axis, actual_angle = child(config, 'Axis'), child(config, 'OpenAngle')
        pivot = child(config, 'Pivot')
        node = pivot.find("Properties/Vector3[@name='Value']") if pivot is not None else None
        actual_pivot = [float(node.findtext(k)) for k in 'XYZ'] if node is not None else []
        movers = {value(e) for e in config.findall('Item') if e.get('class') == 'ObjectValue' and name(e).startswith('Moving_')}
        if (actual_axis is None or value(actual_axis) != service['axis'] or actual_angle is None
                or abs(float(value(actual_angle))-float(service['angle'])) > 1e-6
                or len(actual_pivot) != 3 or not np.allclose(actual_pivot, service['pivot'])
                or movers != set(service['moving'])):
            errors.append('Audited cover motion differs from runtime metadata: '+service['panel'])
        obstacles = added_solids if legacy else [b for b in statics if b.ref not in movers]
        centers, extents = arrays(obstacles)
        hits = []
        for ref in movers:
            if ref not in boxes or not boolprop(current[ref], 'CanCollide'):
                continue
            for fraction in np.linspace(0,1,9):
                posed = swept_box(boxes[ref], service, float(fraction))
                for obstacle in broadphase(posed, obstacles, centers, extents, .065):
                    overlap = sat_penetration(posed, obstacle, .065)
                    if overlap is not None:
                        hits.append({'panel': service['panel'], 'mover': ref, 'fraction': float(fraction),
                                     'obstacle': obstacle.ref, 'path': obstacle.path, 'overlap': float(overlap)})
        sweep_collisions += hits
        sweeps.append({'panel': service['panel'], 'legacy': legacy, 'collisions': len(hits)})
    if sweep_collisions:
        errors.append(f'Cover motion has {len(sweep_collisions)} new collision candidates')

    rigs = []
    for rig in npc.get('rigs', []):
        model_ref = rig['model']
        model = current[model_ref]
        body = {label: ref for label, ref in rig.get('body_parts', {}).items()}
        required = {'HumanoidRootPart','Torso','Head','Left Arm','Right Arm','Left Leg','Right Leg'}
        if not required <= set(body):
            errors.append('R6 body incomplete: '+rig['id'])
            continue
        humanoid = current.get(rig['humanoid'])
        animator = current.get(rig['animator'])
        if humanoid is None or humanoid.get('class') != 'Humanoid' or animator is None or animator.get('class') != 'Animator':
            errors.append('Rig lacks Humanoid/Animator: '+rig['id'])
        connections = {r: set() for r in body.values()}
        joints = []
        for joint in model.iter('Item'):
            if joint.get('class') != 'Motor6D':
                continue
            part0 = joint.findtext("Properties/Ref[@name='Part0']")
            part1 = joint.findtext("Properties/Ref[@name='Part1']")
            if part0 not in connections or part1 not in connections:
                errors.append('Motor does not connect R6 body parts: '+rig['id']+'/'+name(joint))
                continue
            connections[part0].add(part1);connections[part1].add(part0)
            c0, c1 = frame(joint, 'C0'), frame(joint, 'C1')
            if c0 is None or c1 is None:
                errors.append('Motor rest transform missing: '+rig['id']+'/'+name(joint))
            else:
                p0, r0 = frame(current[part0]);p1, r1 = frame(current[part1])
                if (not np.allclose(p0+r0@c0[0], p1+r1@c1[0], atol=1e-5)
                        or not np.allclose(r0@c0[1],r1@c1[1],atol=1e-5)):
                    errors.append('Motor rest joint positions disagree: '+rig['id']+'/'+name(joint))
            joints.append({'name': name(joint), 'part0': part0, 'part1': part1})
        visited, pending = set(), [body['HumanoidRootPart']]
        while pending:
            ref = pending.pop()
            if ref in visited: continue
            visited.add(ref);pending += list(connections[ref]-visited)
        if visited != set(body.values()) or len(joints) != 6:
            errors.append('R6 articulated body is not a six-joint connected tree: '+rig['id'])
        for ref in movable & {e.get('referent') for e in model.iter('Item')}:
            if ref in boxes and boolprop(current[ref], 'Anchored'):
                errors.append('Anchored part pins a moving NPC: '+boxes[ref].path)
        rig_parts = movable & {e.get('referent') for e in model.iter('Item')} & set(boxes)
        assembly = {r:set() for r in rig_parts}
        for joint in model.iter('Item'):
            if joint.get('class') not in ('Motor6D','WeldConstraint'):
                continue
            a,b=(joint.findtext(f"Properties/Ref[@name='{key}']") for key in ('Part0','Part1'))
            if a in assembly and b in assembly:
                assembly[a].add(b);assembly[b].add(a)
        attached,pending=set(),[body['HumanoidRootPart']]
        while pending:
            ref=pending.pop()
            if ref in attached:continue
            attached.add(ref);pending+=list(assembly[ref]-attached)
        if attached != rig_parts:
            errors.append('NPC wardrobe/body has unwelded moving parts: '+rig['id'])
        orientation = current.get(rig.get('orientation'))
        if (orientation is None or orientation.get('class') != 'AlignOrientation'
                or orientation.findtext("Properties/token[@name='Mode']") != '0'
                or orientation.findtext("Properties/Ref[@name='Attachment0']") != rig.get('aim_attachment')):
            errors.append('NPC turning constraint is not valid OneAttachment mode: '+rig['id'])
        rigs.append({'id': rig['id'], 'model': model_ref, 'joints': joints,
                     'connected_body_parts': len(visited),'connected_wardrobe_and_body_parts':len(attached)})
    if len(rigs) < 6:
        errors.append('Expected six individually configured staff rigs')

    runtime_sources = []
    for label, record in scripts.items() if isinstance(scripts, dict) else []:
        ref = record.get('referent')
        if ref not in current:
            errors.append('Runtime manifest references missing source: '+label)
            continue
        item = current[ref]
        source_text = item.findtext("Properties/ProtectedString[@name='Source']", '')
        expected_path = record.get('source')
        if expected_path and Path(expected_path).suffix in ('.luau','.lua'):
            expected = (ROOT/expected_path).read_text()
            if source_text != expected:
                errors.append('Embedded runtime differs from authored file: '+label)
        if record.get('sha256') and hashlib.sha256(source_text.encode()).hexdigest() != record['sha256']:
            errors.append('Runtime manifest hash mismatch: '+label)
        if item.get('class') in ('Script','LocalScript') and boolprop(item, 'Disabled'):
            errors.append('Runtime disabled: '+label)
        # External assets require a known source; this pass uses local rigs and
        # procedural poses, so it should not contain catalog/animation IDs.
        if re.search(r'rbxassetid://[0-9]+', source_text):
            errors.append('Unverified external asset ID in runtime: '+label)
        runtime_sources.append({'name': label, 'ref': ref, 'sha256': hashlib.sha256(source_text.encode()).hexdigest()})
    before_core = next(e for e in old.values() if e.get('class') == 'ModuleScript' and name(e) == 'ExperimentCore')
    after_core = current[before_core.get('referent')]
    if before_core.findtext("Properties/ProtectedString[@name='Source']") != after_core.findtext("Properties/ProtectedString[@name='Source']"):
        errors.append('The five established protocol rules were changed')
    remotes = [e for e in root.iter('Item') if e.get('class') == 'RemoteEvent']
    if len(remotes) != 2 or {name(e) for e in remotes} != {'Request','Push'}:
        errors.append('Network integration added duplicate/competing RemoteEvents')

    return {'result': 'PASS' if not errors else 'REVIEW_REQUIRED',
            'validation': 'Static XML, joint-rest transforms and conservative oriented geometry; no Roblox Studio execution',
            'source_sha256': sha(source), 'target_sha256': sha(target),
            'baseline_v10_instances': len(old), 'new_instances': len(new), 'new_parts': len(newparts),
            'new_primary_colliders': len(added_solids), 'changes': changes,
            'registered_cavities': len(cavities), 'cavities': cavities,
            'standing_routes': routes, 'old_click_targets': len(old_targets), 'click_target_obstructions': blocked_clicks,
            'new_vs_existing_structural_contacts': structural_contacts,
            'stair_flights': stair_results, 'native_water_sections': water_results,
            'declared_connected_routes': connected_routes,
            'interaction_approaches': interactions, 'service_sweeps': sweeps, 'service_collision_candidates': sweep_collisions,
            'rigs': rigs, 'runtime_sources': runtime_sources, 'document_count': len(doc_by_id),
            'errors': errors, 'warnings': warnings,
            'limitations': ['No Roblox avatar, navigation, animation replication, rendering, ocean voxel or live DataStore test.',
                            'Finite standing/ray samples establish local access, not a full navigation mesh.',
                            'Nine sampled cover poses and oriented bounds are conservative approximations.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'artifacts/PROJECT_NULL_GAMEPLAY_V10.rbxlx')
    parser.add_argument('--target', type=Path, default=ROOT/'artifacts/PROJECT_NULL_OCEAN_V11.rbxlx')
    parser.add_argument('--manifest', type=Path, default=ROOT/'artifacts/V11_MANIFEST.json')
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts/V11_AUDIT.json')
    args = parser.parse_args()
    report = validate(args.source, args.target, args.manifest)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({key: report[key] for key in ('result','new_parts','new_primary_colliders','registered_cavities','document_count','errors','warnings')}, ensure_ascii=False, indent=2))
    if report['result'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
