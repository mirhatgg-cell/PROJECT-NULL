#!/usr/bin/env python3
"""Export the V7 addition as an offline, pasteable Roblox Studio installer.

The JSON payload contains plain, dictionary-indexed part records. It is parsed
locally by HttpService:JSONDecode; the installer makes no HTTP requests.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts/PROJECT_NULL_INTERIORS_V7_DETAIL.rbxlx"
OUTPUT = ROOT / "artifacts/INSTALL_V7_COMMAND_BAR.luau"
MATERIALS = {272: "SmoothPlastic", 1088: "Metal", 1312: "Fabric"}
PART_STYLE = {
    "Anchored": True, "CanCollide": False, "CanTouch": False,
    "CanQuery": False, "CastShadow": False, "Transparency": 0,
    "TopSurface": 0, "BottomSurface": 0,
}
GUI_STYLE = {
    "Name": "V7_Legend", "PixelsPerStud": 55, "SizingMode": 1,
    "LightInfluence": .65, "AlwaysOnTop": False,
}
TEXT_STYLE = {
    "Name": "Legend", "Size": (1, 0, 1, 0),
    "BackgroundTransparency": 1, "TextScaled": True,
    "TextWrapped": True, "RichText": False, "Font": 10,
}


def properties(item):
    result = {}
    for prop in item.find("Properties"):
        tag, key = prop.tag, prop.get("name")
        if len(prop):
            result[key] = tuple(float(child.text) for child in prop)
        elif tag == "bool":
            result[key] = prop.text == "true"
        elif tag in {"float", "double"}:
            result[key] = float(prop.text)
        elif tag in {"token", "Color3uint8", "int", "int64"}:
            result[key] = int(prop.text)
        elif tag == "string":
            result[key] = prop.text or ""
        else:
            raise AssertionError(f"Unsupported property type: {tag}")
    return result


def compact(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, (list, tuple)):
        return [compact(v) for v in value]
    if isinstance(value, dict):
        return {k: compact(v) for k, v in value.items()}
    return value


def palette_rgb(packed):
    return ((packed >> 16) & 255, (packed >> 8) & 255, packed & 255)


def export_data(subtree):
    classes = Counter(e.get("class") for e in subtree.iter("Item"))
    assert classes == {"Model": 15, "Part": 292, "StringValue": 6,
                       "SurfaceGui": 16, "TextLabel": 16}, classes
    data = {k: [] for k in ("models", "names", "sizes", "colors", "materials", "rotations", "parts", "notes", "labels")}
    groups = {cls: [e for e in subtree.iter("Item") if e.get("class") == cls]
              for cls in classes}
    prefix = {"Model": "m", "Part": "p", "StringValue": "s", "SurfaceGui": "g", "TextLabel": "t"}
    keys = {e.get("referent"): prefix[cls]+str(i) for cls, items in groups.items()
            for i, e in enumerate(items, 1)}
    parents = {c.get("referent"): p for p in subtree.iter("Item") for c in p.findall("Item")}
    model_ids = {e.get("referent"): i for i, e in enumerate(groups["Model"], 1)}
    part_ids = {e.get("referent"): i for i, e in enumerate(groups["Part"], 1)}

    def intern(key, value):
        if value not in data[key]:
            data[key].append(value)
        return data[key].index(value)+1

    for model in groups["Model"]:
        parent = parents.get(model.get("referent"))
        props = properties(model)
        assert set(props) == {"Name"}
        data["models"].append([model_ids[parent.get("referent")] if parent is not None else 0, props["Name"]])
    for part in groups["Part"]:
        props = properties(part)
        props.setdefault("shape", 1)
        assert {k: props[k] for k in PART_STYLE} == PART_STYLE
        assert set(props) == set(PART_STYLE) | {"Name", "CFrame", "size", "Color3uint8", "Material", "shape"}
        assert props["shape"] in (1, 2)
        frame = props["CFrame"]
        assert len(frame) == 12 and len(props["size"]) == 3
        data["parts"].append([
            model_ids[parents[part.get("referent")].get("referent")],
            intern("names", props["Name"]), *frame[:3],
            intern("sizes", props["size"]), intern("colors", props["Color3uint8"]),
            intern("materials", MATERIALS[props["Material"]]),
            intern("rotations", frame[3:]), props["shape"],
        ])
    for note in groups["StringValue"]:
        props = properties(note)
        assert set(props) == {"Name", "Value"}
        data["notes"].append([model_ids[parents[note.get("referent")].get("referent")], props["Name"], props["Value"]])
    for gui in groups["SurfaceGui"]:
        props = properties(gui)
        assert {k: props[k] for k in GUI_STYLE} == GUI_STYLE
        assert set(props) == set(GUI_STYLE) | {"Face"}
        children = gui.findall("Item")
        assert len(children) == 1 and children[0].get("class") == "TextLabel"
        text = properties(children[0])
        assert {k: text[k] for k in TEXT_STYLE} == TEXT_STYLE
        assert set(text) == set(TEXT_STYLE) | {"Text", "TextColor3"}
        channels = tuple(round(c*255) for c in text["TextColor3"])
        assert all(abs(channels[i]/255-text["TextColor3"][i]) < 1e-12 for i in range(3))
        packed = (255 << 24) | (channels[0] << 16) | (channels[1] << 8) | channels[2]
        data["labels"].append([part_ids[parents[gui.get("referent")].get("referent")],
                               props["Face"], intern("colors", packed), text["Text"]])
    source_records = {}
    for item in subtree.iter("Item"):
        key = keys[item.get("referent")]
        parent = parents.get(item.get("referent"))
        props = properties(item)
        if item.get("class") == "Part":
            props.setdefault("shape", 1)
        source_records[key] = {"class": item.get("class"),
                               "parent": keys[parent.get("referent")] if parent is not None else None,
                               "properties": compact(props)}
    return compact(data), source_records


def decode_records(data):
    """Independent reconstruction verifies each exported property and parent."""
    records = {}
    def put(key, cls, parent, props):
        records[key] = {"class": cls, "parent": parent, "properties": compact(props)}
    for i, (parent, label) in enumerate(data["models"], 1):
        put(f"m{i}", "Model", f"m{parent}" if parent else None, {"Name": label})
    reverse_materials = {v: k for k, v in MATERIALS.items()}
    for i, row in enumerate(data["parts"], 1):
        parent, name_id, x, y, z, size_id, color_id, material_id, rotation_id, shape = row
        props = dict(PART_STYLE, Name=data["names"][name_id-1],
                     CFrame=[x, y, z]+data["rotations"][rotation_id-1],
                     size=data["sizes"][size_id-1], Color3uint8=data["colors"][color_id-1],
                     Material=reverse_materials[data["materials"][material_id-1]], shape=shape)
        put(f"p{i}", "Part", f"m{parent}", props)
    for i, (parent, label, value) in enumerate(data["notes"], 1):
        put(f"s{i}", "StringValue", f"m{parent}", {"Name": label, "Value": value})
    for i, (part, face, color_id, text) in enumerate(data["labels"], 1):
        put(f"g{i}", "SurfaceGui", f"p{part}", dict(GUI_STYLE, Face=face))
        rgb = tuple(v/255 for v in palette_rgb(data["colors"][color_id-1]))
        put(f"t{i}", "TextLabel", f"g{i}", dict(TEXT_STYLE, Text=text, TextColor3=rgb))
    return records


TEMPLATE = '''-- PROJECT: NULL V7: paste the ENTIRE block into Studio Command Bar in EDIT mode.
-- Offline installer: JSONDecode parses the plain data below; no HTTP request.
-- Adds only Visual_Detail_V7. Existing V6 objects are never edited or deleted.
local run = game:GetService("RunService")
assert(run:IsStudio() and not run:IsRunning(), "Stop Play and run this in Studio edit mode.")
local facility = workspace:FindFirstChild("PROJECT_NULL_ARCH_P01")
assert(facility and facility:IsA("Model"), "Open PROJECT_NULL_INTERIORS_V6 first.")
local equipment = facility:FindFirstChild("Equipment")
assert(equipment and equipment:IsA("Model"), "The V6 Equipment model was not found.")
assert(not equipment:FindFirstChild("Visual_Detail_V7"), "V7 is already present; nothing was changed.")
local history = game:GetService("ChangeHistoryService")
local payload = [==[__PAYLOAD__]==]
local d = game:GetService("HttpService"):JSONDecode(payload)
assert(#d.models == 15 and #d.parts == 292 and #d.notes == 6 and #d.labels == 16, "Incomplete installer data.")
local objects, models, parts = {}, {}, {}
local root, recording
local function create(className, name)
    local object = Instance.new(className)
    objects[#objects+1] = object
    object.Name = name
    return object
end
local function color(packed)
    return Color3.fromRGB(math.floor(packed/65536)%256, math.floor(packed/256)%256, packed%256)
end
local faces = {[0]=Enum.NormalId.Right, [1]=Enum.NormalId.Top, [2]=Enum.NormalId.Back, [5]=Enum.NormalId.Front}
local shapes = {[1]=Enum.PartType.Block, [2]=Enum.PartType.Cylinder}
local ok, problem = xpcall(function()
    for i, row in ipairs(d.models) do
        local model = create("Model", row[2])
        models[i] = model
        if row[1] == 0 then
            assert(not root and i == 1, "Invalid root model.")
            root = model
        else
            assert(models[row[1]], "Invalid model parent.")
            model.Parent = models[row[1]]
        end
    end
    assert(root and root.Name == "Visual_Detail_V7", "Invalid V7 root.")
    for i, row in ipairs(d.parts) do
        local p = create("Part", d.names[row[2]])
        parts[i] = p
        p.Anchored = true
        p.CanCollide = false
        p.CanTouch = false
        p.CanQuery = false
        p.CastShadow = false
        p.Transparency = 0
        p.TopSurface = Enum.SurfaceType.Smooth
        p.BottomSurface = Enum.SurfaceType.Smooth
        p.Shape = assert(shapes[row[10]], "Invalid shape.")
        local size = d.sizes[row[6]]
        p.Size = Vector3.new(size[1], size[2], size[3])
        local r = d.rotations[row[9]]
        p.CFrame = CFrame.new(row[3], row[4], row[5], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9])
        p.Color = color(d.colors[row[7]])
        p.Material = assert(Enum.Material[d.materials[row[8]]], "Invalid material.")
        p.Parent = assert(models[row[1]], "Invalid part parent.")
    end
    for _, row in ipairs(d.notes) do
        local note = create("StringValue", row[2])
        note.Value = row[3]
        note.Parent = assert(models[row[1]], "Invalid note parent.")
    end
    for _, row in ipairs(d.labels) do
        local gui = create("SurfaceGui", "V7_Legend")
        gui.Face = assert(faces[row[2]], "Invalid label face.")
        gui.PixelsPerStud = 55
        gui.SizingMode = Enum.SurfaceGuiSizingMode.PixelsPerStud
        gui.LightInfluence = 0.65
        gui.AlwaysOnTop = false
        local text = create("TextLabel", "Legend")
        text.Size = UDim2.new(1, 0, 1, 0)
        text.BackgroundTransparency = 1
        text.Text = row[4]
        text.TextColor3 = color(d.colors[row[3]])
        text.TextScaled = true
        text.TextWrapped = true
        text.RichText = false
        text.Font = Enum.Font.Code
        text.Parent = gui
        gui.Parent = assert(parts[row[1]], "Invalid label parent.")
    end
    assert(#objects == 345 and #parts == 292, "Incomplete model construction.")
    assert(not equipment:FindFirstChild("Visual_Detail_V7"), "V7 appeared during installation; stopping.")
    recording = history:TryBeginRecording("InstallProjectNullV7", "PROJECT: NULL V7 details")
    assert(recording, "Undo recording could not start. Exit Play or finish the active recording, then retry.")
    root.Parent = equipment
    history:FinishRecording(recording, Enum.FinishRecordingOperation.Commit)
    recording = nil
end, function(message) return tostring(message) end)
if not ok then
    if recording then
        pcall(function() history:FinishRecording(recording, Enum.FinishRecordingOperation.Cancel) end)
    end
    for i = #objects, 1, -1 do pcall(function() objects[i]:Destroy() end) end
    error("V7 was not installed: " .. problem, 0)
end
pcall(function() game:GetService("Selection"):Set({root}) end)
print("PROJECT: NULL V7 installed: 292 decorative parts. Press F to focus; Undo removes this addition.")
'''


def main():
    tree = ET.parse(SOURCE)
    subtree = next(e for e in tree.getroot().iter("Item")
                   if e.findtext("Properties/string[@name='Name']") == "Visual_Detail_V7")
    data, expected = export_data(subtree)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    assert "]==]" not in payload
    loaded = json.loads(payload)
    actual = decode_records(loaded)
    assert expected == actual, "Exported property/hierarchy roundtrip failed"
    script = TEMPLATE.replace("__PAYLOAD__", payload)
    assert "__PAYLOAD__" not in script
    assert script.count("JSONDecode") == 2
    OUTPUT.write_text(script, encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "bytes": len(script.encode("utf-8")),
                      "payload_bytes": len(payload.encode("utf-8")),
                      "instances": len(actual), "parts": len(loaded["parts"]),
                      "property_and_parent_roundtrip": "PASS",
                      "sha256": hashlib.sha256(script.encode("utf-8")).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
