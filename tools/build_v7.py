#!/usr/bin/env python3
"""Append a reversible visual pass to V6; preserve every original instance."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from v7_common import Builder, name
import v7_control
import v7_immersion
import v7_medical


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT/"source/PROJECT_NULL_INTERIORS_V6.rbxlx")
    parser.add_argument("--output", type=Path, default=ROOT/"artifacts/PROJECT_NULL_INTERIORS_V7_DETAIL.rbxlx")
    args = parser.parse_args()
    tree = ET.parse(args.source)
    root = tree.getroot()
    equipment = next(e for e in root.iter("Item") if name(e) == "Equipment" and e.get("class") == "Model")
    if any(name(e) == "Visual_Detail_V7" for e in equipment.findall("Item")):
        raise SystemExit("Input already contains V7 details; rebuild from the original V6.")
    b = Builder(root)
    additions = b.model(equipment, "Visual_Detail_V7")
    b.note(additions, "README", "Visual detailing pass: E03 immersion, E04 control, E06 medical. All new parts are anchored and noncolliding, CanQuery=false. No new gameplay. Remove this model to restore V6 content.")
    for module in (v7_immersion, v7_control, v7_medical):
        module.build(b, additions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(args.output, encoding="utf-8", xml_declaration=True)
    groups = {}
    for item in additions.findall("Item"):
        if item.get("class") == "Model":
            groups[name(item)] = sum(e.get("class") == "Part" for e in item.iter("Item"))
    print(json.dumps({"output": str(args.output), "added_parts": len(b.parts), "groups": groups,
                      "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
