#!/usr/bin/env python3
"""Render a reproducible XML geometry comparison, without Roblox Studio.

The orthographic cutaway removes ceilings and near walls. SurfaceGui text,
lighting, Roblox materials and gameplay are not simulated.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import xml.etree.ElementTree as ET

os.environ.setdefault("MPLCONFIGDIR", "/tmp/project-null-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ROOMS = [
    ("E-03  /  IMMERSION", (-23.5, 23.5, -64.02, -48.5, -23.5, 23.5)),
    ("E-04  /  OPERATOR CONTROL", (-63.5, -24.5, -64.02, -48.5, -11.5, 11.5)),
    ("E-06  /  MEDICAL", (46.5, 73.5, -64.02, -54.8, -69.5, -46.5)),
]
CAMERA = np.array([1.0, .88, -1.0])
CAMERA /= np.linalg.norm(CAMERA)
RIGHT = np.array([-CAMERA[2], 0, CAMERA[0]])
RIGHT /= np.linalg.norm(RIGHT)
UP = np.cross(CAMERA, RIGHT)
# Cross order yields a screen-up vector with positive world Y.
if UP[1] < 0:
    UP *= -1
PROJECTION = np.stack([RIGHT, UP], axis=1)
CORNERS = np.array([[-1,-1,-1], [1,-1,-1], [1,1,-1], [-1,1,-1],
                    [-1,-1,1], [1,-1,1], [1,1,1], [-1,1,1]])
FACES = [(0,3,2,1), (4,5,6,7), (0,4,7,3),
         (1,2,6,5), (0,1,5,4), (3,7,6,2)]


def read_parts(path):
    root = ET.parse(path).getroot()
    result = []

    def visit(item, ancestors):
        props = item.find("Properties")
        label = props.findtext("string[@name='Name']", "")
        trail = ancestors + (label,)
        if item.get("class") in ("Part", "Seat", "SpawnLocation"):
            frame = props.find("CoordinateFrame[@name='CFrame']")
            size = props.find("Vector3[@name='size']")
            if frame is not None and size is not None:
                transparency = float(props.findtext("float[@name='Transparency']", "0"))
                xyz = np.array([float(frame.findtext(k)) for k in "XYZ"])
                extent = np.array([float(size.findtext(k)) for k in "XYZ"])
                matrix = np.array([[float(frame.findtext(f"R{i}{j}")) for j in range(3)] for i in range(3)])
                packed = int(props.findtext("Color3uint8[@name='Color3uint8']", "4286611584"))
                color = np.array([(packed >> 16) & 255, (packed >> 8) & 255, packed & 255])/255
                if transparency < .9 and max(extent) >= .1:
                    result.append({"name": label, "path": trail, "xyz": xyz,
                                   "size": extent, "matrix": matrix,
                                   "color": color, "alpha": 1-transparency})
        for child in item.findall("Item"):
            visit(child, trail)

    for item in root.findall("Item"):
        visit(item, ())
    return result


def clip_polygon(poly, axis, boundary, keep_above):
    """Clip a 3D face against an axis-aligned cutaway plane."""
    if not len(poly):
        return poly
    out = []
    previous = poly[-1]
    previous_inside = (previous[axis] >= boundary) if keep_above else (previous[axis] <= boundary)
    for current in poly:
        inside = (current[axis] >= boundary) if keep_above else (current[axis] <= boundary)
        if inside != previous_inside:
            t = (boundary-previous[axis])/(current[axis]-previous[axis])
            out.append(previous + t*(current-previous))
        if inside:
            out.append(current)
        previous, previous_inside = current, inside
    return np.array(out)


def room_faces(parts, bounds):
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    lo, hi = np.array([xmin-.55, ymin, zmin-.55]), np.array([xmax+.55, ymax, zmax+.55])
    result = []
    for part in parts:
        p, s = part["xyz"], part["size"]
        # Tiny electronics are normally hidden in their original housings.
        if part["name"] in {"IC_Pin", "PCB_CopperTrace", "IntegratedCircuit", "Capacitor", "TerminalBlock", "PCB_FR4"}:
            continue
        if "B2_Architecture" in part["path"]:
            n = part["name"].lower()
            if any(word in n for word in ("ceiling", "slab", "pedestal")):
                continue
            # Remove camera-facing boundary walls; retain the far cutaway walls.
            if (abs(p[0]-xmax) < 1.0 and s[1] > 8 and s[0] < 2) or (abs(p[2]-zmin) < 1.0 and s[1] > 8 and s[2] < 2):
                continue
        # Wall-mounted sheets on removed near walls must be cut away too;
        # otherwise their untextured backs obscure the equipment under review.
        if p[1] > ymin+2 and ((abs(p[0]-xmax) < .65 and s[0] < .35) or
                                  (abs(p[2]-zmin) < .65 and s[2] < .35)):
            continue
        if p[1]+s[1]/2 < ymin-.01:
            continue
        vertices = (CORNERS*s/2) @ part["matrix"].T + p
        if np.any(vertices.max(axis=0) < lo) or np.any(vertices.min(axis=0) > hi):
            continue
        for face in FACES:
            poly = vertices[list(face)]
            normal = np.cross(poly[1]-poly[0], poly[2]-poly[0])
            norm = np.linalg.norm(normal)
            if norm < 1e-10:
                continue
            normal /= norm
            if normal @ CAMERA <= .001:
                continue
            for axis in range(3):
                poly = clip_polygon(poly, axis, lo[axis], True)
                poly = clip_polygon(poly, axis, hi[axis], False)
                if len(poly) < 3:
                    break
            if len(poly) < 3:
                continue
            # A mild technical-illustration shade, independent of game lighting.
            light = np.array([-.25, 1, -.65]); light /= np.linalg.norm(light)
            shade = .65 + .30*max(0, normal @ light)
            color = np.clip(part["color"]*shade + .035, 0, 1)
            result.append((float(poly.mean(axis=0) @ CAMERA), poly @ PROJECTION,
                           (*color, max(.4, part["alpha"]))))
    result.sort(key=lambda value: value[0])
    return result


def draw_room(ax, parts, bounds, row_title, version):
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    center = np.array([(xmin+xmax)/2, ymin, (zmin+zmax)/2]) @ PROJECTION
    faces = room_faces(parts, bounds)
    # Draw a quiet floor first so sorting never covers low equipment with slab.
    floor = np.array([[xmin,ymin-.02,zmin], [xmax,ymin-.02,zmin],
                      [xmax,ymin-.02,zmax], [xmin,ymin-.02,zmax]]) @ PROJECTION-center
    ax.add_collection(PolyCollection([floor], facecolors=["#c2ccd1"], edgecolors=["#788a95"], linewidths=.6))
    polygons = [face[1]-center for face in faces]
    colors = [face[2] for face in faces]
    ax.add_collection(PolyCollection(polygons, facecolors=colors, edgecolors=(.10,.16,.19,.34), linewidths=.14))
    corners = np.array([[x,y,z] for x in (xmin-.5,xmax+.5) for y in (ymin,ymax) for z in (zmin-.5,zmax+.5)]) @ PROJECTION-center
    low, high = corners.min(axis=0), corners.max(axis=0)
    padding = .8
    ax.set_xlim(low[0]-padding, high[0]+padding)
    ax.set_ylim(low[1]-padding, high[1]+padding)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor("#f2f5f6")
    ax.text(.025,.98,row_title,transform=ax.transAxes,va="top",fontsize=12,
            fontweight="bold",color="#243d49")
    ax.text(.98,.98,version,transform=ax.transAxes,ha="right",va="top",
            fontsize=10,fontweight="bold",color="#207c84" if version.startswith("V7") else "#677983")
    return len(faces)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,default=ROOT/"source/PROJECT_NULL_INTERIORS_V6.rbxlx")
    parser.add_argument("--updated",type=Path,default=ROOT/"artifacts/PROJECT_NULL_INTERIORS_V7_DETAIL.rbxlx")
    parser.add_argument("--output",type=Path,default=ROOT/"artifacts/PROJECT_NULL_V7_COMPARISON.png")
    args = parser.parse_args()
    versions = [read_parts(args.source), read_parts(args.updated)]
    fig, axes = plt.subplots(3,2,figsize=(16,14.5),facecolor="#f2f5f6")
    fig.subplots_adjust(left=.025,right=.975,top=.92,bottom=.075,hspace=.15,wspace=.04)
    fig.text(.045,.966,"PROJECT: NULL",fontsize=25,fontweight="bold",color="#213b49")
    fig.text(.045,.938,"INTERIOR DETAIL STUDY  /  THREE ROOMS",fontsize=11,color="#617985")
    fig.text(.95,.955,"V6  →  V7",ha="right",fontsize=18,fontweight="bold",color="#207c84")
    counts=[]
    for row,(title,bounds) in enumerate(ROOMS):
        for col,parts in enumerate(versions):
            counts.append(draw_room(axes[row,col],parts,bounds,title,"V6 / ORIGINAL" if col==0 else "V7 / STATIC DETAIL"))
    fig.text(.045,.043,"XML GEOMETRY VISUALIZATION — NOT A ROBLOX STUDIO SCREENSHOT",fontsize=10,fontweight="bold",color="#38535e")
    fig.text(.045,.025,"Identical orthographic camera and crop per pair. Roofs and near walls cut away. Lighting, materials, text and gameplay are not simulated.",fontsize=9,color="#617985")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.output,dpi=160,facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Saved {args.output} (visible faces per panel: {counts})")


if __name__ == "__main__":
    main()
