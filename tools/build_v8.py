#!/usr/bin/env python3
"""Stage 3: append specialized equipment to V7 without editing prior instances."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from v7_common import Builder, name
import v8_calibration
import v8_physical
import v8_servers

ROOT = Path(__file__).resolve().parents[1]
MODEL = "Experimental_Equipment_V8"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT/"artifacts/PROJECT_NULL_INTERIORS_V7_DETAIL.rbxlx")
    parser.add_argument("--output", type=Path, default=ROOT/"artifacts/PROJECT_NULL_EXPERIMENTAL_V8.rbxlx")
    args = parser.parse_args()
    tree = ET.parse(args.source)
    root = tree.getroot()
    equipment = next(e for e in root.iter("Item") if name(e) == "Equipment" and e.get("class") == "Model")
    assert not any(name(e) == MODEL for e in equipment.findall("Item")), "Build V8 from V7, not an already updated file"
    assert any(name(e) == "Visual_Detail_V7" for e in equipment.findall("Item")), "V7 details are required"
    b = Builder(root)
    additions = b.model(equipment, MODEL)
    b.note(additions, "README", "Stage 3 / V8: metrology bench, physical test instrumentation and server infrastructure. Static specialized equipment. Original architecture, V7 and interactive scripts are preserved. Technical interfaces are labelled; these models do not simulate real experimental or clinical procedures.")
    for module in (v8_calibration, v8_physical, v8_servers):
        module.build(b, additions)
    assert len(b.parts) <= 500, "Stage 3 geometry budget exceeded"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(args.output, encoding="utf-8", xml_declaration=True)
    model_root = ET.Element("roblox", {"version": "4"})
    for value in ("null", "nil"):
        ET.SubElement(model_root, "External").text = value
    model_root.append(copy.deepcopy(additions))
    model_path = args.output.with_name("PROJECT_NULL_STAGE3_V8.rbxmx")
    ET.ElementTree(model_root).write(model_path, encoding="utf-8", xml_declaration=True)
    groups = {name(e): sum(p.get("class") == "Part" for p in e.iter("Item"))
              for e in additions.findall("Item") if e.get("class") == "Model"}
    print(json.dumps({"output": str(args.output), "importable_model": str(model_path),
                      "added_parts": len(b.parts), "groups": groups,
                      "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()

