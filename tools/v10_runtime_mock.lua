-- Focused Roblox API doubles for executing the real V10 server source.
-- No Roblox renderer/physics/network/DataStore engine is simulated here.
local function copy(value, seen)
    if type(value) ~= "table" then return value end
    if getmetatable(value) then return value end -- Instances and Vector3 values.
    seen = seen or {}
    if seen[value] then return seen[value] end
    local out = {}; seen[value] = out
    for k,v in pairs(value) do out[copy(k,seen)] = copy(v,seen) end
    return out
end
table.clone = table.clone or function(t) local out={};for k,v in pairs(t) do out[k]=v end;return out end
table.clear = table.clear or function(t) for k in pairs(t) do t[k]=nil end end
math.clamp = math.clamp or function(x,a,b) return math.max(a,math.min(b,x)) end
local function signal()
    local s = {callbacks={}}
    function s:Connect(callback)
        local slot={callback=callback,connected=true};table.insert(self.callbacks,slot)
        return {Disconnect=function() slot.connected=false end}
    end
    function s:Once(callback)
        local connection
        connection=self:Connect(function(...) connection.Disconnect();callback(...) end)
        return connection
    end
    function s:Fire(...)
        local slots=table.clone(self.callbacks)
        for _,slot in ipairs(slots) do if slot.connected then slot.callback(...) end end
    end
    return s
end
_clock=1000; _scheduled={}; _warnings={}; _messages={}; _players={}; _closeCallbacks={}
_getDelay=0; _getFailure=false; _updateDelay=0; _updateFailure=false; _updates=0;_writes=0;_reads=0;_store={}
_rayTarget=nil; _damage={}; _rayCalls=0; _taskErrors={}
local oldTime=os.time
os.clock=function() return _clock end
os.time=function() return 1770000000+math.floor(_clock) end
local function schedule(delay, fn, ...)
    local co=type(fn)=="thread" and fn or coroutine.create(fn)
    table.insert(_scheduled,{co=co,wake=_clock+delay,args={...}})
    return co
end
task={spawn=function(fn,...) return schedule(0,fn,...) end,
    defer=function(fn,...) return schedule(0,fn,...) end,
    delay=function(delay,fn,...) return schedule(delay,fn,...) end,
    wait=function(delay) return coroutine.yield(math.max(delay or .03,.001)) end,
    cancel=function(co) for i=#_scheduled,1,-1 do if _scheduled[i].co==co then table.remove(_scheduled,i) end end end}
function flush_tasks()
    local count=0
    while true do
        local chosen
        for i,entry in ipairs(_scheduled) do if entry.wake<=_clock then chosen=i;break end end
        if not chosen then return end
        count=count+1;assert(count<1000,"Unbounded runnable task loop")
        local entry=table.remove(_scheduled,chosen)
        local ok,delay=coroutine.resume(entry.co,table.unpack(entry.args))
        if not ok then table.insert(_taskErrors,tostring(delay));error(delay) end
        if coroutine.status(entry.co)~="dead" then
            assert(type(delay)=="number","Unexpected coroutine yield")
            table.insert(_scheduled,{co=entry.co,wake=_clock+delay,args={delay}})
        end
    end
end
local vm={}
function vm.__index(v,k)
    if k=="Magnitude" then return math.sqrt(v.X*v.X+v.Y*v.Y+v.Z*v.Z) end
    if k=="Unit" then return v/v.Magnitude end
end
function vm.__add(a,b) return Vector3.new(a.X+b.X,a.Y+b.Y,a.Z+b.Z) end
function vm.__sub(a,b) return Vector3.new(a.X-b.X,a.Y-b.Y,a.Z-b.Z) end
function vm.__mul(a,b)
    if type(a)=="number" then return Vector3.new(a*b.X,a*b.Y,a*b.Z) end
    return Vector3.new(a.X*b,a.Y*b,a.Z*b)
end
function vm.__div(a,b) return Vector3.new(a.X/b,a.Y/b,a.Z/b) end
function vm.__unm(a) return Vector3.new(-a.X,-a.Y,-a.Z) end
Vector3={new=function(x,y,z) return setmetatable({X=x,Y=y,Z=z},vm) end}
Vector3.zero=Vector3.new(0,0,0)
local cm={}
function cm.__add(frame,offset) return CFrame.new(frame.Position+offset) end
CFrame={new=function(x,y,z)
    return setmetatable({Position=type(x)=="table" and x or Vector3.new(x or 0,y or 0,z or 0)},cm)
end}
Color3={fromRGB=function(r,g,b) return {R=r/255,G=g/255,B=b/255} end,
    new=function(r,g,b) return {R=r,G=g,B=b} end}
Enum={RaycastFilterType={Exclude=0},DataStoreRequestType={GetAsync=0,UpdateAsync=1},Material={Neon=1,SmoothPlastic=2}}
RaycastParams={new=function() return {} end}
local methods={};local meta={}
function meta.__index(o,k)
    if methods[k] then return methods[k] end
    if k=="ClassName" then return rawget(o,"_class") end
    if k=="Position" and o._props.CFrame then return o._props.CFrame.Position end
    if o._props[k]~=nil then return o._props[k] end
    for _,child in ipairs(o._children) do if child.Name==k then return child end end
end
function meta.__newindex(o,k,v)
    if k=="Parent" then
        local old=o._props.Parent
        if old then for i,c in ipairs(old._children) do if c==o then table.remove(old._children,i);break end end end
        if v then table.insert(v._children,o) end
    end
    o._props[k]=v
    if o._props.Changed then o._props.Changed:Fire(v) end
    if o._propertySignals[k] then o._propertySignals[k]:Fire() end
end
Instance={new=function(cls,parent)
    local o=setmetatable({_class=cls,_children={},_attributes={},_propertySignals={},
        _props={Name=cls,Changed=signal(),Triggered=signal(),DescendantAdded=signal(),
        ChildAdded=signal(),ChildRemoved=signal(),CharacterAdded=signal(),Died=signal(),
        OnServerEvent=signal(),AncestryChanged=signal()}},meta)
    if cls=="Part" then o.Size=Vector3.new(2,2,.1);o.CFrame=CFrame.new();o.CanQuery=true;o.CanCollide=true end
    if parent then o.Parent=parent end
    return o
end}
function methods:IsA(cls)
    return cls==self.ClassName or cls=="Instance" or (cls=="BasePart" and self.ClassName=="Part")
end
function methods:GetChildren() return table.clone(self._children) end
function methods:GetDescendants()
    local out={}
    local function visit(p) for _,c in ipairs(p._children) do table.insert(out,c);visit(c) end end
    visit(self);return out
end
function methods:FindFirstChild(n,recursive)
    for _,c in ipairs(self._children) do if c.Name==n then return c end end
    if recursive then for _,c in ipairs(self._children) do local found=c:FindFirstChild(n,true);if found then return found end end end
end
function methods:WaitForChild(n) return self:FindFirstChild(n) end
function methods:FindFirstChildOfClass(cls) for _,c in ipairs(self._children) do if c:IsA(cls) then return c end end end
function methods:FindFirstAncestorOfClass(cls)
    local p=self.Parent;while p do if p:IsA(cls) then return p end;p=p.Parent end
end
function methods:IsDescendantOf(parent)
    local p=self.Parent;while p do if p==parent then return true end;p=p.Parent end;return false
end
function methods:GetFullName() return self.Parent and self.Parent:GetFullName().."."..self.Name or self.Name end
function methods:GetPropertyChangedSignal(k)
    self._propertySignals[k]=self._propertySignals[k] or signal();return self._propertySignals[k]
end
function methods:GetAttribute(k) return self._attributes[k] end
function methods:SetAttribute(k,v) self._attributes[k]=v end
function methods:Destroy() self.Parent=nil end
function methods:Raycast()
    _rayCalls=_rayCalls+1
    if _rayTarget then return {Instance=_rayTarget} end
end
function methods:GetServerTimeNow() return _clock end
function methods:TakeDamage(amount)
    assert(amount>=0 and amount<=25,"Unbounded server damage")
    table.insert(_damage,{humanoid=self,amount=amount});self.Health=math.max(0,self.Health-amount)
    if self.Health<=0 then self.Died:Fire() end
end
function methods:FireClient(player,kind,payload)
    table.insert(_messages,{player=player,kind=kind,payload=copy(payload)})
end
function methods:FireAllClients(kind,payload)
    for _,player in ipairs(_players) do self:FireClient(player,kind,payload) end
end
function methods:GetPlayers() return table.clone(_players) end
function methods:GetPlayerByUserId(id) for _,p in ipairs(_players) do if p.UserId==id then return p end end end
function methods:IsServer() return true end
function methods:IsStudio() return _isStudio or false end
function methods:GetDataStore(n) _storeName=n;return self end
function methods:GetAsync(key)
    _reads=_reads+1
    if _getDelay>0 then task.wait(_getDelay) end
    if _getFailure then error("injected GetAsync failure") end
    return copy(_store[key])
end
function methods:UpdateAsync(key,callback)
    _updates=_updates+1
    if _updateDelay>0 then task.wait(_updateDelay) end
    if _updateFailure then error("injected UpdateAsync failure") end
    local result=callback(copy(_store[key]))
    if result~=nil then _store[key]=copy(result);_writes=_writes+1 end
    return copy(result)
end
function methods:GetRequestBudgetForRequestType() return 100 end
warn=function(message) table.insert(_warnings,tostring(message)) end
typeof=function(o)
    if getmetatable(o)==meta then return "Instance" end
    if getmetatable(o)==vm then return "Vector3" end
    return type(o)
end
local function new(cls,parent,name,value)
    local o=Instance.new(cls,parent);o.Name=name
    if value~=nil then o.Value=value end
    return o
end
_new=new
workspace=new("Workspace",nil,"Workspace")
_facility=new("Model",workspace,"PROJECT_NULL_ARCH_P01")
_equipment=new("Model",_facility,"Equipment")
_world=new("Model",_equipment,"Narrative_Gameplay_V10")
_controls=new("Folder",_facility,"Controls");_circuits=new("Folder",_controls,"Circuits")
for _,n in ipairs({"Computers","Ventilation","AcousticAmplifiers","PhysicalHall"}) do new("BoolValue",_circuits,n,true) end
_services={}
for _,n in ipairs({"Players","RunService","DataStoreService","ReplicatedStorage","HttpService","ServerScriptService"}) do
    _services[n]=new(n,nil,n)
end
_services.Players.PlayerAdded=signal();_services.Players.PlayerRemoving=signal()
_services.RunService.Heartbeat=signal()
_services.HttpService.GenerateGUID=function(_,wrap) _guid=(_guid or 0)+1;return "fixture-guid-".._guid end
game={GetService=function(_,n) assert(_services[n],"Unmocked service "..n);return _services[n] end,
    BindToClose=function(_,callback) table.insert(_closeCallbacks,callback) end,
    JobId="fixture-job",PlaceId=1,GameId=1}
_network=new("Folder",_services.ReplicatedStorage,"ProjectNullV10")
_request=new("RemoteEvent",_network,"Request");_push=new("RemoteEvent",_network,"Push")
_scriptFolder=new("Folder",_services.ServerScriptService,"ProjectNullV10")
_coreModule=new("ModuleScript",_scriptFolder,"ExperimentCore")
_contentModule=new("ModuleScript",_scriptFolder,"Content")
script=new("Script",_scriptFolder,"ProjectNullServer_V10")
require=function(module)
    if module==_coreModule then return _engine end
    if module==_contentModule then return _content end
    error("Unknown require")
end
function fixture_player(id)
    local p=new("Player",_services.Players,"Player"..id);p.UserId=id;p.DisplayName="Operator "..id
    local c=new("Model",workspace,"Character"..id)
    local head=new("Part",c,"Head");head.CFrame=CFrame.new(0,0,-4)
    local root=new("Part",c,"HumanoidRootPart");root.CFrame=head.CFrame
    local h=new("Humanoid",c,"Humanoid");h.MaxHealth=100;h.Health=100;p.Character=c
    table.insert(_players,p)
    return p
end
_player=fixture_player(101);_other=fixture_player(202)
_head=_player.Character.Head;_humanoid=_player.Character.Humanoid
_wall=new("Part",_world,"Wall");_wall.CFrame=CFrame.new(0,0,-2)
function fixture_station(name,action,argument,x)
    local p=new("Part",_world,name);p.CFrame=CFrame.new(x or 0,0,0)
    local config=new("Folder",p,"V10_Interact")
    new("StringValue",config,"Action",action);new("StringValue",config,"Argument",argument)
    local prompt=new("ProximityPrompt",p,"V10_Prompt")
    prompt.Enabled=true;prompt.MaxActivationDistance=9;prompt.RequiresLineOfSight=true
    return p
end
_console=fixture_station("ConsoleP01","console","P01",0)
_console2=fixture_station("ConsoleP02","console","P02",20)
_console3=fixture_station("ConsoleP03","console","P03",23)
_console4=fixture_station("ConsoleP04","console","P04",25)
_console5=fixture_station("ConsoleP05","console","P05",27)
_laneLeft=fixture_station("P02Left","response","left",24)
_laneCenter=fixture_station("P02Center","response","center",28)
_laneRight=fixture_station("P02Right","response","right",32)
_document=fixture_station("Protocol","document","DOC_P01_PROTOCOL",40)
_secretDocument=fixture_station("UnseenLog","document","DOC_P03_LOG",45)
_correctionDocument=fixture_station("SignedCorrection","document","DOC_P03_CORRECTION",48)
_cooling=fixture_station("Cooling","cooling","toggle",60)
_repair=fixture_station("Repair","repair","repair",80)
_supply=fixture_station("Supply","supply","filter",100)
_medical=fixture_station("Medical","medical","kit",120)
_npc=fixture_station("Technician","npc","TECH",140)
_records=fixture_station("Records","records","records",160)
_p01Lights={}
for _,channel in ipairs({'A','B','C'}) do
    local part=new('Part',_world,'V10_P01_Light_'..channel)
    local light=new('PointLight',part,'PointLight');light.Enabled=false
    _p01Lights[channel]=part
end
_p02Readouts={}
for _,lane in ipairs({'left','center','right'}) do
    _p02Readouts[lane]=new('TextLabel',_world,'V10_P02_Readout_'..lane)
end
_p05Reference=new('TextLabel',_world,'V10_P05_Reference')
_shutter=new('Part',_world,'V10_ObserverShutter');_shutter.CFrame=CFrame.new(25,3,0)
new('Vector3Value',_shutter,'OpenOffset',Vector3.new(0,2,0))
function place_player(player,target)
    local p=target.Position+Vector3.new(0,0,-4)
    player.Character.Head.CFrame=CFrame.new(p);player.Character.HumanoidRootPart.CFrame=CFrame.new(p)
    _rayTarget=target
end
function interact(target,player)
    player=player or _player
    place_player(player,target);target.V10_Prompt.Triggered:Fire(player);flush_tasks()
end
function request(action,arg,player)
    _request.OnServerEvent:Fire(player or _player,action,arg);flush_tasks()
end
function last_message(kind,player)
    for i=#_messages,1,-1 do
        local m=_messages[i]
        if m.kind==kind and m.player==(player or _player) then return m.payload end
    end
end
function advance(seconds)
    local left=seconds
    while left>0.000001 do
        local step=math.min(.1,left);_clock=_clock+step;left=left-step
        _services.RunService.Heartbeat:Fire(step);flush_tasks()
    end
end
function remove_player(player)
    for i,p in ipairs(_players) do if p==player then table.remove(_players,i);break end end
    player.Parent=nil
    _services.Players.PlayerRemoving:Fire(player)
    flush_tasks()
end
function close_server()
    for _,callback in ipairs(_closeCallbacks) do task.spawn(callback) end
    flush_tasks()
end
