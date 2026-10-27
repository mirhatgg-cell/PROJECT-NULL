#!/usr/bin/env python3
"""Static comparison of Stage 3 geometry. Not a Roblox Studio rendering."""
from pathlib import Path

from render_v7 import read_parts, draw_room, plt

ROOT=Path(__file__).resolve().parents[1]
ROOMS=[
    ('E-07 / METROLOGY',(-57.5,-30.5,-64.02,-49,-59.5,-36.5)),
    ('E-10 / PHYSICAL TEST',(126.5,181.5,-64.02,-43,-35.5,35.5)),
    ('E-16 / SERVERS',(-15.5,15.5,-64.02,-43,51.5,74.5)),
]


def main():
    versions=[read_parts(ROOT/'artifacts/PROJECT_NULL_INTERIORS_V7_DETAIL.rbxlx'),
              read_parts(ROOT/'artifacts/PROJECT_NULL_EXPERIMENTAL_V8.rbxlx')]
    fig,axes=plt.subplots(3,2,figsize=(16,15),facecolor='#f2f5f6')
    fig.subplots_adjust(left=.025,right=.975,top=.92,bottom=.075,hspace=.15,wspace=.04)
    fig.text(.045,.966,'PROJECT: NULL',fontsize=25,fontweight='bold',color='#213b49')
    fig.text(.045,.938,'STAGE 3 / SPECIALIZED EXPERIMENTAL EQUIPMENT',fontsize=11,color='#617985')
    fig.text(.95,.955,'V7  →  V8',ha='right',fontsize=18,fontweight='bold',color='#207c84')
    counts=[]
    for row,(title,bounds) in enumerate(ROOMS):
        for col,parts in enumerate(versions):
            counts.append(draw_room(axes[row,col],parts,bounds,title,'V7 / BEFORE' if col==0 else 'V8 / STAGE 3',updated=col==1))
    fig.text(.045,.043,'XML GEOMETRY VISUALIZATION — NOT A ROBLOX STUDIO SCREENSHOT',fontsize=10,fontweight='bold',color='#38535e')
    fig.text(.045,.025,'Identical camera per pair. Roofs and near walls cut away. Lighting, materials, text and gameplay are not simulated.',fontsize=9,color='#617985')
    out=ROOT/'artifacts/PROJECT_NULL_V8_COMPARISON.png'
    fig.savefig(out,dpi=160,facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'Saved {out}; visible faces per panel: {counts}')


if __name__=='__main__': main()
