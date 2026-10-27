"""Small deterministic Roblox XML authoring helpers; no external assets or scripts."""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

WHITE = (211, 220, 224)
LIGHT = (235, 239, 235)
METAL = (111, 131, 142)
DARK = (29, 41, 48)
BLACK = (16, 25, 31)
CYAN = (59, 191, 202)
AMBER = (219, 164, 72)
TEAL = (92, 144, 145)
BLUE = (89, 126, 153)
RED = (180, 66, 55)


def name(item):
    return item.findtext("Properties/string[@name='Name']", "")


class Builder:
    def __init__(self, root):
        self.root = root
        self.ids = {item.get("referent") for item in root.iter("Item")}
        self.sequence = 0
        self.parts = []

    def prop(self, item, tag, key, value=None):
        props = item.find("Properties")
        el = ET.SubElement(props, tag, {"name": key})
        if value is not None:
            el.text = str(value).lower() if isinstance(value, bool) else str(value)
        return el

    def item(self, parent, cls, label):
        while True:
            self.sequence += 1
            ref = "RBX" + format(0x70000000 + self.sequence, "032X")
            if ref not in self.ids:
                break
        self.ids.add(ref)
        item = ET.SubElement(parent, "Item", {"class": cls, "referent": ref})
        ET.SubElement(item, "Properties")
        self.prop(item, "string", "Name", label)
        return item

    def model(self, parent, label):
        return self.item(parent, "Model", label)

    def note(self, parent, label, text):
        item = self.item(parent, "StringValue", label)
        self.prop(item, "string", "Value", text)
        return item

    def part(self, parent, label, pos, size, color=WHITE, material=272,
             yaw=0, matrix=None, shape=None, transparency=0, shadow=False):
        assert all(math.isfinite(float(x)) and float(x) > 0 for x in size)
        item = self.item(parent, "Part", label)
        vector = self.prop(item, "Vector3", "size")
        for key, value in zip("XYZ", size):
            ET.SubElement(vector, key).text = f"{float(value):.7g}"
        frame = self.prop(item, "CoordinateFrame", "CFrame")
        for key, value in zip("XYZ", pos):
            ET.SubElement(frame, key).text = f"{float(value):.8g}"
        if matrix is None:
            c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
            matrix = ((c, 0, s), (0, 1, 0), (-s, 0, c))
        for i in range(3):
            for j in range(3):
                ET.SubElement(frame, f"R{i}{j}").text = f"{matrix[i][j]:.10g}"
        for key, value in [("Anchored", True), ("CanCollide", False),
                           ("CanTouch", False), ("CanQuery", False),
                           ("CastShadow", shadow)]:
            self.prop(item, "bool", key, value)
        self.prop(item, "float", "Transparency", transparency)
        self.prop(item, "token", "Material", material)
        self.prop(item, "token", "TopSurface", 0)
        self.prop(item, "token", "BottomSurface", 0)
        self.prop(item, "Color3uint8", "Color3uint8",
                  (255 << 24) | (color[0] << 16) | (color[1] << 8) | color[2])
        if shape is not None:
            self.prop(item, "token", "shape", shape)
        self.parts.append(item)
        return item

    def segment(self, parent, label, a, b, diameter=.12, color=DARK, cylinder=True):
        """Connect endpoints. Roblox cylinders run along their local X axis."""
        delta = [b[i] - a[i] for i in range(3)]
        length = math.sqrt(sum(d*d for d in delta))
        assert length > 1e-6
        x = [d/length for d in delta]
        helper = (0, 1, 0) if abs(x[1]) < .9 else (0, 0, 1)
        z = [x[1]*helper[2]-x[2]*helper[1], x[2]*helper[0]-x[0]*helper[2], x[0]*helper[1]-x[1]*helper[0]]
        norm = math.sqrt(sum(v*v for v in z))
        z = [v/norm for v in z]
        y = [z[1]*x[2]-z[2]*x[1], z[2]*x[0]-z[0]*x[2], z[0]*x[1]-z[1]*x[0]]
        matrix = tuple(tuple(v[i] for v in (x, y, z)) for i in range(3))
        return self.part(parent, label, tuple((a[i]+b[i])/2 for i in range(3)),
                         (length, diameter, diameter), color, material=1088,
                         matrix=matrix, shape=2 if cylinder else None)

    def label(self, part, text, color=LIGHT, face=5):
        gui = self.item(part, "SurfaceGui", "V7_Legend")
        self.prop(gui, "token", "Face", face)
        self.prop(gui, "float", "PixelsPerStud", 55)
        self.prop(gui, "token", "SizingMode", 1)
        self.prop(gui, "float", "LightInfluence", .65)
        self.prop(gui, "bool", "AlwaysOnTop", False)
        label = self.item(gui, "TextLabel", "Legend")
        size = self.prop(label, "UDim2", "Size")
        for key, value in [("XS", 1), ("XO", 0), ("YS", 1), ("YO", 0)]:
            ET.SubElement(size, key).text = str(value)
        self.prop(label, "float", "BackgroundTransparency", 1)
        self.prop(label, "string", "Text", text)
        color_el = self.prop(label, "Color3", "TextColor3")
        for key, value in zip("RGB", color):
            ET.SubElement(color_el, key).text = str(value/255)
        self.prop(label, "bool", "TextScaled", True)
        self.prop(label, "bool", "TextWrapped", True)
        self.prop(label, "bool", "RichText", False)
        self.prop(label, "token", "Font", 10)
        return gui
