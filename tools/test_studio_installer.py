"""Exercise the offline installer with a Lua VM and a small Roblox API mock.

This validates transfer logic and rollback, not real Roblox rendering or API execution.
Install test dependency separately: pip install lupa==2.6
"""
from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET

from lupa import LuaRuntime


ROOT = Path(__file__).resolve().parents[1]
MOCK = r'''
local enumValues = {
 Material={SmoothPlastic=272,Metal=1088,Fabric=1312,Plastic=256},
 PartType={Ball=0,Block=1,Cylinder=2},
 NormalId={Right=0,Top=1,Back=2,Left=3,Bottom=4,Front=5},
 SurfaceGuiSizingMode={FixedSize=0,PixelsPerStud=1},
 Font={Code=10,Antique=15},SurfaceType={Smooth=0},
 FinishRecordingOperation={Cancel=0,Commit=1,Append=2},
}
Enum={}
for category, values in pairs(enumValues) do
 local enum={}
 function enum:GetEnumItems()
  local items={}; for _,v in pairs(self) do if type(v)=='table' then table.insert(items,v) end end
  return items
 end
 for key,value in pairs(values) do enum[key]={Name=key,Value=value,EnumType=category} end
 Enum[category]=enum
end
Vector3={new=function(x,y,z) return {_kind='Vector3',X=x,Y=y,Z=z} end}
CFrame={new=function(...) return {_kind='CFrame',values={...}} end}
Color3={new=function(r,g,b) return {_kind='Color3',R=r,G=g,B=b} end}
function Color3.fromRGB(r,g,b) return Color3.new(r/255,g/255,b/255) end
UDim2={new=function(xs,xo,ys,yo) return {_kind='UDim2',XS=xs,XO=xo,YS=ys,YO=yo} end}
function UDim2.fromScale(xs,ys) return UDim2.new(xs,0,ys,0) end
function typeof(v) return type(v)=='table' and v._kind or type(v) end
table.create=function() return {} end
local methods={}
local meta={}
function meta.__index(o,k)
 if methods[k] then return methods[k] end
 if k=='ClassName' then return rawget(o,'_class') end
 return rawget(o,'_props')[k]
end
function meta.__newindex(o,k,v)
 if k=='Parent' then
  local old=o._props.Parent
  if old then for i,c in ipairs(old._children) do if c==o then table.remove(old._children,i);break end end end
  if v then table.insert(v._children,o) end
 end
 o._props[k]=v
end
Instance={new=function(cls,parent)
 local o=setmetatable({_class=cls,_props={Name=cls},_children={},_destroyed=false},meta)
 table.insert(_created,o)
 if parent then o.Parent=parent end
 return o
end}
function methods:IsA(cls) return cls==self.ClassName or cls=='Instance' or (cls=='BasePart' and self.ClassName=='Part') end
function methods:GetChildren() local r={};for _,c in ipairs(self._children) do table.insert(r,c) end;return r end
function methods:GetDescendants()
 local r={};local function visit(p) for _,c in ipairs(p._children) do table.insert(r,c);visit(c) end end
 visit(self);return r
end
function methods:FindFirstChild(n,recursive)
 for _,c in ipairs(self._children) do if c.Name==n then return c end end
 if recursive then for _,c in ipairs(self:GetDescendants()) do if c.Name==n then return c end end end
end
function methods:GetFullName() return self.Parent and self.Parent:GetFullName()..'.'..self.Name or self.Name end
function methods:Destroy()
 for _,c in ipairs(self:GetChildren()) do c:Destroy() end
 self.Parent=nil;rawset(self,'_destroyed',true)
end
function methods:GetService(n) assert(_services[n],'Unexpected service '..n);return _services[n] end
_created={};_logs={};_recording=false;_commit=0;_cancel=0
_services={}
_services.RunService={IsStudio=function() return _studio end, IsRunning=function() return _running end}
_services.ChangeHistoryService={
 TryBeginRecording=function() if _deny then return nil end;_recording=true;return 'test-record' end,
 FinishRecording=function(_,id,op)
  assert(_recording and id=='test-record')
  if op.Value==1 then
   if _failcommit then error('simulated commit failure') end
   _commit=_commit+1
  else _cancel=_cancel+1 end
  _recording=false
 end,
}
_services.HttpService={JSONDecode=function(_,s) return _decode(s) end}
_services.Selection={Set=function(_,selection) _selection=selection end}
game=Instance.new('DataModel');game.Name='game'
workspace=Instance.new('Workspace',game);workspace.Name='Workspace'
local facility=Instance.new('Model',workspace);facility.Name='PROJECT_NULL_ARCH_P01'
_equipment=Instance.new('Model',facility);_equipment.Name='Equipment'
_sentinel=Instance.new('Part',_equipment);_sentinel.Name='OriginalV6Part';_sentinel.Anchored=true
print=function(...) table.insert(_logs,{...}) end
warn=print
'''


def lua_table(lua, value):
    if isinstance(value, dict):
        return lua.table_from({key: lua_table(lua, v) for key, v in value.items()})
    if isinstance(value, list):
        return lua.table_from([lua_table(lua, v) for v in value])
    return value


def runtime(**flags):
    lua = LuaRuntime(unpack_returned_tuples=True)
    g = lua.globals()
    for key, value in {'studio':True, 'running':False, 'deny':False, 'failcommit':False, **flags}.items():
        g['_' + key] = value
    g._decode = lambda s: lua_table(lua, json.loads(s))
    lua.execute(MOCK)
    return lua


def normalized_property(element):
    tag = element.tag
    if tag in ('string', 'ProtectedString'): return element.text or ''
    if tag == 'bool': return element.text == 'true'
    if tag in ('float', 'double', 'int', 'token', 'Color3uint8'): return float(element.text)
    return {e.tag: float(e.text) for e in element}


def actual_property(value, tag):
    if tag == 'token': return float(value.Value)
    if tag == 'Color3uint8': return float((255<<24) | (round(value.R*255)<<16) | (round(value.G*255)<<8) | round(value.B*255))
    if tag == 'CoordinateFrame':
        keys = list('XYZ') + [f'R{i}{j}' for i in range(3) for j in range(3)]
        return {key: float(value['values'][i+1]) for i,key in enumerate(keys)}
    if tag in ('Vector3', 'Color3', 'UDim2'):
        keys = {'Vector3':list('XYZ'),'Color3':list('RGB'),'UDim2':['XS','XO','YS','YO']}[tag]
        return {key: float(value[key]) for key in keys}
    return value


def equal(a, b):
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a, float): return abs(a-b) < 1e-7
    return a == b


def compare(expected, actual):
    assert expected.get('class') == actual.ClassName
    for prop in expected.find('Properties'):
        key = {'size':'Size','shape':'Shape','Color3uint8':'Color'}.get(prop.get('name'),prop.get('name'))
        got = actual_property(actual[key],prop.tag)
        want = normalized_property(prop)
        assert equal(want,got), (actual.Name,key,want,got)
    children = expected.findall('Item')
    assert len(children) == len(actual._children)
    def expected_key(e):
        frame=e.find("Properties/CoordinateFrame[@name='CFrame']")
        position=tuple(float(frame.findtext(k)) for k in 'XYZ') if frame is not None else ()
        return e.get('class'),e.findtext("Properties/string[@name='Name']"),position
    def actual_key(e):
        position=tuple(float(e.CFrame['values'][i]) for i in (1,2,3)) if e.CFrame is not None else ()
        return e.ClassName,e.Name,position
    actual_children=sorted([actual._children[i] for i in range(1,len(actual._children)+1)],key=actual_key)
    for e,a in zip(sorted(children,key=expected_key),actual_children): compare(e,a)


def main():
    script = (ROOT/'artifacts/INSTALL_V7_COMMAND_BAR.luau').read_text()
    expected = next(e for e in ET.parse(ROOT/'artifacts/PROJECT_NULL_INTERIORS_V7_DETAIL.rbxlx').iter('Item') if e.findtext("Properties/string[@name='Name']") == 'Visual_Detail_V7')
    lua = runtime()
    lua.execute(script)
    g=lua.globals()
    added=g._equipment.FindFirstChild(g._equipment,'Visual_Detail_V7')
    assert added is not None, 'Installer did not publish new model'
    compare(expected,added)
    assert not g._sentinel._destroyed and lua.eval('_sentinel.Parent == _equipment')
    assert g._commit==1 and not g._recording
    count=len(g._created)
    try: lua.execute(script)
    except Exception: pass
    assert len(g._equipment._children)==2 and len(g._created)==count, 'Duplicate run changed existing map'
    # Verify denied execution and transaction failures leave the V6 fixture intact.
    for flags in ({'studio':False},{'running':True},{'deny':True},{'failcommit':True}):
        lua=runtime(**flags);g=lua.globals()
        try: lua.execute(script)
        except Exception: pass
        assert len(g._equipment._children)==1 and not g._sentinel._destroyed, flags
        assert not g._recording,flags
    print('PASS: Lua syntax, 345-instance/property transfer, duplicate guard, edit-mode guards, recording denial and failed-commit cleanup (mock APIs only).')


if __name__ == '__main__': main()
