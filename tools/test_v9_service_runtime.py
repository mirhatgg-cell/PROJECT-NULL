"""Execute the actual V9 service script against focused Lua/Roblox API mocks.

Requires lupa==2.6. This exercises server logic, not Roblox physics or rendering.
"""
from pathlib import Path

from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
MOCK = r'''
local function signal()
 local s={callbacks={}}
 function s:Connect(f) table.insert(self.callbacks,f);return {Disconnect=function() end} end
 function s:Fire(...) for _,f in ipairs(self.callbacks) do f(...) end end
 return s
end
local vm={}
function vm.__index(v,k)
 if k=='Magnitude' then return math.sqrt(v.X*v.X+v.Y*v.Y+v.Z*v.Z) end
end
function vm.__add(a,b) return Vector3.new(a.X+b.X,a.Y+b.Y,a.Z+b.Z) end
function vm.__sub(a,b) return Vector3.new(a.X-b.X,a.Y-b.Y,a.Z-b.Z) end
function vm.__mul(a,b)
 if type(a)=='number' then return Vector3.new(a*b.X,a*b.Y,a*b.Z) end
 return Vector3.new(a.X*b,a.Y*b,a.Z*b)
end
Vector3={new=function(x,y,z) return setmetatable({X=x,Y=y,Z=z},vm) end}
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
function cm:Inverse()
 local r={self.r[1],self.r[4],self.r[7],self.r[2],self.r[5],self.r[8],self.r[3],self.r[6],self.r[9]}
 return setmetatable({p=rotate(r,self.p)*-1,r=r},cm)
end
CFrame={new=function(x,y,z)
 local p=type(x)=='table' and x or Vector3.new(x or 0,y or 0,z or 0)
 return setmetatable({p=p,r={1,0,0,0,1,0,0,0,1}},cm)
end}
function CFrame.fromAxisAngle(axis,theta)
 local x,y,z=axis.X,axis.Y,axis.Z;local c,s=math.cos(theta),math.sin(theta);local t=1-c
 return setmetatable({p=Vector3.new(0,0,0),r={t*x*x+c,t*x*y-s*z,t*x*z+s*y,t*x*y+s*z,t*y*y+c,t*y*z-s*x,t*x*z-s*y,t*y*z+s*x,t*z*z+c}},cm)
end
Color3={fromRGB=function(r,g,b) return {R=r/255,G=g/255,B=b/255} end}
Enum={RaycastFilterType={Exclude=0}}
RaycastParams={new=function() return {} end};OverlapParams={new=function() return {} end}
local methods={};local meta={}
function meta.__index(o,k)
 if methods[k] then return methods[k] end
 if k=='ClassName' then return rawget(o,'_class') end
 if k=='Position' and o._props.CFrame then return o._props.CFrame.Position end
 return o._props[k]
end
function meta.__newindex(o,k,v)
 if k=='Parent' then
  local old=o._props.Parent
  if old then for i,c in ipairs(old._children) do if c==o then table.remove(old._children,i);break end end end
  if v then table.insert(v._children,o) end
 end
 if k=='CanCollide' then _collisionWrites=_collisionWrites+1 end
 o._props[k]=v
 if k=='Value' and o._props.Changed then o._props.Changed:Fire(v) end
end
Instance={new=function(cls,parent)
 local o=setmetatable({_class=cls,_children={},_props={Name=cls,Changed=signal(),Triggered=signal(),DescendantAdded=signal()}},meta)
 if cls=='Part' then o.Size=Vector3.new(2,4,.12);o.CFrame=CFrame.new();o.CanCollide=true end
 if parent then o.Parent=parent end
 return o
end}
function methods:IsA(cls) return cls==self.ClassName or cls=='Instance' or (cls=='BasePart' and self.ClassName=='Part') end
function methods:GetChildren() return self._children end
function methods:GetDescendants()
 local out={};local function visit(p) for _,c in ipairs(p._children) do table.insert(out,c);visit(c) end end
 visit(self);return out
end
function methods:FindFirstChild(n)
 for _,c in ipairs(self._children) do if c.Name==n then return c end end
end
function methods:WaitForChild(n) return self:FindFirstChild(n) end
function methods:FindFirstChildOfClass(cls)
 for _,c in ipairs(self._children) do if c:IsA(cls) then return c end end
end
function methods:IsDescendantOf(parent)
 local p=self.Parent;while p do if p==parent then return true end;p=p.Parent end;return false
end
function methods:GetFullName() return self.Parent and self.Parent:GetFullName()..'.'..self.Name or self.Name end
function methods:Raycast(origin,direction,params)
 _rayCalls=_rayCalls+1
 if _rayTarget then return {Instance=_rayTarget} end
 return nil
end
function methods:GetPartBoundsInBox(frame,size,params)
 _queryCalls=_queryCalls+1
 assert(size.X>.15 and size.Y>.15 and size.Z>.15,'Missing occupancy margin')
 if _blockAt and _queryCalls>=_blockAt then return {_blocker} end
 return {}
end
game={GetService=function(_,n) assert(n=='RunService');return {IsServer=function() return true end} end}
task={wait=function()
 _waits=_waits+1
 if _waitHook then _waitHook() end
end,defer=function(f) f() end}
warn=function(message) table.insert(_warnings,message) end
_warnings={};_queryCalls=0;_rayCalls=0;_waits=0;_collisionWrites=0
local function new(cls,parent,name,value)
 local o=Instance.new(cls,parent);o.Name=name
 if value~=nil then o.Value=value end
 return o
end
workspace=new('Workspace',nil,'Workspace')
_facility=new('Model',workspace,'PROJECT_NULL_ARCH_P01')
_equipment=new('Model',_facility,'Equipment')
local controls=new('Folder',_facility,'Controls');local circuits=new('Folder',controls,'Circuits')
_amplifier=new('BoolValue',circuits,'AcousticAmplifiers',true)
_character=new('Model',workspace,'Character');_head=new('Part',_character,'Head');_head.CFrame=CFrame.new(3,0,-4)
_humanoid=new('Humanoid',_character,'Humanoid');_humanoid.Health=100
_player=new('Player',nil,'Player');_player.Character=_character
local blockerModel=new('Model',workspace,'OtherPlayer');new('Humanoid',blockerModel,'Humanoid').Health=100
_blocker=new('Part',blockerModel,'HumanoidRootPart')
_wall=new('Part',_equipment,'OpaqueWall')
function fixture_service(name,position,axis,angle,slide)
 local panel=new('Part',_equipment,name);panel.CFrame=CFrame.new(position)
 local handle=new('Part',_equipment,name..'_Handle');handle.CFrame=CFrame.new(position+Vector3.new(0,0,-.15));handle.Size=Vector3.new(.1,.4,.2)
 local prompt=new('ProximityPrompt',panel,'V9_ServicePrompt');prompt.Enabled=true;prompt.MaxActivationDistance=9
 local config=new('Folder',panel,'V9_Service')
 new('Vector3Value',config,'Pivot',Vector3.new(0,0,0));new('StringValue',config,'Axis',axis)
 new('NumberValue',config,'OpenAngle',angle);new('NumberValue',config,'CurrentAngle',0);new('BoolValue',config,'IsOpen',false)
 new('ObjectValue',config,'Moving_1',panel);new('ObjectValue',config,'Moving_2',handle)
 if slide then new('Vector3Value',config,'Slide',slide) end
 return panel,prompt,config,handle
end
_hinge,_hingePrompt,_hingeConfig,_hingeHandle=fixture_service('Door',Vector3.new(3,0,0),'Y',90)
_slide,_slidePrompt,_slideConfig=fixture_service('Drawer',Vector3.new(10,0,0),'Slide',1,Vector3.new(0,2,0))
_stop=new('Part',_equipment,'EmergencyStop');_stop.CFrame=CFrame.new(20,0,0)
_stopPrompt=new('ProximityPrompt',_stop,'V9_EStopPrompt');_stopPrompt.Enabled=true;_stopPrompt.MaxActivationDistance=9
_indicator=new('Part',_equipment,'Indicator');_text=new('TextLabel',_equipment,'StatusText')
local status=new('Folder',_equipment,'V9_CircuitStatus')
new('ObjectValue',status,'Circuit',_amplifier);new('ObjectValue',status,'Indicator',_indicator);new('ObjectValue',status,'Text',_text);new('StringValue',status,'Caption','ACOUSTIC POWER')
_collisionWrites=0
'''


def close(value, wanted, tolerance=1e-7):
    assert abs(value-wanted)<tolerance,(value,wanted)


def fixture(preload=None):
    lua=LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK)
    if preload: lua.execute(preload)
    lua.execute((ROOT/'src/ServiceController_V9.server.luau').read_text())
    return lua


def main():
    lua=fixture();g=lua.globals()
    assert 'ВКЛЮЧЕНО' in g._text.Text
    lua.execute('_rayTarget=_hinge;_hingePrompt.Triggered:Fire(_player)')
    close(g._hinge.Position.X,0);close(g._hinge.Position.Z,-3)
    assert g._hingeConfig.FindFirstChild(g._hingeConfig,'IsOpen').Value
    assert g._hingePrompt.Enabled and g._collisionWrites==0
    assert g._waits==30 and g._queryCalls==60
    lua.execute('_head.CFrame=CFrame.new(0,0,-7);_rayTarget=_hingeHandle;_hingePrompt.Triggered:Fire(_player)')
    close(g._hinge.Position.X,3);close(g._hinge.Position.Z,0)
    assert not g._hingeConfig.FindFirstChild(g._hingeConfig,'IsOpen').Value

    # Partial obstruction reverses on next trigger and retains actual progress.
    lua=fixture();g=lua.globals()
    lua.execute('_rayTarget=_hinge;_blockAt=17;_hingePrompt.Triggered:Fire(_player)')
    angle=g._hingeConfig.FindFirstChild(g._hingeConfig,'CurrentAngle').Value
    assert 0<angle<90 and 'Закрыть' in g._hingePrompt.ActionText
    assert not g._hingeConfig.FindFirstChild(g._hingeConfig,'IsOpen').Value
    assert g._hingePrompt.Enabled and g._collisionWrites==0
    lua.execute('_blockAt=nil;_queryCalls=0;_hingePrompt.Triggered:Fire(_player)')
    close(g._hingeConfig.FindFirstChild(g._hingeConfig,'CurrentAngle').Value,0)
    close(g._hinge.Position.X,3)

    # Sliding equipment uses the same server checks and collision guard.
    lua=fixture();g=lua.globals()
    lua.execute('_head.CFrame=CFrame.new(10,0,-4);_rayTarget=_slide;_slidePrompt.Triggered:Fire(_player)')
    close(g._slide.Position.Y,2)
    close(g._slideConfig.FindFirstChild(g._slideConfig,'CurrentAngle').Value,1)

    # The downloadable open-inspection map must restore closed reference poses.
    lua=fixture("local q=CFrame.fromAxisAngle(Vector3.new(0,1,0),math.rad(90));_hinge.CFrame=q*_hinge.CFrame;_hingeHandle.CFrame=q*_hingeHandle.CFrame;_hingeConfig:FindFirstChild('CurrentAngle').Value=90;_hingeConfig:FindFirstChild('IsOpen').Value=true")
    g=lua.globals()
    lua.execute('_head.CFrame=CFrame.new(0,0,-7);_rayTarget=_hinge;_hingePrompt.Triggered:Fire(_player)')
    close(g._hinge.Position.X,3);close(g._hinge.Position.Z,0)
    close(g._hinge.CFrame.r[1],1)

    # Reject wall occlusion, excessive range, dead characters and absent ray hits.
    for setup in ('_rayTarget=_wall','_rayTarget=nil','_rayTarget=_hinge;_head.CFrame=CFrame.new(30,0,0)','_rayTarget=_hinge;_humanoid.Health=0'):
        lua=fixture();g=lua.globals();lua.execute(setup+';_hingePrompt.Triggered:Fire(_player)')
        close(g._hinge.Position.X,3);assert g._waits==0

    # Busy service callbacks cannot be reentered during task.wait.
    lua=fixture();g=lua.globals()
    lua.execute('_rayTarget=_hinge;_waitHook=function() _hingePrompt.Triggered:Fire(_player) end;_hingePrompt.Triggered:Fire(_player)')
    assert g._waits==30 and g._collisionWrites==0

    # An animation error restores the prompt; next call can reverse safely.
    lua=fixture();g=lua.globals()
    lua.execute('_rayTarget=_hinge;_waitHook=function() error("injected wait failure") end;_hingePrompt.Triggered:Fire(_player)')
    assert g._hingePrompt.Enabled and len(g._warnings)==1
    assert 0<g._hingeConfig.FindFirstChild(g._hingeConfig,'CurrentAngle').Value<90
    lua.execute('_waitHook=nil;_hingePrompt.Triggered:Fire(_player)')
    close(g._hinge.Position.X,3)

    # Emergency stop changes the actual source BoolValue and dependent status.
    lua=fixture();g=lua.globals()
    lua.execute('_head.CFrame=CFrame.new(20,0,-4);_rayTarget=_wall;_stopPrompt.Triggered:Fire(_player)')
    assert g._amplifier.Value
    lua.execute('_rayTarget=_stop;_stopPrompt.Triggered:Fire(_player)')
    assert not g._amplifier.Value and 'ОТКЛЮЧЕНО' in g._text.Text
    close(g._indicator.Color.R,180/255)
    print('PASS: actual Lua runtime, hinged and sliding motion, partial obstruction reversal, live collision retention, LOS/range/life guards, busy/error cleanup, emergency stop and real circuit status (mock APIs only).')


if __name__=='__main__':main()
