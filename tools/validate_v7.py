#!/usr/bin/env python3
"""Structural/geometry checks. These do not substitute for a Studio playtest."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from v7_common import name

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source/PROJECT_NULL_INTERIORS_V6.rbxlx"
OUTPUT = ROOT / "artifacts/PROJECT_NULL_INTERIORS_V7_DETAIL.rbxlx"
BASE_CLASSES = {"Part", "Seat", "SpawnLocation", "MeshPart", "WedgePart", "UnionOperation"}
LIMITS = {
    "E03_Immersion_Detail": ((-23.6, 23.6), (-64.15, -38.0), (-23.6, 23.6)),
    "E04_Operator_Detail": ((-63.5, -24.5), (-64.15, -40.0), (-11.5, 11.5)),
    "E06_Medical_Detail": ((46.5, 73.5), (-64.15, -40.0), (-69.5, -46.5)),
    "E05_Recovery_Detail": ((40.5, 79.5), (-64.15, -40.0), (-23.5, 7.5)),
}


def index(root):
    items = list(root.iter("Item"))
    mapping = {e.get("referent"): e for e in items}
    assert len(mapping) == len(items), "Duplicate referents"
    parents = {c.get("referent"): p.get("referent") for p in root.iter("Item") for c in p.findall("Item")}
    return mapping, parents


def geometry(item):
    frame = item.find("Properties/CoordinateFrame[@name='CFrame']")
    size_el = item.find("Properties/Vector3[@name='size']")
    assert frame is not None and size_el is not None
    center = tuple(float(frame.findtext(k)) for k in "XYZ")
    size = tuple(float(size_el.findtext(k)) for k in "XYZ")
    matrix = tuple(tuple(float(frame.findtext(f"R{i}{j}")) for j in range(3)) for i in range(3))
    assert all(math.isfinite(v) for v in center+size+sum(matrix, ()))
    assert min(size) > 0
    for i in range(3):
        for j in range(3):
            assert abs(sum(matrix[k][i]*matrix[k][j] for k in range(3))-(1 if i == j else 0)) < 1e-6, "Invalid CFrame rotation"
    det = (matrix[0][0]*(matrix[1][1]*matrix[2][2]-matrix[1][2]*matrix[2][1])
           - matrix[0][1]*(matrix[1][0]*matrix[2][2]-matrix[1][2]*matrix[2][0])
           + matrix[0][2]*(matrix[1][0]*matrix[2][1]-matrix[1][1]*matrix[2][0]))
    assert abs(det-1) < 1e-6, "Reflected/invalid CFrame"
    half = tuple(sum(abs(matrix[i][j])*size[j]/2 for j in range(3)) for i in range(3))
    return center, half


def run():
    before = ET.parse(SOURCE).getroot()
    after = ET.parse(OUTPUT).getroot()
    original, original_parents = index(before)
    current, current_parents = index(after)
    # Check every original property, not just script source or part totals.
    for ref, old in original.items():
        assert ref in current, f"Original item deleted: {name(old)}"
        assert old.get("class") == current[ref].get("class"), f"Class changed: {name(old)}"
        assert ET.tostring(old.find("Properties")) == ET.tostring(current[ref].find("Properties")), f"Original properties changed: {name(old)}"
        assert original_parents.get(ref) == current_parents.get(ref), f"Original hierarchy changed: {name(old)}"
        assert [e.get("referent") for e in old.findall("Item")] == [e.get("referent") for e in current[ref].findall("Item") if e.get("referent") in original], f"Original children changed: {name(old)}"
    refs = [e.text for e in after.iter("Ref") if e.text not in (None, "null", "nil")]
    assert all(ref in current for ref in refs), "Broken object reference"
    new = [e for ref, e in current.items() if ref not in original]
    assert not any(e.get("class") in {"Script", "LocalScript", "ModuleScript", "ClickDetector", "RemoteEvent", "RemoteFunction"} for e in new), "Visual pass introduced behavior"
    parts = [e for e in new if e.get("class") in BASE_CLASSES]
    assert 0 < len(parts) <= 550, f"Unexpected detailing budget: {len(parts)}"
    for part in parts:
        for prop, expected in [("Anchored", "true"), ("CanCollide", "false"), ("CanTouch", "false"), ("CanQuery", "false")]:
            assert part.findtext(f"Properties/bool[@name='{prop}']") == expected, f"Unsafe decoration: {name(part)} / {prop}"
        geometry(part)
    additions = next(e for e in new if name(e) == "Visual_Detail_V7")
    group_counts = {}
    seen = 0
    for group in additions.findall("Item"):
        if group.get("class") != "Model":
            continue
        label = name(group)
        assert label in LIMITS, f"Missing room bounds for {label}"
        group_parts = [e for e in group.iter("Item") if e.get("class") in BASE_CLASSES]
        group_counts[label] = len(group_parts)
        seen += len(group_parts)
        for part in group_parts:
            center, half = geometry(part)
            for i, (lo, hi) in enumerate(LIMITS[label]):
                assert center[i]-half[i] >= lo-.015 and center[i]+half[i] <= hi+.015, f"Part outside {label}: {name(part)} axis {i}: {center[i]-half[i]:.3f}..{center[i]+half[i]:.3f}"
    assert seen == len(parts), "Unbounded new part"
    # New details must not visually fill the main floor-level door openings.
    # Bounds deliberately include full entry width and a little approach space.
    portals = [
        ((-5, 5), (-64, -50), (-24.6, -22.8)),
        ((-7, 7), (-64, -46), (22.8, 24.6)),
        ((22.8, 24.6), (-64, -50), (-6, 6)),
        ((-64.6, -62.8), (-64, -50), (-5, 5)),
        ((55, 65), (-64, -50), (-70.6, -68.8)),
        ((55, 65), (-64, -50), (-47.2, -45.4)),
    ]
    for part in parts:
        center, half = geometry(part)
        for portal in portals:
            overlap = [min(center[i]+half[i], portal[i][1])-max(center[i]-half[i], portal[i][0]) for i in range(3)]
            assert min(overlap) <= .015, f"New decoration inside door clearance: {name(part)}"
    before_classes = Counter(e.get("class") for e in original.values())
    after_classes = Counter(e.get("class") for e in current.values())
    report = {
        "result": "PASS",
        "validation": "Static XML, preservation and geometry checks only; no Roblox Studio execution",
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "original_instances_preserved": len(original),
        "original_properties_unchanged": True,
        "original_hierarchy_preserved": True,
        "original_scripts_preserved": before_classes["Script"],
        "original_click_detectors_preserved": before_classes["ClickDetector"],
        "before_baseparts": sum(before_classes[c] for c in BASE_CLASSES),
        "after_baseparts": sum(after_classes[c] for c in BASE_CLASSES),
        "added_baseparts": len(parts),
        "added_part_percent": round(len(parts)/sum(before_classes[c] for c in BASE_CLASSES)*100, 2),
        "groups": group_counts,
        "unresolved_references": 0,
        "new_collidable_or_queryable_parts": 0,
        "new_parts_in_checked_door_openings": 0,
        "room_envelopes_checked": list(group_counts),
    }
    report_path = ROOT/"artifacts/VALIDATION_V7.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()
