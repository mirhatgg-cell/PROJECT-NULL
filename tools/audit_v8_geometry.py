#!/usr/bin/env python3
"""Independently audit added V8 geometry against V7 using oriented-box SAT.

These are conservative box tests: meshes, cylinders and spheres use their
oriented part bounds. The report is a review aid, not a Roblox Studio playtest.
Allowlisted attachments remain in the output and require exact referents,
paths and a written reason; no overlap is silently discarded. Roblox permits
siblings with identical names, so paths alone cannot identify an allowance.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BASE_CLASSES = {"Part", "Seat", "SpawnLocation", "MeshPart", "WedgePart", "UnionOperation", "TrussPart"}


@dataclass
class Box:
    ref: str
    path: str
    name: str
    cls: str
    center: np.ndarray
    half: np.ndarray
    rotation: np.ndarray
    extent: np.ndarray
    transparency: float
    interactive: bool
    display: bool
    shape: str

    def describe(self):
        return {
            "ref": self.ref, "path": self.path, "name": self.name,
            "class": self.cls, "center": self.center.tolist(),
            "size": (self.half * 2).tolist(),
            "shape_bounds": self.shape, "transparency": self.transparency,
            "click_target": self.interactive, "display": self.display,
        }


def load(path):
    root = ET.parse(path).getroot()
    references = {e.get("referent") for e in root.iter("Item")}
    boxes = []

    def visit(item, ancestors):
        label = item.findtext("Properties/string[@name='Name']", item.get("class", "?"))
        trail = ancestors + [label]
        cls = item.get("class")
        if cls in BASE_CLASSES:
            frame = item.find("Properties/CoordinateFrame[@name='CFrame']")
            vector = item.find("Properties/Vector3[@name='size']")
            if vector is None:
                vector = item.find("Properties/Vector3[@name='Size']")
            if frame is None or vector is None:
                raise ValueError("Missing part geometry: " + "/".join(trail))
            center = np.array([float(frame.findtext(k)) for k in "XYZ"])
            half = np.array([float(vector.findtext(k)) / 2 for k in "XYZ"])
            rotation = np.array([[float(frame.findtext(f"R{i}{j}")) for j in range(3)] for i in range(3)])
            assert np.isfinite(center).all() and np.isfinite(half).all() and np.isfinite(rotation).all()
            assert (half > 0).all(), trail
            assert np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6), trail
            classes = {child.get("class") for child in item.iter("Item")}
            shape = item.findtext("Properties/token[@name='shape']", "1")
            boxes.append(Box(
                ref=item.get("referent"), path="/".join(trail), name=label, cls=cls,
                center=center, half=half, rotation=rotation,
                extent=np.abs(rotation) @ half,
                transparency=float(item.findtext("Properties/float[@name='Transparency']", "0")),
                interactive="ClickDetector" in classes or "ProximityPrompt" in classes,
                display="SurfaceGui" in classes or "BillboardGui" in classes,
                shape="block" if cls == "Part" and shape == "1" and "SpecialMesh" not in classes else "conservative_oriented_bounds",
            ))
        for child in item.findall("Item"):
            visit(child, trail)

    for item in root.findall("Item"):
        visit(item, [])
    return references, boxes


def sat_penetration(a, b, threshold):
    """Return minimum normalized SAT overlap, or None if separated/too shallow."""
    # Rows of these matrices are local axes in world coordinates.
    axes_a, axes_b = a.rotation.T, b.rotation.T
    axes = [*axes_a, *axes_b]
    axes.extend(np.cross(ax, bx) for ax in axes_a for bx in axes_b)
    delta = b.center - a.center
    minimum = float("inf")
    for axis in axes:
        norm = float(np.linalg.norm(axis))
        if norm < 1e-8:  # Parallel axes have no useful cross-product direction.
            continue
        direction = axis / norm
        radius_a = float(np.abs(axes_a @ direction) @ a.half)
        radius_b = float(np.abs(axes_b @ direction) @ b.half)
        overlap = radius_a + radius_b - abs(float(delta @ direction))
        if overlap <= threshold:
            return None
        minimum = min(minimum, overlap)
    return minimum


def read_allowlist(path):
    if path is None:
        return {}
    entries = json.loads(path.read_text())
    assert isinstance(entries, list)
    result = {}
    for entry in entries:
        assert set(entry) == {"new_ref", "original_ref", "new_path", "original_path", "reason"}, "Allowlist entries need exact referents, paths and a reason"
        assert all(isinstance(entry[key], str) and entry[key].strip() for key in entry)
        key = (entry["new_ref"], entry["original_ref"], entry["new_path"], entry["original_path"])
        assert key not in result, "Duplicate attachment allowance"
        result[key] = entry["reason"]
    return result


def audit(source, target, threshold=.025, allowlist=None):
    original_refs, original = load(source)
    _, current = load(target)
    added = [box for box in current if box.ref not in original_refs]
    assert added, "No new V8 BaseParts were found"
    # Transparent collision proxies do not contribute to visual intersections.
    # Active targets and displays are checked even when their carrier is hidden.
    candidates = [box for box in original if box.transparency < .99 or box.interactive or box.display]
    centers = np.array([box.center for box in candidates])
    extents = np.array([box.extent for box in candidates])
    allowances = allowlist or {}
    found_allowances = set()
    overlaps = []
    tested = 0
    for new in added:
        broad = np.where(np.all(np.abs(centers-new.center) < extents+new.extent-threshold, axis=1))[0]
        for index in broad:
            old = candidates[int(index)]
            tested += 1
            penetration = sat_penetration(new, old, threshold)
            if penetration is None:
                continue
            pair = (new.ref, old.ref, new.path, old.path)
            reason = allowances.get(pair)
            if reason is not None:
                found_allowances.add(pair)
            overlaps.append({
                "new": new.describe(), "original": old.describe(),
                "minimum_sat_overlap_studs": round(penetration, 6),
                "reviewed_attachment_reason": reason,
                "conservative_bounds": new.shape != "block" or old.shape != "block",
            })
    active = [row for row in overlaps if row["original"]["click_target"] or row["original"]["display"]]
    unreviewed = [row for row in overlaps if row["reviewed_attachment_reason"] is None]
    counts = Counter(row["new"]["path"].split("Experimental_Equipment_V8/")[-1].split("/")[0] for row in overlaps)
    result = {
        "status": "REVIEW_REQUIRED" if unreviewed or active else "PASS",
        "validation": "Static OBB SAT geometry audit; no Roblox Studio rendering or avatar traversal",
        "shape_limit": "All parts use oriented box bounds; cylinders/meshes can produce conservative candidates",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "target_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "source_baseparts": len(original), "new_baseparts": len(added),
        "original_visible_baseparts": sum(box.transparency < .99 for box in original),
        "original_hidden_collision_boxes_excluded": sum(box.transparency >= .99 and not box.interactive and not box.display for box in original),
        "original_click_targets_checked": sum(box.interactive for box in original),
        "original_display_carriers_checked": sum(box.display for box in original),
        "threshold_studs": threshold, "broad_phase_pairs": tested,
        "overlap_candidates": len(overlaps), "unreviewed_candidates": len(unreviewed),
        "active_control_or_display_candidates": len(active),
        "candidates_by_group": dict(counts),
        "unused_allowances": [dict(new_ref=a, original_ref=b, new_path=c, original_path=d, reason=allowances[(a,b,c,d)]) for a,b,c,d in sorted(set(allowances)-found_allowances)],
        "overlaps": overlaps,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT/"artifacts/PROJECT_NULL_INTERIORS_V7_DETAIL.rbxlx")
    parser.add_argument("--target", type=Path, default=ROOT/"artifacts/PROJECT_NULL_EXPERIMENTAL_V8.rbxlx")
    parser.add_argument("--output", type=Path, default=ROOT/"artifacts/GEOMETRY_AUDIT_V8.json")
    parser.add_argument("--allowlist", type=Path)
    parser.add_argument("--threshold", type=float, default=.025)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    assert args.threshold >= 0
    result = audit(args.source, args.target, args.threshold, read_allowlist(args.allowlist))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k != "overlaps"}, indent=2, ensure_ascii=False))
    if args.strict and result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
