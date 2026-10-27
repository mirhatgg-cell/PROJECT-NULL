#!/usr/bin/env python3
"""Render actual XML cutaways, a station map and an open-service inspection copy."""
from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import render_v7 as renderer
from matplotlib.collections import PolyCollection
from render_v9 import sheet
from validate_v9_physics import rotation
from v7_common import name

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'artifacts/PROJECT_NULL_GAMEPLAY_V10.rbxlx'


def inspection_copy():
    tree = ET.parse(MAP)
    indexed = {e.get('referent'): e for e in tree.iter('Item')}
    services = []
    for version in (9, 10):
        manifest = json.loads((ROOT / f'artifacts/V{version}_MANIFEST.json').read_text())
        services.extend(manifest['services'])
    for service in services:
        pivot = np.asarray(service['pivot'])
        matrix = np.eye(3) if service['axis'] == 'Slide' else rotation(service['axis'], service['angle'])
        for ref in service['moving']:
            frame = indexed[ref].find("Properties/CoordinateFrame[@name='CFrame']")
            point = np.array([float(frame.findtext(k)) for k in 'XYZ'])
            orientation = np.array([[float(frame.findtext(f'R{i}{j}')) for j in range(3)] for i in range(3)])
            point = (point + np.array(service['delta']) if service['axis'] == 'Slide'
                     else pivot + matrix @ (point - pivot))
            orientation = matrix @ orientation
            for key, value in zip('XYZ', point):
                frame.find(key).text = f'{value:.10g}'
            for i in range(3):
                for j in range(3):
                    frame.find(f'R{i}{j}').text = f'{orientation[i, j]:.10g}'
        config = next(e for e in indexed[service['panel']].findall('Item') if name(e) == 'V9_Service')
        for item in config.findall('Item'):
            if name(item) == 'CurrentAngle':
                item.find("Properties/double[@name='Value']").text = str(service['angle'])
            elif name(item) == 'IsOpen':
                item.find("Properties/bool[@name='Value']").text = 'true'
    destination = ROOT / 'artifacts/PROJECT_NULL_V10_OPEN_INSPECTION.rbxlx'
    tree.write(destination, encoding='utf-8', xml_declaration=True)
    print('Open service accesses:', len(services))
    return destination


def station_map(parts, manifest):
    fig, ax = renderer.plt.subplots(figsize=(17, 11), facecolor='#f2f5f6')
    fig.subplots_adjust(left=.055, right=.95, bottom=.10, top=.86)
    fig.text(.055, .95, 'PROJECT: NULL / V10', fontsize=25, fontweight='bold', color='#213b49')
    fig.text(.055, .915, 'PHYSICAL STATIONS AND EVIDENCE / ACTUAL XML PLAN', fontsize=12, color='#207c84')
    polygons, colors = [], []
    for part in parts:
        n = part['name'].lower()
        if (part['xyz'][1] + part['size'][1]/2 < -63.85
                or part['xyz'][1] - part['size'][1]/2 > -58
                or max(part['size']) < .2):
            continue
        if 'ceiling' in n or 'slab' in n:
            continue
        vertices = (renderer.CORNERS * part['size'] / 2) @ part['matrix'].T + part['xyz']
        projected = vertices[:, [0, 2]]
        # Convex hull for the projected cuboid, using a small monotonic chain.
        points = sorted(set(map(tuple, projected)))
        if len(points) < 3:
            continue
        def cross(a, b, c):
            return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        lower, upper = [], []
        for point in points:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
                lower.pop()
            lower.append(point)
        for point in reversed(points):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
                upper.pop()
            upper.append(point)
        polygons.append(lower[:-1] + upper[:-1])
        new = 'Narrative_Gameplay_V10' in part['path']
        colors.append('#91b8b5' if new else '#c9d2d7')
    ax.add_collection(PolyCollection(polygons, facecolors=colors, edgecolors='#758c97', linewidths=.20))
    styles = {
        'console': ('#126d78', 's'), 'document': ('#a3772f', '.'),
        'response': ('#75469a', '^'), 'npc': ('#405e8f', 'o'),
        'cooling': ('#217f64', 'D'), 'medical': ('#b35e57', 'P'),
        'repair': ('#765d3d', 'D'), 'supply': ('#765d3d', 'D'),
        'records': ('#405e8f', 's'),
    }
    offsets = {'P01': (12, -18), 'P02': (10, -18), 'P03': (-42, -18),
               'P04': (-44, 14), 'P05': (12, -18)}
    for entry in manifest['world']['interactions']:
        x, _, z = entry['position']
        action, argument = entry['action'], entry['argument']
        color, marker = styles.get(action, ('#596d76', 'o'))
        ax.scatter(x, z, s=90 if action == 'console' else (42 if action != 'document' else 22),
                   color=color, marker=marker, edgecolors='white', linewidths=.5, zorder=5)
        if action == 'console':
            ax.annotate(argument, (x, z), xytext=offsets.get(argument, (8, 8)),
                        textcoords='offset points', fontsize=11, fontweight='bold', color=color,
                        bbox={'boxstyle': 'round,pad=.25', 'facecolor': '#f2f5f6', 'edgecolor': color},
                        arrowprops={'arrowstyle': '-', 'color': color}, zorder=6)
        elif action in ('cooling', 'repair', 'medical', 'supply', 'records'):
            offset = {'supply': (-38, 10), 'repair': (12, -14)}.get(action, (5, 5))
            ax.annotate(action.upper(), (x, z), xytext=offset, textcoords='offset points',
                        fontsize=8, color=color, zorder=6)
    ax.set_xlim(-83, 224)
    ax.set_ylim(95, -94)
    ax.set_aspect('equal')
    ax.set_xlabel('X / STUDS', fontsize=9, color='#617985')
    ax.set_ylabel('Z / STUDS', fontsize=9, color='#617985')
    ax.set_facecolor('#eef2f3')
    ax.grid(alpha=.12)
    for action, (color, marker) in styles.items():
        ax.scatter([], [], color=color, marker=marker, label=action.upper())
    ax.legend(loc='lower left', bbox_to_anchor=(0, -.19), ncol=5, frameon=False, fontsize=9)
    fig.text(.055, .042, 'XML GEOMETRY PLAN — NOT A ROBLOX STUDIO SCREENSHOT', fontsize=10, color='#38535e', fontweight='bold')
    fig.text(.055, .023, 'Doors, equipment and station locations are taken from the place file. This is not a navigation mesh or an engine playtest.', fontsize=9, color='#617985')
    destination = ROOT / 'artifacts/PROJECT_NULL_V10_STATIONS.png'
    fig.savefig(destination, dpi=150, facecolor=fig.get_facecolor())
    renderer.plt.close(fig)
    print(destination.name)


def main():
    opened = inspection_copy()
    before = renderer.read_parts(ROOT / 'artifacts/PROJECT_NULL_ENGINEERING_V9.rbxlx')
    after = renderer.read_parts(MAP)
    panels = []
    for title, bounds, view in [
        ('E-01 / SHIFT & ARCHIVE', (-15.5,15.5,-64.02,-49,-75.5,-48.5), (1,.9,-1)),
        ('E-04 / RECORDS & P01', (-63.5,-24.5,-64.02,-49,-11.5,11.5), (1,.9,-1)),
        ('E-08 / SUPPLY & REPAIR', (46.5,77.5,-64.02,-49,51.5,78.5), (1,.9,-1)),
        ('E-13 / TWO SENSOR GENERATIONS', (134.5,173.5,-64.02,-49,56.5,87.5), (1,.9,-1)),
    ]:
        panels.append((title,bounds,view,before,after,'V9','V10'))
    sheet(ROOT / 'artifacts/PROJECT_NULL_V10_OVERVIEW.png', panels,
          'V9 → V10 / STAGES 4 + 5',
          'Actual geometry with identical cameras. New cases have modeled contents; text, materials, gameplay and lighting are not rendered.')
    manifest = json.loads((ROOT / 'artifacts/V10_MANIFEST.json').read_text())
    station_map(after, manifest)
    exposed = renderer.read_parts(opened)
    panels = []
    for title, bounds, view, assembly in [
        ('ARCHIVE', (-16,-10,-64.02,-54,-57.5,-51), (.3,.6,-1), 'ArchiveOfWithdrawnForms'),
        ('SUPPLY / FILTER STOCK', (57.5,62.5,-61.1,-56.5,71.8,77.2), (.45,.65,-1), 'FilterStockCabinet'),
        ('P04 / OPTICAL UNIT', (-15.6,-12.4,-54.7,-52.4,59,64.8), (1,.5,-1), 'P04_OpticalObserver'),
        ('P05 / REFERENCE', (-23,-18.5,-61,-56.2,-11.5,-6.5), (.45,.65,-1), 'IndependentReferenceMeter'),
    ]:
        left = [p for p in after if assembly in p['path']]
        right = [p for p in exposed if assembly in p['path']]
        panels.append((title,bounds,view,left,right,'CLOSED','OPEN'))
    sheet(ROOT / 'artifacts/PROJECT_NULL_V10_CONTENTS.png', panels,
          'V10 / CONTENTS, SERVICE ACCESS AND PHYSICAL SIGNALS',
          'Actual authored contents, with all registered service leaves posed open. No engine lighting, text or materials are simulated.')


if __name__ == '__main__':
    main()
