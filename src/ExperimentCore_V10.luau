-- PROJECT: NULL — deterministic experiment state machine.
-- This module contains no Roblox services. Only the server may mutate its state.
local Engine = {}

local MAX_SUPPLY = 12
local MAX_RECORDS = 12
local TITLES = {
    P01 = "Сенсорная синхронизация",
    P02 = "Нарушение восприятия",
    P03 = "Память и реконструкция",
    P04 = "Автономный наблюдатель",
    P05 = "Граница симуляции",
}
local REQUIREMENTS = {
    P01 = {"Computers", "Ventilation", "AcousticAmplifiers"},
    P02 = {"Computers", "Ventilation", "PhysicalHall"},
    P03 = {"Computers", "Ventilation"},
    P04 = {"Computers", "Ventilation", "PhysicalHall"},
    P05 = {"Computers", "Ventilation", "AcousticAmplifiers", "PhysicalHall"},
}
local CIRCUIT_NAMES = {
    Computers = "вычислители", Ventilation = "вентиляция",
    AcousticAmplifiers = "усилители", PhysicalHall = "питание физического стенда",
}

local function finite(value)
    return type(value) == "number" and value == value and value > -math.huge and value < math.huge
end

local function clamp(value, minimum, maximum)
    return math.max(minimum, math.min(maximum, value))
end

local function copy(value)
    if type(value) ~= "table" then return value end
    local result = {}
    for key, item in pairs(value) do result[key] = copy(item) end
    return result
end

local function clock(state, now)
    if finite(now) then state.now = math.max(state.now, now) end
    return state.now
end

local function actorValid(actor)
    -- Studio Start Server assigns negative UserIds to its real test Players.
    -- Zero alone is the public "no owner" sentinel. The server authenticates
    -- the actual Player instance before passing this trusted identifier here.
    return finite(actor) and actor ~= 0 and actor % 1 == 0
end

local function options(...)
    local values, result = {...}, {}
    for i = 1, #values, 2 do
        table.insert(result, {id = values[i], label = values[i + 1]})
    end
    return result
end

local function circuitProblem(state)
    for _, id in ipairs(REQUIREMENTS[state.experiment]) do
        if state.inputs[id] ~= true then return "Отключено: " .. CIRCUIT_NAMES[id] end
    end
    if state.inputs.ownerPresent == false then return "Оператор покинул испытание или потерял сознание" end
    return nil
end

local function prepareProblem(state)
    local problem = circuitProblem(state)
    if problem then return problem end
    if not state.cooling then return "Включите охлаждение на сервисном посту" end
    if state.temperature > 45 then return "Дождитесь охлаждения ниже 45 °C" end
    if state.integrity < 30 then return "Отремонтируйте стенд: исправность ниже 30%" end
    return nil
end

local function record(state, status, result)
    local item = {
        experiment = state.experiment, title = TITLES[state.experiment], status = status,
        result = result, owner = state.owner or 0,
        elapsed = math.floor(math.max(0, state.now - (state.startedAt or state.now)) * 10 + .5) / 10,
        rounds = math.max(0, state.round - (status == "completed" and 0 or 1)),
        temperature = math.floor(state.peakTemperature * 10 + .5) / 10,
        quality = status == "completed" and math.floor(clamp(100 - state.stress * .3, 0, 100)) or 0,
    }
    table.insert(state.records, item)
    while #state.records > MAX_RECORDS do table.remove(state.records, 1) end
    return item
end

local function failed(state, reason, damage)
    state.phase = "failed"
    state.result = reason
    state.cue = nil
    state.stress = clamp(state.stress + 15, 0, 100)
    state.integrity = clamp(state.integrity - 6, 0, 100)
    local item = record(state, "failed", reason)
    if damage and damage > 0 and state.owner then
        table.insert(state.pendingEvents, {
            kind = "damage", owner = state.owner, amount = clamp(damage, 0, 12), reason = reason,
        })
    end
    return {kind = "failed", owner = state.owner or 0, experiment = state.experiment, result = reason, record = copy(item)}
end

-- Every cue carries observable evidence. Its private answer never enters snapshots.
local function cueFor(state)
    local round, id = state.round, state.experiment
    if id == "P01" then
        local sequence = {{"A", "A"}, {"B", "B"}, {"C", "A"}, {"B", "C"}, {"C", "C"}}
        local pair = sequence[round]
        if not pair then return nil end
        local frequencies = {A = 440, B = 660, C = 880}
        return {
            kind = "sync", label = "Сравните световой канал с акустическим. Подтвердите канал только при совпадении; иначе отклоните импульс.",
            visual = pair[1], audio = pair[2], frequency = frequencies[pair[2]],
            evidence = "Акустическая калибровка: A = 440 Гц; B = 660 Гц; C = 880 Гц. Текстовый канал дублирует звук.",
            options = options("A", "Канал A", "B", "Канал B", "C", "Канал C", "reject", "Отклонить импульс"),
            answer = pair[1] == pair[2] and pair[1] or "reject", preview = 2.0, window = 10.0,
        }
    elseif id == "P02" then
        local sequence = {
            {6, {9.2, 6.0, 3.5}, {"БЛИЗКО", "ДАЛЕКО", "ЦЕЛЬ"}},
            {8, {8.0, 4.0, 11.0}, {"ЗАКРЫТО", "ЦЕЛЬ", "ОБХОД"}},
            {5, {7.5, 8.5, 5.0}, {"ЦЕЛЬ", "ОБХОД", "ДАЛЕКО"}},
            {7, {10.0, 7.0, 2.5}, {"ВЫХОД", "ЗАКРЫТО", "ЦЕЛЬ"}},
        }
        local data = sequence[round]
        if not data then return nil end
        local keys = {"left", "center", "right"}
        local answer, minimum = keys[1], math.huge
        for i, value in ipairs(data[2]) do
            local difference = math.abs(value - data[1])
            if difference < minimum then answer, minimum = keys[i], difference end
        end
        return {
            kind = "measurement", label = "Оптические вывески смещены. Выберите путь по независимому лазерному измерению, совпадающему с заданием.",
            targetDistance = data[1], measurements = copy(data[2]), signs = copy(data[3]),
            evidence = string.format("Задание: %.1f stud. Лазер — слева %.1f; по центру %.1f; справа %.1f.", data[1], data[2][1], data[2][2], data[2][3]),
            options = options("left", "Левый путь", "center", "Центральный путь", "right", "Правый путь"),
            answer = answer, preview = 1.5, window = round == 1 and 25.0 or 20.0,
        }
    elseif id == "P03" then
        local sequence = {"manual", "exhaust", "safe", "transfer"}
        if not sequence[round] then return nil end
        return {
            kind = "reconstruction", label = "Восстановите события по независимому журналу обслуживания. Официальное резюме об автоматическом отключении не подтверждено.",
            evidence = "Подписанный журнал: 03:14 — усилители отключены вручную; 03:16 — восстановлена вытяжка; 03:18 — камера переведена в безопасный режим; 03:21 — испытуемый передан в E-05.",
            reconstructionStep = round,
            options = options("safe", "Безопасный режим камеры", "transfer", "Передача в E-05", "manual", "Ручное отключение усилителей", "exhaust", "Восстановление вытяжки"),
            answer = sequence[round], preview = 1.0, window = 18.0,
        }
    elseif id == "P04" then
        local sequence = {"tracking", "occluded", "tracking", "occluded", "adapting", "occluded"}
        local mode = sequence[round]
        if not mode then return nil end
        local movingAllowed = mode == "occluded"
        local holdDuration = mode == "adapting" and 4 or 2
        return {
            kind = "observer", label = movingAllowed and "Шторка закрыта. Сделайте настоящий шаг рядом с пультом, затем подтвердите проход." or string.format("Оптика открыта. Не двигайтесь %d секунды после сигнала, затем подтвердите остановку.", holdDuration),
            observerMode = mode, observerMemory = state.observerMoves,
            movementRequired = movingAllowed, holdDuration = movingAllowed and 0 or holdDuration,
            evidence = mode == "adapting" and "После двух проходов наблюдатель продлил открытое сканирование. Его память — два последних прохода; сквозь закрытую шторку он не видит." or "Правило: открытая оптика — стоять; закрытая шторка — двигаться. Наблюдатель реагирует на открытое движение, а не угадывает намерение.",
            options = options("hold", "Замереть", "move", "Пройти сектор"),
            answer = movingAllowed and "move" or "hold", preview = 2.0, window = 9.0,
        }
    elseif id == "P05" then
        local sequence = {
            {10.00, 10.08, "stable"}, {12.00, 13.10, "stable"},
            {9.00, 8.95, "unstable"}, {8.00, 8.05, "stable"}, {15.00, 14.10, "stable"},
        }
        local data = sequence[round]
        if not data then return nil end
        local answer = data[3] ~= "stable" and "repeat" or (math.abs(data[1] - data[2]) > .2 and "isolate" or "accept")
        return {
            kind = "boundary", label = "Сопоставьте виртуальную телеметрию с независимым физическим каналом. Допуск 0,20. При нестабильном эталоне повторите измерение.",
            virtualReading = data[1], physicalReading = data[2], referenceQuality = data[3], tolerance = .2,
            evidence = string.format("Терминал: %.2f; независимый канал: %.2f. Эталон: %s.", data[1], data[2], data[3] == "stable" and "стабилен" or "НЕСТАБИЛЕН"),
            options = options("accept", "Принять совпадение", "isolate", "Изолировать расхождение", "repeat", "Повторить измерение"),
            answer = answer, preview = 1.5, window = 14.0,
        }
    end
    return nil
end

local function nextCue(state)
    local cue = cueFor(state)
    if not cue then
        state.phase = "completed"
        state.round = state.totalRounds
        state.progress = 1
        state.cue = nil
        state.result = state.experiment == "P05"
            and "Независимая проверка завершена; расхождения изолированы. Происхождение NULL этим испытанием не установлено."
            or "Протокол выполнен. Измерения и действия оператора записаны."
        local item = record(state, "completed", state.result)
        return {kind = "completed", owner = state.owner or 0, experiment = state.experiment, result = state.result, record = copy(item)}
    end
    cue.readyAt = state.now + cue.preview
    cue.deadline = cue.readyAt + cue.window
    state.cue = cue
    state.observerMotionObserved = false
    state.progress = (state.round - 1) / state.totalRounds
    return nil
end

function Engine.new()
    return {
        phase = "idle", experiment = "P01", owner = nil, now = 0, preparedAt = 0,
        temperature = 24, peakTemperature = 24, stress = 0, dose = 0, integrity = 100,
        cooling = true, supply = MAX_SUPPLY, attempts = 0, round = 0, totalRounds = 5,
        progress = 0, records = {}, pendingEvents = {}, result = "", cue = nil,
        observerMoves = 0, observerMotionObserved = false,
        inputs = {Computers = true, Ventilation = true, AcousticAmplifiers = true, PhysicalHall = true, ownerPresent = true, ownerMoving = false},
    }
end

function Engine.setInputs(state, inputs)
    if type(inputs) ~= "table" then return end
    for key in pairs(state.inputs) do
        if type(inputs[key]) == "boolean" then state.inputs[key] = inputs[key] end
    end
end

function Engine.dispatch(state, action, arg, now, actorId)
    clock(state, now)
    if not actorValid(actorId) then return false, "Недействительный оператор" end
    if type(action) ~= "string" or #action > 24 then return false, "Неизвестное действие" end
    local owns = not state.owner or state.owner == actorId
    if action == "cooling" then
        if type(arg) ~= "boolean" then return false, "Ожидается положение охлаждения" end
        state.cooling = arg
        return true, arg and "Охлаждение включено" or "Охлаждение отключено", {kind = "cooling", enabled = arg, owner = actorId}
    elseif action == "resupply" then
        if state.phase == "running" then return false, "Запас пополняют при остановленном испытании" end
        if state.supply >= MAX_SUPPLY then return false, "Запас полон" end
        local amount = math.min(6, MAX_SUPPLY - state.supply)
        state.supply = state.supply + amount
        return true, "Получены расходные материалы", {kind = "resupply", owner = actorId, amount = amount}
    elseif action == "repair" then
        if state.phase == "running" or state.phase == "prepared" then return false, "Сначала остановите и сбросьте испытание" end
        if state.integrity >= 100 then return false, "Стенд исправен" end
        if state.supply < 2 then return false, "Для ремонта нужны 2 комплекта" end
        state.supply = state.supply - 2
        state.integrity = math.min(100, state.integrity + 30)
        return true, "Исправность восстановлена", {kind = "repair", owner = actorId, amount = 30}
    end
    if not owns and not (action == "reset" and state.inputs.ownerPresent == false) then
        return false, "Пульт занят другим оператором"
    end
    if action == "select" then
        if state.phase ~= "idle" then return false, "Сначала завершите и сбросьте текущий протокол" end
        if type(arg) ~= "string" or not TITLES[arg] then return false, "Неизвестный протокол" end
        state.owner = actorId
        state.experiment = arg
        state.inputs.ownerPresent = true
        state.result = ""
        return true, "Выбран " .. arg
    elseif action == "calibrate" then
        if state.phase ~= "idle" then return false, "Калибровка доступна после сброса" end
        local problem = prepareProblem(state)
        if problem then return false, problem end
        if state.supply < 1 then return false, "Нужен комплект калибровки" end
        state.owner = actorId
        state.inputs.ownerPresent = true
        state.supply = state.supply - 1
        state.phase = "prepared"
        state.preparedAt = state.now
        state.result = ""
        return true, "Калибровка принята. Выдержка 2 секунды."
    elseif action == "start" then
        if state.phase ~= "prepared" then return false, "Сначала выполните калибровку" end
        local problem = prepareProblem(state)
        if problem then return false, problem end
        if state.now - state.preparedAt < 2 then return false, "Калибровка ещё не завершена" end
        state.phase = "running"
        state.startedAt = state.now
        state.peakTemperature = state.temperature
        state.attempts = state.attempts + 1
        state.round = 1
        state.totalRounds = ({P01 = 5, P02 = 4, P03 = 4, P04 = 6, P05 = 5})[state.experiment]
        state.observerMoves = 0
        nextCue(state)
        return true, "Испытание запущено", {kind = "started", owner = actorId, experiment = state.experiment}
    elseif action == "respond" then
        if state.phase ~= "running" or not state.cue then return false, "Сейчас нет активного задания" end
        local problem = circuitProblem(state)
        if problem then return false, problem, failed(state, problem, 0) end
        if state.now > state.cue.deadline then
            return false, "Время ответа истекло", failed(state, "Пропущено окно реакции", 4)
        end
        if state.now < state.cue.readyAt then return false, "Подождите начала сигнала" end
        if type(arg) ~= "string" or #arg > 24 then return false, "Недействительный ответ" end
        local known = false
        for _, item in ipairs(state.cue.options) do if item.id == arg then known = true; break end end
        if not known then return false, "Ответ не относится к текущему заданию" end
        if state.experiment == "P04" then
            if state.cue.observerMode ~= "occluded" and state.inputs.ownerMoving then
                return false, "Движение при открытой оптике", failed(state, "Наблюдатель обнаружил движение при открытой оптике", 4)
            end
            if arg == "hold" and arg == state.cue.answer and state.now < state.cue.readyAt + state.cue.holdDuration then
                return false, string.format("Удерживайте неподвижность %d секунды после сигнала", state.cue.holdDuration)
            end
            if arg == "move" and arg == state.cue.answer and not state.observerMotionObserved and not state.inputs.ownerMoving then
                return false, "Сделайте настоящий шаг рядом с пультом при закрытой шторке"
            end
        end
        if arg ~= state.cue.answer then
            return false, "Нарушена процедура", failed(state, "Неверное действие оператора: протокол остановлен", 4)
        end
        if state.experiment == "P04" and arg == "move" then state.observerMoves = state.observerMoves + 1 end
        state.stress = clamp(state.stress - 2, 0, 100)
        state.round = state.round + 1
        local event = nextCue(state)
        return true, event and "Протокол завершён" or "Измерение принято", event
    elseif action == "abort" then
        if state.phase ~= "running" and state.phase ~= "prepared" then return false, "Испытание уже остановлено" end
        return true, "Выполнен безопасный останов", failed(state, "Испытание остановлено оператором", 0)
    elseif action == "reset" then
        if state.phase == "running" then return false, "Сначала выполните безопасный останов" end
        state.phase = "idle"
        state.owner = nil
        state.cue = nil
        state.round = 0
        state.progress = 0
        state.result = ""
        state.startedAt = nil
        state.inputs.ownerPresent = true
        return true, "Пульт сброшен"
    elseif action == "medical" then
        if state.phase == "running" or state.phase == "prepared" then return false, "Медицинская помощь доступна после остановки" end
        if state.supply < 1 then return false, "Медицинский запас исчерпан" end
        state.supply = state.supply - 1
        state.stress = math.max(0, state.stress - 35)
        state.dose = math.max(0, state.dose - 10)
        return true, "Медицинский комплект использован", {kind = "medical", owner = actorId, amount = 25}
    end
    return false, "Неизвестное действие"
end

function Engine.step(state, dt, now)
    clock(state, now)
    dt = finite(dt) and clamp(dt, 0, 2) or 0
    local events = state.pendingEvents
    state.pendingEvents = {}
    local running = state.phase == "running"
    -- Cooling removes more heat as the exchanger rises above ambient. A sound
    -- running loop settles near 42 °C instead of making load thermally invisible.
    local coolingRate = state.cooling and (.18 * math.max(0, state.temperature - 24) + .25) or .25
    local thermalRate = (running and 3.4 or 0) - coolingRate
    state.temperature = clamp(state.temperature + thermalRate * dt, 24, 100)
    state.peakTemperature = math.max(state.peakTemperature, state.temperature)
    if running then
        state.dose = clamp(state.dose + .08 * dt, 0, 100)
        state.stress = clamp(state.stress + (state.temperature >= 60 and 1.8 or .25) * dt, 0, 100)
    else
        state.stress = math.max(0, state.stress - .5 * dt)
    end
    if state.phase == "prepared" or running then
        local problem = circuitProblem(state)
        if problem then
            table.insert(events, failed(state, problem, 0))
        elseif state.temperature >= 80 then
            table.insert(events, failed(state, "Перегрев: сработала тепловая защита", 12))
        elseif running and state.experiment == "P04" and state.cue and state.now >= state.cue.readyAt and state.inputs.ownerMoving then
            if state.cue.observerMode == "occluded" then
                state.observerMotionObserved = true
                if state.now > state.cue.deadline then
                    table.insert(events, failed(state, "Пропущено окно реакции", 4))
                end
            else
                table.insert(events, failed(state, "Наблюдатель обнаружил движение при открытой оптике", 4))
            end
        elseif running and state.cue and state.now > state.cue.deadline then
            table.insert(events, failed(state, "Пропущено окно реакции", 4))
        elseif state.phase == "prepared" and state.now - state.preparedAt > 120 then
            table.insert(events, failed(state, "Срок калибровки истёк", 0))
        end
    end
    -- Include damage queued by a failure detected during this step, once only.
    for _, event in ipairs(state.pendingEvents) do table.insert(events, event) end
    state.pendingEvents = {}
    return events
end

function Engine.snapshot(state, now)
    -- A snapshot is a view, not a clock mutation or a route into private answers.
    local viewTime = finite(now) and math.max(state.now, now) or state.now
    local cue = nil
    if state.cue then
        cue = {}
        for key, value in pairs(state.cue) do
            if key ~= "answer" and key ~= "window" and key ~= "preview" then cue[key] = copy(value) end
        end
        cue.ready = viewTime >= state.cue.readyAt
        cue.remaining = math.max(0, state.cue.deadline - viewTime)
        cue.previewRemaining = math.max(0, state.cue.readyAt - viewTime)
    end
    local requirements = {}
    for _, id in ipairs(REQUIREMENTS[state.experiment]) do
        table.insert(requirements, {id = id, label = CIRCUIT_NAMES[id], enabled = state.inputs[id] == true})
    end
    local objectives = {
        idle = "Выберите протокол на местном пульте и выполните калибровку.",
        prepared = "Дождитесь окончания калибровки и запустите испытание.",
        running = cue and cue.label or "Следуйте протоколу.",
        completed = "Результат записан. Сбросьте пульт перед следующим испытанием.",
        failed = "Устраните причину остановки, при необходимости получите помощь и сбросьте пульт.",
    }
    return {
        phase = state.phase, experiment = state.experiment, title = TITLES[state.experiment], owner = state.owner or 0,
        objective = objectives[state.phase], cue = cue, result = state.result,
        attempts = state.attempts, round = state.round, totalRounds = state.totalRounds,
        calibrationRemaining = state.phase == "prepared" and math.max(0, 2 - (viewTime - state.preparedAt)) or 0,
        telemetry = {
            temperature = state.temperature, stress = state.stress, dose = state.dose, integrity = state.integrity,
            progress = state.progress, cooling = state.cooling, supply = state.supply,
        },
        supply = state.supply, requirements = requirements, records = copy(state.records), serverTime = viewTime,
        recoverable = state.phase ~= "running",
    }
end

return Engine
