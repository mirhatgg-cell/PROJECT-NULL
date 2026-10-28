-- Native ocean water and restrained exterior lighting, initialized once.
-- No asset IDs, Terrain:Clear, perpetual loops, RemoteEvents or gameplay state.
local Environment = {}
local active

local function finite(n)
    return type(n) == "number" and n == n and math.abs(n) < math.huge
end

local function vector(value, positive)
    if type(value) ~= "table" or #value ~= 3 then return nil end
    for _, n in ipairs(value) do
        if not finite(n) or math.abs(n) > 4096 or (positive and (n <= 0 or n > 2048)) then return nil end
    end
    return Vector3.new(value[1], value[2], value[3])
end

function Environment.setup(config)
    if active and not active.destroyed then return active end
    local lighting = game:GetService("Lighting")
    local run = game:GetService("RunService")
    if not run:IsServer() then error("Ocean environment must be initialized on the server") end
    local terrain = workspace:FindFirstChildOfClass("Terrain")
    local state = {destroyed = false, filled = 0, failures = 0, waterReady = false,
                   created = {}, previous = {}, connections = {}, poweredLights = 0}
    local water = type(config) == "table" and config.water or nil
    local boxes = type(water) == "table" and water.fill_boxes or nil
    if terrain and type(boxes) == "table" and #boxes <= 160 then
        for _, box in ipairs(boxes) do
            local center = type(box) == "table" and vector(box.center, false) or nil
            local size = type(box) == "table" and vector(box.size, true) or nil
            if center and size then
                local ok, problem = pcall(function()
                    terrain:FillBlock(CFrame.new(center), size, Enum.Material.Water)
                end)
                if ok then state.filled = state.filled + 1 else
                    state.failures = state.failures + 1
                    warn("V11 ocean section unavailable: " .. tostring(problem))
                end
            else
                state.failures = state.failures + 1
                warn("V11 ocean section has invalid geometry")
            end
        end
        terrain.WaterColor = Color3.fromRGB(18, 46, 56)
        terrain.WaterTransparency = 0.34
        terrain.WaterReflectance = 0.22
        terrain.WaterWaveSize = 0.18
        terrain.WaterWaveSpeed = 8
        state.waterReady = state.filled == #boxes and state.failures == 0
    else
        warn("V11 ocean terrain/config is unavailable; interior systems remain active")
    end
    for _, key in ipairs({"ClockTime", "Brightness", "ExposureCompensation", "FogColor", "FogStart", "FogEnd", "OutdoorAmbient"}) do
        state.previous[key] = lighting[key]
    end
    -- Scene framing, not a canon time or depth. Original interior lights remain.
    lighting.ClockTime = 4.8
    lighting.Brightness = 0.8
    lighting.ExposureCompensation = -0.12
    lighting.OutdoorAmbient = Color3.fromRGB(56, 69, 80)
    lighting.FogColor = Color3.fromRGB(38, 61, 73)
    lighting.FogStart = 180
    lighting.FogEnd = 800
    local atmosphere = lighting:FindFirstChild("OceanAtmosphere_V11")
    if not atmosphere then
        atmosphere = Instance.new("Atmosphere")
        atmosphere.Name = "OceanAtmosphere_V11"
        atmosphere.Parent = lighting
        table.insert(state.created, atmosphere)
    end
    atmosphere.Density = 0.24
    atmosphere.Offset = 0.12
    atmosphere.Color = Color3.fromRGB(128, 158, 173)
    atmosphere.Decay = Color3.fromRGB(41, 60, 75)
    atmosphere.Glare = 0.08
    atmosphere.Haze = 1.6
    if terrain then
        local clouds = terrain:FindFirstChild("OceanClouds_V11")
        if not clouds then
            clouds = Instance.new("Clouds")
            clouds.Name = "OceanClouds_V11"
            clouds.Parent = terrain
            table.insert(state.created, clouds)
        end
        clouds.Cover = 0.66
        clouds.Density = 0.48
        clouds.Color = Color3.fromRGB(119, 137, 148)
    end
    -- The old circuit controller already owns screen/material changes. This
    -- visual adapter only binds newly tagged room luminaires to that same Bool.
    local facility = workspace:FindFirstChild("PROJECT_NULL_ARCH_P01")
    local byCircuit = {}
    if facility then
        for _, part in ipairs(facility:GetDescendants()) do
            if part:IsA("BasePart") and part:FindFirstChild("V11_CircuitVisual") then
                local reference = part:FindFirstChild("Circuit")
                local circuit = reference and reference:IsA("ObjectValue") and reference.Value
                if circuit and circuit:IsA("BoolValue") then
                    byCircuit[circuit] = byCircuit[circuit] or {}
                    for _, light in ipairs(part:GetDescendants()) do
                        if light:IsA("PointLight") or light:IsA("SurfaceLight") or light:IsA("SpotLight") then
                            table.insert(byCircuit[circuit], light)
                            state.poweredLights = state.poweredLights + 1
                        end
                    end
                end
            end
        end
    end
    for circuit, lights in pairs(byCircuit) do
        local function refresh()
            if state.destroyed then return end
            for _, light in ipairs(lights) do
                if light.Parent then light.Enabled = circuit.Value == true end
            end
        end
        refresh()
        table.insert(state.connections, circuit.Changed:Connect(refresh))
    end
    function state:destroy()
        if self.destroyed then return end
        self.destroyed = true
        for _, connection in ipairs(self.connections) do connection:Disconnect() end
        for _, object in ipairs(self.created) do pcall(function() object:Destroy() end) end
        for key, value in pairs(self.previous) do pcall(function() lighting[key] = value end) end
        -- Water belongs to this place. Never clear existing terrain on shutdown.
    end
    active = state
    return state
end

return Environment
