-- Six local R6 staff rigs, one scheduler and no external animation assets.
-- C0 is deliberately used for replicated procedural poses: Motor6D.Transform
-- alone is not a server-to-client animation replication mechanism.
local Director = {}
Director.__index = Director

local PathfindingService = game:GetService("PathfindingService")
local Players = game:GetService("Players")
local atan2 = math.atan2 or function(y, x) return math.atan(y, x) end
local JOINTS = {"RootJoint", "Neck", "Left Shoulder", "Right Shoulder", "Left Hip", "Right Hip"}
local MAX_PATH_REQUESTS = 2

local function finite(value)
    return type(value) == "number" and value == value and value > -math.huge and value < math.huge
end

local function clamp(value, lo, hi)
    return math.max(lo, math.min(hi, value))
end

local function horizontal(a, b)
    local x, z = a.X - b.X, a.Z - b.Z
    return math.sqrt(x*x + z*z)
end

local function child(parent, name, className)
    local value = parent and parent:FindFirstChild(name)
    if value and (not className or value:IsA(className)) then return value end
    return nil
end

local function livePlayer(player)
    if not player or not player:IsA("Player") or player.Parent ~= Players then return nil end
    local character = player.Character
    local humanoid = character and character:FindFirstChildOfClass("Humanoid")
    local head = character and (character:FindFirstChild("Head") or character:FindFirstChild("HumanoidRootPart"))
    if humanoid and humanoid.Health > 0 and head and head:IsA("BasePart") then return head, character end
    return nil
end

local function setNetworkOwner(root)
    pcall(function() root:SetNetworkOwner(nil) end)
end

function Director.new(facility)
    local self = setmetatable({facility=facility, rigs={}, byId={}, elapsed=0, accumulated=0,
                              pathRequests=0, destroyed=false, connections={}}, Director)
    local function register(config)
        if self.destroyed or config.Name ~= "V11_NPC" or not config:IsA("Folder") then return end
        local model = config.Parent
        local idValue = child(config, "Id", "StringValue")
        local homeValue = child(config, "Home", "Vector3Value")
        local workValue = child(config, "WorkTarget", "Vector3Value")
        local modeValue = child(config, "WorkMode", "StringValue")
        local root = child(model, "HumanoidRootPart", "BasePart")
        local humanoid = model and model:FindFirstChildOfClass("Humanoid")
        if not idValue or not homeValue or not workValue or not root or not humanoid or self.byId[idValue.Value] then return end
        local height = child(config, "RootHeight", "NumberValue")
        local state = {id=idValue.Value, model=model, root=root, humanoid=humanoid,
                       home=homeValue.Value, work=workValue.Value, mode=modeValue and modeValue.Value or "inspect",
                       facing=child(root,"StaffFacing","AlignOrientation"),
                       rootHeight=height and height.Value or 3.35, route={}, routeIndex=0,
                       joints={}, originals={}, speakers={}, walking=false, generation=0,
                       nextWalk=12+#self.rigs*2.7, pathPending=false, waypoints=nil, waypointIndex=0,
                       moveDeadline=0, lastMovement=0, lastPosition=root.Position,
                       blockedUntil=0, state="working", removed=false}
        for _, instance in ipairs(model:GetDescendants()) do
            if instance:IsA("Motor6D") then
                state.joints[instance.Name] = instance
                state.originals[instance.Name] = instance.C0
            end
        end
        for _, name in ipairs(JOINTS) do
            if not state.joints[name] then
                warn("V11 NPC lacks R6 joint "..name..": "..state.id)
                return
            end
        end
        local route = child(config, "Route", "Folder")
        if route then
            local points=route:GetChildren()
            table.sort(points,function(a,b) return a.Name<b.Name end)
            for _, point in ipairs(points) do
                if point:IsA("Vector3Value") and horizontal(point.Value,state.home)<=18
                   and math.abs(point.Value.Y-state.home.Y)<=1 then
                    table.insert(state.route,point.Value)
                end
            end
        end
        table.insert(state.route,state.home)
        self.byId[state.id]=state
        table.insert(self.rigs,state)
        setNetworkOwner(root)
        humanoid.WalkSpeed=7
        humanoid.AutoRotate=false
        state.moveConnection=humanoid.MoveToFinished:Connect(function(reached)
            if self.destroyed or state.removed or not state.walking or not state.waypoints then return end
            local waypoint=state.waypoints[state.waypointIndex]
            if reached and waypoint and horizontal(root.Position,waypoint.Position)<2.0 then
                state.waypointIndex=state.waypointIndex+1
                local nextPoint=state.waypoints[state.waypointIndex]
                if nextPoint then
                    humanoid:MoveTo(nextPoint.Position)
                    state.moveDeadline=self.elapsed+6
                else
                    self:_stop(state,"working",false)
                    state.nextWalk=self.elapsed+14
                end
            elseif not reached then
                self:_stop(state,"blocked",true)
            end
        end)
        table.insert(self.connections,state.moveConnection)
    end
    for _, instance in ipairs(facility:GetDescendants()) do register(instance) end
    table.insert(self.connections,facility.DescendantAdded:Connect(function(instance)
        if instance.Name=="V11_NPC" then task.defer(function() register(instance) end) end
    end))
    return self
end

function Director:_stop(state, reason, blocked)
    state.generation=state.generation+1
    state.walking=false
    state.waypoints=nil
    state.state=reason or "working"
    state.humanoid.AutoRotate=false
    -- Stop at the actual current position. Never reset CFrame, teleport home or
    -- let a failed navigation request keep pushing against a closed door.
    if state.root.Parent then state.humanoid:MoveTo(state.root.Position) end
    if state.pathConnection then state.pathConnection:Disconnect();state.pathConnection=nil end
    if blocked then
        state.blockedUntil=self.elapsed+12
        state.nextWalk=self.elapsed+12
    end
end

function Director:_requestPath(state, destination)
    if state.pathPending or state.walking or self.pathRequests>=MAX_PATH_REQUESTS
       or self.elapsed<state.blockedUntil then return end
    state.pathPending=true
    state.generation=state.generation+1
    local generation=state.generation
    self.pathRequests=self.pathRequests+1
    task.spawn(function()
        local path
        local ok,problem=pcall(function()
            path=PathfindingService:CreatePath({AgentRadius=1.1,AgentHeight=5.8,
                                              AgentCanJump=false,WaypointSpacing=3})
            path:ComputeAsync(state.root.Position,destination+Vector3.new(0,state.rootHeight,0))
        end)
        self.pathRequests=math.max(0,self.pathRequests-1)
        state.pathPending=false
        if self.destroyed or state.removed or generation~=state.generation or not state.root.Parent then return end
        if not ok or not path or path.Status~=Enum.PathStatus.Success then
            self:_stop(state,"blocked",true)
            if not ok then warn("V11 NPC path unavailable: "..tostring(problem)) end
            return
        end
        local points=path:GetWaypoints()
        if #points<2 or #points>64 then self:_stop(state,"blocked",true);return end
        for _, point in ipairs(points) do
            if horizontal(point.Position,state.home)>20
               or math.abs(point.Position.Y-(state.home.Y+state.rootHeight))>7 then
                self:_stop(state,"blocked",true)
                return
            end
        end
        state.waypoints=points
        state.waypointIndex=2
        state.walking=true
        state.state="walking"
        state.lastPosition=state.root.Position
        state.lastMovement=self.elapsed
        state.moveDeadline=self.elapsed+6
        state.humanoid.AutoRotate=true
        if state.facing then state.facing.Enabled=false end
        state.pathConnection=path.Blocked:Connect(function(index)
            if index>=state.waypointIndex then self:_stop(state,"blocked",true) end
        end)
        state.humanoid:MoveTo(points[2].Position)
    end)
end

function Director:talk(id, player, active)
    if self.destroyed or type(id)~="string" then return false end
    local state=self.byId[id]
    if not state then return false end
    if active==false then
        if not player then return false end
        state.speakers[player]=nil
        return true
    end
    local head=livePlayer(player)
    if not head or horizontal(head.Position,state.root.Position)>12 then return false end
    state.speakers[player]=self.elapsed+45
    if state.walking or state.pathPending then self:_stop(state,"talking",false) end
    state.nextWalk=self.elapsed+15
    state.state="talking"
    return true
end

function Director:_attention(state)
    local closest,distance=nil,12
    for player,expires in pairs(state.speakers) do
        local head=livePlayer(player)
        if not head or expires<self.elapsed or horizontal(head.Position,state.root.Position)>12 then
            state.speakers[player]=nil
        else
            local d=(head.Position-state.root.Position).Magnitude
            if d<distance then closest,distance=head,d end
        end
    end
    if closest then return closest.Position,true end
    -- A nearby staff member may look toward an approaching visible player, but
    -- this never starts or unlocks dialogue without the server interaction.
    for _,player in ipairs(Players:GetPlayers()) do
        local head,character=livePlayer(player)
        if head then
            local d=(head.Position-state.root.Position).Magnitude
            if d<distance then
                local origin=state.model:FindFirstChild("Head")
                local params=RaycastParams.new()
                params.FilterType=Enum.RaycastFilterType.Exclude
                params.FilterDescendantsInstances={state.model}
                local hit=origin and workspace:Raycast(origin.Position,head.Position-origin.Position,params)
                if hit and hit.Instance and hit.Instance:IsDescendantOf(character) then
                    closest,distance=head,d
                end
            end
        end
    end
    return closest and closest.Position or state.work,false
end

function Director:_pose(state,dt,snapshot)
    local t=self.elapsed
    local target,talking=self:_attention(state)
    local alarm=snapshot.phase=="failed"
    local walking=state.walking
    local atWorkStation=horizontal(state.root.Position,state.work)<=6
    local breath=math.sin(t*1.65)*.025
    local neckPitch,neckYaw,bodyYaw=0,0,0
    local leftArm,rightArm,leftRoll,rightRoll=0,0,-.025,.025
    local leftHip,rightHip=0,0
    local localDirection=state.root.CFrame:VectorToObjectSpace(target-state.root.Position)
    if state.facing then
        state.facing.Enabled=not walking
        local delta=target-state.root.Position
        if not walking and math.abs(delta.X)+math.abs(delta.Z)>.01 then
            state.facing.CFrame=CFrame.Angles(0,atan2(-delta.X,-delta.Z),0)
        end
    end
    if localDirection.Magnitude>.001 then
        local yaw=atan2(-localDirection.X,-localDirection.Z)
        neckYaw=clamp(yaw,-.75,.75)
        neckPitch=clamp(atan2(localDirection.Y-1.7,math.max(.5,math.sqrt(localDirection.X^2+localDirection.Z^2))),-.28,.28)
        bodyYaw=clamp(yaw,-.32,.32)
    end
    if walking then
        local speed=state.root.AssemblyLinearVelocity.Magnitude
        local stride=math.sin(t*6.5)*clamp(speed/7,0,1)*.55
        leftHip,rightHip=stride,-stride
        leftArm,rightArm=-stride*.7,stride*.7
        neckYaw,neckPitch,bodyYaw=0,0,0
        state.state="walking"
    elseif alarm then
        leftArm,rightArm=.24,.38
        rightRoll=.12+math.sin(t*2)*.035
        state.state="alert"
    elseif talking then
        rightArm=.38+math.sin(t*2.1)*.13
        rightRoll=.16+math.sin(t*1.7)*.08
        leftArm=.06
        state.state="talking"
    elseif not atWorkStation and (state.mode=="terminal" or state.mode=="repair" or state.mode=="inspect") then
        -- Inspection routes move away from their fixed station. Do not keep
        -- typing or repairing empty space while waiting to return there.
        leftArm,rightArm=.04,.04
        state.state="waiting"
    elseif state.mode=="terminal" then
        leftArm=.83+math.sin(t*3.0)*.035
        rightArm=.86+math.sin(t*3.4+.5)*.035
        neckPitch=-.16
        state.state="working"
    elseif state.mode=="repair" then
        leftArm=.67
        rightArm=1.12+math.sin(t*2.4)*.13
        rightRoll=.15
        neckPitch=-.13
        state.state="repairing"
    elseif state.mode=="read" then
        leftArm=.78
        rightArm=.9+math.sin(t*.8)*.06
        neckPitch=-.22
        state.state="reading"
    elseif state.mode=="inspect" then
        rightArm=.62+math.sin(t*.75)*.05
        leftArm=.12
        state.state="inspecting"
    else
        neckYaw=neckYaw+math.sin(t*.32)*.08
        state.state="watching"
    end
    local offsets={
        RootJoint=CFrame.new(0,breath,0)*CFrame.Angles(0,bodyYaw,0),
        Neck=CFrame.Angles(-neckPitch,neckYaw,0),
        ["Left Shoulder"]=CFrame.Angles(leftArm,0,leftRoll),
        ["Right Shoulder"]=CFrame.Angles(rightArm,0,rightRoll),
        ["Left Hip"]=CFrame.Angles(leftHip,0,0),
        ["Right Hip"]=CFrame.Angles(rightHip,0,0),
    }
    local alpha=clamp(dt*7.5,0,1)
    for _,name in ipairs(JOINTS) do
        local motor=state.joints[name]
        if motor.Parent then motor.C0=motor.C0:Lerp(state.originals[name]*offsets[name],alpha) end
    end
end

function Director:step(dt,snapshot)
    if self.destroyed or not finite(dt) or dt<0 then return end
    dt=clamp(dt,0,.25)
    self.elapsed=self.elapsed+dt
    self.accumulated=self.accumulated+dt
    if self.accumulated<.1 then return end
    local elapsed=self.accumulated
    self.accumulated=0
    snapshot=type(snapshot)=="table" and snapshot or {}
    for _,state in ipairs(self.rigs) do
        if not state.model:IsDescendantOf(self.facility) or not state.root.Parent or state.humanoid.Health<=0 then
            if not state.removed then
                state.removed=true
                self:_stop(state,"removed",false)
                if state.moveConnection then state.moveConnection:Disconnect() end
            end
        else
            local alert=snapshot.phase=="failed"
            local talking=false
            for player,expires in pairs(state.speakers) do
                local head=livePlayer(player)
                if head and expires>=self.elapsed and horizontal(head.Position,state.root.Position)<=12 then talking=true;break end
            end
            if (alert or talking) and (state.walking or state.pathPending) then self:_stop(state,alert and "alert" or "talking",false) end
            if state.walking then
                local moved=horizontal(state.root.Position,state.lastPosition)
                if moved>.15 then state.lastMovement=self.elapsed;state.lastPosition=state.root.Position end
                if self.elapsed>state.moveDeadline or self.elapsed-state.lastMovement>2.8
                   or horizontal(state.root.Position,state.home)>22 then
                    self:_stop(state,"blocked",true)
                end
            elseif not alert and not talking and not state.pathPending and self.elapsed>=state.nextWalk then
                state.routeIndex=state.routeIndex%#state.route+1
                local target=state.route[state.routeIndex]
                if horizontal(target,state.root.Position)<.8 then
                    state.nextWalk=self.elapsed+9
                else
                    state.nextWalk=self.elapsed+12
                    self:_requestPath(state,target)
                end
            end
            self:_pose(state,elapsed,snapshot)
        end
    end
end

function Director:destroy()
    if self.destroyed then return end
    self.destroyed=true
    for _,state in ipairs(self.rigs) do
        state.generation=state.generation+1
        state.speakers={}
        if state.root.Parent then state.humanoid:MoveTo(state.root.Position) end
        if state.facing then state.facing.Enabled=false end
        if state.pathConnection then state.pathConnection:Disconnect();state.pathConnection=nil end
        for _,name in ipairs(JOINTS) do
            local motor=state.joints[name]
            if motor.Parent then motor.C0=state.originals[name] end
        end
    end
    for _,connection in ipairs(self.connections) do connection:Disconnect() end
    self.connections={}
end

return Director
