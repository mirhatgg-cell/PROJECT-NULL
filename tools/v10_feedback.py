"""Physical, server-driven trial signals for the V10 narrative/gameplay pass.

The P04 optical unit has a real front aperture and a separately animated blade.
Its maintenance door is an ordinary V9 service panel. P01 lamps are mounted to
their serviceable driver case; P05 reuses the independently powered meter.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from v7_common import name, WHITE, METAL, DARK, BLACK, LIGHT, CYAN, TEAL, AMBER
from v9_common import setprop


def build(b, parent, root):
    addition = b.model(parent, 'Physical_Protocol_Feedback_V10')
    b.note(addition, 'Purpose', 'Actual light channels, independent reference readout and optical shutter reflect the server-owned protocol state. No client supplied answer controls these objects.')

    def part(model, label, position, size, color=METAL, role='detail', **kwargs):
        return b.part(model, label, position, size, color, material=kwargs.pop('material', 1088), role=role, **kwargs)

    def movers(door, parts):
        config = next(e for e in door.findall('Item') if name(e) == 'V9_Service')
        service = next(s for s in b.services if s['panel'] == door.get('referent'))
        for target in parts:
            service['moving'].append(target.get('referent'))
            reference = b.item(config, 'ObjectValue', 'Moving_' + str(len(service['moving'])))
            b.prop(reference, 'Ref', 'Value', target.get('referent'))

    # E16 west wall. The optical axis is +X, aimed into the room. The aperture
    # consists of four strips; there is no full front box across the lens train.
    observer = b.model(addition, 'P04_OpticalObserver')
    x, y, z = -14.15, -53.7, 61.7
    sx, sy, sz, t = 1.7, 1.6, 2.0, .08
    b.cavity(observer, (x,y,z), (sx,sy,sz), t, 'Z-')
    part(observer, 'OpticalRearWall', (x-sx/2+t/2,y,z), (t,sy,sz), DARK, 'housing')
    for side in (-1,1):
        part(observer, 'OpticalHorizontalShell', (x,y+side*(sy/2-t/2),z), (sx-2*t,t,sz-2*t), WHITE, 'housing')
    part(observer, 'OpticalNorthWall', (x,y,z+sz/2-t/2), (sx-2*t,sy,t), WHITE, 'housing')
    door = part(observer, 'ObserverServiceDoor', (x,y,z-sz/2+t/2), (sx-2*t,sy,t), WHITE, 'panel')
    handle = part(observer, 'ObserverServiceHandle', (x+.47,y,z-sz/2-.035), (.14,.48,.12), DARK)
    b.service(door, (x-sx/2+t,y,z-sz/2+t/2), angle=100,
              label='P-04: оптика и электроника наблюдателя', moving=[handle])
    setprop(b.find('V9_ServicePrompt', under=door), 'token', 'KeyboardKeyCode', 102)
    front = x+sx/2-t/2
    for side in (-1,1):
        part(observer, 'OpticalApertureHorizontalBorder', (front,y+side*.59,z), (t,.42,sz-2*t), DARK, 'housing')
        part(observer, 'OpticalApertureVerticalBorder', (front,y,z+side*.65), (t,.76,.54), DARK, 'housing')
    for zz in (z-.72,z+.72):
        part(observer, 'OpticalBoardSpacer', (x-.57,y-.25,zz), (.16,.1,.1), METAL, 'internal')
    part(observer, 'ObserverSensorBoard', (x-.53,y,z), (.065,1.14,1.56), TEAL, 'internal')
    part(observer, 'ObserverCMOSDetector', (x-.45,y,z), (.105,.32,.32), BLACK, 'internal')
    part(observer, 'ObserverSignalProcessor', (x-.46,y-.39,z+.45), (.12,.28,.35), BLACK, 'internal')
    part(observer, 'ObserverDriveController', (x-.46,y+.37,z-.45), (.12,.23,.31), BLACK, 'internal')
    for xx in (x-.12,x+.37,x+.69):
        b.segment(observer, 'OpticalLensRetainer', (xx-.045,y,z), (xx+.045,y,z), .62, DARK, role='internal')
        b.segment(observer, 'OpticalGlassElement', (xx+.046,y,z), (xx+.065,y,z), .45, CYAN, role='internal')
        part(observer, 'LensRailCradle', (xx,y-.38,z), (.14,.15,.77), METAL, 'internal')
    for zz in (z-.38,z+.38):
        b.segment(observer, 'LensSupportRail', (x-.37,y-.43,zz), (x+.69,y-.43,zz), .075, METAL, role='internal')
    b.segment(observer, 'SensorSignalLoom', (x-.43,y-.42,z-.55), (x-.14,y-.42,z-.55), .065, CYAN, role='internal')

    # Blade baked CLOSED across the aperture. +Z1.3 moves it clear, exposing the
    # optics for tracking/adapting. Occluded/idle keeps this baked closed frame.
    shutter = part(observer, 'V10_ObserverShutter', (-13.15,y,z), (.065,.82,.82), DARK, 'internal')
    offset = b.item(shutter, 'Vector3Value', 'OpenOffset')
    vector = b.prop(offset, 'Vector3', 'Value')
    for key, value in zip('XYZ', (0,0,1.3)):
        ET.SubElement(vector, key).text = str(value)
    for yy in (y-.49,y+.49):
        part(observer, 'ShutterSlideGuide', (-13.15,yy,z+.76), (.14,.1,2.44), METAL, 'housing')
    part(observer, 'ShutterDriveBearing', (-13.24,y,z+1.9), (.25,.98,.18), DARK, 'housing')
    b.segment(observer, 'ShutterLeadScrew', (-13.21,y+.45,z-.38), (-13.21,y+.45,z+1.8), .07, DARK, role='internal')
    part(observer, 'ShutterDriveMotor', (-13.49,y+.35,z+.82), (.34,.32,.34), DARK, 'internal')
    for zz in (z-.65,z+.65):
        part(observer, 'ObserverWallMount', (-15.22,y,zz), (.56,.28,.34), METAL, 'structure')
    part(observer, 'ObserverWallMountPlate', (-15.46,y,z), (.08,1.35,1.8), DARK, 'structure')
    b.segment(observer, 'ObserverPowerCable', (-14.68,y+.55,z+.65), (-15.35,y+.55,z+.65), .08, DARK)
    b.segment(observer, 'ObserverWallCable', (-15.35,y+.55,z+.65), (-15.35,-50.4,z+.65), .08, DARK)
    for yy in (-52.7,-51.7,-50.7):
        part(observer, 'ObserverCableClip', (-15.39,yy,z+.65), (.14,.12,.22), METAL)
    plate = part(observer, 'ObserverWarningPlate', (-13.292,y-.64,z), (.025,.2,1.5), DARK)
    b.label(plate, 'P-04 / ОПТИЧЕСКИЙ КАНАЛ', LIGHT, face=0)

    # E04 north wall: clear the top of the official incident notice. Bulbs and
    # labels move with the driver-case door so service access stays coherent.
    cx,cy,cz = -59,-53.7,10.8
    driver, door, faces = b.shell(addition, 'P01_SignalDriver', (cx,cy,cz),
                                 (3.8,1.25,.7), METAL,.075,'Z-',True,100)
    setprop(b.find('V9_ServicePrompt', under=door), 'token', 'KeyboardKeyCode', 102)
    part(driver, 'LampDriverPCB', (cx,cy,cz+.19), (3.3,.87,.06), TEAL, 'internal')
    for index in range(3):
        bx=cx-1.2+index*1.2
        part(driver, 'LampDriverSwitch', (bx,cy,cz+.11), (.37,.3,.09), BLACK, 'internal')
        part(driver, 'LampCurrentResistor', (bx+.31,cy-.22,cz+.11), (.13,.25,.09), AMBER, 'internal')
    attached=[]
    lamps={}
    for channel,dx in zip(('A','B','C'),(-1.2,0,1.2)):
        bx=cx+dx
        base=b.segment(driver,'LampSocket_'+channel,(bx,cy+.13,10.49),(bx,cy+.13,10.32),.49,DARK,role='detail')
        lamp=b.segment(driver,'V10_P01_Light_'+channel,(bx,cy+.13,10.31),(bx,cy+.13,10.22),.37,CYAN,role='detail')
        setprop(lamp,'token','Material',288)
        light=b.item(lamp,'PointLight','ChannelLight')
        b.prop(light,'float','Brightness',0)
        b.prop(light,'float','Range',5)
        b.prop(light,'bool','Enabled',False)
        colour=b.prop(light,'Color3','Color')
        for key,value in zip('RGB',CYAN):ET.SubElement(colour,key).text=str(value/255)
        label=part(driver,'ChannelLabel_'+channel,(bx,cy-.35,10.39),(.67,.23,.04),DARK)
        b.label(label,channel,LIGHT)
        attached.extend((base,lamp,label))
        lamps[channel]=lamp.get('referent')
    movers(door,attached)
    for xx in (cx-1.5,cx+1.5):
        part(driver,'DriverWallStandOff',(xx,cy,11.28),(.24,.35,.31),METAL,'structure')
    b.segment(driver,'LampDriverWallCable',(cx-1.67,cy+.5,11.23),(cx-1.67,-51.2,11.23),.075,DARK)

    # The narrative pass already creates this independent battery instrument.
    # Reuse its real service door as a readable display instead of placing a
    # second simulated "independent" meter on the operator's computer.
    meter=b.find('IndependentReferenceMeter',under=root,cls='Model')
    assert meter is not None, 'Build v10_world before v10_feedback'
    meter_door=b.find('V9_ServiceDoor',under=meter,cls='Part')
    assert meter_door is not None
    labels=[e for e in meter_door.iter('Item') if e.get('class')=='TextLabel']
    assert len(labels)==1, 'Expected one existing physical reference label'
    reference=labels[0]
    setprop(reference,'string','Name','V10_P05_Reference')
    setprop(reference,'string','Text','НЕЗАВИСИМЫЙ ЭТАЛОН\nP-05 / ОЖИДАНИЕ\nПИТАНИЕ ОТДЕЛЕНО')
    b.note(meter,'LiveReadout','V10_P05_Reference is updated from the independent physical cue channel, including its reference-quality flag. The meter has its own modeled battery, oscillator and board.')

    return {
        'groups':{name(e):sum(p.get('class')=='Part' for p in e.iter('Item')) for e in addition.findall('Item') if e.get('class')=='Model'},
        'observer':{'model':observer.get('referent'),'shutter':shutter.get('referent'),
                    'closed_position':(-13.15,y,z),'open_offset':(0,0,1.3),
                    'open_modes':['tracking','adapting'],'closed_modes':['occluded','idle']},
        'p01_lamps':lamps,'p05_reference':reference.get('referent'),
    }
