#!/usr/bin/env python3
"""Technical illustrations from the actual V11 XML, not Roblox screenshots."""
from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import render_v7 as renderer
from matplotlib.collections import PolyCollection
from render_v9 import camera
from validate_v9_physics import rotation
from v7_common import name

ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'artifacts/PROJECT_NULL_OCEAN_V11.rbxlx'


def open_inspection():
    tree=ET.parse(MAP)
    indexed={e.get('referent'):e for e in tree.iter('Item')}
    services=[]
    for version in (9,10,11):
        services.extend(json.loads((ROOT/f'artifacts/V{version}_MANIFEST.json').read_text())['services'])
    for service in services:
        pivot=np.asarray(service['pivot'])
        transform=np.eye(3) if service['axis']=='Slide' else rotation(service['axis'],service['angle'])
        for ref in service['moving']:
            frame=indexed[ref].find("Properties/CoordinateFrame[@name='CFrame']")
            point=np.array([float(frame.findtext(k)) for k in 'XYZ'])
            matrix=np.array([[float(frame.findtext(f'R{i}{j}')) for j in range(3)] for i in range(3)])
            point=point+np.asarray(service['delta']) if service['axis']=='Slide' else pivot+transform@(point-pivot)
            matrix=transform@matrix
            for k,v in zip('XYZ',point):frame.find(k).text=f'{v:.10g}'
            for i in range(3):
                for j in range(3):frame.find(f'R{i}{j}').text=f'{matrix[i,j]:.10g}'
        config=next(e for e in indexed[service['panel']].findall('Item') if name(e)=='V9_Service')
        for item in config.findall('Item'):
            if name(item)=='CurrentAngle':item.find("Properties/double[@name='Value']").text=str(service['angle'])
            if name(item)=='IsOpen':item.find("Properties/bool[@name='Value']").text='true'
    output=ROOT/'artifacts/PROJECT_NULL_V11_OPEN_INSPECTION.rbxlx'
    tree.write(output,encoding='utf-8',xml_declaration=True)
    print('Opened registered service assemblies:',len(services),flush=True)
    return output


def header(fig,title,subtitle):
    fig.text(.04,.96,'PROJECT: NULL / V11',fontsize=25,fontweight='bold',color='#213b49')
    fig.text(.04,.925,title,fontsize=12,fontweight='bold',color='#207c84')
    fig.text(.04,.038,'ACTUAL XML GEOMETRY — NOT A ROBLOX STUDIO SCREENSHOT',fontsize=10,fontweight='bold',color='#38535e')
    fig.text(.04,.018,subtitle,fontsize=9,color='#617985')


def exterior(parts,manifest):
    camera((1,.68,-1))
    bounds=(-195,350,-89,38,-176,154)
    # Seabed is intentionally omitted so vessel scale remains readable.
    shown=[]
    for p in parts:
        if 'Distant_Seafloor_Background' in p['path']:continue
        if p['name'] in ('CrewDeckRoof','StairTowerRoof'):
            # Subdivide these exact surfaces only for painter depth ordering;
            # their union equals the authored slab, with no new scene parts.
            nx=max(1,int(np.ceil(p['size'][0]/18)))
            nz=max(1,int(np.ceil(p['size'][2]/18)))
            for i in range(nx):
                for j in range(nz):
                    offset=np.array([(i+.5)*p['size'][0]/nx-p['size'][0]/2,0,
                                     (j+.5)*p['size'][2]/nz-p['size'][2]/2])
                    shown.append({**p,'xyz':p['xyz']+p['matrix']@offset,
                                  'size':np.array([p['size'][0]/nx,p['size'][1],p['size'][2]/nz])})
        else:shown.append(p)
    faces=renderer.room_faces(shown,bounds)
    sea=np.array([[-215,-38,-205],[370,-38,-205],[370,-38,190],[-215,-38,190]])
    faces.append((float(sea.mean(axis=0)@renderer.CAMERA),sea@renderer.PROJECTION,(.18,.35,.43,.3)))
    faces.sort(key=lambda entry:entry[0])
    fig,ax=renderer.plt.subplots(figsize=(18,11),facecolor='#f2f5f6')
    fig.subplots_adjust(left=.025,right=.975,top=.88,bottom=.08)
    ax.add_collection(PolyCollection([f[1] for f in faces],facecolors=[f[2] for f in faces],
                                    edgecolors=(.10,.16,.19,.28),linewidths=.15))
    xy=np.concatenate([f[1] for f in faces])
    lo,hi=xy.min(axis=0),xy.max(axis=0)
    ax.set_xlim(lo[0]-8,hi[0]+8);ax.set_ylim(lo[1]-8,hi[1]+8)
    ax.set_aspect('equal');ax.axis('off')
    header(fig,'OCEAN VESSEL / PRESERVED LABORATORIES BELOW THE CREW DECK',
           'Blue plane marks the configured waterline. Native Terrain waves and clouds are initialized in Play; materials and lighting are not simulated here.')
    fig.savefig(ROOT/'artifacts/PROJECT_NULL_V11_EXTERIOR.png',dpi=150,facecolor=fig.get_facecolor())
    renderer.plt.close(fig)


def interiors(parts,manifest):
    fig,axes=renderer.plt.subplots(2,2,figsize=(18,14),facecolor='#f2f5f6')
    fig.subplots_adjust(left=.025,right=.975,top=.88,bottom=.075,hspace=.10,wspace=.04)
    panels=[
        ('CREW / MESS / HYGIENE',(-83,81,-28.1,-9,-62,-7),(1,.85,-1)),
        ('POWER / WATER / DUTY OFFICE',(-83,93,-28.1,-9,7,62),(1,.85,-1)),
        ('SAFETY / COMMS / OBSERVATION',(87,208,-28.1,-9,-62,62),(1,.85,-1)),
        ('ACTUAL THREE-FLIGHT STAIR',(-150,-91,-64.1,-25,-29,29),(1,.8,-1)),
    ]
    # Clip roofs rather than drawing through them. Solid walls and furniture
    # remain actual geometry; front boundary walls are removed for the cutaway.
    shown=[]
    rooms=manifest['interiors']['rooms']
    for p in parts:
        n=p['name']
        if any(word in n.lower() for word in ('roof','ceiling')):continue
        if n=='StairTowerEastPier' or (n=='StairTowerSideWall' and p['xyz'][2]<0):continue
        room=next((r for r in rooms if any(segment.startswith(r['id']+'_') for segment in p['path'])),None)
        if room:
            if n=='RoomSideWall' and abs(p['xyz'][0]-room['bounds'][1])<.1:continue
            if n.startswith('Rear') and p['xyz'][2]<0:continue
        shown.append(p)
    for ax,(title,bounds,view) in zip(axes.flat,panels):
        camera(view)
        renderer.draw_room(ax,shown,bounds,title,'V11',True)
    header(fig,'CONNECTED ROOMS / PHYSICAL ROUTES / SERVICEABLE EQUIPMENT',
           'Cutaways use authored geometry. Roofs and near walls removed; text, character physics, game lighting and animated poses are not rendered.')
    fig.savefig(ROOT/'artifacts/PROJECT_NULL_V11_INTERIORS.png',dpi=150,facecolor=fig.get_facecolor())
    renderer.plt.close(fig)


def crew(parts,manifest):
    fig,axes=renderer.plt.subplots(2,3,figsize=(16,13),facecolor='#f2f5f6')
    fig.subplots_adjust(left=.035,right=.965,top=.88,bottom=.085,hspace=.12,wspace=.05)
    for ax,rig in zip(axes.flat,manifest['npcs']['rigs']):
        home=np.asarray(rig['home'])
        shown=[]
        for p in parts:
            if 'Staff_'+rig['id'] in p['path']:
                shown.append({**p,'xyz':p['xyz']-home})
        camera((.55,.4,-1))
        renderer.draw_room(ax,shown,(-2.5,2.5,-.05,6.5,-2,2),rig['id'],'R6',True)
    header(fig,'SIX LOCAL STAFF RIGS / RETAINED IDENTITIES AND DISTINCT WARDROBE',
           'Oriented Part bounds show the local wardrobe. Six Motor6D joints and Animator per rig; rendering and motion must be checked in Studio.')
    fig.savefig(ROOT/'artifacts/PROJECT_NULL_V11_CREW.png',dpi=150,facecolor=fig.get_facecolor())
    renderer.plt.close(fig)


def main():
    open_inspection()
    parts=renderer.read_parts(MAP)
    manifest=json.loads((ROOT/'artifacts/V11_MANIFEST.json').read_text())
    for label,fn in [('exterior',lambda:exterior(parts,manifest)),('interiors',lambda:interiors(parts,manifest)),('crew',lambda:crew(parts,manifest))]:
        fn();print('Rendered',label,flush=True)


if __name__=='__main__':main()
