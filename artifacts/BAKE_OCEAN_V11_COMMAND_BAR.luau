-- Optional editor tool: run in Studio Command Bar with Play stopped.
-- The normal V11 game constructs the same native ocean automatically in Play.
local run = game:GetService("RunService")
assert(run:IsStudio() and not run:IsRunning(), "Остановите Play и выполните команду в редакторе Studio")
local folder = game:GetService("ServerScriptService"):FindFirstChild("ProjectNullV10")
assert(folder and folder:FindFirstChild("ShipConfig"), "Сначала откройте PROJECT_NULL_OCEAN_V11.rbxlx")
local config = require(folder.ShipConfig)
local terrain = workspace:FindFirstChildOfClass("Terrain")
assert(terrain and config.water and config.water.fill_boxes, "Нет конфигурации океана V11")
for _, box in ipairs(config.water.fill_boxes) do
    terrain:FillBlock(CFrame.new(box.center[1], box.center[2], box.center[3]),
        Vector3.new(box.size[1], box.size[2], box.size[3]), Enum.Material.Water)
end
terrain.WaterColor = Color3.fromRGB(18, 46, 56)
terrain.WaterTransparency = 0.34
terrain.WaterReflectance = 0.22
terrain.WaterWaveSize = 0.18
terrain.WaterWaveSpeed = 8
print("V11: вода создана в редакторе. Сохраните место через File → Save to File.")
