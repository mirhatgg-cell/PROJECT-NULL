"""Execute the real native-water bootstrap with bounded Roblox API doubles."""
from pathlib import Path

from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
MOCK = r'''
Vector3={new=function(x,y,z) return {X=x,Y=y,Z=z} end}
CFrame={new=function(v) return {Position=v} end}
Color3={fromRGB=function(r,g,b) return {r=r,g=g,b=b} end}
Enum={Material={Water='Water'}}
local methods,meta={},{}
function meta.__index(o,k) return methods[k] or o.props[k] end
function meta.__newindex(o,k,v)
 if k=='Parent' then
  local old=o.props.Parent
  if old then for i,c in ipairs(old.children) do if c==o then table.remove(old.children,i);break end end end
  if v then table.insert(v.children,o) end
 end
 o.props[k]=v
end
Instance={new=function(cls)
 return setmetatable({props={ClassName=cls,Name=cls},children={}},meta)
end}
function methods:FindFirstChild(n) for _,c in ipairs(self.children) do if c.Name==n then return c end end end
function methods:FindFirstChildOfClass(n) for _,c in ipairs(self.children) do if c.ClassName==n then return c end end end
function methods:IsA(n) return self.ClassName==n or (n=='BasePart' and self.ClassName=='Part') end
function methods:GetDescendants()
 local out={};local function visit(o) for _,c in ipairs(o.children) do table.insert(out,c);visit(c) end end
 visit(self);return out
end
function methods:Destroy() self.Parent=nil;self.destroyed=true end
function methods:FillBlock(cf,size,material)
 assert(material=='Water');table.insert(_fills,{center=cf.Position,size=size})
end
workspace=Instance.new('Workspace')
_terrain=Instance.new('Terrain');_terrain.Parent=workspace
_lighting=Instance.new('Lighting');_lighting.ClockTime=0;_lighting.Brightness=.3
_lighting.ExposureCompensation=-.35;_lighting.FogColor='original'
_lighting.FogStart=0;_lighting.FogEnd=1234;_lighting.OutdoorAmbient='original ambient'
_server=true;_fills={};_warnings={}
game={GetService=function(_,n)
 if n=='Lighting' then return _lighting end
 if n=='RunService' then return {IsServer=function() return _server end} end
 error('Unexpected service '..n)
end}
warn=function(s) table.insert(_warnings,s) end
_config={water={fill_boxes={
 {center={-500,-100,0},size={400,124,1200}},
 {center={600,-100,0},size={400,124,1200}},
 {center={70,-150,0},size={740,116,300}},
}}}
'''


def fixture():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK)
    lua.globals()._env = lua.execute((ROOT/'src/OceanEnvironment_V11.luau').read_text())
    return lua


def main():
    lua=fixture(); g=lua.globals()
    lua.execute('_state=_env.setup(_config)')
    assert g._state.waterReady and g._state.filled==3 and len(g._fills)==3
    assert g._terrain.WaterTransparency==.34 and g._lighting.ClockTime==4.8
    lua.execute('_again=_env.setup(_config);assert(_again==_state)')
    assert len(g._fills)==3
    assert len(g._lighting.children)==1 and len(g._terrain.children)==1
    lua.execute('_state:destroy();_state:destroy()')
    assert g._lighting.ClockTime==0 and g._lighting.FogEnd==1234
    assert len(g._fills)==3 and len(g._lighting.children)==len(g._terrain.children)==0

    lua=fixture();g=lua.globals()
    lua.execute('table.insert(_config.water.fill_boxes,{center={0,0,0},size={-1,2,3}});_state=_env.setup(_config)')
    assert not g._state.waterReady and g._state.filled==3 and g._state.failures==1
    assert len(g._warnings)==1
    lua=fixture();g=lua.globals()
    lua.execute('_terrain.Parent=nil;_state=_env.setup(_config)')
    assert not g._state.waterReady and len(g._fills)==0
    lua=fixture()
    lua.execute('_server=false;local ok=pcall(function() _env.setup(_config) end);assert(not ok);assert(#_fills==0)')
    lua=fixture();g=lua.globals()
    lua.execute('''
      local f=Instance.new('Model');f.Name='PROJECT_NULL_ARCH_P01';f.Parent=workspace
      local p=Instance.new('Part');p.Parent=f
      local tag=Instance.new('StringValue');tag.Name='V11_CircuitVisual';tag.Parent=p
      _circuit=Instance.new('BoolValue');_circuit.Value=true
      _circuit.Changed={Connect=function(self,fn) self.fn=fn;return {Disconnect=function() self.disconnected=true end} end}
      local ref=Instance.new('ObjectValue');ref.Name='Circuit';ref.Value=_circuit;ref.Parent=p
      _roomLight=Instance.new('PointLight');_roomLight.Parent=p
      _state=_env.setup(_config)
      assert(_state.poweredLights==1 and _roomLight.Enabled)
      _circuit.Value=false;_circuit.Changed.fn();assert(not _roomLight.Enabled)
      _circuit.Value=true;_circuit.Changed.fn();assert(_roomLight.Enabled)
      _state:destroy();assert(_circuit.Changed.disconnected)
    ''')
    print('PASS: actual ocean module native water, bounds, idempotence, cleanup, missing Terrain, server guard and existing-circuit luminaires.')


if __name__=='__main__':main()
