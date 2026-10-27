#!/usr/bin/env python3
"""Render actual V9 geometry and an open-service inspection copy; no engine rendering."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import render_v7 as renderer
from validate_v9_physics import rotation
from v7_common import name

ROOT=Path(__file__).resolve().parents[1]


def open_inspection():
    tree=ET.parse(ROOT/'artifacts/PROJECT_NULL_ENGINEERING_V9.rbxlx')
    indexed={e.get('referent'):e for e in tree.iter('Item')}
    manifest=json.loads((ROOT/'artifacts/V9_MANIFEST.json').read_text())
    for service in manifest['services']:
        axis=service['axis'];angle=service['angle'];pivot=np.array(service['pivot'])
        q=np.eye(3) if axis=='Slide' else rotation(axis,angle)
        for ref in service['moving']:
            frame=indexed[ref].find("Properties/CoordinateFrame[@name='CFrame']")
            p=np.array([float(frame.findtext(k)) for k in 'XYZ'])
            r=np.array([[float(frame.findtext(f'R{i}{j}')) for j in range(3)] for i in range(3)])
            p=p+np.array(service['delta']) if axis=='Slide' else pivot+q@(p-pivot)
            r=q@r
            for key,value in zip('XYZ',p):frame.find(key).text=f'{value:.10g}'
            for i in range(3):
                for j in range(3):frame.find(f'R{i}{j}').text=f'{r[i,j]:.10g}'
        config=next(e for e in indexed[service['panel']].findall('Item') if name(e)=='V9_Service')
        for value in config.findall('Item'):
            if name(value)=='CurrentAngle':value.find("Properties/double[@name='Value']").text=str(angle)
            elif name(value)=='IsOpen':value.find("Properties/bool[@name='Value']").text='true'
    path=ROOT/'artifacts/PROJECT_NULL_V9_OPEN_INSPECTION.rbxlx'
    tree.write(path,encoding='utf-8',xml_declaration=True)
    return path


def camera(vector):
    renderer.CAMERA=np.array(vector,dtype=float)
    renderer.CAMERA/=np.linalg.norm(renderer.CAMERA)
    renderer.RIGHT=np.array([-renderer.CAMERA[2],0,renderer.CAMERA[0]])
    renderer.RIGHT/=np.linalg.norm(renderer.RIGHT)
    renderer.UP=np.cross(renderer.CAMERA,renderer.RIGHT)
    if renderer.UP[1]<0:renderer.UP*=-1
    renderer.PROJECTION=np.stack([renderer.RIGHT,renderer.UP],axis=1)


def sheet(path,panels,header,subtitle):
    fig,axes=renderer.plt.subplots(len(panels),2,figsize=(17,5*len(panels)),facecolor='#f2f5f6')
    fig.subplots_adjust(left=.025,right=.975,top=.935,bottom=.055,hspace=.15,wspace=.04)
    fig.text(.045,.975,'PROJECT: NULL',fontsize=25,fontweight='bold',color='#213b49')
    fig.text(.045,.951,header,fontsize=12,color='#207c84',fontweight='bold')
    counts=[]
    for row,(title,bounds,view,left,right,left_label,right_label) in enumerate(panels):
        camera(view)
        counts.append(renderer.draw_room(axes[row,0],left,bounds,title,left_label,updated=False))
        counts.append(renderer.draw_room(axes[row,1],right,bounds,title,right_label,updated=True))
    fig.text(.045,.027,'XML GEOMETRY STUDY — NOT A ROBLOX STUDIO SCREENSHOT',fontsize=10,fontweight='bold',color='#38535e')
    fig.text(.045,.013,subtitle,fontsize=9,color='#617985')
    fig.savefig(path,dpi=150,facecolor=fig.get_facecolor())
    renderer.plt.close(fig)
    print(path.name,'visible faces:',counts)


def main():
    opened=open_inspection()
    before=renderer.read_parts(ROOT/'artifacts/PROJECT_NULL_EXPERIMENTAL_V8.rbxlx')
    closed=renderer.read_parts(ROOT/'artifacts/PROJECT_NULL_ENGINEERING_V9.rbxlx')
    exposed=renderer.read_parts(opened)
    panels=[]
    for title,bounds,view in [
        ('E-07 / REPLANNED LAB',(-57.5,-30.5,-64.02,-47,-59.5,-36.5),(1,.9,-1)),
        ('P02 / MAINTENANCE ACCESS',(126.5,181.5,-64.02,-42,-35.5,35.5),(1,.8,-1)),
        ('E-03 / IMMERSION',(-23.5,23.5,-64.02,-43,-23.5,23.5),(1,.9,-1)),
        ('THERM / SKID',(10,46,-64.02,-46,53,78),(-1,1,-1)),
    ]:
        panels.append((title,bounds,view,before,closed,'V8 / BEFORE','V9 / REWORK'))
    sheet(ROOT/'artifacts/PROJECT_NULL_V9_OVERVIEW.png',panels,'V8 → V9 / PHYSICAL ENGINEERING REWORK',
          'Same geometry camera per pair. Architectural roofs and near walls cut away. Lighting and physics are not simulated.')
    panels=[]
    for title,bounds,view,assembly in [
        ('CAL / RACK',(-47.2,-40.8,-64.02,-49.6,-46,-37.5),(.45,.65,-1),'LAB_CAL_03_ModularServiceRack'),
        ('P02 / RACK',(128.1,135.9,-64.02,-53.5,-1.5,7),(.45,.65,-1),'EXP_P02_04_InstrumentServiceRack'),
        ('FCU / COIL',(6.5,16.5,-64.02,-53.5,54,61.5),(-1,.8,1),'THERM_016_FanCoil'),
        ('NIF / MODULES',(18,24,-64.02,-53,5,12.5),(.3,.65,-1),'EXP_NIF_FourChannelCabinet'),
    ]:
        left=[p for p in closed if assembly in p['path']]
        right=[p for p in exposed if assembly in p['path']]
        panels.append((title,bounds,view,left,right,'CLOSED','OPEN'))
    sheet(ROOT/'artifacts/PROJECT_NULL_V9_INTERNALS.png',panels,'V9 / REAL MODELED INTERNAL ASSEMBLIES',
          'Both columns use actual place geometry. Service leaves posed with their registered hinges. Labels and game lighting are not rendered.')


if __name__=='__main__':main()
