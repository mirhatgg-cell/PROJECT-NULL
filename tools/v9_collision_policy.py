"""Explicit collision audit for the 678 V7/V8 additions; never edits the input.

Primary objects become collidable/queryable; small trim, markings and cables
stay decorative. REBUILD_NAMES identifies filled blocks needing real cavities,
not a transparency change or an invisible full-volume collision proxy.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from v7_common import name


PRIMARY_NAMES = frozenset('''
BoltedBasePlate IsolationPad GantryUpright RearDiagonalBrace PostClamp
GantryCrossMember BeamEndCover FixedSensorCarriage SensorBoom BoomHingeAxle
SensorDropLink SensorBridge UpperSensorHousing HeadrestSensorPad InterfaceEnclosure
EnclosureFront PedestalBase PedestalStem StopBackingBox AcousticFrame FabricInsert
CeilingServiceRail Splashback BasinBottom BasinBack BasinFront BasinNorth BasinSouth
SoapDispenser PaperTowelCabinet ClosedBinBody BinFloorFoot SeparateClosedLid
Upright CasterFork CasterWheel RolledShelf SealedSupplyBox SupplyBoxLid
ClosedInstrumentTray InstrumentTrayLid LaboratoryCountertop FloorLevelingFoot
BenchUpright LongitudinalFrame LowerFrameRail CrossFrame LowerShelf RailMount
LinearGuide ScrewBearingBlock GuideCarriage HeadSupportStem InstrumentHeadHousing
InstrumentEnclosure EnclosureTopCover ReferenceBasePlate IsolationFoot
IsolatedLowerFrame ReferenceUpright CrossSupport InstrumentBackbone ReferenceLoop_1
ReferenceLoop_2 ReferenceJunctionBody ReferenceJunctionFace TrackingWallPlate
TrackingBracket TrackingBracketBrace TrackingYoke TrackingHeadHousing LadderSideRail
LadderCrossRung CeilingAnchorPlate TraySupportChannel DataWallSleeve
IsolatedFloorPlinth FanCoilCasing ServiceFaceFrame ServiceFaceInsert
'''.split())

REBUILD_NAMES = frozenset('''
UpperSensorHousing InterfaceEnclosure StopBackingBox SoapDispenser
PaperTowelCabinet ClosedBinBody SealedSupplyBox ClosedInstrumentTray
InstrumentHeadHousing InstrumentEnclosure ReferenceJunctionBody
TrackingHeadHousing FanCoilCasing
'''.split())

# These thin visible closures need to belong to the service panel's moving
# assembly when a filled body is replaced; they are not independent interiors.
SERVICE_FACE_NAMES = frozenset('''
EnclosureFront SeparateClosedLid SupplyBoxLid InstrumentTrayLid
EnclosureTopCover ReferenceJunctionFace ServiceFaceInsert ServiceFaceFrame
'''.split())


def classify(part):
    label = name(part)
    if label in REBUILD_NAMES:
        return 'replace_with_hollow_assembly'
    return 'primary_solid' if label in PRIMARY_NAMES else 'small_detail'


def should_collide(part):
    return name(part) in PRIMARY_NAMES


def audit(path):
    tree = ET.parse(path)
    rows=[]

    def visit(item, ancestors=()):
        trail=ancestors+(name(item),)
        label=name(item)
        if item.get('class')=='Part' and any(root in ancestors for root in ('Visual_Detail_V7','Experimental_Equipment_V8')):
            category=classify(item)
            rows.append({
                'referent':item.get('referent'), 'path':'/'.join(trail), 'name':label,
                'category':category, 'proposed_can_collide':should_collide(item),
                'proposed_can_query':should_collide(item),
                'currently_collidable':item.findtext("Properties/bool[@name='CanCollide']",'true')=='true',
                'current_transparency':float(item.findtext("Properties/float[@name='Transparency']",'0')),
                'move_with_service_panel':label in SERVICE_FACE_NAMES,
            })
        for child in item.findall('Item'): visit(child,trail)

    for item in tree.getroot().findall('Item'):visit(item)
    assert len(rows)==678, f'Expected audited V7+V8 additions, found {len(rows)}'
    primary=[row for row in rows if row['proposed_can_collide']]
    return {
        'source':str(path), 'validation':'Policy proposal only; no runtime physics test and no input mutation',
        'added_parts_audited':len(rows),
        'currently_collidable':sum(row['currently_collidable'] for row in rows),
        'currently_visually_transparent':sum(row['current_transparency']>0 for row in rows),
        'proposed_primary_collision_parts':len(primary),
        'proposed_small_details_without_collision':len(rows)-len(primary),
        'filled_parts_requiring_hollow_rebuild':sum(row['category']=='replace_with_hollow_assembly' for row in rows),
        'categories':dict(Counter(row['category'] for row in rows)),
        'rows':rows,
    }


def main():
    root=Path(__file__).resolve().parents[1]
    result=audit(root/'artifacts/PROJECT_NULL_EXPERIMENTAL_V8.rbxlx')
    output=Path('/workspace/scratch/v9_collision_policy.json')
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key!='rows'},indent=2))
    print('Full per-referent proposal:',output)


if __name__=='__main__':main()
