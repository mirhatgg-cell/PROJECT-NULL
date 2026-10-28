"""Sectional ocean research vessel enclosing the preserved B2 laboratories.

This is static marine architecture. Terrain water is filled once by the shared
environment runtime from the conservative boxes returned here, never through
the inhabited hull. Positions describe this scene, not an asserted canon depth.
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

from v7_common import name, WHITE, METAL, DARK, BLACK, LIGHT, CYAN, BLUE, AMBER, RED, TEAL
from v9_common import setprop

HULL = (56, 72, 80)
LOWER = (34, 48, 54)
DECK = (113, 128, 133)
REPAIR = (83, 108, 115)
SALT = (133, 145, 142)


def build(b, parent, root):
    initial_parts = len(b.parts)
    initial_services = len(b.services)
    model = b.model(parent, 'Ocean_Vessel_V11')
    b.note(model, 'DesignBasis', 'Marine research vessel around the existing B2 laboratory slab. Deck/waterline coordinates are scene construction values, not a canonical ocean depth. No simulated propulsion or arbitrary external assets.')
    circuits = b.find('Circuits', under=root, cls='Folder')
    computers = b.find('Computers', under=circuits, cls='BoolValue') if circuits is not None else None
    lights = []
    routes = []

    def group(label):
        return b.model(model, label)

    def part(p, label, center, size, color=HULL, role='detail', **kw):
        return b.part(p, label, center, size, color, material=kw.pop('material', 1088), role=role, **kw)

    def wall(p, label, a, c, low, high, thickness=.8, color=HULL, role='housing'):
        dx, dz = c[0]-a[0], c[1]-a[1]
        length = math.hypot(dx, dz)
        return part(p, label, ((a[0]+c[0])/2, (low+high)/2, (a[1]+c[1])/2),
                    (length, high-low, thickness), color, role,
                    yaw=-math.degrees(math.atan2(dz, dx)))

    def rail(p, label, a, c, top=-24.5, floor=-28):
        length = math.hypot(c[0]-a[0], c[1]-a[1])
        count = max(1, math.ceil(length/11))
        for index in range(count+1):
            t=index/count
            x,z=a[0]+(c[0]-a[0])*t,a[1]+(c[1]-a[1])*t
            part(p, label+'_Post', (x,(floor+top)/2,z), (.18,top-floor,.18), METAL, 'structure')
        for height in (top, (top+floor)/2):
            b.segment(p, label+'_Rail', (a[0],height,a[1]), (c[0],height,c[1]), .16, METAL, role='structure')
        wall(p,label+'_ToePlate',a,c,floor,floor+.16,.17,DARK,'structure')

    def lamp(p,label,center,color=LIGHT,brightness=.8,range_=16):
        body=part(p,label,center,(.6,.3,.6),color,material=288)
        light=b.item(body,'PointLight','Luminaire')
        b.prop(light,'float','Brightness',brightness)
        b.prop(light,'float','Range',range_)
        b.prop(light,'bool','Shadows',False)
        element=b.prop(light,'Color3','Color')
        for axis,value in zip('RGB',color):ET.SubElement(element,axis).text=str(value/255)
        lights.append(light.get('referent'))
        return body

    def powered_label(p,text,face=5):
        gui=b.label(p,text,LIGHT,face)
        label=next(e for e in gui.findall('Item') if e.get('class')=='TextLabel')
        b.note(label,'PoweredText',text)
        if computers is not None:
            circuit=b.item(p,'ObjectValue','Circuit')
            b.prop(circuit,'Ref','Value',computers.get('referent'))
        return label

    def shell(p,label,center,size,color=WHITE,front='Z-',angle=100):
        case,door,faces=b.shell(p,label,center,size,color,.12,front,True,angle)
        svc=b.services[-1]
        pivot=list(svc['pivot'])
        axis=0 if front.startswith('X') else 2
        pivot[axis]+=(-1 if front.endswith('-') else 1)*.12
        svc['pivot']=tuple(pivot)
        config=b.find('V9_Service',under=door,cls='Folder')
        vector=b.find('Pivot',under=config,cls='Vector3Value').find("Properties/Vector3[@name='Value']")
        for axis_,value in zip('XYZ',pivot):vector.find(axis_).text=str(value)
        prompt=b.find('V9_ServicePrompt',under=door,cls='ProximityPrompt')
        setprop(prompt,'token','KeyboardKeyCode',102)
        return case,door,faces

    def attach_to_door(door, moving):
        svc=next(s for s in b.services if s['panel']==door.get('referent'))
        config=b.find('V9_Service',under=door,cls='Folder')
        for target in moving:
            svc['moving'].append(target.get('referent'))
            ref=b.item(config,'ObjectValue','Moving_'+str(len(svc['moving'])))
            b.prop(ref,'Ref','Value',target.get('referent'))

    shell_group=group('Hull_Plated_DoubleSkin')
    # The lower chine is a sloping strip, not a filled hull volume.
    span=20
    for i,x in enumerate(range(-140,260,span)):
        cx=x+span/2
        color=(HULL,REPAIR,HULL,HULL)[i%4]
        part(shell_group,'KeelPlate',(cx,-85.4,0),(span+.04,1.2,228),LOWER,'housing')
        part(shell_group,'InnerBottomPlate',(cx,-81.8,0),(span+.04,.65,222),DARK,'housing')
        if i%2==0:
            part(shell_group,'DoubleBottomFrameWeb',(x+.15,-83.45,0),(.45,3.1,222),METAL,'structure')
        for side in (-1,1):
            part(shell_group,'OuterSidePlate',(cx,-50,side*132),(span+.04,44,1.1),color,'housing')
            part(shell_group,'InnerSideLiner',(cx,-51.5,side*125.2),(span+.04,39,.45),LOWER,'housing')
            dy,dz=14,side*18
            length=math.hypot(dy,dz)
            matrix=((1,0,0),(0,dy/length,-dz/length),(0,dz/length,dy/length))
            part(shell_group,'ChinePlate',(cx,-79,side*123),(span+.04,length,1.0),LOWER,'housing',matrix=matrix)
            part(shell_group,'TopSheerStrake',(cx,-30.3,side*132.8),(span+.04,2.4,.28),LIGHT,'detail')
            part(shell_group,'WaterlineWearStrip',(cx,-38.6,side*132.62),(span-.25,.35,.08),SALT)
            part(shell_group,'FrameStiffener',(x+.15,-51.5,side*128.4),(.45,39,6.3),METAL,'structure')
            part(shell_group,'DeckEdgeBracket',(x+.15,-30.8,side*128.4),(.65,4,6.2),DARK,'structure')
        if i%4==1:
            patch=part(shell_group,'SignedPlateRepair',(cx,-44.2,-132.65),(9,8,.2),REPAIR)
            b.label(patch,'HULL / %02d\nУЛЬТРАЗВУКОВОЙ КОНТРОЛЬ'%(i+1),LIGHT)
            for dx in (-3.7,3.7):
                for yy in (-47.4,-41):
                    part(shell_group,'RepairStud',(cx+dx,yy,-132.81),(.2,.2,.1),METAL)

    # Sloped forebody: eight longitudinal seams per side form a real pointed bow.
    for side in (-1,1):
        for i in range(8):
            xa,xb=260+i*10,270+i*10
            za,zb=side*132*(340-xa)/80,side*132*(340-xb)/80
            wall(shell_group,'BowShellPlate',(xa,za),(xb,zb),-86,-28,1.15,HULL)
            wall(shell_group,'BowInnerLiner',(xa,za-side*5),(xb,zb-side*5),-80,-31,.45,LOWER)
            wall(shell_group,'BowSheerTrim',(xa,za+side*.65),(xb,zb+side*.65),-31.5,-29.5,.25,LIGHT,'detail')
        wall(shell_group,'AftQuarter',( -170,side*96),(-140,side*132),-86,-28,1.15,HULL)
        wall(shell_group,'AftQuarterInner',(-167,side*93),(-140,side*126),-81,-31,.45,LOWER)
    part(shell_group,'TransomShell',(-170,-57,0),(1.15,58,192),HULL,'housing')
    part(shell_group,'TransomInnerLiner',(-164.6,-56,0),(.45,50,184),LOWER,'housing')
    part(shell_group,'StemCollision',(339.5,-57,0),(1.2,58,1.2),DARK,'structure')

    deck=group('Weather_Deck_And_Egress')
    # Split physical floor plates around the complete three-flight stair void.
    for xa,xb,za,zb in [(-140,-95,-132,-28),(-140,-95,28,132),(-95,260,-132,132)]:
        length=xb-xa
        segments=max(1,math.ceil(length/25))
        for i in range(segments):
            x0=xa+length*i/segments;x1=xa+length*(i+1)/segments
            part(deck,'SectionalWeatherDeck',((x0+x1)/2,-28.6,(za+zb)/2),(x1-x0+.02,1.2,zb-za),DECK,'walkable')
    # Narrow strips reproduce the tapered foredeck with a continuous floor.
    for xa in range(260,340,2):
        width=max(3.4,264*(340-xa)/80)
        part(deck,'ForedeckPlate',(xa+1,-28.6,0),(2.02,1.2,width),DECK,'walkable')
        part(shell_group,'ForepeakBottom',(xa+1,-85.4,0),(2.02,1.2,max(3,228*(340-xa)/80)),LOWER,'housing')
    for xa in range(-170,-140,2):
        half=96+(xa+170+2)*1.2
        if xa < -150:
            part(deck,'AftDeckPlate',(xa+1,-28.6,0),(2.02,1.2,2*half),DECK,'walkable')
        else:
            for side in (-1,1):
                part(deck,'AftDeckPlateAroundStairs',(xa+1,-28.6,side*(half+28)/2),(2.02,1.2,half-28),DECK,'walkable')
        part(shell_group,'AftKeelPlate',(xa+1,-85.4,0),(2.02,1.2,156+(xa+172)*2.4),LOWER,'housing')
    for side in (-1,1):
        # Port gate at X±8 connects to the marine service gangway.
        pieces=[((-140,side*130),(260,side*130))] if side>0 else [((-140,-130),(-8,-130)),((8,-130),(260,-130))]
        for a,c in pieces:rail(deck,'WeatherSafety',a,c)
        rail(deck,'BowSafety',(260,side*130),(336,side*3))
        rail(deck,'QuarterSafety',(-168,side*94),(-140,side*130))
    rail(deck,'TransomSafetyA',(-168,-94),(-168,-8))
    rail(deck,'TransomSafetyB',(-168,8),(-168,94))
    for a,c in [((-150,-28),(-95,-28)),((-150,28),(-95,28)),((-150,-28),(-150,28)),((-95,-28),(-95,-8)),((-95,23),(-95,28))]:
        rail(deck,'StairVoidGuard',a,c)
    routes += [dict(id='PORT_WEATHER_ROUTE',floor=-28,bounds=[[-140,260],[-114.5,-111.5]]),
               dict(id='STARBOARD_WEATHER_ROUTE',floor=-28,bounds=[[-140,260],[111.5,114.5]])]
    for x in (-120,-40,40,120,200):
        for side in (-1,1):
            part(deck,'DeckEdgeDrain',(x,-27.94,side*126),(5,.05,.7),DARK)
        marker=part(deck,'SectionMarking',(x,-27.96,-109),(5,.03,2),DARK)
        b.label(marker,'D / '+str((x+140)//20),LIGHT,face=1)
    for x,z in [(-130,-117),(-40,117),(80,-117),(200,117),(310,0),(-157,72)]:
        part(deck,'DeckLuminairePost',(x,-24.4,z),(.24,7.2,.24),METAL,'structure')
        lamp(deck,'ShieldedDeckLight',(x,-20.7,z),LIGHT,.75,20)
        part(deck,'LampWeatherShield',(x,-20.42,z),(1.0,.12,1.0),DARK)

    bridge=group('Forebridge_Navigation')
    # Room floor is part of the weather deck; its west doorway joins the central
    # crew corridor without a second threshold or an invisible collision proxy.
    part(bridge,'BridgeRoof',(235,-6.4,0),(42,1.2,83),WHITE,'housing')
    # The crew-deck builder owns the shared X215 bulkhead and its Z±7 portal.
    # Duplicating that wall here would hide surfaces and create two door headers.
    for side in (-1,1):
        z=side*40
        for xa,xb in ((215,232),(240,255)):
            part(bridge,'BridgeSideSill',((xa+xb)/2,-25,z),(xb-xa,6,.65),WHITE,'housing')
            part(bridge,'BridgeSideWindow',((xa+xb)/2,-16,z),(xb-xa,12,.3),BLUE,'housing',material=1568,transparency=.35)
            part(bridge,'BridgeWindowUpperFrame',((xa+xb)/2,-8.6,z),(xb-xa,2.2,.65),WHITE,'housing')
        part(bridge,'BridgeSideDoorHeader',(236,-10.5,z),(8,7,.65),WHITE,'housing')
        for x in (215,232,240,255):part(bridge,'WindowMullion',(x,-17.5,z),(.28,21,.75),DARK,'structure')
        leaf=part(bridge,'BridgeWatertightLeaf',(236,-21,side*39.35),(8,14,.35),WHITE,'panel')
        handle=part(bridge,'DoggingHandle',(233.7,-20.8,side*39.04),(.28,1.7,.32),DARK)
        glass=part(bridge,'DoorInspectionPort',(236,-17.7,side*39.04),(3.4,3.2,.08),BLUE,material=1568,transparency=.3)
        b.slide(leaf,(8.5,0,0),'Герметичная дверь мостика',moving=[handle,glass])
        setprop(b.find('V9_ServicePrompt',under=leaf),'token','KeyboardKeyCode',102)
        for y in (-28.12,-13.85):part(bridge,'DoorSlideTrack',(240,y,side*39.25),(17,.18,.7),DARK,'structure')
    for z in (-32,-16,0,16,32):
        part(bridge,'BridgeFrontSill',(255,-25,z),(.65,6,16),WHITE,'housing')
        part(bridge,'ForwardObservationGlass',(255,-16,z),(.3,12,15.7),BLUE,'housing',material=1568,transparency=.32)
        part(bridge,'FrontWindowCrown',(255,-8.6,z),(.65,2.2,16),WHITE,'housing')
        part(bridge,'FrontWindowMullion',(254.78,-17.5,z+8),(.8,21,.24),DARK,'structure')
    part(bridge,'BridgeDeckThreshold',(215,-27.94,0),(.7,.1,14),METAL,'walkable')
    for i,z in enumerate((-24,-8,8,24)):
        case,door,_=shell(bridge,'MarineConsole_'+str(i+1),(247,-24.1,z),(5.5,7.2,7),TEAL,'X-')
        powered_label(door,('КАНАЛ СВЯЗИ','БОРТОВОЙ ЖУРНАЛ','ВНЕШНИЕ ДАТЧИКИ','НАВИГАЦИОННЫЙ КОНТРОЛЬ')[i],face=3)
        part(case,'ConsoleControllerPCB',(248.95,-24.1,z),(.1,5.9,5.7),TEAL,'internal')
        for k in range(3):
            part(case,'ProcessorAndDissipator',(248.4,-26+k*1.6,z),(.65,.75,3.6),DARK,'internal')
            part(case,'ConsoleBusTerminal',(247,-26+k*1.6,z+2.8),(1.3,.45,.4),AMBER,'internal')
        b.segment(case,'ConsoleSignalBundle',(247,-26.9,z+2.3),(248.7,-26.9,z+2.3),.18,CYAN,role='internal')
        part(bridge,'ConsoleBase',(247,-27.85,z),(6,.3,7.4),DARK,'structure')
    for z in (-26,26):
        part(bridge,'BridgeTaskTable',(228,-23.4,z),(8,.35,6),METAL,'structure')
        for dx in (-3.4,3.4):part(bridge,'TaskTableLeg',(228+dx,-25.775,z),(.35,4.45,4.7),DARK,'structure')
        part(bridge,'ChartFolder',(228,-23.15,z),(4,.12,3),LIGHT)
        lamp(bridge,'BridgeCeilingLight',(232,-7.3,z),LIGHT,.65,22)
    for x in (225,245):
        lamp(bridge,'BridgePassageLight',(x,-7.3,0),CYAN,.45,18)
    routes.append(dict(id='BRIDGE_APPROACH',floor=-28,bounds=[[215.7,240],[-3.2,3.2]]))

    topside=group('Marine_Topside_Systems')
    # Separate exhaust, intake and communications; they are not fantasy weapons.
    for x,z in [(-40,-86),(70,86),(165,-86)]:
        part(topside,'IntakeFoot',(x,-27.7,z),(10,.6,10),DARK,'structure')
        casing,door,_=shell(topside,'WeatherIntakeAndFilter',(x,-23.1,z),(7,8.6,6),WHITE,'Z-')
        part(casing,'PleatedSaltFilter',(x,-22.8,z+.6),(6.3,6.6,.6),LIGHT,'internal')
        for k in range(5):part(casing,'FilterStiffener',(x-2.4+k*1.2,-22.8,z+.2),(.08,6.6,.15),METAL,'internal')
        louvres=[part(casing,'IntakeLouvre',(x,yy,z-3.09),(6.3,.38,.3),DARK)
                 for yy in (-25.8,-24.3,-22.8,-21.3,-19.8)]
        attach_to_door(door,louvres)
        part(topside,'WeatherCowl',(x,-18.55,z),(8.3,.5,7.2),DARK,'housing')
        b.segment(topside,'IntakeControlConduit',(x+3.8,-24,z),(x+3.8,-27.5,z),.16,DARK)
    # A roof-mounted lattice mast whose feet attach to the bridge roof.
    for x in (223,229):
        for z in (-3,3):
            part(topside,'MastRoofFoot',(x,-5.65,z),(1.8,.35,1.8),DARK,'structure')
            b.segment(topside,'MastLeg',(x,-5.5,z),(226,24,z*.35),.25,METAL,role='structure')
    for y in (0,8,16):
        b.segment(topside,'MastHorizontalBrace',(223,y,-3),(229,y,3),.17,METAL)
        b.segment(topside,'MastCrossBrace',(223,y,3),(229,y,-3),.17,METAL)
    part(topside,'RadarPedestal',(226,24.2,0),(2,.5,2),WHITE,'structure')
    part(topside,'MarineRadarArray',(226,25.5,0),(.55,1.9,12),LIGHT,'housing')
    for z in (-3.8,3.8):b.segment(topside,'CommunicationsWhip',(226,24,z),(226,34,z),.09,DARK)
    lamp(topside,'WhiteMastNavigationLight',(226,27.2,0),LIGHT,1.2,26)
    part(topside,'MastLanternStalk',(226,26.8,0),(.3,1,.3),METAL,'structure')
    lamp(topside,'PortNavigationLight',(239,-5.4,-40),RED,.65,13)
    lamp(topside,'StarboardNavigationLight',(239,-5.4,40),(65,160,115),.65,13)
    for side in (-1,1):part(topside,'NavigationLanternMount',(239,-5.65,side*40),(.35,.3,.35),METAL,'structure')
    # Existing lab emergency state is not overwritten. These are separate marine
    # emergency luminaires with a modeled local battery and protected feed.
    battery,door,_=shell(topside,'MarineEmergencyBattery',(220,-24.5,54),(5.5,6.4,4),DARK,'Z-')
    part(topside,'MarineBatteryFoot',(220,-27.85,54),(5.5,.3,4),METAL,'structure')
    for x in (218.7,220,221.3):
        part(battery,'SealedBatteryModule',(x,-24.8,54.2),(.95,4.9,2.9),BLACK,'internal')
        part(battery,'BatteryFuse',(x,-21.75,54),(.55,.3,.6),AMBER,'internal')
    b.label(door,'АВАРИЙНЫЙ БОРТОВОЙ СВЕТ\nЛОКАЛЬНАЯ БАТАРЕЯ',LIGHT)
    b.segment(topside,'EmergencyLightingRiser',(222.8,-24.2,54),(222.8,-7.1,54),.17,DARK)
    b.segment(topside,'RoofLightingFeed',(222.8,-7.1,54),(239,-7.1,40),.17,DARK)
    for x,z in ((-100,109),(110,-109)):
        part(topside,'SurveillanceMount',(x,-25,z),(1.2,6,.6),METAL,'structure')
        part(topside,'CameraCase',(x,-22.2,z),(1.4,1.0,2.4),WHITE,'housing')
        part(topside,'CameraWindow',(x,-22.2,z-1.23),(.8,.65,.1),BLACK)
        b.segment(topside,'CameraFeed',(x,-22.5,z+.8),(x,-27.4,z+.8),.09,DARK)

    # Low covered trunks follow the deck perimeter, clear of the stair opening.
    # Branches terminate at actual lamp posts rather than at arbitrary walls.
    for side in (-1,1):
        b.segment(topside,'ProtectedEmergencyLightTrunk',(-138,-27.83,side*124),(260,-27.83,side*124),.18,DARK)
    b.segment(topside,'ForwardEmergencyBusCrossing',(260,-27.83,-124),(260,-27.83,124),.18,DARK)
    b.segment(topside,'BatteryDeckFeed',(222.8,-24.2,54),(222.8,-27.83,54),.17,DARK)
    b.segment(topside,'BatteryForwardFeed',(222.8,-27.83,54),(260,-27.83,54),.17,DARK)
    for x,z in [(-130,-117),(-40,117),(80,-117),(200,117)]:
        b.segment(topside,'LuminaireBranch',(x,-27.83,124 if z>0 else -124),(x,-27.83,z),.12,DARK)
    b.segment(topside,'AftLuminaireBranch',(-138,-27.83,124),(-157,-27.83,72),.12,DARK)
    b.segment(topside,'ForepeakLightingFeed',(260,-27.83,124),(310,-27.83,48),.12,DARK)
    b.segment(topside,'ForepeakLuminaireBranch',(310,-27.83,48),(310,-27.83,0),.12,DARK)

    dock=group('Marine_Service_And_Rescue_Deck')
    part(dock,'ServiceGangway',(0,-28.45,-137),(12,.9,18),METAL,'walkable')
    part(dock,'DockWorkingDeck',(0,-28.45,-156.5),(36,.9,25),DECK,'walkable')
    for x in (-12,12):
        part(dock,'SealedDockPontoon',(x,-34.5,-157),(6,7,23),LOWER,'housing')
        for z in (-165,-151):part(dock,'PontoonDeckSupport',(x,-30.3,z),(1,3.6,1),METAL,'structure')
    for x in (-6,6):rail(dock,'GangwayGuard',(x,-130),(x,-144))
    for a,c in [((-18,-144),(-6,-144)),((6,-144),(18,-144)),((-18,-144),(-18,-169)),((18,-144),(18,-169)),((-18,-169),(18,-169))]:rail(dock,'DockSafety',a,c)
    for x in (-13,13):
        part(dock,'MooringBitt',(x,-26.7,-164),(.55,2.6,.55),DARK,'structure')
        b.segment(dock,'MooringCrossbar',(x-1,-26,-164),(x+1,-26,-164),.24,METAL,role='structure')
    rail(dock,'AftApronLeft',(-168,-8),(-186,-8))
    rail(dock,'AftApronRight',(-168,8),(-186,8))
    rail(dock,'AftApronEnd',(-186,-8),(-186,8))
    part(dock,'AftRescueApron',(-177,-28.45,0),(18,.9,16),DECK,'walkable')
    rescue,door,_=shell(dock,'RescueEquipmentLocker',(-158,-24.5,17),(7,6.5,4.4),AMBER,'Z-')
    part(dock,'RescueLockerFoot',(-158,-27.875,17),(7,.25,4.4),METAL,'structure')
    for x in (-159.8,-158,-156.2):part(rescue,'BuoyantRescuePack',(x,-24.2,17),(1.45,4.5,3.5),LIGHT,'internal')
    b.label(door,'СПАСАТЕЛЬНОЕ СНАРЯЖЕНИЕ\nНЕ ЗАГРОМОЖДАТЬ ПРОХОД',BLACK)
    routes += [dict(id='DOCK_GANGWAY',floor=-28,bounds=[[-4.6,4.6],[-166,-125]]),
               dict(id='AFT_RESCUE_APPROACH',floor=-28,bounds=[[-184,-157],[-6.5,6.5]])]

    submerged=group('Underwater_Monitoring')
    engineering_connections=[]
    # The upper ballast room supplies these exact deck penetration coordinates.
    # Interdeck pipes are above the preserved laboratory ceilings and terminate
    # in submerged external strainers/nozzles at Z146, outside the water margin.
    for identity,x,z in [('BALLAST_INTAKE',115,51),('BALLAST_DISCHARGE',155,39)]:
        points=[(x,-28.2,z),(x,-33,z),(x,-33,146),(x,-49,146)]
        for a,c in zip(points,points[1:]):
            b.segment(submerged,identity+'_Pipe',a,c,.55,TEAL,role='internal')
        part(submerged,identity+'_HullGland',(x,-33,132.7),(1.8,1.8,.55),METAL,'housing')
        part(submerged,identity+'_SeaSupport',(x,-46,146),(2.1,1.1,2.1),METAL,'housing')
        part(submerged,identity+'_StrainerCap',(x,-49,146),(2.5,.5,2.5),DARK,'housing')
        for dx in (-1,1):
            part(submerged,identity+'_StrainerBar',(x+dx,-50.1,146),(.16,1.8,2.1),METAL,'detail')
        engineering_connections.append({'id':identity,'deck_port':list(points[0]),
                                        'sea_port':list(points[-1]),'pipe_path':[list(p) for p in points]})
    for x in (-95,65,205):
        for side in (-1,1):
            z=side*132.8
            part(submerged,'OceanSensorFlange',(x,-62,z),(3.2,4,.6),METAL,'structure')
            part(submerged,'PressureProbeBody',(x,-62,side*135),(1.8,2.1,3.5),TEAL,'housing')
            part(submerged,'PressureProbeTip',(x,-62,side*137.1),(.8,.9,.5),BLACK)
            b.segment(submerged,'ArmouredProbeCable',(x,-64,side*135),(x,-75,side*146),.2,DARK)
            b.segment(submerged,'MooringCable',(x,-75,side*146),(x+8,-240.5,side*164),.18,DARK)
            part(submerged,'MonitoringAnchor',(x+8,-242,side*164),(5,2,5),LOWER,'structure')
            part(submerged,'MooringEye',(x+8,-240.5,side*164),(.6,1,.6),METAL,'structure')
    for side in (-1,1):
        for x in (-30,140):
            part(submerged,'MarineDepositPatch',(x,-66,side*132.7),(15,4,.16),(52,77,70))
    # The seabed is a distant scene background, not an asserted station depth.
    seafloor=group('Distant_Seafloor_Background')
    for x in (-1400,-400,600,1600):
        for z in (-1400,-400,600,1600):
            part(seafloor,'SeafloorShelf',(x,-247,z),(1000,8,1000),(36,44,45),'structure',material=896)
    for i in range(12):
        x=-650+i*127;z=(-1 if i%2 else 1)*(240+i*27)
        part(seafloor,'SeabedOutcrop',(x,-239+(i%3),z),(35+(i%4)*13,14+(i%3)*6,45),LOWER,'detail',yaw=(i*37)%180,material=896)

    # A rectangular side strip for each longitudinal hull interval follows the
    # bow taper while maintaining a voxel-safe dry margin beside inhabited bays.
    water_boxes=[]
    def water_box(x0,x1,z0,z1,y0=-244,y1=-38):
        water_boxes.append({'center':[(x0+x1)/2,(y0+y1)/2,(z0+z1)/2],
                            'size':[x1-x0,y1-y0,z1-z0]})
    water_box(-700,-180,-650,650)
    water_box(350,850,-650,650)
    water_box(-180,-176,-650,650)
    intervals=[(-176,-168,104),(-168,-160,116),(-160,-152,125.6),
               (-152,-144,135.2),(-144,-140,140),(-140,260,140)]
    for x0 in range(260,340,8):intervals.append((x0,x0+8,132*(340-x0)/80+8))
    intervals.append((340,350,8))
    for x0,x1,half in intervals:
        water_box(x0,x1,-650,-half)
        water_box(x0,x1,half,650)
    water_box(-180,350,-145,145,-244,-92)
    metadata={
        'bounds':{'x':[-186,340],'y':[-251,34],'z':[-169,169]},
        'hull':{'aft':-170,'bow_tip':340,'beam':264,'bottom':-86,'main_deck':-28,
                'old_laboratory_envelope':{'x':[-93,227],'y':[-67.3,-37],'z':[-95,97]},
                'stair_opening':{'x':[-150,-95],'z':[-28,28]},
                'bridge_entry':{'x':215,'z':[-7,7],'floor':-28}},
        'water':{'center':[75,-141,0],'bounds':{'x':[-700,850],'y':[-244,-38],'z':[-650,650]},
                 'waterline':-38,'shipdryvolume':{'x':[-180,350],'y':[-92,5],'z':[-140,140]},
                 'fill_boxes':water_boxes,'color':[18,39,50],'transparency':.35,'reflectance':.3,
                 'wave_size':.16,'wave_speed':8,'placement_is_canon_depth':False},
        'routes':routes,'lights':lights,
        'engineering_connections':engineering_connections,
        'groups':{name(e):sum(p.get('class') in ('Part','Seat','WedgePart') for p in e.iter('Item'))
                  for e in model.findall('Item') if e.get('class')=='Model'},
        'new_parts':len(b.parts)-initial_parts,'service_accesses':len(b.services)-initial_services,
        'powered_bridge_displays':'Existing Circuits.Computers; original controller handles PoweredText',
        'independent_lighting':'Modeled marine emergency battery; no new laboratory circuit is fabricated',
    }
    return metadata
