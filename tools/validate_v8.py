#!/usr/bin/env python3
"""Check V8 preservation, XML references, room envelopes and door travel volumes."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from v7_common import name
from validate_v7 import BASE_CLASSES, geometry, index

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/"artifacts/PROJECT_NULL_INTERIORS_V7_DETAIL.rbxlx"
OUTPUT = ROOT/"artifacts/PROJECT_NULL_EXPERIMENTAL_V8.rbxlx"
MODEL = "Experimental_Equipment_V8"
LIMITS = {
    "E07_Metrology": ((-57.5,-30.5),(-64.15,-40),(-59.5,-36.5)),
    "E10_Experimental_Equipment": ((126.5,181.5),(-64.15,-40),(-35.5,35.5)),
    "E16_Server_Infrastructure": ((-15.5,15.5),(-64.15,-40),(51.5,74.5)),
}


def overlaps(a, b, tolerance=.025):
    center, half = a
    other, radius = b
    return all(min(center[i]+half[i],other[i]+radius[i])-max(center[i]-half[i],other[i]-radius[i]) > tolerance for i in range(3))


def main():
    source = ET.parse(SOURCE).getroot()
    output = ET.parse(OUTPUT).getroot()
    before, before_parents = index(source)
    after, after_parents = index(output)
    for ref, old in before.items():
        assert ref in after and old.get("class") == after[ref].get("class"), f"Missing/changed original: {name(old)}"
        assert ET.tostring(old.find("Properties")) == ET.tostring(after[ref].find("Properties")), f"Original properties changed: {name(old)}"
        assert before_parents.get(ref) == after_parents.get(ref), f"Original parent changed: {name(old)}"
        assert [e.get("referent") for e in old.findall("Item")] == [e.get("referent") for e in after[ref].findall("Item") if e.get("referent") in before], f"Original child order changed: {name(old)}"
    broken = [e.text for e in output.iter("Ref") if e.text not in (None,"null","nil") and e.text not in after]
    assert not broken, broken
    new = [e for ref,e in after.items() if ref not in before]
    allowed = {"Model","Part","StringValue","SurfaceGui","TextLabel"}
    assert all(e.get("class") in allowed for e in new), "Unexpected new behavior or unsupported asset class"
    parts = [e for e in new if e.get("class") == "Part"]
    assert 0 < len(parts) <= 500
    for part in parts:
        for prop,value in (("Anchored","true"),("CanCollide","false"),("CanTouch","false"),("CanQuery","false")):
            assert part.findtext(f"Properties/bool[@name='{prop}']") == value, (name(part),prop)
        geometry(part)
    addition = next(e for e in new if name(e) == MODEL)
    assert set(e.get("referent") for e in addition.iter("Item")) == set(e.get("referent") for e in new), "Unexpected additions outside stage model"
    groups = {}
    for group in addition.findall("Item"):
        if group.get("class") != "Model": continue
        assert name(group) in LIMITS, name(group)
        entries = [e for e in group.iter("Item") if e.get("class") == "Part"]
        groups[name(group)] = len(entries)
        for part in entries:
            center,half=geometry(part)
            for axis,(lo,hi) in enumerate(LIMITS[name(group)]):
                assert center[axis]-half[axis] >= lo-.015 and center[axis]+half[axis] <= hi+.015, (name(group),name(part),axis,center[axis]-half[axis],center[axis]+half[axis])
    assert sum(groups.values()) == len(parts)
    # Reproduce the original door controller's local open translation.
    doors = next(e for e in before.values() if name(e) == "Doors")
    travel = []
    for model in doors.findall("Item"):
        leaf = next((e for e in model.findall("Item") if name(e) == "Leaf"), None)
        if leaf is None: continue
        center,half=geometry(leaf)
        size=leaf.find("Properties/Vector3[@name='size']")
        local_delta=(float(size.findtext('X'))+.25,0,0) if float(size.findtext('Y'))>12 else (0,float(size.findtext('Y'))+.25,0)
        frame=leaf.find("Properties/CoordinateFrame[@name='CFrame']")
        delta=tuple(sum(float(frame.findtext(f'R{i}{j}'))*local_delta[j] for j in range(3)) for i in range(3))
        swept_center=tuple(center[i]+delta[i]/2 for i in range(3))
        swept_half=tuple(half[i]+abs(delta[i])/2 for i in range(3))
        travel.append((name(model),(swept_center,swept_half)))
    for part in parts:
        bounds=geometry(part)
        for door,swept in travel:
            assert not overlaps(bounds,swept), f"New detail in {door} leaf travel: {name(part)}"
    # Standalone import model must contain exactly the same addition.
    standalone=ET.parse(ROOT/'artifacts/PROJECT_NULL_STAGE3_V8.rbxmx').getroot()
    assert ET.tostring(standalone.find('Item')) == ET.tostring(addition)
    counts_before=Counter(e.get('class') for e in before.values())
    counts_after=Counter(e.get('class') for e in after.values())
    report={"result":"PASS","stage":3,"validation":"Static XML and geometry only; Roblox Studio execution still required",
            "source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "output_sha256":hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
            "preserved_instances":len(before),"original_properties_and_hierarchy_unchanged":True,
            "preserved_scripts":counts_before['Script'],"preserved_click_detectors":counts_before['ClickDetector'],
            "before_baseparts":sum(counts_before[c] for c in BASE_CLASSES),"after_baseparts":sum(counts_after[c] for c in BASE_CLASSES),
            "added_baseparts":len(parts),"part_increase_percent":round(100*len(parts)/sum(counts_before[c] for c in BASE_CLASSES),2),
            "groups":groups,"broken_references":0,"new_collidable_or_queryable_parts":0,
            "door_leaf_travel_volumes_checked":len(travel),"standalone_model_matches":True}
    (ROOT/'artifacts/VALIDATION_V8.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__': main()
