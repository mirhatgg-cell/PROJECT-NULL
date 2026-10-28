"""Connected V11 crew deck, marine service rooms and a three-flight stair tower.

The lower laboratories remain in place. Only their west outer wall is split to
make a real door-sized connection; the access contains no teleport or ladder.
"""
from __future__ import annotations

import hashlib
import math
import xml.etree.ElementTree as ET

from v7_common import name, WHITE, LIGHT, METAL, DARK, BLACK, CYAN, AMBER, RED, TEAL, BLUE
from v9_common import setprop

FLOOR = -28.0
PAPER = (213, 207, 182)
WOOD = (114, 99, 79)
FABRIC = (91, 110, 121)
ROOM_SPECS = [
    ('C01', 'Каюты сменного персонала', (-80,-30,-60,-9), 'DOC_CREW_SHIFT'),
    ('C02', 'Камбуз и кают-компания', (-20,30,-60,-9), 'DOC_MESS_NOTICE'),
    ('C03', 'Санитарный блок', (40,78,-60,-9), 'DOC_HYGIENE'),
    ('C04', 'Пост безопасности', (90,140,-60,-9), 'DOC_SECURITY_WATCH'),
    ('C05', 'Радиорубка и связь', (150,205,-60,-9), 'DOC_COMMS_LOG'),
    ('C06', 'Судовой распределительный пост', (-80,-30,9,60), 'DOC_SHIP_POWER'),
    ('C07', 'Водоподготовка и жизнеобеспечение', (-20,30,9,60), 'DOC_WATER_BALANCE'),
    ('C08', 'Дежурная администрация', (40,90,9,60), 'DOC_ADMIN_INDEX'),
    ('C09', 'Балластная насосная', (110,160,9,60), 'DOC_BALLAST_LOG'),
    ('C10', 'Пост внешнего наблюдения', (170,205,9,60), 'DOC_OBSERVATION'),
]


def build(b, parent, root):
    addition = b.model(parent, 'Connected_Crew_Deck_V11')
    rooms, interactions, routes, stairs = [], [], [], []
    first_service = len(b.services)

    def part(m, label, pos, size, color=METAL, role='detail', **kw):
        return b.part(m, label, pos, size, color, role=role, material=kw.pop('material',1088), **kw)

    def line(m, label, a, c, diameter=.12, color=METAL, role='detail'):
        return b.segment(m, label, a, c, diameter, color, role=role)

    def sign(m, label, pos, size, text, color=CYAN, face=5):
        p = part(m,label,pos,size,DARK)
        b.label(p,text,color,face)
        return p

    def vector(parent_value, key, values):
        node = setprop(parent_value,'Vector3',key,'')
        for axis,value in zip('XYZ',values): ET.SubElement(node,axis).text=str(value)

    def document(m, doc_id, x, z, title, yaw=0):
        y=FLOOR+5.3
        facing=1 if yaw==180 else -1
        backing=part(m,'DocumentMount_'+doc_id,(x,y,z-facing*.045),(3.3,2.7,.08),METAL,role='housing',yaw=yaw)
        leaf=part(m,'Document_'+doc_id,(x,y,z+facing*.025),(3.05,2.45,.045),PAPER,role='control',yaw=yaw)
        b.label(leaf,title,DARK)
        cfg=b.item(leaf,'Folder','V10_Interact');b.note(cfg,'Action','document');b.note(cfg,'Argument',doc_id)
        prompt=b.item(leaf,'ProximityPrompt','V10_Prompt')
        for key,value in [('ActionText','Прочитать'),('ObjectText',title)]:b.prop(prompt,'string',key,value)
        for key,value in [('HoldDuration',.25),('MaxActivationDistance',9)]:b.prop(prompt,'float',key,value)
        b.prop(prompt,'bool','Enabled',True);b.prop(prompt,'bool','RequiresLineOfSight',True)
        b.prop(prompt,'token','KeyboardKeyCode',101)
        interactions.append({'part':leaf.get('referent'),'action':'document','argument':doc_id,
                             'label':title,'position':(x,y,z+facing*.025)})
        return leaf

    # The original west wall is the only architectural object modified here.
    candidates=[]
    for old in root.iter('Item'):
        if old.get('class')!='Part' or name(old)!='OuterWall':continue
        frame=old.find("Properties/CoordinateFrame[@name='CFrame']")
        if frame is not None and abs(float(frame.findtext('X'))+93)<.001:candidates.append(old)
    assert len(candidates)==1, 'Expected the original west laboratory outer wall'
    old=candidates[0]
    before=hashlib.sha256(ET.tostring(old.find('Properties'))).hexdigest()
    frame=old.find("Properties/CoordinateFrame[@name='CFrame']")
    frame.find('Z').text='-51'
    vector(old,'size',(1,26,88))  # [-95,-7], original referent retained.
    tower=b.model(addition,'LAB_Crew_Stair_Tower')
    part(tower,'WestGalleryPortalNorthPier',(-93,-51,46),(1,26,78),WHITE,'housing')
    part(tower,'WestGalleryPortalHeader',(-93,-44,0),(1,12,14),WHITE,'housing')
    modified=[{'referent':old.get('referent'),'reason':'Split a single west outer wall for a fourteen-stud-wide, fourteen-stud-high physical gallery connection.',
               'before_properties_sha256':before,'portal_bounds':(-93.5,-92.5,-64,-50,-7,7)}]
    part(tower,'LowerStairHallFloor',(-118.75,-64.25,0),(52.5,.5,50),DARK,'walkable')
    # Stairwell walls are split by the lower portal and upper crossover opening.
    part(tower,'StairTowerWestWall',(-145.2,-35.5,0),(.4,57,50.4),WHITE,'housing')
    for zz in (-25.2,25.2):part(tower,'StairTowerSideWall',(-119.9,-35.5,zz),(50.6,57,.4),WHITE,'housing')
    # East wall strips for y/z rectangles, leaving ground and crew exits open.
    for yl,yh,open_z in [(-64,-50,(-7,7)),(-50,-28,None),(-28,-16,(-7,22)),(-16,-7,None)]:
        intervals=[(-25,25)] if open_z is None else [(-25,open_z[0]),(open_z[1],25)]
        for zl,zh in intervals:
            if zh>zl:part(tower,'StairTowerEastPier',(-95.2,(yl+yh)/2,(zl+zh)/2),(.4,yh-yl,zh-zl),WHITE,'housing')
    part(tower,'StairTowerRoof',(-120,-6.75,0),(50.8,.5,50.8),WHITE,'housing')
    lower=part(tower,'LowerFlightLanding',(-139,-64.15,-9),(11,.3,31),METAL,'walkable')
    right=part(tower,'RightFlightLanding',(-110.75,-52.2,-8),(11.5,.4,24),METAL,'walkable')
    left=part(tower,'LeftFlightLanding',(-139.5,-40.2,8),(11,.4,24),METAL,'walkable')
    upper=part(tower,'UpperFlightLanding',(-105.75,-28.2,16),(21.5,.4,8),METAL,'walkable')
    crossover=part(tower,'CrewDeckCrossover',(-97.75,-28.2,7.5),(14.5,.4,29),METAL,'walkable')
    for index,(start_x,z,start_y,direction,landing) in enumerate([
        (-137,-16,-64,1,right),(-115,0,-52,-1,left),(-137,16,-40,1,upper)],1):
        flight=b.model(tower,f'Flight_{index:02d}')
        treads=[]
        for step in range(20):
            x=start_x+direction*1.05*step;top=start_y+.6*(step+1)
            tread=part(flight,f'Tread_{step+1:02d}',(x,top-.15,z),(1.1,.3,6.4),METAL,'walkable')
            treads.append(tread.get('referent'))
            part(flight,'TreadNosing',(x-direction*.45,top+.012,z),(.12,.025,6.2),AMBER)
            if step%4==0 or step==19:
                for side in (-1,1):
                    zz=z+side*3.4
                    part(flight,'HandrailUpright',(x,top+1.55,zz),(.14,3.1,.14),DARK,'structure')
        for side in (-1,1):
            zz=z+side*3.4
            line(flight,'ContinuousHandrail',(start_x-direction*.4,start_y+3.35,zz),
                 (start_x+direction*20.35,start_y+15.35,zz),.16,DARK,'structure')
            line(flight,'StairStringer',(start_x-direction*.4,start_y-.25,zz),
                 (start_x+direction*20.35,start_y+11.75,zz),.25,DARK,'structure')
        stairs.append({'id':f'Flight_{index:02d}','treads':treads,'landings':[landing.get('referent')],
                       'start_approach':(start_x-direction*1.6,start_y,z),
                       'start':(start_x,start_y+.6,z),'end':(start_x+direction*19.95,start_y+12,z),
                       'rise':.6,'pitch':1.05,'width':6.4,'direction':direction})
    # Landing guards follow outer edges and leave the actual flight joins open.
    for yy,segments in [(-52,[((-105,-20),(-105,4)),((-116.5,-20),(-105,-20)),((-116.5,4),(-105,4))]),
                        (-40,[((-145,-4),(-145,20)),((-145,-4),(-134,-4)),((-145,20),(-134,20))]),
                        (-28,[((-116.5,12),(-105,12)),((-116.5,20),(-105,20)),((-105,22),(-90.5,22)),((-105,-7),(-95,-7))])]:
        for (xa,za),(xb,zb) in segments:
            line(tower,'LandingGuardTop',(xa,yy+3.2,za),(xb,yy+3.2,zb),.16,DARK,'structure')
            for x,z in ((xa,za),(xb,zb)):part(tower,'LandingGuardPost',(x,yy+1.6,z),(.16,3.2,.16),DARK,'structure')
    for xx in (-141,-98):
        for zz in (-22,22):
            part(tower,'TowerCornerStiffener',(xx,-36,zz),(.35,55,.35),METAL,'structure')
    sign(tower,'LowerCrewWayfinding',(-94.55,-56,-5.8),(.035,2.6,4.4),'ЖИЛАЯ ПАЛУБА\nЛЕСТНИЦА ↑',CYAN,face=0)
    sign(tower,'UpperLabWayfinding',(-94.95,-22,20),(.035,2.6,4.4),'ЛАБОРАТОРИИ\nЛЕСТНИЦА ↓',CYAN,face=0)
    routes.append({'id':'LAB_TO_CREW_STAIR','points':[(-86,-64,0),(-97,-64,0),(-139,-64,0),(-139,-64,-16),
        (-138.6,-64,-16),(-116.65,-52,-16),(-110,-52,-16),(-110,-52,0),(-113.4,-52,0),
        (-135.35,-40,0),(-139,-40,0),(-139,-40,16),(-138.6,-40,16),(-116.65,-28,16),
        (-98,-28,16),(-94,-28,0),(-86,-28,0)],'width':3.6,'stair_treads':60})

    # Crew deck floor is supplied by the hull module, with the staircase opening.
    shell=b.model(addition,'Crew_Deck_Superstructure')
    part(shell,'CrewDeckRoof',(62.5,-6.75,0),(305,.5,136),WHITE,'housing')
    for xx in (-90,215):
        for zl,zh in [(-68,-7),(7,68)]:part(shell,'EndBulkhead',(xx,-17.5,(zl+zh)/2),(.4,21,zh-zl),WHITE,'housing')
        part(shell,'EndEntryHeader',(xx,-11.5,0),(.4,9,14),WHITE,'housing')
    for side in (-1,1):
        z=side*68
        part(shell,'OuterSill',(62.5,-25,z),(305,6,.4),WHITE,'housing')
        part(shell,'OuterRoofBand',(62.5,-9,z),(305,4,.4),WHITE,'housing')
        for x in range(-84,213,16):
            part(shell,'OuterWindowMullion',(x,-17.5,z),(.28,13,.5),METAL,'housing')
            part(shell,'OuterSafetyGlass',(x+7.6,-17.5,z),(14.9,13,.15),BLUE,'housing',material=1568,transparency=.35)
    # Main corridor cable and ventilation trunks are continuous, not loose ends.
    for z in (-4.5,4.5):
        part(shell,'CorridorCableTray',(62.5,-10.4,z),(303,.32,.85),METAL,'structure')
        for dz,color in ((-.23,DARK),(.05,AMBER),(.25,TEAL)):
            part(shell,'ContinuousShipCable',(62.5,-10.15,z+dz),(302,.1,.1),color)
    part(shell,'CorridorVentilationDuct',(62.5,-9.25,0),(303,1.0,1.3),METAL,'structure')
    for x in range(-84,211,24):
        for z in (-4.5,4.5):part(shell,'TrayRoofHanger',(x,-8.65,z),(.12,2.9,.12),DARK,'structure')
        part(shell,'CorridorFloorGuide',(x,-27.98,0),(11,.025,.2),CYAN)
    routes.append({'id':'CREW_MAIN_CORRIDOR','points':[(-89,-28,0),(210,-28,0),(217,-28,0)],'width':12})

    def table(m,label,x,z,width=7,depth=3,y=FLOOR+3.25):
        obj=b.model(m,label)
        part(obj,'Worktop',(x,y,z),(width,.22,depth),METAL,'structure')
        for dx in (-width/2+.3,width/2-.3):
            for dz in (-depth/2+.3,depth/2-.3):part(obj,'TableLeg',(x+dx,(FLOOR+y-.11)/2,z+dz),(.24,y-.11-FLOOR,.24),DARK,'structure')
        return obj

    def cabinet(m,label,x,z,w=4.4,h=7,d=2.8,color=WHITE):
        front='Z+' if z<0 else 'Z-'
        obj,door,faces=b.shell(m,label,(x,FLOOR+h/2,z),(w,h,d),color,.12,front,True,100)
        for yy in (FLOOR+h*.2,FLOOR+h*.5,FLOOR+h*.8):
            part(obj,'CabinetShelf',(x,yy,z),(w-.3,.1,d-.3),METAL,'structure')
        return obj,door

    def board(obj,x,y,z,width=2.7,height=2.3):
        part(obj,'ControllerPCB',(x,y,z),(width,height,.07),TEAL,'internal')
        for dx in (-width*.26,0,width*.26):
            part(obj,'ControllerIC',(x+dx,y+height*.16,z-.1),(width*.14,height*.2,.12),BLACK,'internal')
            part(obj,'TerminalGroup',(x+dx,y-height*.31,z-.12),(width*.15,height*.14,.18),AMBER,'internal')
        for dx in (-width*.18,width*.18):part(obj,'PowerCapacitor',(x+dx,y-height*.08,z-.18),(width*.11,height*.2,.3),METAL,'internal')

    def monitor(m,label,x,z,y=FLOOR+4.4,caption='СЛУЖЕБНЫЙ КАНАЛ'):
        facing=1 if z<0 else -1
        part(m,label+'_Foot',(x,y-1.0,z+.15),(1.4,.12,.75),DARK,'structure')
        part(m,label+'_Stem',(x,y-.62,z+.16),(.2,.7,.2),METAL,'structure')
        case,door,_=b.shell(m,label,(x,y,z),(2.6,1.65,.72),DARK,.075,'Z-' if facing>0 else 'Z+',True,95)
        board(case,x,y,z+.05,2.1,1.2)
        face=sign(m,label+'_Display',(x,y,z+facing*.38),(2.3,1.4,.035),caption,CYAN,face=2 if facing>0 else 5)
        circuit=b.find('Computers',under=b.find('Circuits',cls='Folder'),cls='BoolValue')
        if circuit is not None:
            ref=b.item(face,'ObjectValue','Circuit');b.prop(ref,'Ref','Value',circuit.get('referent'))
            label_item=next(e for e in face.iter('Item') if e.get('class')=='TextLabel')
            b.note(label_item,'PoweredText',caption)
        keyboard=part(m,label+'_Keyboard',(x,y-1.2,z+facing*1.0),(2,.12,.7),BLACK)
        for i in range(4):part(m,'KeyRows',(x,y-1.12,z+facing*(1.24-i*.15)),(1.7,.035,.07),METAL)
        line(m,'MonitorSupplyLoom',(x,y-.65,z+.3),(x,FLOOR-.05,z+.3),.08,DARK)
        part(m,'FloorCableReceptacle',(x,FLOOR+.01,z+.3),(.55,.12,.55),DARK)
        return case

    def filled_archive(m,label,x,z,color=WHITE):
        case,door=cabinet(m,label,x,z,color=color)
        for yy in (FLOOR+1.4,FLOOR+3.5,FLOOR+5.6):
            for i in range(4):
                xx=x-1.35+i*.9
                part(case,'IndexedBinder',(xx,yy+.65,z),(.6,1.2,1.7),(TEAL,DARK,FABRIC,WOOD)[i],'internal')
                sign(case,'BinderIndex',(xx,yy+.7,z-.87),(.44,.4,.025),f'{i+1:02d}',PAPER)
        return case

    def wall_document(m,code,doc_id,xmin,xmax,zmin,zmax):
        # Side of the rear wall facing the room, away from NPC routes.
        x=xmin+5; z=zmin+.35 if zmin<0 else zmax-.35
        yaw=180 if zmin<0 else 0
        document(m,doc_id,x,z,code+' / СЛУЖЕБНАЯ ЗАПИСЬ',yaw)

    room_models={}
    for code,title,(xmin,xmax,zmin,zmax),doc_id in ROOM_SPECS:
        obj=b.model(addition,code+'_'+title.replace(' ','_'))
        room_models[code]=obj
        cx=(xmin+xmax)/2;cz=(zmin+zmax)/2;front=zmax if zmin<0 else zmin;rear=zmin if zmin<0 else zmax
        width=xmax-xmin;depth=zmax-zmin
        for xx in (xmin,xmax):part(obj,'RoomSideWall',(xx,-17.5,cz),(.3,21,depth),WHITE,'housing')
        for xl,xh in [(xmin,cx-4),(cx+4,xmax)]:part(obj,'RoomEntryPier',((xl+xh)/2,-17.5,front),(xh-xl,21,.3),WHITE,'housing')
        part(obj,'RoomEntryHeader',(cx,-11.5,front),(8,9,.3),WHITE,'housing')
        part(obj,'RearWindowSill',(cx,-25,rear),(width,6,.3),WHITE,'housing')
        part(obj,'RearWindowHead',(cx,-10,rear),(width,6,.3),WHITE,'housing')
        for xx in (xmin+.2,cx,xmax-.2):part(obj,'RearWindowMullion',(xx,-17.5,rear),(.22,9,.35),METAL,'housing')
        for xx in ((xmin+cx)/2,(cx+xmax)/2):part(obj,'RearSafetyGlass',(xx,-17.5,rear),(width/2-.3,9,.12),BLUE,'housing',material=1568,transparency=.35)
        for xx in (xmin+.25,xmax-.25):
            part(obj,'DoorFramePost',(cx-4.2 if xx<xmin+1 else cx+4.2,-22,front),(.18,12,.32),DARK,'structure')
        sign(obj,'RoomIdentifier',(cx,-14.3,front+(0.2 if zmin<0 else -.2)),(7.5,1.4,.07),code+' / '+title.upper(),CYAN,face=2 if zmin<0 else 5)
        for xx in range(math.ceil(xmin)+2,math.floor(xmax),8):
            part(obj,'FloorExpansionJoint',(xx,-27.98,cz),(.025,.025,depth-.5),DARK)
        # Every room has a real feeder and a local roof duct branch to the corridor.
        line(obj,'RoomFeederCable',(cx,-10.15,4.5 if zmin>0 else -4.5),(cx,-10.15,cz),.13,DARK)
        part(obj,'RoomVentBranch',(cx,-9.25,cz/2),(1.0,.8,abs(cz)),METAL,'structure')
        vent=part(obj,'RoomDiffuser',(cx,-9.9,cz),(3.5,.25,2.0),METAL,'structure')
        for i in range(6):part(obj,'DiffuserSlot',(cx-1.4+i*.56,-10.04,cz),(.12,.03,1.6),BLACK)
        lamp=part(obj,'CrewWorkLight',(cx,-8.1,cz),(6,.2,.8),LIGHT,material=288)
        light=b.item(lamp,'PointLight','RoomWorkLight');b.prop(light,'float','Brightness',.7);b.prop(light,'float','Range',23)
        col=b.prop(light,'Color3','Color')
        for k,v in zip('RGB',LIGHT):ET.SubElement(col,k).text=str(v/255)
        circuit=b.find('Computers',under=b.find('Circuits',cls='Folder'),cls='BoolValue')
        if circuit is not None:
            ref=b.item(lamp,'ObjectValue','Circuit');b.prop(ref,'Ref','Value',circuit.get('referent'))
            b.note(lamp,'V11_CircuitVisual','RoomWorkLight')
        wall_document(obj,code,doc_id,xmin,xmax,zmin,zmax)
        entry=(cx,FLOOR,front)
        rooms.append({'id':code,'label':title,'bounds':(xmin,xmax,-28.5,-7,zmin,zmax),
                      'deck':'Жилая и служебная палуба','entry':entry,'document':doc_id})
        routes.append({'id':code+'_ENTRY','points':[(cx,FLOOR,0),(cx,FLOOR,front),(cx,FLOOR,front+(-6 if front<0 else 6))],'width':5})

    # Furniture is deliberately different in each room; central approaches and
    # the NPC work strips stay clear. All large surfaces have physical roles.
    crew=room_models['C01']
    for x in (-73,-60):
        bunk=b.model(crew,'TwinBerthModule')
        for y in (FLOOR+1.2,FLOOR+5.1):
            part(bunk,'BerthTray',(x,y,-45),(7.7,.2,3.5),METAL,'structure')
            part(bunk,'Mattress',(x,y+.35,-45),(7.2,.5,3.2),FABRIC,'structure',material=1312)
            part(bunk,'Pillow',(x-2.5,y+.68,-45),(1.6,.3,2.8),LIGHT,material=1312)
            part(bunk,'FoldedBlanket',(x+1.7,y+.7,-45),(2.9,.26,3.05),TEAL,material=1312)
        for dx in (-3.8,3.8):
            for dz in (-1.7,1.7):part(bunk,'BunkCornerPost',(x+dx,FLOOR+3.25,-45+dz),(.18,6.5,.18),DARK,'structure')
        for i in range(5):part(bunk,'BunkLadderRung',(x+3.85,FLOOR+.65+i*1.05,-46.9),(.25,.12,1.3),METAL,'structure')
    for x in (-74,-66,-58,-50):
        case,door=cabinet(crew,'CrewPersonalLocker',x,-54,w=5.1,h=6.5,d=2.5,color=FABRIC)
        part(case,'FoldedUniform',(x,FLOOR+1.75,-54),(3.7,.5,1.7),BLUE,'internal',material=1312)
        part(case,'PersonalBag',(x,FLOOR+3.9,-54),(2.6,1.2,1.6),DARK,'internal')
        part(case,'PersonalNotebook',(x+.6,FLOOR+5.4,-54),(.9,.13,1.5),PAPER,'internal')
    table(crew,'CrewWritingDesk',-39,-37,7,3)
    line(crew,'PersonalMug',(-39,FLOOR+3.4,-37),(-39,FLOOR+4.0,-37),.4,WHITE)
    sign(crew,'VacantBerthTag',(-30.2,-22.4,-37),(.06,1.3,4.4),'СМЕНА 12 / МЕСТО СОХРАНЕНО',AMBER,face=3)

    mess=room_models['C02']
    for x in (-9,16):
        table(mess,'DiningTable',x,-31,12,5)
        for z in (-35.1,-26.9):
            part(mess,'DiningBench',(x,FLOOR+1.75,z),(11,.3,1.5),WOOD,'structure')
            for dx in (-4.5,4.5):part(mess,'BenchLeg',(x+dx,FLOOR+.8,z),(.24,1.6,.6),METAL,'structure')
        for dx in (-3,0,3):
            part(mess,'MealTray',(x+dx,FLOOR+3.4,-31),(2.2,.08,1.6),WHITE)
            line(mess,'Cup',(x+dx+.6,FLOOR+3.4,-31.3),(x+dx+.6,FLOOR+4.0,-31.3),.43,METAL)
    for x in (-12,0,12,24):
        counter,door=cabinet(mess,'GalleySupplyCase',x,-54,6.8,5.8,3.4,TEAL)
        for yy in (FLOOR+1.6,FLOOR+3.7):
            for dx in (-1.8,0,1.8):line(counter,'SealedFoodCanister',(x+dx,yy+.05,-54),(x+dx,yy+1.15,-54),.85,LIGHT,'internal')
    part(mess,'GalleyExtractionHood',(6,-15,-53),(26,1.6,5),METAL,'housing')
    part(mess,'GalleyExhaustBranch',(6,-10.9,-53),(1.4,6.6,1.4),METAL,'structure')

    hygiene=room_models['C03']
    for x in (47,58,69):
        part(hygiene,'Washbasin',(x,FLOOR+3.0,-50),(6,.3,4),LIGHT,'structure')
        part(hygiene,'BasinBacksplash',(x,FLOOR+4.0,-52),(6,2,.15),WHITE,'housing')
        part(hygiene,'Mirror',(x,FLOOR+6.0,-52.11),(4.8,2.7,.08),METAL)
        line(hygiene,'FaucetRiser',(x,FLOOR+3.15,-51),(x,FLOOR+4.1,-51),.14,METAL)
        line(hygiene,'FaucetSpout',(x,FLOOR+4.1,-51),(x,FLOOR+4.1,-50.3),.14,METAL)
        line(hygiene,'FreshWaterFeed',(x,FLOOR+.6,-51),(x,FLOOR+3.0,-51),.16,TEAL)
    for x in (46,60):
        part(hygiene,'ShowerDrain',(x,-27.94,-29),(8,.1,8),METAL,'walkable')
        for dx in (-4,4):part(hygiene,'ShowerPrivacyPanel',(x+dx,-22,-29),(.15,12,9),LIGHT,'housing')
        line(hygiene,'ShowerRiser',(x,-27.5,-33),(x,-17,-33),.13,METAL)
        part(hygiene,'ShowerHead',(x,-16.9,-32.5),(1.4,.16,1.4),METAL)
    soap,door=cabinet(hygiene,'HygieneSupplyLocker',72,-38,3,5.4,2.4,WHITE)
    for i in range(4):part(soap,'RolledTowel',(72,FLOOR+1.7+i*.7,-38),(2.3,.4,1.6),LIGHT,'internal',material=1312)

    security=room_models['C04']
    table(security,'WatchDesk',114,-32,14,4,y=FLOOR+3.3)
    for x in (110,114,118):monitor(security,'WatchDisplay',x,-31.8,caption='КОНТРОЛЬ ДОСТУПА\nЖУРНАЛ СОБЫТИЙ')
    filled_archive(security,'AccessRegisterCabinet',134,-48,DARK)
    case,door=cabinet(security,'EmergencyEquipmentCabinet',98,-48,5.8,8,3.1,AMBER)
    for yy in (FLOOR+1.6,FLOOR+3.7,FLOOR+5.8):
        part(case,'SealedRespiratorPack',(98,yy+.65,-48),(4.4,1.2,1.9),DARK,'internal')
    sign(security,'NoUnverifiedReport',(126,-24.5,-59.78),(6,2,.06),'НЕ ПОДМЕНЯТЬ ПЕРВИЧНУЮ ЗАПИСЬ СВОДКОЙ',AMBER,face=2)

    comms=room_models['C05']
    table(comms,'CommsOperatorDesk',176,-32,14,4,y=FLOOR+3.3)
    for x in (172,176,180):monitor(comms,'CommsDisplay',x,-31.8,caption='СВЯЗЬ / НЕЗАВИСИМЫЙ КАНАЛ')
    for x in (159,195):
        case,door=cabinet(comms,'RadioReceiverRack',x,-49,5.5,8.2,3.5,DARK)
        for yy in (FLOOR+1.6,FLOOR+3.7,FLOOR+5.8):
            part(case,'RadioModule',(x,yy+.55,-49),(4.8,.9,2.8),METAL,'internal')
            board(case,x,yy+.6,-48.2,4, .7)
        line(comms,'RadioAntennaFeed',(x,FLOOR+.3,-48.5),(x,-10.1,-48.5),.16,DARK)
    part(comms,'CommsRoofFeed',(177,-9.2,-42),(1.3,1.2,34),METAL,'structure')

    electrical=room_models['C06']
    for x in (-73,-63,-53,-43):
        case,door=cabinet(electrical,'MarineDistributionCabinet',x,49,7.6,10,4,DARK)
        board(case,x,FLOOR+5.3,50.4,6.5,7.7)
        for yy in (FLOOR+2.1,FLOOR+4.6,FLOOR+7.1):
            for dx in (-1.8,0,1.8):part(case,'MarineCircuitContactor',(x+dx,yy,49.4),(1.15,1.6,1.9),BLACK,'internal')
        for dx,col in ((-2.4,AMBER),(0,TEAL),(2.4,DARK)):
            line(case,'CabinetBusBar',(x+dx,FLOOR+.8,49),(x+dx,FLOOR+9.1,49),.16,col,'internal')
        line(electrical,'MarineRiser',(x,FLOOR+10.2,49),(x,-10.2,49),.23,DARK)
    work=table(electrical,'SwitchboardInspectionShelf',-54,35.5,12,3,y=FLOOR+3.2)
    part(work,'LockoutKit',(-54,FLOOR+3.55,35.5),(2,.5,1.2),AMBER,'internal')
    part(electrical,'SwitchboardFeederTray',(-55,-10.2,49),(41,.45,1),METAL,'structure')
    part(electrical,'SwitchboardSupplyTray',(-55,-10.2,26.75),(1,.45,44.5),METAL,'structure')

    life=room_models['C07']
    for x in (-9,12):
        case,door=cabinet(life,'WaterTreatmentSkidCase',x,47,10,9,6,TEAL)
        for dx in (-3,0,3):
            line(case,'FilterPressureTube',(x+dx,FLOOR+1.1,47),(x+dx,FLOOR+7.4,47),1.5,METAL,'internal')
            for yy in (FLOOR+1.4,FLOOR+7):part(case,'PressureCoupling',(x+dx,yy,47),(.8,.35,2),DARK,'internal')
        board(case,x,FLOOR+5.7,49.1,7.5,2.0)
    for z,y,color in ((54,-16.4,TEAL),(56,-15.4,BLUE)):
        line(life,'WaterHeader',(-15,y,z),(20,y,z),.5,color,'structure')
        for x in (-9,12):
            port_z=46.2 if z==54 else 47.8
            line(life,'WaterFilterOverheadBranch',(x,y,z),(x,y,port_z),.4,color,'structure')
            line(life,'WaterFilterRoofPort',(x,y,port_z),(x,-19,port_z),.4,color,'structure')
    for z,y,color in ((54,-16.4,TEAL),(56,-15.4,BLUE)):
        line(life,'WaterDeckSupplyRiser',(20,y,z),(20,FLOOR-.2,z),.5,color,'structure')
        part(life,'WaterDeckPenetration',(20,FLOOR-.01,z),(1.2,.14,1.2),DARK,'housing')
    table(life,'SampleAndMembraneBench',3,25,10,3)
    for i in range(5):line(life,'SealedWaterSample',(-.6+i*1.8,FLOOR+3.3,25),(-.6+i*1.8,FLOOR+4.1,25),.45,LIGHT,'internal')

    admin=room_models['C08']
    table(admin,'DutyArchivistDesk',64,32,13,4,y=FLOOR+3.3)
    monitor(admin,'ArchiveIndexDisplay',64,32,caption='АРХИВ / ИНДЕКС ИСТОЧНИКОВ')
    for x,col in ((47,WHITE),(82,FABRIC)):filled_archive(admin,'DutyRecordCabinet',x,51,col)
    for i in range(4):
        part(admin,'PendingFolder',(59+i*2.3,FLOOR+3.54,32),(1.7,.16,2.4),PAPER,'internal')
    sign(admin,'ContradictionBoard',(75,-24.5,59.78),(9,3,.1),'СВОДКА ≠ ПЕРВИЧНЫЙ ЖУРНАЛ\nСВЕРЯТЬ ПОДПИСЬ И ВРЕМЯ',AMBER)

    ballast=room_models['C09']
    for x in (121,145):
        skid=b.model(ballast,'BallastPumpModule')
        part(skid,'PumpBase',(x,FLOOR+.3,45),(13,.6,8),DARK,'structure')
        case,door,_=b.shell(skid,'BallastMotorCase',(x,FLOOR+3.6,45),(7,5.5,5),METAL,.16,'Z-',True,100)
        line(case,'MotorRotor',(x-2.4,FLOOR+3.6,45),(x+2.4,FLOOR+3.6,45),1.8,DARK,'internal')
        for dx in (-1.9,0,1.9):
            part(case,'StatorLamination',(x+dx,FLOOR+3.6,45),(.8,3.7,3.7),TEAL,'internal')
        board(case,x,FLOOR+3.6,46.9,4.6,3.5)
        pump,cover,_=b.shell(skid,'BallastPressureCase',(x+5.2,FLOOR+3.1,45),(3.2,4.5,4.5),TEAL,.14,'Z-',True,100)
        line(pump,'ImpellerHub',(x+4.1,FLOOR+3.1,45),(x+6.3,FLOOR+3.1,45),1.9,METAL,'internal')
        for y in (-.9,0,.9):part(pump,'ImpellerBlade',(x+5.2,FLOOR+3.1+y,45),(1.1,.25,2.8),METAL,'internal')
        for z,y,port_z,color in ((51,-18.8,45.8,TEAL),(39,-17.4,44.2,BLUE)):
            line(skid,'PumpRoofPort',(x+5.2,-22.65,port_z),(x+5.2,y,port_z),.7,color,'structure')
            line(skid,'PumpOverheadPipe',(x+5.2,y,port_z),(x+5.2,y,z),.7,color,'structure')
    line(ballast,'BallastIntakeHeader',(115,-18.8,51),(155,-18.8,51),.9,TEAL,'structure')
    line(ballast,'BallastPressureHeader',(115,-17.4,39),(155,-17.4,39),.9,BLUE,'structure')
    for x,z,y,color in ((115,51,-18.8,TEAL),(155,39,-17.4,BLUE)):
        line(ballast,'BallastDeckFeed',(x,y,z),(x,FLOOR-.2,z),.9,color,'structure')
        part(ballast,'BallastDeckPenetration',(x,FLOOR-.01,z),(1.7,.14,1.7),DARK,'housing')

    observation=room_models['C10']
    for x in (179,195):
        stand=b.model(observation,'MarineObservationPedestal')
        part(stand,'ObservationBase',(x,FLOOR+.15,47),(4,.3,3),DARK,'structure')
        part(stand,'ObservationColumn',(x,FLOOR+2.2,47),(.6,4.1,.6),METAL,'structure')
        case,door,_=b.shell(stand,'OpticalRecordingInstrument',(x,FLOOR+5.0,47),(3,2.6,2.6),DARK,.09,'Z-',True,100)
        board(case,x,FLOOR+5.0,47.8,2.4,1.8)
        for dx in (-.7,.7):line(case,'OpticalDetector',(x+dx,FLOOR+5.1,46.2),(x+dx,FLOOR+5.1,47),.55,CYAN,'internal')
    part(observation,'ObservationBench',(187,FLOOR+1.7,27),(19,.3,2.4),FABRIC,'structure',material=1312)
    for x in (180,194):part(observation,'ObservationBenchLeg',(x,FLOOR+.8,27),(.3,1.6,1.6),METAL,'structure')

    # Offset each front hinge pin outside its face; this avoids butt-joint
    # clipping after ninety degrees without changing a closed panel's pose.
    indexed={e.get('referent'):e for e in root.iter('Item')}
    parents={c:p for p in root.iter('Item') for c in p.findall('Item')}
    cavities={c['model']:c for c in b.cavities}
    for service in b.services[first_service:]:
        panel=indexed[service['panel']];cavity=cavities.get(parents[panel].get('referent'))
        if cavity and cavity['front'] in ('Z-','Z+'):
            pivot=list(service['pivot']);pivot[2]+=(-1 if cavity['front']=='Z-' else 1)*(cavity['thickness']/2+.045)
            service['pivot']=tuple(pivot)
            config=b.find('V9_Service',under=panel,cls='Folder')
            vector(b.find('Pivot',under=config,cls='Vector3Value'),'Value',pivot)
        prompt=b.find('V9_ServicePrompt',under=panel,cls='ProximityPrompt')
        if prompt is not None:setprop(prompt,'token','KeyboardKeyCode',102)

    return {'rooms':rooms,'interactions':interactions,'routes':routes,'stairs':stairs,
            'modified_refs':[old.get('referent')],'modifications':modified,
            'groups':{name(e):sum(p.get('class')=='Part' for p in e.iter('Item')) for e in addition.findall('Item') if e.get('class')=='Model'},
            'portal':{'referent':old.get('referent'),'center':(-93,-57,0),'width':14,'height':14},
            'npc_work_zones':{'SECURITY':{'home':(114,-28,-27),'route':(122,-28,-27)},
                'OPERATOR':{'home':(176,-28,-27),'route':(184,-28,-27)},
                'ENGINEER':{'home':(-54,-28,29),'route':(-44,-28,29)},
                'ARCHIVIST':{'home':(64,-28,28),'route':(72,-28,28)}}}
