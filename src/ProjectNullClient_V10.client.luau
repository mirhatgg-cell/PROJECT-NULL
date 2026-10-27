-- PROJECT: NULL V10 — Russian operator interface, journal and bounded local effects.
-- All gameplay changes are requests. The server owns experiments, health and saves.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")
local Lighting = game:GetService("Lighting")
local SoundService = game:GetService("SoundService")
local TextService = game:GetService("TextService")
local UserInputService = game:GetService("UserInputService")

local player = Players.LocalPlayer
local playerGui = player:WaitForChild("PlayerGui", 30)
local remotes = ReplicatedStorage:WaitForChild("ProjectNullV10", 30)
if not playerGui or not remotes then
    warn("PROJECT: NULL V10: interface services did not appear")
    return
end
local request = remotes:WaitForChild("Request", 15)
local push = remotes:WaitForChild("Push", 15)
if not request or not push or not request:IsA("RemoteEvent") or not push:IsA("RemoteEvent") then return end

local oldGui = playerGui:FindFirstChild("ProjectNullV10")
if oldGui then oldGui:Destroy() end
for _, effectName in ipairs({"ProjectNullV10_Grade", "ProjectNullV10_Blur"}) do
    local effect = Lighting:FindFirstChild(effectName)
    if effect then effect:Destroy() end
end
local oldSounds = SoundService:FindFirstChild("ProjectNullV10_Audio")
if oldSounds then oldSounds:Destroy() end

local function make(className, parent, properties)
    local object = Instance.new(className)
    for key, value in pairs(properties or {}) do object[key] = value end
    object.Parent = parent
    return object
end
local C = {
    background = Color3.fromRGB(13, 23, 29),
    surface = Color3.fromRGB(23, 37, 45),
    raised = Color3.fromRGB(32, 49, 58),
    border = Color3.fromRGB(68, 91, 102),
    text = Color3.fromRGB(225, 235, 237),
    muted = Color3.fromRGB(161, 183, 191),
    cyan = Color3.fromRGB(85, 207, 213),
    amber = Color3.fromRGB(232, 183, 96),
    red = Color3.fromRGB(231, 112, 102),
    green = Color3.fromRGB(130, 208, 168),
}
local PROTOCOLS = {
    P01 = "СЕНСОРНАЯ СИНХРОНИЗАЦИЯ",
    P02 = "НАРУШЕНИЕ ВОСПРИЯТИЯ",
    P03 = "ПАМЯТЬ И РЕКОНСТРУКЦИЯ",
    P04 = "АВТОНОМНЫЙ НАБЛЮДАТЕЛЬ",
    P05 = "ГРАНИЦА СИМУЛЯЦИИ",
}
local PHASES = {
    idle = "ОЖИДАНИЕ", prepared = "ПОДГОТОВЛЕНО", running = "ИСПЫТАНИЕ",
    completed = "ЗАВЕРШЕНО", failed = "ОСТАНОВЛЕНО", calibrating = "КАЛИБРОВКА",
}
local snapshot = {phase = "idle", telemetry = {}, profile = {}}
local currentModal, lastContextKey = nil, ""
local documents, dialogueCache = {}, {}
local muted, reducedEffects = false, false
local uiWidth, uiHeight, bodyWidth = 800, 600, 660
local lastRequest = {}
local lastCueKey, lastPhase = "", ""
local modalSignature, cueSignature = "", ""
local noticeUntil = 0
local connections = {}

local screen = make("ScreenGui", playerGui, {
    Name = "ProjectNullV10", ResetOnSpawn = false, IgnoreGuiInset = false,
    DisplayOrder = 40, ZIndexBehavior = Enum.ZIndexBehavior.Sibling,
})
local root = make("Frame", screen, {Name = "Root", Size = UDim2.fromScale(1, 1), BackgroundTransparency = 1})
local function corner(object, radius) make("UICorner", object, {CornerRadius = UDim.new(0, radius or 6)}) end
local function border(object, color)
    make("UIStroke", object, {Color = color or C.border, Thickness = 1, Transparency = 0.2})
end
local function label(parent, text, size, color, height)
    local item = make("TextLabel", parent, {
        Name = "Text", BackgroundTransparency = 1, BorderSizePixel = 0,
        Size = UDim2.new(1, 0, 0, height or 24), Text = tostring(text or ""),
        TextSize = size or 15, Font = Enum.Font.Code, TextColor3 = color or C.text,
        TextXAlignment = Enum.TextXAlignment.Left, TextYAlignment = Enum.TextYAlignment.Top,
        TextWrapped = true, RichText = false,
    })
    return item
end
local function block(parent, text, size, color)
    local value = tostring(text or "")
    local textSize = size or 15
    local measured = TextService:GetTextSize(value, textSize, Enum.Font.Code, Vector2.new(math.max(180, bodyWidth), 10000))
    return label(parent, value, textSize, color, math.max(textSize + 6, measured.Y + 8))
end
local function send(action, argument)
    local now = os.clock()
    if now - (lastRequest[action] or -10) < 0.18 then return end
    lastRequest[action] = now
    request:FireServer(action, argument)
end
local function button(parent, text, callback, color)
    local item = make("TextButton", parent, {
        Name = "Action", Size = UDim2.new(1, 0, 0, 40), BackgroundColor3 = C.raised,
        BorderSizePixel = 0, Text = text, Font = Enum.Font.Code, TextSize = 14,
        TextColor3 = color or C.text, AutoButtonColor = true, TextWrapped = true, RichText = false,
    })
    corner(item, 4)
    item.Activated:Connect(callback)
    return item
end
local function enabled(item, value)
    item.Active = value
    item.Selectable = value
    item.AutoButtonColor = value
    item.TextTransparency = value and 0 or 0.58
    item.BackgroundTransparency = value and 0 or 0.45
end
local function clear(parent)
    for _, child in ipairs(parent:GetChildren()) do
        if not child:IsA("UIListLayout") and not child:IsA("UIPadding") then child:Destroy() end
    end
end
local function owned()
    local owner = snapshot.owner
    return owner == nil or owner == 0 or owner == player.UserId
end
local function finite(value, fallback)
    if type(value) ~= "number" or value ~= value or value == math.huge or value == -math.huge then return fallback end
    return value
end
local function clamp(value, low, high) return math.max(low, math.min(high, value)) end
local function tableCount(value)
    local count = 0
    if type(value) == "table" then for _ in pairs(value) do count = count + 1 end end
    return count
end
local function stringify(value)
    if type(value) ~= "table" then return tostring(value or "") end
    local lines = {}
    for key, item in pairs(value) do
        if type(item) ~= "table" then table.insert(lines, tostring(key) .. ": " .. tostring(item)) end
    end
    table.sort(lines)
    return table.concat(lines, "\n")
end

-- These short sounds are shipped with Roblox; no uploaded asset ID or HTTP request.
local audioFolder = make("Folder", SoundService, {Name = "ProjectNullV10_Audio"})
local cueSound = make("Sound", audioFolder, {
    Name = "Cue", SoundId = "rbxasset://sounds/electronicpingshort.wav", Volume = 0.16,
})
local clickSound = make("Sound", audioFolder, {
    Name = "Relay", SoundId = "rbxasset://sounds/switch.wav", Volume = 0.12,
})
local grade = make("ColorCorrectionEffect", Lighting, {
    Name = "ProjectNullV10_Grade", Enabled = true, Brightness = 0, Contrast = 0,
    Saturation = 0, TintColor = Color3.new(1, 1, 1),
})
local blur = make("BlurEffect", Lighting, {Name = "ProjectNullV10_Blur", Size = 0, Enabled = true})
local function play(sound)
    if not muted then
        -- Missing local audio must never interrupt the operator interface.
        pcall(function() sound:Play() end)
    end
end

local hud = make("Frame", root, {
    Name = "Telemetry", AnchorPoint = Vector2.new(1, 0), Position = UDim2.new(1, -12, 0, 12),
    Size = UDim2.fromOffset(300, 188), BackgroundColor3 = C.background, BackgroundTransparency = 0.1,
})
corner(hud); border(hud)
make("UIPadding", hud, {PaddingLeft = UDim.new(0, 12), PaddingRight = UDim.new(0, 12), PaddingTop = UDim.new(0, 10)})
local hudTitle = label(hud, "PROJECT: NULL / B2", 13, C.cyan, 20)
local hudPhase = label(hud, "ОЖИДАНИЕ СИСТЕМЫ", 13, C.muted, 20)
hudPhase.Position = UDim2.fromOffset(0, 23)
local hudObjective = label(hud, "Подойдите к посту подготовки E-01. Удерживайте E для взаимодействия.", 12, C.text, 56)
hudObjective.Position = UDim2.fromOffset(0, 46)
local meterY = 107
local function meter(title, offset)
    local text = label(hud, title, 12, C.muted, 18)
    text.Position = UDim2.fromOffset(0, offset)
    local track = make("Frame", hud, {
        Position = UDim2.new(0, 0, 0, offset + 19), Size = UDim2.new(1, 0, 0, 4),
        BackgroundColor3 = C.raised, BorderSizePixel = 0,
    })
    local fill = make("Frame", track, {Size = UDim2.fromScale(0, 1), BackgroundColor3 = C.cyan, BorderSizePixel = 0})
    return text, fill
end
local temperatureText, temperatureFill = meter("ТЕМПЕРАТУРА —", meterY)
local stressText, stressFill = meter("НАГРУЗКА —", meterY + 32)

local quick = make("Frame", root, {
    Name = "QuickControls", AnchorPoint = Vector2.new(0, 1), Position = UDim2.new(0, 12, 1, -12),
    Size = UDim2.fromOffset(386, 38), BackgroundTransparency = 1,
})
make("UIListLayout", quick, {FillDirection = Enum.FillDirection.Horizontal, Padding = UDim.new(0, 6), SortOrder = Enum.SortOrder.LayoutOrder})
local openModal, renderModal
local journalButton = button(quick, "ЖУРНАЛ [J]", function()
    if currentModal and currentModal.kind == "journal" then
        currentModal = nil
        send("close")
    else
        currentModal = {kind = "journal", title = "ЛИЧНЫЙ ЖУРНАЛ"}
    end
    modalSignature = ""
    if renderModal then renderModal() end
end, C.cyan)
local muteButton
muteButton = button(quick, "ЗВУК: ВКЛ", function()
    muted = not muted
    cueSound.Volume = muted and 0 or 0.16
    clickSound.Volume = muted and 0 or 0.12
    if muted then cueSound:Stop(); clickSound:Stop() end
    muteButton.Text = muted and "ЗВУК: ВЫКЛ" or "ЗВУК: ВКЛ"
end)
local effectsButton
effectsButton = button(quick, "ЭФФЕКТЫ: ВКЛ", function()
    reducedEffects = not reducedEffects
    effectsButton.Text = reducedEffects and "ЭФФЕКТЫ: ВЫКЛ" or "ЭФФЕКТЫ: ВКЛ"
end)
for index, item in ipairs({journalButton, muteButton, effectsButton}) do
    item.LayoutOrder = index
    item.Size = UDim2.new(1 / 3, -4, 1, 0)
end

local toast = make("TextLabel", root, {
    Name = "Notice", AnchorPoint = Vector2.new(0.5, 0), Position = UDim2.new(0.5, 0, 0, 12),
    Size = UDim2.fromOffset(500, 48), BackgroundColor3 = C.surface, BackgroundTransparency = 0.05,
    Font = Enum.Font.Code, TextSize = 14, TextColor3 = C.amber, TextWrapped = true,
    RichText = false, Visible = false, ZIndex = 12,
})
corner(toast); border(toast, C.amber)
local function notice(text)
    toast.Text = tostring(text or "")
    toast.Visible = toast.Text ~= ""
    noticeUntil = os.clock() + 5
end

local overlay = make("Frame", root, {
    Name = "Modal", Size = UDim2.fromScale(1, 1), BackgroundColor3 = Color3.new(0, 0, 0),
    BackgroundTransparency = 0.42, Visible = false, ZIndex = 20,
})
local modal = make("Frame", overlay, {
    Name = "Panel", AnchorPoint = Vector2.new(0.5, 0.5), Position = UDim2.fromScale(0.5, 0.5),
    Size = UDim2.fromOffset(760, 530), BackgroundColor3 = C.background, BorderSizePixel = 0, ZIndex = 21,
})
corner(modal, 8); border(modal, C.cyan)
local modalTitle = label(modal, "ОПЕРАТОРСКИЙ ТЕРМИНАЛ", 17, C.cyan, 30)
modalTitle.Position = UDim2.fromOffset(18, 18)
modalTitle.Size = UDim2.new(1, -88, 0, 45)
modalTitle.ZIndex = 22
local closeButton = button(modal, "X", function()
    currentModal = nil
    overlay.Visible = false
    modalSignature = ""
    send("close")
end)
closeButton.Size = UDim2.fromOffset(38, 36)
closeButton.AnchorPoint = Vector2.new(1, 0)
closeButton.Position = UDim2.new(1, -14, 0, 14)
closeButton.ZIndex = 22
local body = make("ScrollingFrame", modal, {
    Name = "Body", BackgroundTransparency = 1, BorderSizePixel = 0,
    Position = UDim2.fromOffset(18, 72), Size = UDim2.new(1, -36, 1, -113),
    ScrollBarThickness = 5, ScrollBarImageColor3 = C.border,
    CanvasSize = UDim2.fromOffset(0, 0), AutomaticCanvasSize = Enum.AutomaticSize.Y,
    ScrollingDirection = Enum.ScrollingDirection.Y, ZIndex = 22,
})
make("UIListLayout", body, {Padding = UDim.new(0, 10), SortOrder = Enum.SortOrder.LayoutOrder})
make("UIPadding", body, {PaddingRight = UDim.new(0, 8), PaddingBottom = UDim.new(0, 14)})
local modalFoot = label(modal, "СЛЕДУЙТЕ ПРОТОКОЛУ · E — ВЗАИМОДЕЙСТВИЕ · J — ЖУРНАЛ", 11, C.muted, 24)
modalFoot.Position = UDim2.new(0, 18, 1, -31)
modalFoot.Size = UDim2.new(1, -36, 0, 24)
modalFoot.ZIndex = 22

local cuePanel = make("Frame", root, {
    Name = "ExperimentCue", AnchorPoint = Vector2.new(1, 1), Position = UDim2.new(1, -12, 1, -62),
    Size = UDim2.fromOffset(410, 310), BackgroundColor3 = C.background,
    BackgroundTransparency = 0.03, Visible = false, ZIndex = 8,
})
corner(cuePanel); border(cuePanel, C.cyan)
local cueTitle = label(cuePanel, "СИГНАЛ ИСПЫТАНИЯ", 13, C.cyan, 18)
cueTitle.Position = UDim2.fromOffset(12, 10)
cueTitle.Size = UDim2.new(1, -24, 0, 18)
local cueTime = label(cuePanel, "", 12, C.amber, 18)
cueTime.Position = UDim2.fromOffset(12, 34)
cueTime.Size = UDim2.new(1, -24, 0, 18)
local cueScroll = make("ScrollingFrame", cuePanel, {
    Name = "CueBody", BackgroundTransparency = 1, BorderSizePixel = 0,
    Position = UDim2.fromOffset(12, 59), Size = UDim2.new(1, -24, 1, -69),
    ScrollBarThickness = 5, ScrollBarImageColor3 = C.cyan,
    CanvasSize = UDim2.fromOffset(0, 0), AutomaticCanvasSize = Enum.AutomaticSize.Y,
    ScrollingDirection = Enum.ScrollingDirection.Y,
})
make("UIListLayout", cueScroll, {Padding = UDim.new(0, 9), SortOrder = Enum.SortOrder.LayoutOrder})
make("UIPadding", cueScroll, {PaddingRight = UDim.new(0, 8), PaddingBottom = UDim.new(0, 8)})
local cueText = label(cueScroll, "", 14, C.text, 58)
local cueEvidence = label(cueScroll, "", 14, C.cyan, 80)
local cueInstruction = label(cueScroll, "", 13, C.amber, 50)
local cueButtons = make("Frame", cueScroll, {Size = UDim2.new(1, 0, 0, 96), BackgroundTransparency = 1})
make("UIListLayout", cueButtons, {FillDirection = Enum.FillDirection.Vertical, Padding = UDim.new(0, 6), SortOrder = Enum.SortOrder.LayoutOrder})
for index, item in ipairs({cueText, cueEvidence, cueInstruction, cueButtons}) do item.LayoutOrder = index end
local responseButtons = {}

local consoleStatus
local function listDocuments(profile)
    local result = {}
    local present = {}
    for _, doc in ipairs(type(profile.journal) == "table" and profile.journal or {}) do
        if type(doc) == "table" and type(doc.id) == "string" then documents[doc.id] = doc end
    end
    if type(profile.documents) == "table" then
        for key, value in pairs(profile.documents) do
            local id = type(value) == "string" and value or (type(key) == "string" and value and key or nil)
            if type(value) == "table" and type(value.id) == "string" then id = value.id; documents[id] = value end
            if id and not present[id] then
                present[id] = true
                table.insert(result, documents[id] or {id = id, title = id, body = "Подойдите к найденному документу, чтобы прочитать его снова."})
            end
        end
    end
    for id, doc in pairs(documents) do
        if not present[id] then present[id] = true; table.insert(result, doc) end
    end
    table.sort(result, function(a, b) return tostring(a.id) < tostring(b.id) end)
    return result
end
local function formattedRequirements()
    local requirements = snapshot.requirements
    if type(requirements) == "string" then return requirements end
    if type(requirements) ~= "table" then return "Проверьте питание, охлаждение и калибровку перед запуском." end
    local lines = {}
    for key, value in pairs(requirements) do
        if type(value) == "table" then
            table.insert(lines, tostring(value.label or value.name or key) .. ": " .. tostring(value.enabled ~= nil and (value.enabled and "ВКЛ" or "ВЫКЛ") or value.status or value.reason or value.ready or value.ok or ""))
        else
            table.insert(lines, tostring(key) .. ": " .. tostring(value))
        end
    end
    table.sort(lines)
    return table.concat(lines, "\n")
end
local function addRequest(text, action, argument, canUse, color)
    local item = button(body, text, function() send(action, argument); play(clickSound) end, color)
    enabled(item, canUse ~= false)
    return item
end
local function renderConsole(context)
    local protocol = context.argument or snapshot.experiment or "P01"
    block(body, protocol .. " / " .. (PROTOCOLS[protocol] or "ПРОТОКОЛ"), 17, C.text)
    consoleStatus = block(body, "", 14, C.muted)
    block(body, "Запуск: выбрать протокол → включить охлаждение → откалибровать → начать. Ответы во время испытания отображаются в отдельной панели. При угрозе используйте аварийный стоп.", 14, C.muted)
    block(body, formattedRequirements(), 13, C.muted)
    if type(snapshot.evidenceRequired) == "table" and #snapshot.evidenceRequired > 0 then
        block(body, "ПЕРЕД КАЛИБРОВКОЙ НАЙДИТЕ И ПРОЧИТАЙТЕ:", 14, C.amber)
        for _, document in ipairs(snapshot.evidenceRequired) do
            block(body, tostring(document.title or document.id or "Документ") .. " / " .. tostring(document.room or "E-07"), 14, C.amber)
        end
        block(body, "Независимые записи нужны для реконструкции событий P03. Найденные документы сохраняются в личном журнале.", 13, C.muted)
    end
    local mine = owned()
    local running = snapshot.phase == "running"
    addRequest("ВЫБРАТЬ " .. protocol, "select", protocol, mine and not running, C.cyan)
    addRequest("КАЛИБРОВАТЬ", "calibrate", nil, mine and not running and snapshot.evidenceReady ~= false, C.cyan)
    addRequest("ЗАПУСТИТЬ ИСПЫТАНИЕ", "start", nil, mine and snapshot.phase == "prepared", C.green)
    addRequest("АВАРИЙНО ОСТАНОВИТЬ", "abort", nil, mine and (running or snapshot.phase == "prepared"), C.red)
    addRequest("СБРОСИТЬ ЦИКЛ", "reset", nil, mine and (snapshot.phase == "completed" or snapshot.phase == "failed" or (snapshot.phase == "idle" and type(snapshot.owner) == "number" and snapshot.owner ~= 0)), C.amber)
    if not mine then block(body, "Пост занят другим оператором. Наблюдение доступно; управление остаётся у владельца цикла.", 13, C.amber) end
end
local function renderJournal()
    local profile = type(snapshot.profile) == "table" and snapshot.profile or {}
    block(body, "ЛИЧНЫЙ АРХИВ / СОБРАННЫЕ СВИДЕТЕЛЬСТВА", 16, C.cyan)
    block(body, tostring(profile.saveStatus or "Состояние сохранения ещё не получено."), 13, C.muted)
    local completed = {}
    for id, value in pairs(type(profile.completed) == "table" and profile.completed or {}) do
        if value then table.insert(completed, tostring(id)) end
    end
    table.sort(completed)
    block(body, "Пройдено: " .. (#completed > 0 and table.concat(completed, ", ") or "нет завершённых протоколов"), 14, C.green)
    addRequest("СОХРАНИТЬ ПРОГРЕСС", "save", nil, true, C.cyan)
    local docs = listDocuments(profile)
    block(body, "Документы: " .. tostring(#docs), 14, C.text)
    if #docs == 0 then block(body, "Найдите бумажные журналы и папки в помещениях комплекса. Удерживайте E рядом с документом.", 14, C.muted) end
    for _, doc in ipairs(docs) do
        local entry = doc
        button(body, tostring(entry.title or entry.id) .. (entry.room and (" / " .. entry.room) or ""), function()
            openModal({kind = "document", argument = entry.id, title = entry.title, data = entry})
        end, C.text)
    end
    block(body, "ЖУРНАЛ ИСПЫТАНИЙ", 14, C.cyan)
    local records = type(profile.records) == "table" and profile.records or {}
    if #records == 0 then block(body, "Подтверждённые результаты появятся после испытания.", 13, C.muted) end
    for index = #records, math.max(1, #records - 11), -1 do
        local record = records[index]
        if record then
            if type(record) == "table" then
                block(body, tostring(record.experiment or record.id or "Протокол") .. " / " .. tostring(record.result or record.status or record.outcome or "записан") .. "\n" .. tostring(record.summary or record.detail or record.timestamp or ""), 13, C.muted)
            else block(body, tostring(record), 13, C.muted) end
        end
    end
end
renderModal = function()
    if not currentModal then overlay.Visible = false; consoleStatus = nil; return end
    overlay.Visible = true
    local profile = type(snapshot.profile) == "table" and snapshot.profile or {}
    local context = currentModal
    local signature = table.concat({context.kind or "", context.argument or "", context.title or "", snapshot.phase or "", snapshot.experiment or "", tostring(snapshot.owner or ""), tostring(tableCount(profile.documents)), tostring(tableCount(profile.records)), tostring(profile.saveStatus or ""), tostring(tableCount(snapshot.evidenceRequired)), tostring(uiWidth)}, "|")
    if signature == modalSignature then return end
    modalSignature = signature
    clear(body); consoleStatus = nil
    body.CanvasPosition = Vector2.new(0, 0)
    modalTitle.Text = tostring(context.title or "ТЕРМИНАЛ PROJECT: NULL")
    if context.kind == "console" then
        renderConsole(context)
    elseif context.kind == "document" then
        local doc = context.data or documents[context.argument] or context
        block(body, tostring(doc.title or context.title or "ДОКУМЕНТ"), 18, C.cyan)
        block(body, tostring(doc.id or context.argument or "") .. "  /  " .. tostring(doc.room or "Архив комплекса"), 12, C.muted)
        block(body, tostring(doc.body or "Текст документа не получен. Взаимодействуйте с оригиналом в помещении."), 16, C.text)
        button(body, "К ЛИЧНОМУ ЖУРНАЛУ", function() openModal({kind = "journal", title = "ЛИЧНЫЙ ЖУРНАЛ"}) end, C.cyan)
    elseif context.kind == "npc" then
        local data = context.data or dialogueCache[context.argument] or context
        block(body, tostring(data.name or context.title or "СОТРУДНИК"), 18, C.cyan)
        block(body, tostring(data.role or "Персонал комплекса"), 13, C.muted)
        block(body, tostring(data.text or data.body or context.body or "Следуйте инструкции действующего протокола."), 16, C.text)
    elseif context.kind == "journal" or context.kind == "records" then
        renderJournal()
    elseif context.kind == "cooling" then
        block(body, "ХОЛОДИЛЬНЫЙ КОНТУР / THERM", 18, C.cyan)
        block(body, "Охлаждение отводит тепло экспериментального оборудования. Для работы требуется питание вентиляции. Прерывание охлаждения повышает температуру; защита остановит цикл при превышении порога.", 15, C.text)
        addRequest("ВКЛЮЧИТЬ ОХЛАЖДЕНИЕ", "cooling", true, true, C.green)
        addRequest("ОТКЛЮЧИТЬ ОХЛАЖДЕНИЕ", "cooling", false, true, C.amber)
    elseif context.kind == "repair" then
        block(body, "СЕРВИСНЫЙ ПОСТ / ВОССТАНОВЛЕНИЕ", 18, C.cyan)
        block(body, tostring(context.body or "После аварийной остановки замените расходный блок и восстановите оборудование. Во время испытания ремонт запрещён."), 15, C.text)
        addRequest("ВОССТАНОВИТЬ ОБОРУДОВАНИЕ", "repair", nil, snapshot.phase ~= "running", C.green)
    elseif context.kind == "supply" then
        block(body, "ЧИСТЫЕ РАСХОДНЫЕ МАТЕРИАЛЫ", 18, C.cyan)
        block(body, tostring(context.body or "Получите сменный расходный блок для обслуживания. Запас ограничен вместимостью сервисного комплекта."), 15, C.text)
        addRequest("ПОЛУЧИТЬ РАСХОДНЫЙ БЛОК", "supply", nil, true, C.cyan)
    elseif context.kind == "medical" then
        block(body, "МЕДИЦИНСКИЙ ПОСТ / ВОССТАНОВЛЕНИЕ", 18, C.cyan)
        block(body, tostring(context.body or "После остановки эксперимента пройдите восстановление. Медицинская помощь во время активного испытания недоступна."), 15, C.text)
        addRequest("ПРОЙТИ ВОССТАНОВЛЕНИЕ", "medical", nil, snapshot.phase ~= "running", C.green)
    else
        block(body, tostring(context.body or "Подойдите к действующему посту взаимодействия."), 15, C.text)
    end
    -- Sibling Z-index avoids click-through between body controls and the backdrop.
    for _, descendant in ipairs(body:GetDescendants()) do
        if descendant:IsA("GuiObject") then descendant.ZIndex = 23 end
    end
end
openModal = function(context)
    currentModal = context
    modalSignature = ""
    renderModal()
end

local function observableEvidence(cue)
    local lines = {}
    if cue.kind == "sync" then
        table.insert(lines, "СВЕТОВОЙ КАНАЛ: " .. tostring(cue.visual or "—"))
        table.insert(lines, "АКУСТИЧЕСКИЙ КАНАЛ: " .. tostring(cue.audio or "—") .. " / " .. tostring(cue.frequency or "—") .. " Гц")
    elseif cue.kind == "measurement" then
        table.insert(lines, "ЗАДАНИЕ: " .. tostring(cue.targetDistance or "—") .. " stud")
        local measurements = type(cue.measurements) == "table" and cue.measurements or {}
        local signs = type(cue.signs) == "table" and cue.signs or {}
        for index, name in ipairs({"ЛЕВЫЙ", "ЦЕНТР", "ПРАВЫЙ"}) do
            table.insert(lines, name .. ": лазер " .. tostring(measurements[index] or "—") .. " stud / вывеска «" .. tostring(signs[index] or "—") .. "»")
        end
    elseif cue.kind == "reconstruction" then
        table.insert(lines, "ВОССТАНОВЛЕНИЕ / СОБЫТИЕ " .. tostring(cue.reconstructionStep or snapshot.round or "—"))
    elseif cue.kind == "observer" then
        local modes = {tracking = "ОПТИКА ОТКРЫТА", adapting = "ПРОДЛЁННОЕ СКАНИРОВАНИЕ", occluded = "ШТОРКА ЗАКРЫТА"}
        table.insert(lines, modes[cue.observerMode] or tostring(cue.observerMode or "—"))
        table.insert(lines, "Память наблюдателя: " .. tostring(cue.observerMemory or 0) .. " прохода")
    elseif cue.kind == "boundary" then
        table.insert(lines, "ВИРТУАЛЬНЫЙ КАНАЛ: " .. tostring(cue.virtualReading or "—"))
        table.insert(lines, "НЕЗАВИСИМЫЙ КАНАЛ: " .. tostring(cue.physicalReading or "—"))
        table.insert(lines, "ЭТАЛОН: " .. (cue.referenceQuality == "stable" and "СТАБИЛЕН" or "НЕСТАБИЛЕН") .. " / ДОПУСК: " .. tostring(cue.tolerance or 0.2))
    end
    if cue.evidence and cue.evidence ~= "" then table.insert(lines, tostring(cue.evidence)) end
    return table.concat(lines, "\n")
end
local function cueInstructionText(cue)
    if cue.kind == "measurement" then
        return "Дойдите до выбранного датчика в E-10 и удерживайте E. Датчики подписаны ЛЕВЫЙ / ЦЕНТР / ПРАВЫЙ. Кнопки ниже показывают направления; ответ принимается у физического датчика."
    elseif cue.kind == "observer" then
        return cue.movementRequired and "После начала сигнала сделайте настоящий шаг рядом с пультом, затем нажмите «Пройти сектор». Двигаться можно только при закрытой шторке." or string.format("Оставайтесь неподвижны %.0f сек. после начала сигнала, затем нажмите «Замереть». Открытая оптика обнаруживает настоящее движение персонажа.", math.max(0, finite(cue.holdDuration, 2)))
    elseif cue.kind == "sync" then
        return "Звук дублируется текстом. Сравните оба канала; при расхождении отклоните импульс."
    end
    return "Дождитесь начала сигнала и выберите действие по показаниям. Результат попадёт в журнал испытания."
end
local function cueButtonReady(cue, id)
    if cue.kind == "measurement" then return false end
    local readyAt = finite(cue.readyAt, 0)
    if cue.kind == "observer" and cue.observerMode ~= "occluded" and id == "hold" then readyAt = readyAt + math.max(0, finite(cue.holdDuration, 2)) end
    return workspace:GetServerTimeNow() >= readyAt
end
local function resizeCue()
    local width = math.max(190, math.min(uiWidth - 24, 450))
    local contentWidth = width - 42
    local contentHeight = 0
    for _, item in ipairs({cueText, cueEvidence, cueInstruction}) do
        local measured = TextService:GetTextSize(item.Text, item.TextSize, Enum.Font.Code, Vector2.new(contentWidth, 10000))
        local height = math.max(item.TextSize + 8, measured.Y + 8)
        item.Size = UDim2.new(1, 0, 0, height)
        contentHeight = contentHeight + height + 9
    end
    contentHeight = contentHeight + cueButtons.Size.Y.Offset + 80
    local cue = type(snapshot.cue) == "table" and snapshot.cue or {}
    local physicalNarrow = uiWidth < 720 and (cue.kind == "measurement" or cue.kind == "observer")
    if physicalNarrow then
        -- Walking trials leave the lower touch area free for Roblox movement controls.
        cuePanel.AnchorPoint = Vector2.new(1, 0)
        cuePanel.Position = UDim2.new(1, -12, 0, 12)
        cuePanel.Size = UDim2.fromOffset(width, math.min(contentHeight, 340, math.max(100, uiHeight * 0.45)))
    else
        cuePanel.AnchorPoint = Vector2.new(1, 1)
        cuePanel.Position = UDim2.new(1, -12, 1, -62)
        cuePanel.Size = UDim2.fromOffset(width, math.min(math.max(220, contentHeight), math.max(180, uiHeight - 90)))
    end
    -- A narrow display gives the actionable signal priority over duplicate HUD text.
    hud.Visible = not (uiWidth < 720 and cuePanel.Visible)
end
local function updateCue()
    local cue = type(snapshot.cue) == "table" and snapshot.cue or nil
    local running = snapshot.phase == "running" and snapshot.owner == player.UserId
    cuePanel.Visible = running and cue ~= nil
    if not cuePanel.Visible then cueSignature = ""; hud.Visible = true; return end
    cueTitle.Text = tostring(snapshot.experiment or "P--") .. " / ЭТАП " .. tostring(snapshot.round or "—") .. "/" .. tostring(snapshot.totalRounds or "—")
    cueText.Text = tostring(cue.label or snapshot.objective or "Наблюдайте за показаниями.")
    cueEvidence.Text = observableEvidence(cue)
    cueInstruction.Text = cueInstructionText(cue)
    local options = type(cue.options) == "table" and cue.options or {}
    local parts = {tostring(snapshot.experiment), tostring(cue.kind), tostring(cue.label), tostring(cue.deadline)}
    for _, option in ipairs(options) do table.insert(parts, tostring(option.id) .. ":" .. tostring(option.label)) end
    local signature = table.concat(parts, "|")
    if signature ~= cueSignature then
        cueSignature = signature
        clear(cueButtons)
        responseButtons = {}
        cueScroll.CanvasPosition = Vector2.new(0, 0)
        for index, option in ipairs(options) do
            if index <= 6 and type(option) == "table" and type(option.id) == "string" then
                local optionId = option.id
                local response = button(cueButtons, tostring(option.label or option.id), function()
                    if cue.kind ~= "measurement" and cueButtonReady(cue, optionId) then
                        send("respond", optionId)
                        play(clickSound)
                    end
                end, C.cyan)
                response.LayoutOrder = index
                response.Size = UDim2.new(1, 0, 0, 36)
                responseButtons[optionId] = response
                enabled(response, cueButtonReady(cue, optionId))
            end
        end
        local count = math.min(#options, 6)
        cueButtons.Size = UDim2.new(1, 0, 0, math.max(0, count * 42 - 6))
        for _, descendant in ipairs(cueScroll:GetDescendants()) do
            if descendant:IsA("GuiObject") then descendant.ZIndex = 9 end
        end
        if lastCueKey ~= signature then
            -- Relative pitches identify acoustic channels; the text remains canonical.
            cueSound.PlaybackSpeed = ({A = 0.8, B = 1, C = 1.25})[cue.audio] or 1
            play(cueSound)
            lastCueKey = signature
        end
    end
    resizeCue()
end

local function refreshSnapshot()
    if snapshot.phase == "running" and lastPhase ~= "running" and snapshot.owner == player.UserId then
        -- Preserve the server's physical console anchor while giving the signal room.
        currentModal = nil
        overlay.Visible = false
        modalSignature = ""
    end
    local telemetry = type(snapshot.telemetry) == "table" and snapshot.telemetry or {}
    hudTitle.Text = "PROJECT: NULL / " .. tostring(snapshot.experiment or "B2")
    hudPhase.Text = PHASES[snapshot.phase] or tostring(snapshot.phase or "ОЖИДАНИЕ")
    hudPhase.TextColor3 = snapshot.phase == "failed" and C.red or (snapshot.phase == "running" and C.cyan or C.muted)
    hudObjective.Text = tostring(snapshot.objective or "Найдите пост подготовки E-01. Удерживайте E у оборудования.")
    local temperature = finite(telemetry.temperature, nil)
    local stress = finite(telemetry.stress, nil)
    temperatureText.Text = temperature and string.format("ТЕМПЕРАТУРА %.1f °C / ОХЛ. %s", temperature, telemetry.cooling and "ВКЛ" or "ВЫКЛ") or "ТЕМПЕРАТУРА —"
    temperatureFill.Size = UDim2.fromScale(temperature and clamp((temperature - 15) / 75, 0, 1) or 0, 1)
    temperatureFill.BackgroundColor3 = temperature and temperature >= 65 and C.red or C.cyan
    stressText.Text = stress and string.format("НАГРУЗКА %.0f%% / ЦИКЛ %.0f%%", stress, finite(telemetry.progress, 0) <= 1 and finite(telemetry.progress, 0) * 100 or finite(telemetry.progress, 0)) or "НАГРУЗКА —"
    stressFill.Size = UDim2.fromScale(stress and clamp(stress / 100, 0, 1) or 0, 1)
    stressFill.BackgroundColor3 = stress and stress >= 70 and C.red or C.amber
    local profile = type(snapshot.profile) == "table" and snapshot.profile or {}
    listDocuments(profile)
    updateCue()
    renderModal()
    if consoleStatus then
        consoleStatus.Text = (PHASES[snapshot.phase] or tostring(snapshot.phase)) .. "\n" .. tostring(snapshot.statusText or snapshot.objective or "") .. "\n" .. string.format("Температура: %.1f °C   Нагрузка: %.0f%%   Расходники: %s", temperature or 0, stress or 0, tostring(snapshot.supply or telemetry.supply or "—"))
        consoleStatus.Size = UDim2.new(1, 0, 0, 86)
    end
    if lastPhase ~= snapshot.phase then
        if snapshot.phase == "failed" then notice("АВАРИЙНАЯ ОСТАНОВКА. Проверьте причину и восстановите оборудование."); play(cueSound) end
        if snapshot.phase == "completed" then notice("ИСПЫТАНИЕ ЗАВЕРШЕНО. Результат добавлен в журнал."); play(cueSound) end
        lastPhase = snapshot.phase
    end
end

local function contextKey(context)
    if type(context) ~= "table" then return "" end
    return tostring(context.kind or "") .. ":" .. tostring(context.argument or "")
end
local function applyContext(context, force)
    if type(context) ~= "table" then
        if lastContextKey ~= "" and currentModal and currentModal.kind ~= "journal" then
            currentModal = nil
            overlay.Visible = false
        end
        lastContextKey = ""
        return
    end
    local key = contextKey(context)
    if force or key ~= lastContextKey then
        lastContextKey = key
        local copied = {}
        for k, v in pairs(context) do copied[k] = v end
        if copied.kind == "document" and documents[copied.argument] then copied.data = documents[copied.argument] end
        if copied.kind == "npc" and dialogueCache[copied.argument] then copied.data = dialogueCache[copied.argument] end
        openModal(copied)
    end
end
connections[#connections + 1] = push.OnClientEvent:Connect(function(kind, payload)
    if kind == "snapshot" and type(payload) == "table" then
        snapshot = payload
        applyContext(payload.context, false)
        refreshSnapshot()
    elseif kind == "notice" then
        notice(type(payload) == "table" and (payload.text or payload.message) or payload)
    elseif kind == "context" and type(payload) == "table" then
        applyContext(payload, true)
    elseif kind == "document" and type(payload) == "table" and type(payload.id) == "string" then
        documents[payload.id] = payload
        openModal({kind = "document", argument = payload.id, title = payload.title, data = payload})
    elseif kind == "dialogue" and type(payload) == "table" then
        local id = payload.id or payload.argument or payload.name or "staff"
        dialogueCache[id] = payload
        openModal({kind = "npc", argument = id, title = payload.name, data = payload})
    end
end)

local function resize()
    local camera = workspace.CurrentCamera
    local view = camera and camera.ViewportSize or Vector2.new(1024, 720)
    uiWidth, uiHeight = view.X, view.Y
    local narrow = uiWidth < 720
    local modalWidth = math.min(790, uiWidth - 24)
    modal.Size = UDim2.fromOffset(modalWidth, math.max(200, math.min(620, uiHeight - 94)))
    bodyWidth = modalWidth - 54
    hud.Size = UDim2.fromOffset(math.min(narrow and 250 or 310, uiWidth - 24), 188)
    quick.Size = UDim2.fromOffset(math.min(410, uiWidth - 24), 38)
    toast.Size = UDim2.fromOffset(math.min(500, uiWidth - 24), 52)
    toast.Position = UDim2.new(0.5, 0, 0, narrow and 208 or 12)
    cuePanel.Position = UDim2.new(1, -12, 1, -62)
    resizeCue()
    modalFoot.Text = narrow and "E — ДЕЙСТВИЕ · J — ЖУРНАЛ · X — ЗАКРЫТЬ" or "СЛЕДУЙТЕ ПРОТОКОЛУ · E — ВЗАИМОДЕЙСТВИЕ · J — ЖУРНАЛ"
    modalSignature = ""
    renderModal()
end
local lastViewport = Vector2.new(0, 0)
local accumulated = 0
connections[#connections + 1] = RunService.Heartbeat:Connect(function(dt)
    accumulated = accumulated + dt
    if accumulated < 0.12 then return end
    accumulated = 0
    local camera = workspace.CurrentCamera
    if camera and camera.ViewportSize ~= lastViewport then lastViewport = camera.ViewportSize; resize() end
    if toast.Visible and os.clock() >= noticeUntil then toast.Visible = false end
    local cue = type(snapshot.cue) == "table" and snapshot.cue or nil
    if cuePanel.Visible and cue then
        local serverNow = workspace:GetServerTimeNow()
        local deadline = finite(cue.deadline, nil)
        local preview = math.max(0, finite(cue.readyAt, 0) - serverNow)
        if preview > 0 then
            cueTime.Text = string.format("НАБЛЮДЕНИЕ / СИГНАЛ ЧЕРЕЗ %.1f СЕК.", preview)
        else
            cueTime.Text = deadline and string.format("ОСТАЛОСЬ %.1f СЕК.", math.max(0, deadline - serverNow)) or "СЛЕДУЙТЕ ИНСТРУКЦИИ"
        end
        for id, response in pairs(responseButtons) do enabled(response, cueButtonReady(cue, id)) end
    end
    local telemetry = type(snapshot.telemetry) == "table" and snapshot.telemetry or {}
    local stress = clamp(finite(telemetry.stress, 0), 0, 100) / 100
    local intensity = snapshot.phase == "running" and snapshot.owner == player.UserId and not reducedEffects and stress or 0
    -- A mild steady grade avoids flashing, camera shake and loss of legibility.
    grade.Saturation = -0.16 * intensity
    grade.Contrast = 0.06 * intensity
    grade.Brightness = -0.015 * intensity
    grade.TintColor = Color3.new(1 - 0.035 * intensity, 1, 1)
    blur.Size = 1.5 * intensity
end)
connections[#connections + 1] = UserInputService.InputBegan:Connect(function(input, processed)
    if processed or UserInputService:GetFocusedTextBox() then return end
    if input.KeyCode == Enum.KeyCode.J then
        if currentModal and currentModal.kind == "journal" then
            currentModal = nil; overlay.Visible = false; send("close")
        else openModal({kind = "journal", title = "ЛИЧНЫЙ ЖУРНАЛ"}) end
    elseif input.KeyCode == Enum.KeyCode.X and currentModal then
        currentModal = nil; overlay.Visible = false; send("close")
    end
end)
script.Destroying:Connect(function()
    for _, connection in ipairs(connections) do connection:Disconnect() end
    grade:Destroy(); blur:Destroy(); audioFolder:Destroy()
    if screen.Parent then screen:Destroy() end
end)
resize()
refreshSnapshot()
send("hello")
