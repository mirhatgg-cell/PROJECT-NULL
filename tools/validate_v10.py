#!/usr/bin/env python3
"""Static V10 integration, collision, service-motion and interaction-access audit.

This executes no Roblox engine. Parts, meshes and cylinders are conservatively
represented by their oriented bounds; avatar and actual raycast checks remain
necessary in Studio.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

from audit_v8_geometry import Box, load, sat_penetration
from validate_v9_physics import (
    BASE, PASSAGES, ROLES, SOLID, ancestors, boolprop, box_for_bounds,
    items, path_of, rotation,
)
from v7_common import name

ROOT = Path(__file__).resolve().parents[1]
ADDITIONAL_PASSAGES = {
    'E01_central_preparation_route': ((-1.35, 1.35), (-63, -58.5), (-74.0, -50.0)),
    'E04_southern_operator_route': ((-58.8, -27.0), (-63, -58.5), (-6.3, -3.5)),
    'E12_control_entry_route': ((201.35, 204.05), (-63, -58.5), (-10.2, 8.5)),
}
ALLOWED_ACTIONS = {'console', 'document', 'cooling', 'repair', 'supply', 'medical', 'npc', 'records', 'response'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def child(item, label, cls=None):
    return next((e for e in item.findall('Item') if name(e) == label
                 and (cls is None or e.get('class') == cls)), None)


def value(item):
    props = item.find('Properties')
    return next((e.text for e in props if e.get('name') == 'Value'), None)


def broadphase(box, candidates, centers, extents, threshold=.025):
    if not candidates:
        return []
    indices = np.where(np.all(np.abs(centers - box.center) < extents + box.extent - threshold, axis=1))[0]
    return [candidates[int(i)] for i in indices]


def arrays(boxes):
    return np.array([b.center for b in boxes]), np.array([b.extent for b in boxes])


def ray_entry(origin, destination, box):
    """Finite segment versus OBB; return first fractional entry or None."""
    local_origin = box.rotation.T @ (origin - box.center)
    local_delta = box.rotation.T @ (destination - origin)
    enter, leave = 0.0, 1.0
    for axis in range(3):
        if abs(local_delta[axis]) < 1e-10:
            if abs(local_origin[axis]) > box.half[axis] + 1e-7:
                return None
            continue
        a = (-box.half[axis] - local_origin[axis]) / local_delta[axis]
        b = (box.half[axis] - local_origin[axis]) / local_delta[axis]
        enter, leave = max(enter, min(a, b)), min(leave, max(a, b))
        if enter > leave + 1e-8:
            return None
    return enter if leave >= 0 and enter <= 1 else None


def swept_box(start, service, fraction):
    pivot = np.asarray(service['pivot'], dtype=float)
    if service['axis'] == 'Slide':
        center = start.center + np.asarray(service['delta'], dtype=float) * fraction
        orientation = start.rotation
    else:
        transform = rotation(service['axis'], float(service['angle']) * fraction)
        center = pivot + transform @ (start.center - pivot)
        orientation = transform @ start.rotation
    return replace(start, center=center, rotation=orientation, extent=np.abs(orientation) @ start.half)


def cavity_check(cavity, current, parents, boxes, roles, all_solids):
    model = cavity['model']
    center = np.asarray(cavity['center'], dtype=float)
    matrix = np.asarray(cavity.get('matrix', np.eye(3)), dtype=float)
    half = np.asarray(cavity['size'], dtype=float) / 2 - float(cavity.get('thickness', .12))
    assert np.isfinite(center).all() and np.all(half > 0)
    assert np.allclose(matrix.T @ matrix, np.eye(3), atol=1e-6)
    inside, scope_used = [], model
    for scope in (model, parents.get(model)):
        if scope not in current:
            continue
        descendants = {e.get('referent') for e in current[scope].iter('Item')}
        found = [r for r in descendants if r in boxes and roles.get(r) == 'internal'
                 and np.all(np.abs(matrix.T @ (boxes[r].center - center)) <= half + .02)]
        if found:
            inside, scope_used = found, scope
            break
    filled = []
    for box in all_solids:
        point = matrix.T @ (box.center - center)
        extent = np.abs(matrix.T @ box.rotation) @ box.half
        overlap = np.maximum(0, np.minimum(point + extent, half) - np.maximum(point - extent, -half))
        if min(overlap / (2 * half)) >= .75 and float(np.prod(2 * box.half) / np.prod(2 * half)) >= .5:
            filled.append(box.ref)
    return {'model': model, 'path': path_of(model, current, parents),
            'internal_scope': scope_used, 'internal_parts_inside': len(inside),
            'filled_collision_proxies': filled}


def reachable(target, all_solids, all_queryable):
    """Find a standing body and unobstructed first-hit segment to a target.

    These finite samples establish one plausible ground-level approach; they do
    not prove a continuous navigable path from spawn. Door states are closed.
    """
    solid_centers, solid_extents = arrays(all_solids)
    query_centers, query_extents = arrays(all_queryable)
    blocked_body, blocked_ray = Counter(), Counter()
    unsupported = 0
    trials = 0
    for distance in (2.8, 4.0, 5.5, 7.0):
        for angle in np.linspace(0, 2 * np.pi, 40, endpoint=False):
            origin = np.array([target.center[0] + np.cos(angle) * distance, -59.35,
                               target.center[2] + np.sin(angle) * distance])
            if float(np.linalg.norm(origin - target.center)) > 9.0:
                continue
            trials += 1
            body = box_for_bounds('candidate standing body',
                                  ((origin[0] - .9, origin[0] + .9), (-63.85, -58.6),
                                   (origin[2] - .9, origin[2] + .9)))
            occupied = []
            for other in broadphase(body, all_solids, solid_centers, solid_extents):
                if sat_penetration(body, other, .04) is not None:
                    occupied.append(other)
            if occupied:
                for other in occupied:
                    blocked_body[other.path] += 1
                continue
            support_origin = np.array([origin[0], -63.75, origin[2]])
            support_end = np.array([origin[0], -64.5, origin[2]])
            support_box = box_for_bounds('standing floor support',
                                        ((origin[0]-.01, origin[0]+.01), (-64.5, -63.75),
                                         (origin[2]-.01, origin[2]+.01)))
            supports = []
            for other in broadphase(support_box, all_solids, solid_centers, solid_extents, -.001):
                fraction = ray_entry(support_origin, support_end, other)
                if fraction is not None:
                    supports.append((fraction, other.ref))
            if not supports:
                unsupported += 1
                continue
            midpoint = (origin + target.center) / 2
            extent = np.abs(origin - target.center) / 2 + .0001
            query = replace(target, center=midpoint, half=extent, extent=extent, rotation=np.eye(3))
            hits = []
            for other in broadphase(query, all_queryable, query_centers, query_extents, -.0001):
                t = ray_entry(origin, target.center, other)
                if t is not None:
                    hits.append((t, other.ref, other.path))
            hits.sort()
            if hits and hits[0][1] == target.ref:
                return {'reachable': True, 'sampled_standing_head': origin.tolist(),
                        'distance': round(float(np.linalg.norm(origin-target.center)), 4),
                        'sample_trials': trials, 'first_hit': target.ref,
                        'floor_support': min(supports)[1]}
            if hits:
                blocked_ray[hits[0][2]] += 1
    return {'reachable': False, 'sample_trials': trials,
            'body_blockers': dict(blocked_body.most_common(8)),
            'ray_blockers': dict(blocked_ray.most_common(8)), 'unsupported_samples': unsupported}


def validate(source, target, manifest_path):
    manifest = json.loads(manifest_path.read_text())
    old_root = ET.parse(source).getroot()
    root = ET.parse(target).getroot()
    before, old_parents = items(old_root)
    current, parents = items(root)
    _, geometry = load(target)
    boxes = {b.ref: b for b in geometry}
    roles = manifest['roles']
    errors, warnings = [], []
    assert set(roles.values()) <= ROLES
    assert manifest['source_sha256'] == sha(source), 'Source hash mismatch'
    assert manifest['output_sha256'] == sha(target), 'Output hash mismatch'
    removed = sorted(set(before) - set(current))
    modified = [ref for ref in before if ref in current and
                ET.tostring(before[ref].find('Properties')) != ET.tostring(current[ref].find('Properties'))]
    reparented = [ref for ref in before if ref in current and old_parents.get(ref) != parents.get(ref)]
    if removed or modified or reparented:
        errors.append('V9 instances removed, modified or reparented')
    broken = [e.text for e in root.iter('Ref') if e.text not in (None, 'null', 'nil') and e.text not in current]
    if broken:
        errors.append(f'Broken XML references: {broken[:10]}')
    new_refs = set(current) - set(before)
    new_parts = new_refs & set(boxes)
    if new_parts != set(roles):
        errors.append(f'Every new part needs exactly one physical role; missing {len(new_parts-set(roles))}, extra {len(set(roles)-new_parts)}')
    for ref in new_parts:
        part, role = current[ref], roles.get(ref)
        if role not in ROLES:
            continue
        if boolprop(part, 'CanCollide') != (role in SOLID) or boolprop(part, 'CanQuery') != (role in SOLID or role == 'control'):
            errors.append(f'Physical-role flags differ: {path_of(ref, current, parents)}')
        if not boolprop(part, 'Anchored') or boolprop(part, 'CanTouch'):
            errors.append(f'Unexpected unanchored/touch-enabled equipment: {path_of(ref, current, parents)}')
        if role in SOLID and boxes[ref].transparency >= .95:
            errors.append(f'Invisible primary solid: {path_of(ref, current, parents)}')
    all_solids = [b for b in geometry if boolprop(current[b.ref], 'CanCollide', True)]
    new_solids = [b for b in all_solids if b.ref in new_parts]
    new_centers, new_extents = arrays(new_solids)
    all_centers, all_extents = arrays(all_solids)
    # Roblox treats colliding parts as queryable even if CanQuery was false in XML.
    queryable = [b for b in geometry if boolprop(current[b.ref], 'CanQuery', True)
                 or boolprop(current[b.ref], 'CanCollide', True)]
    cavities = [cavity_check(c, current, parents, boxes, roles, all_solids) for c in manifest.get('cavities', [])]
    for c in cavities:
        if not c['internal_parts_inside'] or c['filled_collision_proxies']:
            errors.append('Empty or collision-filled new cavity: ' + c['path'])

    route_results = []
    for label, bounds in {**PASSAGES, **ADDITIONAL_PASSAGES}.items():
        corridor = box_for_bounds(label, bounds)
        # Old routes are fully rechecked. Additional routes report inherited
        # conditions separately so the new work cannot silently worsen them.
        found = []
        for other in broadphase(corridor, all_solids, all_centers, all_extents):
            depth = sat_penetration(corridor, other, .025)
            if depth is not None:
                found.append({'ref': other.ref, 'path': other.path, 'overlap': round(depth, 5), 'new': other.ref in new_refs})
        if found and (label in PASSAGES or any(e['new'] for e in found)):
            errors.append('Standing-body route obstructed: ' + label)
        elif found:
            warnings.append('Additional sampled route has pre-existing geometry: ' + label)
        route_results.append({'name': label, 'bounds': bounds, 'obstructions': found})

    click_targets = [b for b in geometry if b.ref in before and
                     any(e.get('class') == 'ClickDetector' for e in current[b.ref].findall('Item'))]
    target_overlaps = []
    for button in click_targets:
        for other in broadphase(button, new_solids, new_centers, new_extents):
            depth = sat_penetration(button, other, .025)
            if depth is not None:
                target_overlaps.append({'target': button.describe(), 'new_solid': other.describe(), 'overlap': round(depth, 5)})
    if target_overlaps:
        errors.append(f'New solids obstruct existing ClickDetector targets: {len(target_overlaps)}')

    # A new sign can leave the old button itself untouched while cutting its
    # drive housing. Review substantive new/old physical intersections too.
    # Mechanical mounting allowances are narrow and each matched reference is
    # retained in the report, with its reason.
    old_solids = [b for b in all_solids if b.ref in before]
    old_centers, old_extents = arrays(old_solids)
    structural_intersections = []
    for added in new_solids:
        for original in broadphase(added, old_solids, old_centers, old_extents, .12):
            depth = sat_penetration(added, original, .12)
            if depth is None:
                continue
            allowance = None
            if (added.name == 'WallStandOff' and '/ELEC_SignedRepair/' in added.path
                    and original.name in ('Wall', 'AcousticFrame', 'FabricInsert')):
                allowance = 'Repair-tray standoff anchors into an existing wall or acoustic-panel mounting layer.'
            elif (added.name == 'DriverWallStandOff' and '/Physical_Protocol_Feedback_V10/P01_SignalDriver/' in added.path
                    and original.ref == 'RBX000000000000000000000000700000BF'
                    and original.path.endswith('/E04_Operator_Detail/AcousticWallAndDocumentation/AcousticFrame')
                    and np.allclose(original.center, (-59, -53, 11.28))
                    and np.allclose(added.center[[1, 2]], (-53.7, 11.28))):
                allowance = 'P01 driver standoffs join the case rear at Z=11.15 to the existing acoustic backing frame at Z=11.16..11.40.'
            elif (added.name == 'ResponsePostFoot' and '/P02_PhysicalResponsePosts/' in added.path
                    and original.name == 'PlatformSupport'):
                allowance = 'Response post foot meets the existing course support as a physical mounting joint.'
            structural_intersections.append({'new_solid': added.describe(), 'existing_solid': original.describe(),
                                             'overlap': round(depth, 5), 'mounting_reason': allowance})
    unreviewed_structures = [entry for entry in structural_intersections if not entry['mounting_reason']]
    if unreviewed_structures:
        errors.append(f'New physical geometry intersects existing equipment: {len(unreviewed_structures)}')

    # Original service assemblies are checked only against new obstacles;
    # their existing self contacts were inspected in V9. New assemblies are
    # checked against every static collider, including new equipment.
    v9_manifest = json.loads((ROOT / 'artifacts/V9_MANIFEST.json').read_text())
    new_services = manifest.get('services', [])
    service_results, sweep_collisions = [], []
    controlled = set()
    for service in new_services:
        panel_ref = service['panel']
        if panel_ref not in new_parts or roles.get(panel_ref) != 'panel':
            errors.append('New service panel is not an authored physical panel: ' + panel_ref)
            continue
        panel = current[panel_ref]
        config, prompt = child(panel, 'V9_Service', 'Folder'), child(panel, 'V9_ServicePrompt', 'ProximityPrompt')
        if config is None or prompt is None:
            errors.append('Service metadata/prompt missing: ' + path_of(panel_ref, current, parents))
        else:
            pivot_item = child(config, 'Pivot', 'Vector3Value')
            axis_item = child(config, 'Axis', 'StringValue')
            angle_item = child(config, 'OpenAngle', 'NumberValue')
            actual_pivot = pivot_item.find("Properties/Vector3[@name='Value']") if pivot_item is not None else None
            pivot_values = [float(actual_pivot.findtext(k)) for k in 'XYZ'] if actual_pivot is not None else []
            actual_movers = {value(e) for e in config.findall('Item') if e.get('class') == 'ObjectValue'
                             and name(e).startswith('Moving_')}
            if (len(pivot_values) != 3 or not np.allclose(pivot_values, service['pivot'], atol=1e-6) or axis_item is None
                    or value(axis_item) != service['axis'] or angle_item is None
                    or abs(float(value(angle_item))-float(service['angle'])) > 1e-6
                    or actual_movers != set(service['moving'])):
                errors.append('Service runtime metadata differs from its audited motion: ' + panel_ref)
            if not boolprop(prompt, 'Enabled') or not boolprop(prompt, 'RequiresLineOfSight'):
                errors.append('Service prompt disabled or lacks line-of-sight requirement: ' + panel_ref)
        movers = service['moving']
        if panel_ref not in movers or len(set(movers)) != len(movers) or controlled.intersection(movers):
            errors.append('Invalid/duplicated service mover registration: ' + panel_ref)
        controlled.update(movers)
        if service['axis'] not in ('X', 'Y', 'Z', 'Slide') or not 0 < abs(float(service['angle'])) <= 150:
            errors.append('Invalid service transform: ' + panel_ref)
    for legacy, entries in ((True, v9_manifest['services']), (False, new_services)):
        for service in entries:
            movers = set(service['moving'])
            obstacles = new_solids if legacy else [b for b in all_solids if b.ref not in movers]
            centers, extents = arrays(obstacles)
            collision_count = 0
            for mover in movers:
                if mover not in boxes or not boolprop(current[mover], 'CanCollide'):
                    continue
                for fraction in np.linspace(0, 1, 9):
                    posed = swept_box(boxes[mover], service, float(fraction))
                    for other in broadphase(posed, obstacles, centers, extents, .065):
                        depth = sat_penetration(posed, other, .065)
                        if depth is not None:
                            collision_count += 1
                            sweep_collisions.append({'legacy': legacy, 'panel': service['panel'], 'mover': mover,
                                                     'fraction': float(fraction), 'obstacle': other.ref,
                                                     'obstacle_path': other.path, 'overlap': round(depth, 5)})
            service_results.append({'panel': service['panel'], 'legacy': legacy, 'sampled_collisions': collision_count})
    if sweep_collisions:
        errors.append(f'Service motion has new collision candidates: {len(sweep_collisions)}')

    # The optical shutter is a separate game actuator, not an avatar-blocking
    # maintenance cover. Check its actual baked pose, configured travel and all
    # nine poses against the housing and the internal optics it exposes.
    feedback = manifest.get('feedback', {})
    feedback_results = {'observer_shutter': {}, 'p01_lamps': {}, 'p05_reference': {}}
    observer = feedback.get('observer', {})
    shutter_ref = observer.get('shutter')
    if shutter_ref not in boxes:
        errors.append('Physical P04 observer shutter missing')
    else:
        shutter = boxes[shutter_ref]
        shutter_item = current[shutter_ref]
        offset_item = child(shutter_item, 'OpenOffset', 'Vector3Value')
        offset_vector = offset_item.find("Properties/Vector3[@name='Value']") if offset_item is not None else None
        offset = [float(offset_vector.findtext(k)) for k in 'XYZ'] if offset_vector is not None else []
        if (len(offset) != 3 or not np.allclose(offset, observer['open_offset'])
                or not np.allclose(shutter.center, observer['closed_position'])
                or roles.get(shutter_ref) != 'internal'
                or boolprop(shutter_item, 'CanCollide') or boolprop(shutter_item, 'CanQuery')):
            errors.append('Physical P04 observer shutter travel/role mismatch')
        if len(offset) == 3:
            optical_refs = {e.get('referent') for e in current[observer['model']].iter('Item')}
            obstacles = [b for b in geometry if b.ref != shutter_ref and
                         (boolprop(current[b.ref], 'CanCollide', True)
                          or b.ref in optical_refs and roles.get(b.ref) == 'internal')]
            centers, extents = arrays(obstacles)
            shutter_contacts = []
            for fraction in np.linspace(0, 1, 9):
                posed = replace(shutter, center=shutter.center + np.asarray(offset)*fraction)
                for obstacle in broadphase(posed, obstacles, centers, extents, .025):
                    depth = sat_penetration(posed, obstacle, .025)
                    if depth is not None:
                        shutter_contacts.append({'fraction': float(fraction), 'obstacle': obstacle.ref,
                                                 'path': obstacle.path, 'overlap': round(depth, 5)})
            if shutter_contacts:
                errors.append('P04 optical shutter intersects its housing or optics during travel')
            feedback_results['observer_shutter'] = {'ref': shutter_ref, 'samples': 9,
                                                   'closed_position': shutter.center.tolist(),
                                                   'open_offset': offset, 'collision_candidates': shutter_contacts}
    lamps = feedback.get('p01_lamps', {})
    if set(lamps) != {'A', 'B', 'C'}:
        errors.append('Three physical P01 signal channels missing')
    for channel, ref in lamps.items():
        lamp = current.get(ref)
        if lamp is None or ref not in boxes or name(lamp) != 'V10_P01_Light_' + channel:
            errors.append('Invalid P01 signal lamp: ' + channel)
            continue
        if child(lamp, 'ChannelLight', 'PointLight') is None:
            errors.append('P01 signal lamp lacks actual light: ' + channel)
        feedback_results['p01_lamps'][channel] = {'ref': ref, 'path': path_of(ref, current, parents)}
    reference_ref = feedback.get('p05_reference')
    if reference_ref not in current or current[reference_ref].get('class') != 'TextLabel' or name(current[reference_ref]) != 'V10_P05_Reference':
        errors.append('Independent physical P05 reference display missing')
    else:
        feedback_results['p05_reference'] = {'ref': reference_ref, 'path': path_of(reference_ref, current, parents)}

    content = json.loads((ROOT / 'tools/v10_content.json').read_text())
    documents = {d['id']: d for d in content['documents']}
    assert len(documents) == len(content['documents']), 'Duplicate lore document IDs'
    interactions, console_ids, response_ids = [], set(), set()
    for record in manifest.get('world', {}).get('interactions', []):
        ref = record['part']
        if ref not in boxes:
            errors.append('Interaction is not a BasePart: ' + ref)
            continue
        part = current[ref]
        config, prompt = child(part, 'V10_Interact', 'Folder'), child(part, 'V10_Prompt', 'ProximityPrompt')
        if config is None or prompt is None:
            errors.append('Interaction metadata/prompt missing: ' + path_of(ref, current, parents))
            continue
        action_item, argument_item = child(config, 'Action', 'StringValue'), child(config, 'Argument', 'StringValue')
        action, argument = value(action_item) if action_item is not None else None, value(argument_item) if argument_item is not None else None
        if action not in ALLOWED_ACTIONS or action != record['action'] or argument != record['argument']:
            errors.append('Interaction metadata mismatch: ' + path_of(ref, current, parents))
        if not boolprop(part, 'CanQuery') or not boolprop(prompt, 'Enabled') or not boolprop(prompt, 'RequiresLineOfSight'):
            errors.append('Interaction visibility/query flags invalid: ' + path_of(ref, current, parents))
        distance = float(prompt.findtext("Properties/float[@name='MaxActivationDistance']", '0'))
        if not 0 < distance <= 10:
            errors.append('Interaction range invalid: ' + path_of(ref, current, parents))
        if action == 'console':
            console_ids.add(argument)
        if action == 'response':
            response_ids.add(argument)
            if argument not in ('left', 'center', 'right'):
                errors.append('Physical P02 station has invalid lane: ' + str(argument))
        if action == 'document' and argument not in documents:
            errors.append('Document interaction references nonexistent content: ' + str(argument))
        if action == 'npc' and argument not in content['staff']:
            errors.append('NPC interaction references nonexistent staff: ' + str(argument))
        approach = reachable(boxes[ref], all_solids, queryable)
        if not approach['reachable']:
            errors.append('No sampled standing-body interaction approach: ' + path_of(ref, current, parents))
        interactions.append({**record, 'path': path_of(ref, current, parents), **approach})
    if console_ids != {'P01', 'P02', 'P03', 'P04', 'P05'}:
        errors.append('Five experiment consoles not present: ' + repr(console_ids))
    if response_ids != {'left', 'center', 'right'}:
        errors.append('Three physical P02 response lanes not present: ' + repr(response_ids))
    doc_ids_in_world = {r['argument'] for r in interactions if r['action'] == 'document'}
    if set(documents) - doc_ids_in_world:
        errors.append('Lore documents have no physical access: ' + repr(sorted(set(documents) - doc_ids_in_world)))

    # Verify script text against authored files rather than trusting mere names.
    script_checks = []
    expected_sources = {
        'ExperimentCore': ('ModuleScript', ROOT / 'src/ExperimentCore_V10.luau'),
        'ProjectNullServer_V10': ('Script', ROOT / 'src/ProjectNullServer_V10.server.luau'),
        'ProjectNullClient_V10': ('LocalScript', ROOT / 'src/ProjectNullClient_V10.client.luau'),
    }
    for label, (cls, path) in expected_sources.items():
        matches = [e for e in root.iter('Item') if name(e) == label and e.get('class') == cls]
        if len(matches) != 1:
            errors.append('Missing/duplicated runtime source: ' + label)
            continue
        item = matches[0]
        source_text = item.findtext("Properties/ProtectedString[@name='Source']", '')
        if source_text != path.read_text():
            errors.append('Embedded runtime differs from source: ' + label)
        if cls != 'ModuleScript' and boolprop(item, 'Disabled'):
            errors.append('Runtime script disabled: ' + label)
        trail = path_of(item.get('referent'), current, parents)
        if cls == 'LocalScript' and 'StarterPlayer/StarterPlayerScripts/' not in trail:
            errors.append('Client runtime not in StarterPlayerScripts: ' + trail)
        if cls in ('Script', 'ModuleScript') and not trail.startswith('ServerScriptService/'):
            errors.append('Server runtime/module misplaced: ' + trail)
        script_checks.append({'name': label, 'path': trail, 'source_sha256': hashlib.sha256(source_text.encode()).hexdigest()})
    content_modules = [e for e in root.iter('Item') if e.get('class') == 'ModuleScript' and name(e) == 'Content']
    if len(content_modules) != 1 or not path_of(content_modules[0].get('referent'), current, parents).startswith('ServerScriptService/'):
        errors.append('Private narrative Content module missing or exposed')
    remote_checks = []
    for label in ('Request', 'Push'):
        matches = [e for e in root.iter('Item') if e.get('class') == 'RemoteEvent' and name(e) == label
                   and path_of(e.get('referent'), current, parents) == 'ReplicatedStorage/ProjectNullV10/' + label]
        if len(matches) != 1:
            errors.append('Required RemoteEvent missing: ' + label)
        remote_checks.append({'name': label, 'count': len(matches)})
    staff_rigs = []
    for staff_id in content.get('staff', {}):
        rigs = [e for e in root.iter('Item') if e.get('class') == 'Model' and name(e) == 'Staff_' + staff_id]
        if len(rigs) != 1:
            errors.append('Staff rig missing: ' + staff_id)
            continue
        rig = rigs[0]
        labels = {name(e): e.get('class') for e in rig.findall('Item')}
        valid = labels.get('Humanoid') == 'Humanoid' and labels.get('Head') == 'Part'
        if not valid:
            errors.append('Staff lacks humanoid/head: ' + staff_id)
        else:
            humanoid = child(rig, 'Humanoid', 'Humanoid')
            neck = next((e for e in rig.iter('Item') if e.get('class') in ('Motor6D', 'Motor')
                         and name(e) == 'Neck'), None)
            if neck is None and boolprop(humanoid, 'RequiresNeck', True):
                errors.append('Stationed staff has no neck joint and still requires one: ' + staff_id)
        staff_rigs.append({'id': staff_id, 'children': labels, 'valid': valid})
    return {
        'result': 'PASS' if not errors else 'REVIEW_REQUIRED',
        'validation': 'Static XML and conservative oriented bounds; no Roblox Studio execution',
        'source_sha256': sha(source), 'target_sha256': sha(target),
        'protected_v9_instances': len(before), 'modified_v9_instances': modified,
        'removed_v9_instances': removed, 'reparented_v9_instances': reparented,
        'new_instances': len(new_refs), 'new_parts': len(new_parts),
        'new_part_roles': dict(Counter(roles.values())), 'new_primary_colliders': len(new_solids),
        'registered_cavities': len(cavities), 'cavities': cavities,
        'standing_body_routes': route_results,
        'existing_click_targets_checked': len(click_targets), 'existing_click_target_overlaps': target_overlaps,
        'new_vs_existing_physical_intersections': structural_intersections,
        'services_checked': service_results, 'service_sweep_samples_per_mover': 9,
        'service_sweep_collision_candidates': sweep_collisions,
        'physical_protocol_feedback': feedback_results,
        'interaction_approaches': interactions, 'lore_document_count': len(documents),
        'runtime_sources': script_checks, 'remotes': remote_checks, 'staff_rigs': staff_rigs,
        'warnings': warnings, 'errors': errors,
        'limitations': [
            'No real Roblox rendering, avatar traversal, physics, replication or audio test was executed.',
            'Interaction approaches sample a ground-level body and finite ray, not a continuous path from spawn.',
            'Cylinders, spheres and meshes use conservative oriented boxes.',
            'Service movement uses nine sampled poses; actual continuous animation still needs engine testing.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'artifacts/PROJECT_NULL_ENGINEERING_V9.rbxlx')
    parser.add_argument('--target', type=Path, default=ROOT / 'artifacts/PROJECT_NULL_GAMEPLAY_V10.rbxlx')
    parser.add_argument('--manifest', type=Path, default=ROOT / 'artifacts/V10_MANIFEST.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/V10_AUDIT.json')
    args = parser.parse_args()
    report = validate(args.source, args.target, args.manifest)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('result', 'protected_v9_instances', 'new_instances',
                     'new_parts', 'new_primary_colliders', 'registered_cavities', 'lore_document_count',
                     'warnings', 'errors')}, ensure_ascii=False, indent=2))
    if report['result'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
