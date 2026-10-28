"""Check actual R6 XML and execute the actual NPC director against API doubles.

The doubles provide math, events and a controlled navigation service; they do
not simulate Roblox humanoid physics, replication or visual animation quality.
"""
from __future__ import annotations

import math
from pathlib import Path
import xml.etree.ElementTree as ET

from lupa import LuaRuntime

from v7_common import name
from v9_common import Builder9
from v11_npcs import build, BODY

ROOT=Path(__file__).resolve().parents[1]
_AUTHORED=None

EXTENSION=r'''
local cm={}
function cm.__index(c,k)
 if k=='Position' then return c.p end
 return cm[k]
end
local function rotate(r,p)
 return Vector3.new(r[1]*p.X+r[2]*p.Y+r[3]*p.Z,r[4]*p.X+r[5]*p.Y+r[6]*p.Z,r[7]*p.X+r[8]*p.Y+r[9]*p.Z)
end
function cm.__mul(a,b)
 local r={}
 for i=0,2 do for j=0,2 do
  r[i*3+j+1]=0
  for k=0,2 do r[i*3+j+1]=r[i*3+j+1]+a.r[i*3+k+1]*b.r[k*3+j+1] end
 end end
 return setmetatable({p=a.p+rotate(a.r,b.p),r=r},cm)
end
function cm:VectorToObjectSpace(p)
 return rotate({self.r[1],self.r[4],self.r[7],self.r[2],self.r[5],self.r[8],self.r[3],self.r[6],self.r[9]},p)
end
function cm:Lerp(other,alpha)
 local r={};for i=1,9 do r[i]=self.r[i]+(other.r[i]-self.r[i])*alpha end
 return setmetatable({p=self.p+(other.p-self.p)*alpha,r=r},cm)
end
CFrame={new=function(x,y,z)
 local p=type(x)=='table' and x or Vector3.new(x or 0,y or 0,z or 0)
 return setmetatable({p=p,r={1,0,0,0,1,0,0,0,1}},cm)
end}
function _frame(x,y,z,...)
 return setmetatable({p=Vector3.new(x,y,z),r={...}},cm)
end
function CFrame.Angles(x,y,z)
 local cx,sx,cy,sy,cz,sz=math.cos(x),math.sin(x),math.cos(y),math.sin(y),math.cos(z),math.sin(z)
 return _frame(0,0,0,1,0,0,0,cx,-sx,0,sx,cx)*_frame(0,0,0,cy,0,sy,0,1,0,-sy,0,cy)*_frame(0,0,0,cz,-sz,0,sz,cz,0,0,0,1)
end
Enum.PathStatus={Success=1,NoPath=2}
_pathCalls=0;_pathDelay=0;_pathFailure=false;_pathNoRoute=false;_paths={}
_services.PathfindingService={CreatePath=function(_,options)
 assert(options.AgentCanJump==false and options.AgentRadius>=1,'Unsafe humanoid path parameters')
 _pathCalls=_pathCalls+1
 local path={Status=_pathNoRoute and Enum.PathStatus.NoPath or Enum.PathStatus.Success,
             Blocked=Instance.new('Folder').Triggered}
 function path:ComputeAsync(start,finish)
  if _pathDelay>0 then task.wait(_pathDelay) end
  if _pathFailure then error('Fixture path service rejected') end
  self.start=start;self.finish=finish
 end
 function path:GetWaypoints()
  return {{Position=self.start},{Position=self.finish}}
 end
 table.insert(_paths,path)
 return path
end}
_npcModels={}
function _configureRig(model)
 local root=model.HumanoidRootPart
 root.AssemblyLinearVelocity=Vector3.zero
 root.SetNetworkOwner=function(self,owner) self.ownerWasSet=true;self.networkOwner=owner end
 local humanoid=model.Humanoid
 humanoid.MoveToFinished=Instance.new('Folder').Triggered
 humanoid.MoveTo=function(self,point) self.moveTarget=point;self.moves=(self.moves or 0)+1 end
end
function _tick(seconds,phase)
 local remaining=seconds
 while remaining>.00001 do
  local step=math.min(.1,remaining);remaining=remaining-step
  _clock=_clock+step
  _director:step(step,{phase=phase or 'idle'})
  flush_tasks()
 end
end
'''


def authored():
    global _AUTHORED
    if _AUTHORED is not None:return _AUTHORED
    root=ET.parse(ROOT/'artifacts/PROJECT_NULL_GAMEPLAY_V10.rbxlx').getroot()
    before={e.get('referent'):ET.tostring(e) for e in root.iter('Item')
            if name(e) in ('Staff_TECH','Staff_MEDIC','Head')}
    builder=Builder9(root)
    facility=builder.find('PROJECT_NULL_ARCH_P01',cls='Model')
    parent=builder.model(facility,'Crew_Test_V11')
    metadata=build(builder,parent,root)
    indexed={e.get('referent'):e for e in root.iter('Item')}
    _AUTHORED=(root,before,metadata,indexed)
    return _AUTHORED


def matrix(item,key='CFrame'):
    frame=item.find(f"Properties/CoordinateFrame[@name='{key}']")
    return ([float(frame.findtext(k)) for k in 'XYZ'],
            [[float(frame.findtext(f'R{i}{j}')) for j in range(3)] for i in range(3)])


def product(a,b):
    p,r=a;q,s=b
    return ([p[i]+sum(r[i][j]*q[j] for j in range(3)) for i in range(3)],
            [[sum(r[i][k]*s[k][j] for k in range(3)) for j in range(3)] for i in range(3)])


def flat(matrix):
    p,r=matrix
    return p+sum(r,[])


def frame_error(a,b):
    return max(abs(a.Position.X-b.Position.X),abs(a.Position.Y-b.Position.Y),
               abs(a.Position.Z-b.Position.Z),
               *(abs(a.r[i]-b.r[i]) for i in range(1,10)))


def static_checks():
    root,before,meta,idx=authored()
    assert len(meta['rigs'])==6
    assert len(meta['removed_refs'])==12
    assert all(idx[ref].findtext("Properties/bool[@name='Anchored']")=='false' for ref in meta['movable_refs'])
    for e in root.iter('Item'):
        keys=[p.get('name') for p in e.find('Properties')]
        assert len(keys)==len(set(keys)),('Duplicate properties',name(e))
    identities=set()
    for rig in meta['rigs']:
        model=idx[rig['model']]
        parts=rig['body_parts']
        assert set(parts)==set(BODY)
        assert len(rig['motors'])==6
        assert idx[rig['animator']].get('class')=='Animator'
        humanoid=idx[rig['humanoid']]
        assert idx[rig['animator']] in humanoid.findall('Item')
        assert humanoid.findtext("Properties/token[@name='RigType']")=='0'
        assert float(humanoid.findtext("Properties/float[@name='WalkSpeed']"))>0
        assert humanoid.findtext("Properties/bool[@name='RequiresNeck']")=='true'
        assert idx[rig['orientation']].get('class')=='AlignOrientation'
        assert idx[rig['orientation']].findtext("Properties/Ref[@name='Attachment0']")==rig['aim_attachment']
        assert idx[rig['orientation']].findtext("Properties/token[@name='Mode']")=='0'
        assert idx[rig['root']].findtext("Properties/bool[@name='CanCollide']")=='false'
        assert idx[parts['Head']].findtext("Properties/bool[@name='CanQuery']")=='true'
        graph={p.get('referent'):set() for p in model.iter('Item') if p.get('class')=='Part'}
        for joint in model.iter('Item'):
            if joint.get('class') not in ('Motor6D','WeldConstraint'):continue
            a=joint.findtext("Properties/Ref[@name='Part0']");c=joint.findtext("Properties/Ref[@name='Part1']")
            assert a in graph and c in graph
            graph[a].add(c);graph[c].add(a)
            if joint.get('class')=='Motor6D':
                left=flat(product(matrix(idx[a]),matrix(joint,'C0')))
                right=flat(product(matrix(idx[c]),matrix(joint,'C1')))
                assert max(abs(x-y) for x,y in zip(left,right))<1e-7,('Joint would snap at load',rig['id'],name(joint))
        visited=set();pending=[rig['root']]
        while pending:
            ref=pending.pop()
            if ref in visited:continue
            visited.add(ref);pending.extend(graph[ref]-visited)
        assert visited==set(graph),('Unconnected NPC wardrobe/body',rig['id'])
        for ref in graph:
            assert ref in meta['movable_refs']
            assert idx[ref].findtext("Properties/bool[@name='Anchored']")=='false'
            if ref not in parts.values():
                assert idx[ref].findtext("Properties/bool[@name='Massless']")=='true'
                assert idx[ref].findtext("Properties/bool[@name='CanCollide']")=='false'
        actions=[e for e in model.iter('Item') if name(e)=='V10_Interact']
        assert len(actions)==1
        argument=next(e for e in actions[0].findall('Item') if name(e)=='Argument')
        assert argument.findtext("Properties/string[@name='Value']")==rig['id']
        identities.add(tuple(sorted(name(e) for e in model.findall('Item') if e.get('class')=='Part')))
        if rig['id'] in ('TECH','MEDIC'):
            assert rig['model'] in before and parts['Head'] in before
            old=ET.fromstring(before[parts['Head']])
            for child in old.findall('Item'):
                assert ET.tostring(child)==ET.tostring(next(e for e in idx[parts['Head']].findall('Item') if e.get('referent')==child.get('referent')))
    assert len(identities)==6,'Skins must have different actual silhouettes/accessories'
    assert not list(root.iter('AnimationId'))
    print('PASS: six connected R6 rigs, exact rest joints, Animator, physical bodies, distinct local skins and retained old head prompts')
    return root,meta,idx


def fixture():
    _,_,meta,idx=authored()
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.execute((ROOT/'tools/v10_runtime_mock.lua').read_text())
    lua.execute(EXTENSION)
    deferred=[];objects={}
    def create(e,parent):
        obj=lua.globals()._new(e.get('class'),parent,name(e));objects[e.get('referent')]=obj
        for p in e.find('Properties'):
            key=p.get('name')
            if key=='Name':continue
            if p.tag=='CoordinateFrame':
                xyz=[float(p.findtext(k)) for k in 'XYZ']
                r=[float(p.findtext(f'R{i}{j}')) for i in range(3) for j in range(3)]
                obj[key]=lua.globals()._frame(*(xyz+r))
            elif p.tag=='Vector3':
                obj['Size' if key=='size' else key]=lua.globals().Vector3.new(*(float(p.findtext(k)) for k in 'XYZ'))
            elif p.tag=='bool':obj[key]=p.text=='true'
            elif p.tag in ('float','double','int','token'):obj[key]=float(p.text)
            elif p.tag=='string':obj[key]=p.text or ''
            elif p.tag=='Ref':deferred.append((obj,key,p.text))
        for child in e.findall('Item'):create(child,obj)
        return obj
    for rig in meta['rigs']:
        obj=create(idx[rig['model']],lua.globals()._world)
        lua.globals()._npcModels[rig['id']]=obj
        lua.globals()._configureRig(obj)
    for obj,key,ref in deferred:
        if ref in objects:obj[key]=objects[ref]
    module=lua.execute((ROOT/'src/NPCDirector_V11.luau').read_text())
    director=module.new(lua.globals()._facility)
    lua.globals()._director=director
    # Keep a single rig eligible for navigation in the focused route scenarios.
    for i in range(1,len(director.rigs)+1):director.rigs[i].nextWalk=9999
    return lua,director


def run_checks():
    lua,director=fixture();g=lua.globals();tech=director.byId['TECH']
    assert len(director.rigs)==6
    assert all(director.rigs[i].root.ownerWasSet for i in range(1,7))
    original=tech.joints['Right Shoulder'].C0
    g._tick(1,'idle')
    assert frame_error(tech.joints['Right Shoulder'].C0,original)>1e-4
    assert tech.state=='inspecting' and director.byId['ENGINEER'].state=='repairing'
    assert director.byId['ARCHIVIST'].state=='reading' and director.byId['OPERATOR'].state=='working'
    print('PASS: actual director creates one scheduler state and role-specific replicated joint poses')

    for staff_id in ('ENGINEER','OPERATOR'):
        worker=director.byId[staff_id];original=worker.root.CFrame
        worker.root.CFrame=g.CFrame.new(worker.home.X+10,worker.home.Y+worker.rootHeight,worker.home.Z)
        g._tick(.2,'idle');assert worker.state=='waiting'
        worker.root.CFrame=original
        g._tick(.2,'idle')
        assert worker.state==('repairing' if staff_id=='ENGINEER' else 'working')
    print('PASS: fixed-station work poses stop away from equipment and resume after physical return')

    head=g._player.Character.Head
    head.CFrame=g.CFrame.new(tech.root.Position.X,tech.root.Position.Y+1,tech.root.Position.Z-4)
    assert director.talk(director,'TECH',g._player,True)
    g._tick(.2,'idle');assert tech.state=='talking'
    assert tech.facing.Enabled and tech.facing.CFrame is not None
    assert not director.talk(director,'TECH',None,True)
    assert not director.talk(director,'TECH',None,False)
    assert not director.talk(director,'MISSING',g._player,True)
    head.CFrame=g.CFrame.new(500,0,0)
    assert not director.talk(director,'TECH',g._player,True)
    g._tick(.2,'failed');assert tech.state=='alert'
    director.talk(director,'TECH',g._player,False)
    print('PASS: live/near conversation guards, player attention, close and actual alarm pose switching')

    lua,director=fixture();g=lua.globals();tech=director.byId['TECH'];tech.nextWalk=0
    position=tech.root.Position
    g._tick(.2,'idle');assert tech.walking and g._pathCalls==1
    assert not tech.facing.Enabled
    assert tech.humanoid.AutoRotate and tech.humanoid.moveTarget is not None
    tech.root.CFrame=g.CFrame.new(tech.humanoid.moveTarget)
    tech.root.AssemblyLinearVelocity=g.Vector3.new(4,0,0)
    g._tick(.2,'idle')
    assert tech.state=='walking'
    tech.humanoid.MoveToFinished.Fire(tech.humanoid.MoveToFinished,True)
    assert not tech.walking and tech.state=='working'
    assert abs(tech.root.Position.X-position.X)>1
    print('PASS: actual bounded PathfindingService request, Humanoid MoveTo, walk pose and reached-waypoint return')

    lua,director=fixture();g=lua.globals();tech=director.byId['TECH'];tech.nextWalk=0
    original=tech.root.CFrame
    g._tick(.2,'idle');assert tech.walking
    g._paths[1].Blocked.Fire(g._paths[1].Blocked,2)
    assert not tech.walking and tech.blockedUntil>director.elapsed
    g._tick(2,'idle');assert g._pathCalls==1
    assert frame_error(tech.root.CFrame,original)<1e-9
    print('PASS: blocked path stops physical movement without teleporting or retry storm')

    lua,director=fixture();g=lua.globals();tech=director.byId['TECH'];tech.nextWalk=0
    original=tech.root.CFrame
    g._tick(3.5,'idle');assert not tech.walking
    assert frame_error(tech.root.CFrame,original)<1e-9 and g._pathCalls==1
    lua,director=fixture();g=lua.globals();tech=director.byId['TECH'];tech.nextWalk=0;g._pathNoRoute=True
    g._tick(2,'idle');assert not tech.walking and g._pathCalls==1
    g._tick(11,'idle');assert g._pathCalls<=2
    print('PASS: stuck/no-route detection and bounded retry cooldown')

    lua,director=fixture();g=lua.globals();g._pathDelay=2
    for i in range(1,7):director.rigs[i].nextWalk=0
    g._tick(.1,'idle');assert director.pathRequests==2 and g._pathCalls==2
    director.destroy(director)
    g._clock=g._clock+3;g.flush_tasks()
    assert director.pathRequests==0 and not any(director.rigs[i].walking for i in range(1,7))
    original=director.elapsed
    director.step(director,10,lua.table_from({'phase':'idle'}))
    assert director.elapsed==original
    print('PASS: global maximum two pending paths and safe teardown while asynchronous computation returns')

    lua,director=fixture();g=lua.globals();tech=director.byId['TECH']
    original=tech.originals['Neck']
    g._tick(.5,'idle');assert frame_error(tech.joints['Neck'].C0,original)>1e-4
    director.destroy(director);assert frame_error(tech.joints['Neck'].C0,original)<1e-9
    assert not tech.facing.Enabled
    director.destroy(director)
    for value in (float('nan'),float('inf'),-.5):director.step(director,value,lua.table_from({}))
    assert not list(g._taskErrors.values())
    print('PASS: rest-pose restoration, idempotent cleanup and invalid-time handling')


def main():
    static_checks()
    run_checks()
    print('V11 NPC checks: PASS; real Roblox character physics, pathfinding mesh and appearance remain Studio acceptance tests.')


if __name__=='__main__':main()
