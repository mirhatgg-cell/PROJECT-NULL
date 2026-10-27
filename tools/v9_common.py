"""V9 authoring: explicit physical roles, hollow equipment and service metadata."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from v7_common import Builder, name, WHITE, METAL, DARK, BLACK, LIGHT, CYAN, BLUE, AMBER, RED, TEAL

SOLID_ROLES = {'structure','housing','panel','walkable'}


def setprop(item, tag, key, value):
    props=item.find('Properties')
    for old in list(props):
        if old.get('name')==key: props.remove(old)
    node=ET.SubElement(props,tag,{'name':key})
    node.text=str(value).lower() if isinstance(value,bool) else str(value)
    return node


class Builder9(Builder):
    def __init__(self, root):
        super().__init__(root)
        self.roles={}
        self.services=[]
        self.removed=[]
        self.cavities=[]

    def cavity(self,model,center,size,thickness=.12,front='Z-',matrix=None):
        record={'model':model.get('referent'),'center':tuple(center),'size':tuple(size),
                'thickness':thickness,'front':front}
        if matrix is not None: record['matrix']=matrix
        self.cavities.append(record)
        return record

    def role(self, part, role):
        assert role in SOLID_ROLES|{'detail','internal','control'}
        solid=role in SOLID_ROLES
        setprop(part,'bool','CanCollide',solid)
        setprop(part,'bool','CanQuery',solid or role=='control')
        setprop(part,'bool','CanTouch',False)
        if solid: setprop(part,'bool','CastShadow',True)
        self.roles[part.get('referent')]=role
        return part

    def part(self,*args,role='detail',**kwargs):
        return self.role(super().part(*args,**kwargs),role)

    def segment(self,*args,role='detail',**kwargs):
        return self.role(super().segment(*args,**kwargs),role)

    def find(self, label, under=None, cls=None):
        return next((e for e in (under if under is not None else self.root).iter('Item')
                     if name(e)==label and (cls is None or e.get('class')==cls)),None)

    def remove(self, item):
        if item is None: return
        for parent in self.root.iter():
            if item in list(parent):
                self.removed.append({'referent':item.get('referent'),'name':name(item),
                                     'descendants':sum(1 for _ in item.iter('Item'))})
                parent.remove(item)
                return
        raise ValueError(f'Item not attached: {name(item)}')

    def remove_named(self, parent, labels):
        for item in list(parent.findall('Item')):
            if name(item) in labels: self.remove(item)

    def service(self, panel, pivot, axis='Y', angle=100, label='Сервисная панель', moving=None):
        """Register a hinge. World-space pivot, world X/Y/Z axis, signed degrees.

        Include attached handles/faceplates in moving. Panel is always included.
        The server runtime discovers V9_Service folders and their ObjectValues.
        """
        assert axis in ('X','Y','Z') and 0<abs(angle)<=150
        self.role(panel,'panel')
        config=self.item(panel,'Folder','V9_Service')
        pivot_value=self.item(config,'Vector3Value','Pivot')
        vec=self.prop(pivot_value,'Vector3','Value')
        for key,value in zip('XYZ',pivot): ET.SubElement(vec,key).text=str(value)
        self.note(config,'Axis',axis)
        number=self.item(config,'NumberValue','OpenAngle');self.prop(number,'double','Value',angle)
        number=self.item(config,'NumberValue','CurrentAngle');self.prop(number,'double','Value',0)
        marker=self.item(config,'BoolValue','IsOpen');self.prop(marker,'bool','Value',False)
        movers=[panel]+[p for p in (moving or []) if p is not panel]
        for i,part in enumerate(movers,1):
            target=self.item(config,'ObjectValue',f'Moving_{i}')
            self.prop(target,'Ref','Value',part.get('referent'))
        prompt=self.item(panel,'ProximityPrompt','V9_ServicePrompt')
        for key,value in [('ActionText','Открыть'),('ObjectText',label)]:self.prop(prompt,'string',key,value)
        self.prop(prompt,'float','HoldDuration',.25)
        self.prop(prompt,'float','MaxActivationDistance',9)
        self.prop(prompt,'bool','RequiresLineOfSight',True)
        self.prop(prompt,'bool','Enabled',True)
        self.services.append({'panel':panel.get('referent'),'pivot':tuple(pivot),'axis':axis,'angle':angle,
                              'moving':[p.get('referent') for p in movers],'label':label})
        return config

    def slide(self,panel,delta,label='Выдвижной ящик',moving=None):
        frame=panel.find("Properties/CoordinateFrame[@name='CFrame']")
        pivot=tuple(float(frame.findtext(k)) for k in 'XYZ')
        config=self.service(panel,pivot,axis='X',angle=1,label=label,moving=moving)
        axis_value=next(e for e in config.findall('Item') if name(e)=='Axis')
        setprop(axis_value,'string','Value','Slide')
        value=self.item(config,'Vector3Value','Slide')
        vec=self.prop(value,'Vector3','Value')
        for key,v in zip('XYZ',delta): ET.SubElement(vec,key).text=str(v)
        self.services[-1]['axis']='Slide';self.services[-1]['delta']=tuple(delta)
        return config

    def shell(self,parent,label,center,size,color=WHITE,thickness=.12,front='Z-',service=True,angle=100):
        """Axis-aligned six-face collidable case. Front becomes hinged door.

        Returns (model, panel, faces). Use explicit thin panels for rotated cases.
        front supports X-/X+/Z-/Z+. Hinge is left edge viewed from outside.
        """
        assert front in ('X-','X+','Z-','Z+')
        model=self.model(parent,label)
        self.cavity(model,center,size,thickness,front)
        x,y,z=center;sx,sy,sz=size;t=thickness
        faces={}
        specs={
            'X-':((x-sx/2+t/2,y,z),(t,sy,sz)),
            'X+':((x+sx/2-t/2,y,z),(t,sy,sz)),
            'Y-':((x,y-sy/2+t/2,z),(sx-2*t,t,sz-2*t)),
            'Y+':((x,y+sy/2-t/2,z),(sx-2*t,t,sz-2*t)),
            'Z-':((x,y,z-sz/2+t/2),(sx-2*t,sy,t)),
            'Z+':((x,y,z+sz/2-t/2),(sx-2*t,sy,t)),
        }
        for face,(pos,extent) in specs.items():
            faces[face]=self.part(model,'V9_ServiceDoor' if face==front else 'Shell_'+face,pos,extent,color,1088,role='panel' if face==front else 'housing')
        door=faces[front]
        if service:
            if front=='Z-':pivot=(x-sx/2+t,y,z-sz/2+t/2)
            elif front=='Z+':pivot=(x+sx/2-t,y,z+sz/2-t/2)
            elif front=='X-':pivot=(x-sx/2+t/2,y,z+sz/2-t)
            else:pivot=(x+sx/2-t/2,y,z-sz/2+t)
            self.service(door,pivot,angle=angle,label=label)
        return model,door,faces
