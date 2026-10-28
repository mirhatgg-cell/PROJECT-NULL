"""Local R6 staff rigs: in-place staff upgrade, named clothing and real joints.

No catalogue assets, animation IDs or player-avatar requests are required.
The seven R6 body parts are connected by Motor6D joints; all visible wardrobe
and tools are massless weld attachments to those body parts.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from v7_common import name, WHITE, LIGHT, METAL, DARK, BLACK, CYAN, AMBER, TEAL, RED
from v9_common import setprop

STAFF = {
    'TECH': {'name': 'Илья Ветров', 'role': 'Техник смены', 'home': (11.5,-64,-71.3),
             'route': ((8.4,-64,-71.3),), 'work': (11.5,-61,-73), 'mode': 'inspect',
             'uniform': (72,103,116), 'skin': (172,148,128)},
    'MEDIC': {'name': 'Лидия Кравцова', 'role': 'Медицинский сотрудник', 'home': (76.4,-64,-7.4),
              'route': ((76.4,-64,-3.9),), 'work': (76.4,-61,-10), 'mode': 'read',
              'uniform': (178,201,196), 'skin': (188,155,135)},
    'OPERATOR': {'name': 'Нина Соколова', 'role': 'Нейрооператор', 'home': (176,-28,-27),
                 'route': ((184,-28,-27),), 'work': (176,-25,-30), 'mode': 'terminal',
                 'uniform': (67,85,112), 'skin': (167,132,111)},
    'ENGINEER': {'name': 'Марк Белов', 'role': 'Инженер контура', 'home': (-54,-28,29),
                 'route': ((-44,-28,29),), 'work': (-54,-23,34), 'mode': 'repair',
                 'uniform': (113,106,77), 'skin': (150,119,99)},
    'SECURITY': {'name': 'Артём Громов', 'role': 'Вахтенный безопасности', 'home': (114,-28,-27),
                 'route': ((122,-28,-27),), 'work': (114,-25,-30), 'mode': 'watch',
                 'uniform': (52,62,67), 'skin': (128,100,85)},
    'ARCHIVIST': {'name': 'Софья Левина', 'role': 'Регистратор смен', 'home': (64,-28,28),
                  'route': ((72,-28,28),), 'work': (64,-25,32), 'mode': 'read',
                  'uniform': (100,108,110), 'skin': (204,176,150)},
}
BODY = ('HumanoidRootPart','Torso','Head','Left Arm','Right Arm','Left Leg','Right Leg')


def build(b, parent, root):
    before = {e.get('referent'): ET.tostring(e.find('Properties')) for e in root.iter('Item')}
    initial_refs = set(before)
    result = {'rigs': [], 'movable_refs': [], 'modified_refs': [], 'removed_refs': [], 'new_refs': []}
    folder = b.item(parent, 'Folder', 'Crew_Rigs_V11')

    def position(part):
        frame=part.find("Properties/CoordinateFrame[@name='CFrame']")
        return tuple(float(frame.findtext(k)) for k in 'XYZ')

    def vector(parent, cls, label, value):
        item=b.item(parent,cls,label)
        target=b.prop(item,'Vector3','Value')
        for key,v in zip('XYZ',value):ET.SubElement(target,key).text=str(v)
        return item

    def cframe(item,key,xyz):
        frame=b.prop(item,'CoordinateFrame',key)
        for k,v in zip('XYZ',xyz):ET.SubElement(frame,k).text=str(v)
        for i in range(3):
            for j in range(3):ET.SubElement(frame,f'R{i}{j}').text=str(int(i==j))

    def packed(color):return (255<<24)|(color[0]<<16)|(color[1]<<8)|color[2]

    def attach(model,label,target,pos,size,color,shape=None):
        part=b.part(model,label,pos,size,color,272,shape=shape)
        setprop(part,'bool','Anchored',False)
        setprop(part,'bool','Massless',True)
        setprop(part,'bool','CanQuery',False)
        weld=b.item(part,'WeldConstraint','WardrobeWeld')
        b.prop(weld,'Ref','Part0',target.get('referent'))
        b.prop(weld,'Ref','Part1',part.get('referent'))
        result['movable_refs'].append(part.get('referent'))
        return part

    for staff_id, data in STAFF.items():
        model=b.find('Staff_'+staff_id,under=root,cls='Model')
        existing=model is not None
        if not existing:
            model=b.model(folder,'Staff_'+staff_id)
            x,floor,z=data['home']
            broad=staff_id=='SECURITY'
            slim=staff_id=='ARCHIVIST'
            torso_width=2.02 if broad else (1.64 if slim else 1.8)
            parts={}
            for label,offset,size,color,role,shape in [
                ('HumanoidRootPart',(0,3.35,0),(1.8,2.1,.8),BLACK,'detail',None),
                ('Torso',(0,3.35,0),(torso_width,2.1,.9),data['uniform'],'structure',None),
                ('Head',(0,5.05,0),(1.25,1.3,1.2),data['skin'],'control',0),
                ('Left Arm',(-1.27,3.35,0),(.7,2.05,.8),data['uniform'],'detail',None),
                ('Right Arm',(1.27,3.35,0),(.7,2.05,.8),data['uniform'],'detail',None),
                ('Left Leg',(-.47,1.2,0),(.78,2.2,.82),DARK,'structure',None),
                ('Right Leg',(.47,1.2,0),(.78,2.2,.82),DARK,'structure',None),
            ]:
                p=b.part(model,label,(x+offset[0],floor+offset[1],z+offset[2]),size,color,272,role=role,shape=shape)
                parts[label]=p
            humanoid=b.item(model,'Humanoid','Humanoid')
        else:
            parts={label:b.find(label,under=model,cls='Part') for label in BODY}
            humanoid=b.find('Humanoid',under=model,cls='Humanoid')
            assert all(parts.values()) and humanoid is not None
            # Remove only the six rigid prototype body joints. Visible old parts,
            # existing head interaction metadata and both staff IDs survive.
            old_joints=[e for e in model.iter('Item') if e.get('class')=='WeldConstraint']
            for joint in old_joints:
                result['removed_refs'].append(joint.get('referent'));b.remove(joint)
        x,floor,z=data['home']
        root_part=parts['HumanoidRootPart']
        torso=parts['Torso'];head=parts['Head']
        for label,part in parts.items():
            b.role(part,'structure' if label in ('Torso','Left Leg','Right Leg') else ('control' if label=='Head' else 'detail'))
            setprop(part,'bool','Anchored',False)
            setprop(part,'bool','Massless',False)
            setprop(part,'bool','CanTouch',False)
            setprop(part,'Color3uint8','Color3uint8',packed(data['skin'] if label=='Head' else (data['uniform'] if label in ('Torso','Left Arm','Right Arm') else DARK)))
            result['movable_refs'].append(part.get('referent'))
        setprop(root_part,'float','Transparency',1)
        setprop(root_part,'bool','CanCollide',False)
        setprop(root_part,'bool','CanQuery',False)
        setprop(root_part,'int','RootPriority',127)
        setprop(model,'Ref','PrimaryPart',root_part.get('referent'))
        aim=b.item(root_part,'Attachment','V11_AimAttachment')
        facing=b.item(root_part,'AlignOrientation','StaffFacing')
        b.prop(facing,'Ref','Attachment0',aim.get('referent'))
        # Official Roblox creator-docs enum: OneAttachment=0, TwoAttachment=1.
        b.prop(facing,'token','Mode',0)
        b.prop(facing,'bool','Enabled',True)
        b.prop(facing,'bool','RigidityEnabled',False)
        b.prop(facing,'float','Responsiveness',8)
        b.prop(facing,'float','MaxTorque',20000)
        b.prop(facing,'float','MaxAngularVelocity',8)
        for key,value,tag in [('DisplayName',data['name'],'string'),('Health',100,'float'),
                              ('MaxHealth',100,'float'),('WalkSpeed',7,'float'),('HipHeight',.1,'float'),
                              ('JumpPower',0,'float'),('RigType',0,'token'),('RequiresNeck',True,'bool'),
                              ('BreakJointsOnDeath',False,'bool'),('AutoRotate',True,'bool'),
                              ('NameDisplayDistance',18,'float'),('HealthDisplayDistance',0,'float')]:
            setprop(humanoid,tag,key,value)
        animator=b.item(humanoid,'Animator','Animator')
        colors=b.item(model,'BodyColors','Body Colors')
        for key in ('HeadColor3','LeftArmColor3','RightArmColor3','TorsoColor3','LeftLegColor3','RightLegColor3'):
            color=data['skin'] if key=='HeadColor3' else (DARK if 'Leg' in key else data['uniform'])
            prop=b.prop(colors,'Color3',key)
            for channel,value in zip('RGB',color):ET.SubElement(prop,channel).text=str(value/255)

        torso_pos=position(torso)
        joints={}
        joint_specs=[
            ('RootJoint',root_part,torso,(0,0,0)),
            ('Neck',torso,head,(0,1.05,0)),
            ('Left Shoulder',torso,parts['Left Arm'],(-.9,.75,0)),
            ('Right Shoulder',torso,parts['Right Arm'],(.9,.75,0)),
            ('Left Hip',torso,parts['Left Leg'],(-.47,-1.05,0)),
            ('Right Hip',torso,parts['Right Leg'],(.47,-1.05,0)),
        ]
        for label,part0,part1,offset in joint_specs:
            world=tuple(torso_pos[i]+offset[i] for i in range(3))
            p0,p1=position(part0),position(part1)
            joint=b.item(part0,'Motor6D',label)
            b.prop(joint,'Ref','Part0',part0.get('referent'))
            b.prop(joint,'Ref','Part1',part1.get('referent'))
            cframe(joint,'C0',tuple(world[i]-p0[i] for i in range(3)))
            cframe(joint,'C1',tuple(world[i]-p1[i] for i in range(3)))
            joints[label]=joint.get('referent')

        # Bind every pre-existing visible component to the appropriate R6 part.
        # The old foot/face geometry is retained, but no longer anchored in air.
        for part in list(model.findall('Item')):
            if part.get('class')!='Part' or part in parts.values():continue
            label=name(part);p=position(part)
            if label in ('Eye','Mouth'):target=head
            elif label=='Boot':target=parts['Left Leg'] if p[0]<x else parts['Right Leg']
            else:target=torso
            b.role(part,'detail')
            setprop(part,'bool','Anchored',False);setprop(part,'bool','Massless',True)
            weld=b.item(part,'WeldConstraint','WardrobeWeld')
            b.prop(weld,'Ref','Part0',target.get('referent'));b.prop(weld,'Ref','Part1',part.get('referent'))
            result['movable_refs'].append(part.get('referent'))

        # Local wardrobe geometry is authored for each identity rather than
        # requested from a player avatar or an unverifiable catalogue asset.
        def wear(label,target,offset,size,color,shape=None):
            base=position(target)
            return attach(model,label,target,tuple(base[i]+offset[i] for i in range(3)),size,color,shape)
        if not existing:
            for dx in (-.24,.24):wear('Eye',head,(dx,.13,-.583),(.12,.1,.035),BLACK)
            wear('Mouth',head,(0,-.23,-.591),(.34,.055,.025),DARK)
            for label,leg in (('Left Boot',parts['Left Leg']),('Right Boot',parts['Right Leg'])):
                wear(label,leg,(0,-1.05,-.15),(.8,.28,1.12),BLACK)
            badge=wear('StaffBadge',torso,(.46,.1,-.48),(.5,.7,.045),LIGHT)
            b.label(badge,data['role'],DARK)
        wear('UniformSeam',torso,(0,0,-.47),(.035,1.7,.025),LIGHT)
        if staff_id=='TECH':
            wear('GreyHair',head,(0,.52,.06),(1.25,.34,1.15),(90,93,88))
            wear('WorkGoggleBand',head,(0,.14,-.57),(1.24,.23,.12),DARK)
            for dx in (-.3,.3):wear('WorkGoggleLens',head,(dx,.14,-.66),(.46,.27,.08),CYAN)
            wear('UtilityPouch',torso,(-.67,-.65,-.5),(.48,.66,.3),AMBER)
            wear('Multimeter',parts['Right Arm'],(0,-.7,-.42),(.52,.7,.22),DARK)
        elif staff_id=='MEDIC':
            wear('MedicalCoat',torso,(0,-.22,.015),(1.92,2.62,1.01),LIGHT)
            wear('CoatSplit',torso,(0,-.71,-.51),(.055,1.4,.035),TEAL)
            wear('MedicalMask',head,(0,-.22,-.6),(.91,.42,.15),(166,202,195))
            wear('TiedHair',head,(0,.43,.15),(1.23,.41,1.13),(75,54,47))
            wear('HairBun',head,(0,.15,.69),(.52,.55,.4),(75,54,47),0)
            wear('Clipboard',parts['Left Arm'],(0,-.63,-.49),(.79,1.1,.09),TEAL)
            wear('Glove',parts['Right Arm'],(0,-.89,0),(.73,.39,.83),LIGHT)
        elif staff_id=='OPERATOR':
            wear('ShortHair',head,(0,.48,.05),(1.25,.37,1.16),(49,37,34))
            wear('HeadsetBand',head,(0,.62,0),(1.41,.11,.57),DARK)
            for dx in (-.7,.7):wear('HeadsetCup',head,(dx,.06,.02),(.2,.53,.47),DARK)
            wear('Microphone',head,(.39,-.3,-.65),(.48,.1,.12),METAL)
            wear('OperatorJacket',torso,(0,0,.03),(1.91,2.13,.99),(65,82,113))
            wear('SleeveStripe',parts['Left Arm'],(0,.12,-.43),(.72,.31,.06),CYAN)
            wear('WristConsole',parts['Right Arm'],(0,-.72,-.44),(.51,.51,.11),CYAN)
        elif staff_id=='ENGINEER':
            wear('SafetyHelmet',head,(0,.53,0),(1.5,.38,1.41),AMBER)
            wear('HelmetBrim',head,(0,.32,-.13),(1.65,.1,1.65),AMBER)
            wear('HelmetStripe',head,(0,.75,0),(.24,.07,1.26),LIGHT)
            wear('HighVisibilityVest',torso,(0,.04,-.03),(1.94,1.93,1.04),(142,125,63))
            for dx in (-.57,.57):wear('VestReflector',torso,(dx,.02,-.57),(.12,1.75,.045),LIGHT)
            wear('ToolBelt',torso,(0,-.78,0),(1.97,.21,1.07),DARK)
            wear('WrenchHandle',parts['Right Arm'],(0,-1.14,-.12),(.17,.86,.18),METAL)
            wear('WrenchHead',parts['Right Arm'],(0,-1.57,-.12),(.46,.23,.24),METAL)
            wear('Glove',parts['Left Arm'],(0,-.89,0),(.73,.39,.83),BLACK)
        elif staff_id=='SECURITY':
            wear('SecurityCap',head,(0,.48,.02),(1.38,.32,1.3),DARK)
            wear('CapVisor',head,(0,.34,-.63),(1.28,.07,.63),DARK)
            wear('ArmoredVest',torso,(0,.06,-.01),(2.16,1.86,1.15),(42,51,57))
            for dx in (-.64,.64):wear('VestPouch',torso,(dx,-.41,-.67),(.44,.57,.23),BLACK)
            wear('SafetyRadio',torso,(-.64,.6,-.68),(.34,.58,.25),DARK)
            wear('ShoulderMark',parts['Left Arm'],(0,.62,-.44),(.63,.39,.05),AMBER)
        else:
            wear('SilverHair',head,(0,.51,.08),(1.3,.37,1.13),(151,151,141))
            for dx in (-.31,.31):
                wear('GlassesRim',head,(dx,.12,-.61),(.52,.3,.09),DARK)
                wear('GlassesLens',head,(dx,.12,-.67),(.39,.2,.035),(139,174,179))
            wear('GlassesBridge',head,(0,.12,-.64),(.13,.06,.06),DARK)
            wear('ArchiveCoat',torso,(0,-.22,.025),(1.78,2.58,1.0),(112,119,119))
            wear('DocumentFolder',parts['Left Arm'],(0,-.56,-.49),(.96,1.21,.12),(167,154,119))
            wear('ArchiveKeys',torso,(.65,-.7,-.56),(.27,.5,.11),METAL)

        # Keep badges outside coats and vests, rather than buried in a new skin.
        for badge in model.findall('Item'):
            if name(badge)=='StaffBadge':
                badge.find("Properties/CoordinateFrame[@name='CFrame']/Z").text=str(z-.65)

        if not existing:
            config=b.item(head,'Folder','V10_Interact');b.note(config,'Action','npc');b.note(config,'Argument',staff_id)
            prompt=b.item(head,'ProximityPrompt','V10_Prompt')
            for key,value in [('ActionText','Поговорить'),('ObjectText',data['name']+' / '+data['role'])]:b.prop(prompt,'string',key,value)
            b.prop(prompt,'float','HoldDuration',.25);b.prop(prompt,'float','MaxActivationDistance',9)
            b.prop(prompt,'bool','RequiresLineOfSight',True);b.prop(prompt,'bool','Enabled',True)
            b.prop(prompt,'token','KeyboardKeyCode',101)
        marker=b.item(model,'Folder','V11_NPC')
        b.note(marker,'Id',staff_id);b.note(marker,'WorkMode',data['mode'])
        vector(marker,'Vector3Value','Home',data['home'])
        vector(marker,'Vector3Value','WorkTarget',data['work'])
        height=b.item(marker,'NumberValue','RootHeight');b.prop(height,'double','Value',3.35)
        route=b.item(marker,'Folder','Route')
        for i,point in enumerate(data['route'],1):vector(route,'Vector3Value',f'Point_{i:02d}',point)
        result['rigs'].append({'id':staff_id,'model':model.get('referent'),'root':root_part.get('referent'),
                               'humanoid':humanoid.get('referent'),'animator':animator.get('referent'),
                               'orientation':facing.get('referent'),'aim_attachment':aim.get('referent'),
                               'body_parts':{k:v.get('referent') for k,v in parts.items()},'motors':joints,
                               'home':data['home'],'route':data['route'],'work_target':data['work'],
                               'appearance':data['role'],'existing_model_retained':existing})
    current={e.get('referent'):e for e in root.iter('Item')}
    result['modified_refs']=sorted(ref for ref,old in before.items() if ref in current
                                   and ET.tostring(current[ref].find('Properties'))!=old)
    result['new_refs']=sorted(set(current)-initial_refs)
    result['movable_refs']=sorted(set(result['movable_refs']))
    return result
