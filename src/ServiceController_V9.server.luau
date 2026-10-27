-- PROJECT: NULL V9 — server-authoritative service access and actual circuit state.
-- Main collision surfaces stay enabled during motion. No RemoteEvents are used.
local run = game:GetService("RunService")
if not run:IsServer() then return end

local facility = workspace:WaitForChild("PROJECT_NULL_ARCH_P01", 30)
if not facility then
    warn("V9 service controller: facility was not found")
    return
end

local STEPS = 30
local STEP_TIME = 0.025
local EPSILON = 0.000001
local AXES = {
    X = Vector3.new(1, 0, 0),
    Y = Vector3.new(0, 1, 0),
    Z = Vector3.new(0, 0, 1),
}
local OCCUPANCY_PADDING = Vector3.new(0.15, 0.15, 0.15)
local seenServices, seenStops, seenStatuses = {}, {}, {}

local function finite(value)
    return type(value) == "number" and value == value and value > -math.huge and value < math.huge
end

local function child(parent, name, className)
    local result = parent and parent:FindFirstChild(name)
    if result and result:IsA(className) then return result end
    return nil
end

local function liveHumanoid(part)
    local ancestor = part
    while ancestor and ancestor ~= workspace do
        if ancestor:IsA("Model") then
            local humanoid = ancestor:FindFirstChildOfClass("Humanoid")
            if humanoid and humanoid.Health > 0 then return humanoid end
        end
        ancestor = ancestor.Parent
    end
    return nil
end

local function authorized(player, target, prompt, permitted)
    if not player or not player:IsA("Player") or not target:IsDescendantOf(facility) then return false end
    if not prompt.Enabled then return false end
    local character = player.Character
    local humanoid = character and character:FindFirstChildOfClass("Humanoid")
    if not humanoid or humanoid.Health <= 0 then return false end
    local origin = character:FindFirstChild("Head") or character:FindFirstChild("HumanoidRootPart")
    if not origin or not origin:IsA("BasePart") then return false end
    local direction = target.Position - origin.Position
    local maxDistance = math.max(0, prompt.MaxActivationDistance) + 1
    if direction.Magnitude > maxDistance or direction.Magnitude < 0.0001 then return false end
    local params = RaycastParams.new()
    params.FilterType = Enum.RaycastFilterType.Exclude
    params.FilterDescendantsInstances = {character}
    local hit = workspace:Raycast(origin.Position, direction, params)
    return hit ~= nil and permitted[hit.Instance] == true
end

local function motion(state, progress)
    if state.axis == "Slide" then
        return CFrame.new(state.slide * progress)
    end
    local pivot = state.pivot
    return CFrame.new(pivot) * CFrame.fromAxisAngle(AXES[state.axis], math.rad(state.openAngle * progress))
        * CFrame.new(-pivot.X, -pivot.Y, -pivot.Z)
end

local function nextTarget(state, attemptedTarget)
    if state.progress <= EPSILON then return 1 end
    if state.progress >= 1 - EPSILON then return 0 end
    return 1 - attemptedTarget
end

local function refresh(state)
    state.current.Value = state.progress * state.openAngle
    state.isOpen.Value = state.progress >= 1 - EPSILON
    local action = state.target > state.progress and "Открыть" or "Закрыть"
    if state.progress > EPSILON and state.progress < 1 - EPSILON then
        action = action .. " (пауза)"
    end
    state.prompt.ActionText = action
end

local function candidateFrames(state, progress)
    local transform = motion(state, progress)
    local frames = {}
    for i, mover in ipairs(state.movers) do
        assert(mover.part:IsDescendantOf(facility), "A service mover was removed from the facility")
        frames[i] = transform * mover.closed
    end
    return frames
end

local function occupied(state, frames)
    for i, mover in ipairs(state.movers) do
        local hits = workspace:GetPartBoundsInBox(frames[i], mover.part.Size + OCCUPANCY_PADDING, state.overlap)
        for _, hit in ipairs(hits) do
            if liveHumanoid(hit) then return true end
        end
    end
    return false
end

local function applyFrames(state, frames, progress)
    -- A property failure must not leave half the assembly at the next pose.
    local previous = {}
    for i, mover in ipairs(state.movers) do previous[i] = mover.part.CFrame end
    local ok, problem = pcall(function()
        for i, mover in ipairs(state.movers) do mover.part.CFrame = frames[i] end
    end)
    if not ok then
        for i, mover in ipairs(state.movers) do
            pcall(function() mover.part.CFrame = previous[i] end)
        end
        error(problem, 0)
    end
    state.progress = progress
    state.current.Value = progress * state.openAngle
    state.isOpen.Value = progress >= 1 - EPSILON
end

local function activate(state, player)
    if state.busy or not authorized(player, state.panel, state.prompt, state.permitted) then return end
    state.busy = true
    local enabledBefore = state.prompt.Enabled
    state.prompt.Enabled = false
    local target = state.target
    local start = state.progress
    local ok, problem = xpcall(function()
        for step = 1, STEPS do
            local t = step / STEPS
            local smooth = t * t * (3 - 2 * t)
            local progress = start + (target - start) * smooth
            local frames = candidateFrames(state, progress)
            -- Reject the next occupied pose before assigning any CFrame.
            if occupied(state, frames) then break end
            applyFrames(state, frames, progress)
            task.wait(STEP_TIME)
        end
    end, function(message) return tostring(message) end)
    state.target = nextTarget(state, target)
    state.busy = false
    pcall(function() refresh(state) end)
    pcall(function() state.prompt.Enabled = enabledBefore end)
    if not ok then warn("V9 service motion stopped: " .. problem) end
end

local function bindService(config)
    if seenServices[config] then return end
    local panel = config.Parent
    local prompt = panel and child(panel, "V9_ServicePrompt", "ProximityPrompt")
    if not panel or not panel:IsA("BasePart") or not prompt then return end
    local pivot = child(config, "Pivot", "Vector3Value")
    local axis = child(config, "Axis", "StringValue")
    local angle = child(config, "OpenAngle", "NumberValue")
    local current = child(config, "CurrentAngle", "NumberValue")
    local isOpen = child(config, "IsOpen", "BoolValue")
    if not pivot or not axis or not angle or not current or not isOpen then
        warn("V9 service panel has incomplete metadata: " .. panel:GetFullName())
        return
    end
    if not finite(angle.Value) or math.abs(angle.Value) < EPSILON or not finite(current.Value) then return end
    if axis.Value ~= "Slide" and (not AXES[axis.Value] or math.abs(angle.Value) > 150) then return end
    local slide = child(config, "Slide", "Vector3Value")
    if axis.Value == "Slide" and not slide then return end
    local state = {
        panel = panel, prompt = prompt, pivot = pivot.Value, axis = axis.Value,
        openAngle = angle.Value, current = current, isOpen = isOpen,
        slide = slide and slide.Value or Vector3.new(0, 0, 0),
        movers = {}, permitted = {}, busy = false,
        progress = math.max(0, math.min(1, current.Value / angle.Value)),
    }
    local initialInverse = motion(state, state.progress):Inverse()
    local moverParts = {}
    local function addMover(part)
        if part and part:IsA("BasePart") and part:IsDescendantOf(facility) and not state.permitted[part] then
            state.permitted[part] = true
            table.insert(moverParts, part)
            table.insert(state.movers, {part = part, closed = initialInverse * part.CFrame})
        end
    end
    addMover(panel)
    for _, reference in ipairs(config:GetChildren()) do
        if reference:IsA("ObjectValue") and string.match(reference.Name, "^Moving_%d+$") then
            addMover(reference.Value)
        end
    end
    state.overlap = OverlapParams.new()
    state.overlap.FilterType = Enum.RaycastFilterType.Exclude
    state.overlap.FilterDescendantsInstances = moverParts
    state.target = state.progress > EPSILON and 0 or 1
    refresh(state)
    seenServices[config] = true
    prompt.Triggered:Connect(function(player) activate(state, player) end)
end

local function bindStop(prompt)
    if seenStops[prompt] then return end
    local button = prompt.Parent
    if not button or not button:IsA("BasePart") then return end
    local controls = child(facility, "Controls", "Folder")
    local circuits = controls and child(controls, "Circuits", "Folder")
    local amplifier = circuits and child(circuits, "AcousticAmplifiers", "BoolValue")
    if not amplifier then return end
    seenStops[prompt] = true
    local permitted = {[button] = true}
    prompt.Triggered:Connect(function(player)
        if authorized(player, button, prompt, permitted) then amplifier.Value = false end
    end)
end

local function bindStatus(config)
    if seenStatuses[config] then return end
    local circuitRef = child(config, "Circuit", "ObjectValue")
    local indicatorRef = child(config, "Indicator", "ObjectValue")
    local textRef = child(config, "Text", "ObjectValue")
    local caption = child(config, "Caption", "StringValue")
    local circuit = circuitRef and circuitRef.Value
    local indicator = indicatorRef and indicatorRef.Value
    local text = textRef and textRef.Value
    if not circuit or not circuit:IsA("BoolValue") or not indicator or not indicator:IsA("BasePart")
        or not text or not text:IsA("TextLabel") or not caption then return end
    local function update()
        if not indicator:IsDescendantOf(facility) or not text:IsDescendantOf(facility) then return end
        local on = circuit.Value == true
        indicator.Color = on and Color3.fromRGB(59, 191, 202) or Color3.fromRGB(180, 66, 55)
        text.Text = caption.Value .. "\n" .. (on and "ПИТАНИЕ ВКЛЮЧЕНО" or "ПИТАНИЕ ОТКЛЮЧЕНО")
    end
    seenStatuses[config] = true
    update()
    circuit.Changed:Connect(function() pcall(update) end)
end

local function inspect(instance)
    if instance:IsA("Folder") and instance.Name == "V9_Service" then
        bindService(instance)
    elseif instance:IsA("ProximityPrompt") and instance.Name == "V9_EStopPrompt" then
        bindStop(instance)
    elseif instance:IsA("Folder") and instance.Name == "V9_CircuitStatus" then
        bindStatus(instance)
    end
end

for _, instance in ipairs(facility:GetDescendants()) do inspect(instance) end
facility.DescendantAdded:Connect(function(instance)
    -- Deferred binding also permits complete off-tree assemblies to be inserted.
    task.defer(function() inspect(instance) end)
end)
