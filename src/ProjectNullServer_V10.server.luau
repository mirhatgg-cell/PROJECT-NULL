-- PROJECT: NULL V10: authoritative experiments, physical access, journals and saves.
-- Legacy architecture/controllers remain responsible for their original equipment.
local RunService = game:GetService("RunService")
if not RunService:IsServer() then return end
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local DataStoreService = game:GetService("DataStoreService")

local facility = workspace:WaitForChild("PROJECT_NULL_ARCH_P01", 30)
local network = ReplicatedStorage:WaitForChild("ProjectNullV10", 30)
if not facility or not network then
    warn("PROJECT: NULL V10: facility/network is missing")
    return
end
local Request = network:WaitForChild("Request", 10)
local Push = network:WaitForChild("Push", 10)
if not Request or not Push then
    warn("PROJECT: NULL V10: remotes are missing")
    return
end
local Engine = require(script.Parent:WaitForChild("ExperimentCore"))
local Content = require(script.Parent:WaitForChild("Content"))
local state = Engine.new()
local profiles, contexts, buckets, bound = {}, {}, {}, {}
local documentById, staff = {}, Content.staff or {}
local phaseLabels = {idle = "ОЖИДАНИЕ", prepared = "ПОДГОТОВКА", running = "ИСПЫТАНИЕ", completed = "ЗАВЕРШЕНО", failed = "ОСТАНОВЛЕНО"}
local validExperiments = {P01 = true, P02 = true, P03 = true, P04 = true, P05 = true}
local RECORD_LIMIT, AUTOSAVE_TIME, SAVE_COOLDOWN = 20, 60, 10
local lastSupply = -math.huge
local effects = {beacons = {}, labels = {}, p01Lights = {}, p02Labels = {}, p05Labels = {}, shutters = {}}
local heartbeatElapsed, effectsElapsed, saveElapsed, recordSequence = 0, 0, 0, 0
local closing = false
local idleAwayAt
local movement = {owner = 0, position = nil, time = 0, movingUntil = 0}
local circuitsFolder = facility:WaitForChild("Controls", 10)
circuitsFolder = circuitsFolder and circuitsFolder:WaitForChild("Circuits", 10)

for _, document in ipairs(Content.documents or {}) do
    if type(document.id) == "string" then documentById[document.id] = document end
end

local function now()
    return workspace:GetServerTimeNow()
end

local function copyMap(source)
    local result = {}
    for key, value in pairs(source or {}) do result[key] = value end
    return result
end

local function finite(value)
    return type(value) == "number" and value == value and value > -math.huge and value < math.huge
end

local function clipped(value, maximum)
    if type(value) ~= "string" then return "" end
    return string.sub(value, 1, maximum)
end

local function emptyProfile()
    return {version = 10, documents = {}, completed = {}, attempts = {}, records = {}}
end

local function cleanRecord(record)
    if type(record) ~= "table" or type(record.id) ~= "string" or not validExperiments[record.experiment] then return nil end
    local result = {
        id = clipped(record.id, 128), experiment = record.experiment,
        title = clipped(record.title, 200), status = record.status == "completed" and "completed" or "failed",
        result = clipped(record.result, 700), timestamp = finite(record.timestamp) and math.floor(record.timestamp) or 0,
    }
    for _, key in ipairs({"elapsed", "rounds", "temperature", "quality"}) do
        if finite(record[key]) then result[key] = math.max(-1000000, math.min(1000000, record[key])) end
    end
    return result
end

local function sanitizeProfile(raw)
    local result = emptyProfile()
    if type(raw) ~= "table" then return result end
    if type(raw.documents) == "table" then
        for key, value in pairs(raw.documents) do
            if documentById[key] and value == true then result.documents[key] = true end
        end
    end
    if type(raw.completed) == "table" then
        for id in pairs(validExperiments) do if raw.completed[id] == true then result.completed[id] = true end end
    end
    if type(raw.attempts) == "table" then
        for id in pairs(validExperiments) do
            local count = raw.attempts[id]
            if finite(count) then result.attempts[id] = math.max(0, math.min(1000000, math.floor(count))) end
        end
    end
    local seen = {}
    if type(raw.records) == "table" then
        for _, record in ipairs(raw.records) do
            local clean = cleanRecord(record)
            if clean and not seen[clean.id] then
                seen[clean.id] = true
                table.insert(result.records, clean)
            end
            if #result.records >= RECORD_LIMIT then break end
        end
    end
    return result
end

local function mergedRecords(first, second)
    local result, seen = {}, {}
    -- Session records come first; records use stable IDs across retried saves.
    for _, list in ipairs({first, second}) do
        for _, record in ipairs(list or {}) do
            local clean = cleanRecord(record)
            if clean and not seen[clean.id] then
                seen[clean.id] = true
                table.insert(result, clean)
            end
        end
    end
    table.sort(result, function(a, b)
        if a.timestamp == b.timestamp then return a.id > b.id end
        return a.timestamp > b.timestamp
    end)
    while #result > RECORD_LIMIT do table.remove(result) end
    return result
end

local store
local canUseStore = game.GameId ~= nil and game.GameId > 0
if canUseStore then
    local ok, value = pcall(function() return DataStoreService:GetDataStore("PROJECT_NULL_PROGRESS_V10") end)
    if ok then store = value else warn("V10 save service unavailable: " .. tostring(value)) end
end

local function tell(player, message)
    if player and player.Parent == Players then Push:FireClient(player, "notice", message) end
end

local function alive(player)
    if not player or not player:IsA("Player") or player.Parent ~= Players then return nil end
    local character = player.Character
    local humanoid = character and character:FindFirstChildOfClass("Humanoid")
    local origin = character and (character:FindFirstChild("Head") or character:FindFirstChild("HumanoidRootPart"))
    if not humanoid or humanoid.Health <= 0 or not origin or not origin:IsA("BasePart") then return nil end
    return humanoid, origin, character
end

local function accessible(player, part, prompt)
    local humanoid, origin, character = alive(player)
    if not humanoid or not part or not part:IsA("BasePart") or not part:IsDescendantOf(facility) then return false end
    if not prompt or prompt.Parent ~= part or not prompt.Enabled then return false end
    local distance = part.Position - origin.Position
    if distance.Magnitude > math.max(0, prompt.MaxActivationDistance) + 1 or distance.Magnitude < 0.0001 then return false end
    local params = RaycastParams.new()
    params.FilterType = Enum.RaycastFilterType.Exclude
    params.FilterDescendantsInstances = {character}
    local hit = workspace:Raycast(origin.Position, distance, params)
    return hit ~= nil and hit.Instance == part
end

local function takeToken(player, cost)
    local time = now()
    local bucket = buckets[player]
    if not bucket then bucket = {tokens = 8, time = time, hello = -math.huge}; buckets[player] = bucket end
    bucket.tokens = math.min(8, bucket.tokens + math.max(0, time - bucket.time) * 4)
    bucket.time = time
    if bucket.tokens < cost then return false end
    bucket.tokens = bucket.tokens - cost
    return true
end

local function updateMovement()
    local time = now()
    local snapshot = Engine.snapshot(state, time)
    local ownerId = snapshot.owner or 0
    local owner = ownerId ~= 0 and Players:GetPlayerByUserId(ownerId) or nil
    local character = owner and owner.Character
    local root = character and character:FindFirstChild("HumanoidRootPart")
    if movement.owner ~= ownerId or not root or not root:IsA("BasePart") then
        movement.owner, movement.position, movement.time, movement.movingUntil = ownerId, root and root.Position or nil, time, 0
        return
    end
    local elapsed = time - movement.time
    if elapsed < 1 / 120 then return end
    if movement.position then
        local displacement = root.Position - movement.position
        local horizontal = math.sqrt(displacement.X * displacement.X + displacement.Z * displacement.Z)
        -- Server-observed position changes, not a client-supplied "I moved" flag.
        if horizontal > math.max(0.008, elapsed * 0.75) then movement.movingUntil = time + 0.35 end
    end
    movement.position, movement.time = root.Position, time
end

local function inputs()
    local values = {}
    for _, name in ipairs({"Computers", "Ventilation", "AcousticAmplifiers", "PhysicalHall"}) do
        local circuit = circuitsFolder and circuitsFolder:FindFirstChild(name)
        values[name] = circuit ~= nil and circuit:IsA("BoolValue") and circuit.Value == true
    end
    local snapshot = Engine.snapshot(state, now())
    local owner = snapshot.owner and snapshot.owner ~= 0 and Players:GetPlayerByUserId(snapshot.owner) or nil
    values.ownerPresent = snapshot.owner == nil or snapshot.owner == 0 or alive(owner) ~= nil
    values.ownerMoving = movement.movingUntil > now()
    return values
end

local function publicProfile(profile)
    local journal = {}
    for id in pairs(profile.documents) do
        local document = documentById[id]
        if document then
            table.insert(journal, {id = id, title = document.title, room = document.room, body = document.body})
        end
    end
    table.sort(journal, function(a, b) return a.id < b.id end)
    return {
        documents = copyMap(profile.documents), journal = journal,
        completed = copyMap(profile.completed), attempts = copyMap(profile.attempts),
        records = mergedRecords(profile.records, {}), saveStatus = profile.saveStatus,
    }
end

local function sendSnapshot(player)
    local profile = profiles[player]
    if not profile or player.Parent ~= Players then return end
    local snapshot = Engine.snapshot(state, now())
    snapshot.profile = publicProfile(profile)
    snapshot.circuits = inputs()
    snapshot.circuits.ownerPresent = nil
    snapshot.circuits.ownerMoving = nil
    snapshot.evidenceRequired = {}
    if snapshot.experiment == "P03" then
        for _, id in ipairs({"DOC_P03_LOG", "DOC_P03_CORRECTION"}) do
            if not profile.documents[id] then
                local document = documentById[id]
                table.insert(snapshot.evidenceRequired, {id = id, title = document and document.title or id, room = document and document.room or "E-07"})
            end
        end
    end
    snapshot.evidenceReady = #snapshot.evidenceRequired == 0
    local context = contexts[player]
    if context and context.opened then
        snapshot.context = {kind = context.action, argument = context.argument, title = context.title}
    end
    Push:FireClient(player, "snapshot", snapshot)
end

local function broadcast()
    for _, player in ipairs(Players:GetPlayers()) do sendSnapshot(player) end
end

local saveProfile
local function loadProfile(player, profile)
    if profile.loading or profile.loaded or not store or player.UserId <= 0 then return end
    profile.loading = true
    profile.saveStatus = "Загрузка сохранения…"
    task.spawn(function()
        local ok, saved = pcall(function() return store:GetAsync("u_" .. tostring(player.UserId)) end)
        profile.loading = false
        if ok then
            local clean = sanitizeProfile(saved)
            for id in pairs(clean.documents) do profile.documents[id] = true end
            for id in pairs(clean.completed) do profile.completed[id] = true end
            for id in pairs(validExperiments) do
                profile.attempts[id] = (clean.attempts[id] or 0) + (profile.pendingAttempts[id] or 0)
            end
            profile.records = mergedRecords(profile.records, clean.records)
            profile.loaded = true
            profile.saveStatus = profile.dirty and "Есть несохранённые изменения" or "Сохранение загружено"
        else
            -- Never overwrite an unknown persisted profile after a failed read.
            profile.loaded = false
            profile.saveStatus = "Сохранение недоступно; прогресс этой сессии в памяти"
            warn("V10 profile load failed for user " .. tostring(player.UserId) .. ": " .. tostring(saved))
        end
        sendSnapshot(player)
        if player.Parent ~= Players or closing then
            -- A player can leave while GetAsync yields. Preserve any changes
            -- made before the read finished and save only after a successful read.
            if ok and profile.dirty then saveProfile(player, true)
            elseif not profile.saving then profiles[player] = nil end
        end
    end)
end

saveProfile = function(player, force)
    local profile = profiles[player]
    if not profile or profile.saving then return false end
    if not store or player.UserId <= 0 then
        profile.saveStatus = "Локальный режим: прогресс хранится до выхода"
        return false
    end
    if not profile.loaded then
        profile.saveStatus = "Запись отложена: сначала требуется загрузить сохранение"
        if not profile.loading then loadProfile(player, profile) end
        return false
    end
    if not profile.dirty then return true end
    if not force and now() - profile.lastSave < SAVE_COOLDOWN then
        profile.saveStatus = "Сохранение уже запланировано"
        return false
    end
    profile.saving = true
    profile.lastSave = now()
    profile.saveStatus = "Сохранение…"
    local payload = sanitizeProfile(profile)
    local attemptDelta = copyMap(profile.pendingAttempts)
    local revision = profile.revision
    task.spawn(function()
        local ok, saved = pcall(function()
            return store:UpdateAsync("u_" .. tostring(player.UserId), function(previous)
                local merged = sanitizeProfile(previous)
                for id in pairs(payload.documents) do merged.documents[id] = true end
                for id in pairs(payload.completed) do merged.completed[id] = true end
                for id in pairs(validExperiments) do
                    merged.attempts[id] = math.min(1000000, (merged.attempts[id] or 0) + (attemptDelta[id] or 0))
                end
                merged.records = mergedRecords(payload.records, merged.records)
                return merged
            end)
        end)
        profile.saving = false
        if ok then
            local clean = sanitizeProfile(saved)
            for id in pairs(validExperiments) do
                profile.pendingAttempts[id] = math.max(0, (profile.pendingAttempts[id] or 0) - (attemptDelta[id] or 0))
                profile.attempts[id] = (clean.attempts[id] or 0) + profile.pendingAttempts[id]
            end
            for id in pairs(clean.documents) do profile.documents[id] = true end
            for id in pairs(clean.completed) do profile.completed[id] = true end
            profile.records = mergedRecords(profile.records, clean.records)
            profile.dirty = profile.revision ~= revision
            profile.saveStatus = profile.dirty and "Есть новые изменения; запись запланирована" or "Прогресс сохранён"
        else
            profile.saveStatus = "Ошибка записи; прогресс остаётся в памяти"
            warn("V10 profile save failed for user " .. tostring(player.UserId) .. ": " .. tostring(saved))
        end
        sendSnapshot(player)
        if player.Parent ~= Players and not profile.saving then profiles[player] = nil end
    end)
    return true
end

local function dirty(profile)
    profile.dirty = true
    profile.revision = profile.revision + 1
    if profile.loaded then profile.saveStatus = "Есть несохранённые изменения" end
end

local function handleEvent(event)
    if type(event) ~= "table" then return end
    local player = finite(event.owner) and Players:GetPlayerByUserId(event.owner) or nil
    if not player and finite(event.owner) then
        for candidate in pairs(profiles) do if candidate.UserId == event.owner then player = candidate; break end end
    end
    local profile = player and profiles[player]
    if event.kind == "damage" then
        local humanoid = alive(player)
        if humanoid and finite(event.amount) then humanoid:TakeDamage(math.max(0, math.min(15, event.amount))) end
    elseif event.kind == "medical" then
        local humanoid = alive(player)
        if humanoid and finite(event.amount) then humanoid.Health = math.min(humanoid.MaxHealth, humanoid.Health + math.max(0, math.min(25, event.amount))) end
    elseif event.kind == "completed" or event.kind == "failed" then
        if not profile or not validExperiments[event.experiment] then return end
        if event.kind == "completed" then profile.completed[event.experiment] = true end
        local source = type(event.record) == "table" and event.record or {}
        recordSequence = recordSequence + 1
        local record = {}
        for key, value in pairs(source) do record[key] = value end
        record.id = tostring(game.JobId or "local") .. ":" .. tostring(os.time()) .. ":" .. tostring(recordSequence) .. ":" .. tostring(player.UserId)
        record.experiment = event.experiment
        record.status = event.kind
        record.result = type(event.result) == "string" and event.result or source.result or "Протокол завершён"
        record.timestamp = os.time()
        local clean = cleanRecord(record)
        if clean then profile.records = mergedRecords({clean}, profile.records) end
        dirty(profile)
        tell(player, event.kind == "completed" and "Протокол принят. Результат добавлен в журнал." or "Испытание остановлено. Причина записана в журнал.")
    end
end

local refreshEffects
local function dispatch(player, action, argument)
    updateMovement()
    Engine.setInputs(state, inputs())
    local ok, reason, event = Engine.dispatch(state, action, argument, now(), player.UserId)
    if event then handleEvent(event) end
    if ok and action == "start" then
        local profile = profiles[player]
        local id = Engine.snapshot(state, now()).experiment
        if profile and validExperiments[id] then
            profile.attempts[id] = (profile.attempts[id] or 0) + 1
            profile.pendingAttempts[id] = (profile.pendingAttempts[id] or 0) + 1
            dirty(profile)
        end
    end
    if not ok then tell(player, type(reason) == "string" and reason or "Действие сейчас недоступно") end
    if refreshEffects then refreshEffects(Engine.snapshot(state, now())) end
    return ok
end

local function contextAllowed(player, required)
    local context = contexts[player]
    if not context or context.action ~= required or not accessible(player, context.part, context.prompt) then
        tell(player, "Подойдите к соответствующему посту и используйте E.")
        return nil
    end
    return context
end

local function dialogue(player, id)
    local person = staff[id]
    if type(person) ~= "table" then return end
    local snapshot = Engine.snapshot(state, now())
    local profile = profiles[player]
    local message
    if snapshot.phase == "failed" then
        message = id == "MEDIC" and "Испытание остановлено. Пройдите к медицинскому посту E-06; набор помогает только живому участнику. Затем сбросьте протокол на его терминале." or "Сначала прочтите причину остановки. Проверьте питание, вентиляцию и охлаждение. Повреждённый тракт восстанавливается на ремонтном посту, затем нужен сброс и новая калибровка."
    elseif snapshot.phase == "running" then
        message = id == "MEDIC" and "Следите за нагрузкой. Аварийная остановка доступна участнику в любой момент; продолжение через предупреждение повышает риск." or "Серия идёт. Показания и инструкция терминала важнее старой таблички. Не меняйте автоматы и охлаждение во время серии без необходимости."
    elseif snapshot.phase == "prepared" then
        message = "Калибровка принята. Дождитесь окончания проверки, затем запустите серию с того же терминала. Перед запуском прочтите локальный протокол."
    else
        local completed = 0
        for _ in pairs(profile and profile.completed or {}) do completed = completed + 1 end
        if completed >= 5 then
            message = "Все пять локальных протоколов выполнены. Сравните записи и найденные документы: подтверждённые измерения ещё не объясняют природу NULL. Центральный эксперимент остаётся закрытым."
        elseif completed > 0 then
            message = "В вашем журнале уже есть принятые протоколы: " .. tostring(completed) .. " из 5. Сохраните результаты на архивном терминале и переходите к следующему посту."
        else
            local lines = person.lines or {}
            message = lines[1] or "Начните с P-01 в операторской E-04. Документы у оборудования объясняют процедуру; после остановки проверяйте причину в журнале."
        end
    end
    Push:FireClient(player, "dialogue", {id = id, argument = id, name = person.name or id, role = person.role or "Персонал", text = message})
end

local function openInteraction(player, part, prompt, action, argument)
    if not profiles[player] or not takeToken(player, 1) or not accessible(player, part, prompt) then return end
    if action == "response" then
        local snapshot = Engine.snapshot(state, now())
        if snapshot.owner ~= player.UserId or snapshot.experiment ~= "P02" or snapshot.phase ~= "running" then
            tell(player, "Этот датчик принимает ответ участника активного P-02.")
            return
        end
        if argument ~= "left" and argument ~= "center" and argument ~= "right" then return end
        dispatch(player, "respond", argument)
        broadcast()
        return
    end
    local titles = {console = "Терминал " .. argument, cooling = "Охлаждение", repair = "Ремонтный пост", supply = "Чистые расходники", medical = "Медицинский пост", records = "Архив протоколов", document = "Документ", npc = "Персонал"}
    if not titles[action] then return end
    contexts[player] = {part = part, prompt = prompt, action = action, argument = argument, title = titles[action], opened = true}
    if action == "console" and validExperiments[argument] then
        dispatch(player, "select", argument)
    elseif action == "document" then
        local document = documentById[argument]
        if not document then return end
        if not profiles[player].documents[argument] then profiles[player].documents[argument] = true; dirty(profiles[player]) end
        Push:FireClient(player, "document", {id = document.id, title = document.title, room = document.room, body = document.body})
    elseif action == "npc" then
        dialogue(player, argument)
    end
    Push:FireClient(player, "context", {kind = action, argument = argument, title = titles[action]})
    sendSnapshot(player)
end

local function bindInteraction(config)
    if bound[config] then return end
    local part = config.Parent
    local actionValue = config:FindFirstChild("Action")
    local argumentValue = config:FindFirstChild("Argument")
    local prompt = part and part:FindFirstChild("V10_Prompt")
    if not part or not part:IsA("BasePart") or not prompt or not prompt:IsA("ProximityPrompt") then return end
    if not actionValue or not actionValue:IsA("StringValue") or not argumentValue or not argumentValue:IsA("StringValue") then return end
    bound[config] = true
    local action, argument = actionValue.Value, argumentValue.Value
    prompt.Triggered:Connect(function(player) openInteraction(player, part, prompt, action, argument) end)
end

local function register(instance)
    if instance.Name == "V10_Interact" and instance:IsA("Folder") then bindInteraction(instance) end
    if instance.Name == "V10_RunBeacon" and instance:IsA("BasePart") then table.insert(effects.beacons, instance) end
    if instance:IsA("TextLabel") and string.sub(instance.Name, 1, 11) == "V10_Status_" then table.insert(effects.labels, instance) end
    if instance:IsA("BasePart") and string.match(instance.Name, "^V10_P01_Light_[ABC]$") then
        table.insert(effects.p01Lights, {part = instance, channel = string.sub(instance.Name, -1)})
    end
    if instance:IsA("TextLabel") and string.match(instance.Name, "^V10_P02_Readout_") then
        local index = ({left = 1, center = 2, right = 3})[string.sub(instance.Name, 17)]
        if index then table.insert(effects.p02Labels, {label = instance, index = index}) end
    end
    if instance:IsA("TextLabel") and instance.Name == "V10_P05_Reference" then table.insert(effects.p05Labels, instance) end
    if instance:IsA("BasePart") and instance.Name == "V10_ObserverShutter" then
        local offset = instance:FindFirstChild("OpenOffset")
        if offset and offset:IsA("Vector3Value") then table.insert(effects.shutters, {part = instance, closed = instance.CFrame, offset = offset.Value}) end
    end
end
for _, instance in ipairs(facility:GetDescendants()) do register(instance) end
facility.DescendantAdded:Connect(function(instance) task.defer(function() register(instance) end) end)

local function playerAdded(player)
    if profiles[player] then return end
    local profile = emptyProfile()
    profile.pendingAttempts, profile.loaded, profile.loading, profile.saving = {}, false, false, false
    profile.revision, profile.lastSave, profile.dirty = 0, -math.huge, false
    profile.lastMedical = -math.huge
    local persistent = store and player.UserId > 0
    profile.saveStatus = persistent and "Загрузка сохранения…" or "Локальный режим: прогресс хранится до выхода"
    profiles[player] = profile
    if persistent then loadProfile(player, profile) end
end
Players.PlayerAdded:Connect(playerAdded)
for _, player in ipairs(Players:GetPlayers()) do playerAdded(player) end

local allowedActions = {hello = true, close = true, select = true, calibrate = true, start = true, respond = true, abort = true, reset = true, cooling = true, repair = true, medical = true, supply = true, save = true, records = true}
Request.OnServerEvent:Connect(function(player, action, argument)
    if closing or not profiles[player] or type(action) ~= "string" or not allowedActions[action] or not takeToken(player, 1) then return end
    if action == "hello" then
        local bucket = buckets[player]
        if now() - bucket.hello < 1 then return end
        bucket.hello = now()
        sendSnapshot(player)
        return
    elseif action == "close" then
        if contexts[player] then contexts[player].opened = false end
        return
    elseif action == "records" then
        -- A journal contains only the requesting player's discovered information.
        sendSnapshot(player)
        return
    elseif action == "save" then
        saveProfile(player, false)
        sendSnapshot(player)
        return
    end
    if not alive(player) then return end
    if action == "abort" then
        local snapshot = Engine.snapshot(state, now())
        if snapshot.owner ~= player.UserId then return end
        dispatch(player, "abort", nil)
    elseif action == "select" or action == "calibrate" or action == "start" or action == "respond" or action == "reset" then
        local context = contextAllowed(player, "console")
        if not context then return end
        local snapshot = Engine.snapshot(state, now())
        if action == "select" then
            if type(argument) ~= "string" or argument ~= context.argument or not validExperiments[argument] then return end
        else
            if snapshot.experiment ~= context.argument then tell(player, "Используйте терминал текущего протокола."); return end
            if action == "respond" and (type(argument) ~= "string" or #argument > 80) then return end
            if action == "respond" and snapshot.experiment == "P02" then
                tell(player, "P-02: подойдите к выбранному датчику в зале и удерживайте E.")
                return
            end
            if action == "calibrate" and snapshot.experiment == "P03" then
                local profile = profiles[player]
                if not profile.documents.DOC_P03_LOG or not profile.documents.DOC_P03_CORRECTION then
                    tell(player, "P-03: сначала найдите официальную сводку в E-04 и подписанный журнал в E-07. Найденные документы останутся в личном журнале.")
                    sendSnapshot(player)
                    return
                end
            end
            if action ~= "respond" then argument = nil end
        end
        dispatch(player, action, argument)
    elseif action == "cooling" then
        if not contextAllowed(player, "cooling") or type(argument) ~= "boolean" then return end
        dispatch(player, "cooling", argument)
    elseif action == "repair" then
        if not contextAllowed(player, "repair") then return end
        dispatch(player, "repair", nil)
    elseif action == "medical" then
        if not contextAllowed(player, "medical") then return end
        local profile = profiles[player]
        if now() - profile.lastMedical < 20 then tell(player, "Повторная помощь доступна через 20 секунд."); return end
        if dispatch(player, "medical", nil) then profile.lastMedical = now() end
    elseif action == "supply" then
        if not contextAllowed(player, "supply") then return end
        if now() - lastSupply < 45 then tell(player, "Следующая выдача расходников — через " .. tostring(math.ceil(45 - (now() - lastSupply))) .. " с."); return end
        if dispatch(player, "resupply", nil) then lastSupply = now() end
    end
    broadcast()
end)

refreshEffects = function(snapshot)
    local color = snapshot.phase == "failed" and Color3.fromRGB(220, 72, 55)
        or snapshot.phase == "running" and Color3.fromRGB(226, 170, 59) or Color3.fromRGB(57, 188, 193)
    for _, part in ipairs(effects.beacons) do
        if part:IsDescendantOf(facility) then
            part.Color = color
            local light = part:FindFirstChildOfClass("PointLight")
            if light then light.Color = color; light.Enabled = true end
        end
    end
    local telemetry = snapshot.telemetry or {}
    local text = string.format("%s / %s\n%.1f °C  |  НАГРУЗКА %.0f%%\n%s", snapshot.experiment or "P-00", phaseLabels[snapshot.phase] or snapshot.phase or "", telemetry.temperature or 0, telemetry.stress or 0, snapshot.statusText or snapshot.objective or "")
    for _, label in ipairs(effects.labels) do if label:IsDescendantOf(facility) then label.Text = text end end
    local cue = snapshot.cue
    local p01Active = snapshot.phase == "running" and snapshot.experiment == "P01" and cue and cue.ready
    local channelColors = {A = Color3.fromRGB(61, 202, 211), B = Color3.fromRGB(235, 183, 62), C = Color3.fromRGB(213, 108, 171)}
    for _, entry in ipairs(effects.p01Lights) do
        local part = entry.part
        if part:IsDescendantOf(facility) then
            local enabled = p01Active and cue.visual == entry.channel or false
            part.Color = enabled and channelColors[entry.channel] or Color3.fromRGB(37, 53, 63)
            local light = part:FindFirstChildOfClass("PointLight")
            if light then light.Enabled = enabled; light.Brightness = enabled and 1.2 or 0; light.Color = channelColors[entry.channel] end
        end
    end
    local routeActive = snapshot.phase == "running" and snapshot.experiment == "P02" and cue
    local routeLabels = {"ЛЕВЫЙ ДАТЧИК", "ЦЕНТРАЛЬНЫЙ ДАТЧИК", "ПРАВЫЙ ДАТЧИК"}
    for _, entry in ipairs(effects.p02Labels) do
        if entry.label:IsDescendantOf(facility) then
            local index = entry.index
            if routeActive then
                entry.label.Text = string.format("%s\nВЫВЕСКА: %s\nНЕЗАВИСИМЫЙ ЛАЗЕР: %.1f stud\nЗАДАНИЕ: %.1f stud\nУДЕРЖИВАЙТЕ E У ДАТЧИКА", routeLabels[index], cue.signs and cue.signs[index] or "—", cue.measurements and cue.measurements[index] or 0, cue.targetDistance or 0)
            else entry.label.Text = routeLabels[index] .. "\nP-02 / ОЖИДАНИЕ СЕРИИ\nЗАПУСК: E-12" end
        end
    end
    for _, label in ipairs(effects.p05Labels) do
        if label:IsDescendantOf(facility) then
            if snapshot.phase == "running" and snapshot.experiment == "P05" and cue then
                label.Text = string.format("НЕЗАВИСИМЫЙ КАНАЛ\n%.2f\nЭТАЛОН: %s\nДОПУСК ±%.2f", cue.physicalReading or 0, cue.referenceQuality == "stable" and "СТАБИЛЕН" or "НЕСТАБИЛЕН", cue.tolerance or .2)
            else label.Text = "НЕЗАВИСИМЫЙ КАНАЛ\nP-05 / ОЖИДАНИЕ СЕРИИ" end
        end
    end
    for _, shutter in ipairs(effects.shutters) do
        if shutter.part:IsDescendantOf(facility) then
            local open = snapshot.phase == "running" and snapshot.experiment == "P04" and cue and cue.observerMode ~= "occluded"
            shutter.part.CFrame = open and shutter.closed + shutter.offset or shutter.closed
        end
    end
end

local function releaseUnusedReservation(snapshot)
    local inactive = snapshot.phase == "idle" or snapshot.phase == "completed" or snapshot.phase == "failed"
    if not inactive or not snapshot.owner or snapshot.owner == 0 then idleAwayAt = nil; return snapshot end
    local owner = Players:GetPlayerByUserId(snapshot.owner)
    local context = owner and contexts[owner]
    local atConsole = context and context.action == "console" and context.argument == snapshot.experiment
        and accessible(owner, context.part, context.prompt)
    if atConsole then idleAwayAt = nil; return snapshot end
    if not idleAwayAt then idleAwayAt = now(); return snapshot end
    if now() - idleAwayAt < 15 then return snapshot end
    -- Only waiting/terminal phases can be released. A recorded result remains
    -- in its owner's journal; prepared/running phases are never discarded here.
    Engine.dispatch(state, "reset", nil, now(), snapshot.owner)
    idleAwayAt = nil
    tell(owner, "Пульт освобождён после завершения/ожидания. Вернитесь к терминалу, чтобы выбрать протокол снова.")
    return Engine.snapshot(state, now())
end

RunService.Heartbeat:Connect(function(dt)
    if closing then return end
    if not finite(dt) or dt < 0 then return end
    local elapsed = math.min(dt, 0.25)
    updateMovement()
    Engine.setInputs(state, inputs())
    local events = Engine.step(state, elapsed, now()) or {}
    for _, event in ipairs(events) do handleEvent(event) end
    if #events > 0 then broadcast() end
    heartbeatElapsed = heartbeatElapsed + elapsed
    effectsElapsed = effectsElapsed + elapsed
    saveElapsed = saveElapsed + elapsed
    if effectsElapsed >= 0.1 then
        effectsElapsed = 0
        refreshEffects(Engine.snapshot(state, now()))
    end
    if heartbeatElapsed >= 1 then
        heartbeatElapsed = 0
        local snapshot = releaseUnusedReservation(Engine.snapshot(state, now()))
        refreshEffects(snapshot)
        broadcast()
    end
    if saveElapsed >= AUTOSAVE_TIME then
        saveElapsed = 0
        for _, player in ipairs(Players:GetPlayers()) do
            local profile = profiles[player]
            if profile and not profile.loaded and store and player.UserId > 0 then loadProfile(player, profile) else saveProfile(player, false) end
        end
    end
end)

refreshEffects(Engine.snapshot(state, now()))

Players.PlayerRemoving:Connect(function(player)
    local snapshot = Engine.snapshot(state, now())
    if snapshot.owner == player.UserId then
        Engine.setInputs(state, {Computers = false, Ventilation = false, AcousticAmplifiers = false, PhysicalHall = false, ownerPresent = false})
        for _, event in ipairs(Engine.step(state, 0, now()) or {}) do handleEvent(event) end
        -- Release a departed owner after the core has recorded the interruption.
        Engine.dispatch(state, "reset", nil, now(), player.UserId)
    end
    contexts[player], buckets[player] = nil, nil
    local profile = profiles[player]
    if profile then
        if not saveProfile(player, true) and not profile.saving and not profile.loading then profiles[player] = nil end
    end
end)

game:BindToClose(function()
    closing = true
    for _, player in ipairs(Players:GetPlayers()) do saveProfile(player, true) end
    local deadline = os.clock() + 8
    while os.clock() < deadline do
        local saving = false
        for _, profile in pairs(profiles) do if profile.saving or profile.loading then saving = true; break end end
        if not saving then break end
        task.wait(0.1)
    end
end)
