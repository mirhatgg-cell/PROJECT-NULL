-- Server-only dialogue graph evaluation. No Roblox services or client state.
local Dialogue = {}
local content = {staff = {}, dialogues = {}}

function Dialogue.configure(authored)
    assert(type(authored) == "table", "Dialogue content is missing")
    content = authored
end

local function allowed(rule, profile, snapshot, depth)
    if rule == nil then return true end
    if type(rule) ~= "table" or (depth or 0) > 8 then return false end
    profile, snapshot = profile or {}, snapshot or {}
    depth = (depth or 0) + 1
    if rule.document then
        return type(rule.document) == "string" and type(profile.documents) == "table"
            and profile.documents[rule.document] == true
    elseif rule.completed then
        return type(rule.completed) == "string" and type(profile.completed) == "table"
            and profile.completed[rule.completed] == true
    elseif rule.phase then
        return type(rule.phase) == "string" and snapshot.phase == rule.phase
    elseif rule.any then
        if type(rule.any) ~= "table" or #rule.any == 0 then return false end
        for _, item in ipairs(rule.any) do if allowed(item, profile, snapshot, depth) then return true end end
        return false
    elseif rule.all then
        if type(rule.all) ~= "table" or #rule.all == 0 then return false end
        for _, item in ipairs(rule.all) do if not allowed(item, profile, snapshot, depth) then return false end end
        return true
    end
    return false
end

function Dialogue.allowed(rule, profile, snapshot)
    return allowed(rule, profile, snapshot, 0)
end

function Dialogue.canRead(document, profile, snapshot)
    return type(document) == "table" and allowed(document.requires, profile, snapshot, 0)
end

local function getGraph(id)
    if type(id) ~= "string" or #id > 40 then return nil end
    local person = content.staff and content.staff[id]
    local graph = content.dialogues and content.dialogues[id]
    if type(person) ~= "table" or type(graph) ~= "table" then return nil end
    return graph, person
end

local function render(id, nodeId, profile, snapshot, seen)
    local graph, person = getGraph(id)
    if not graph then return nil, "Сотрудник сейчас недоступен" end
    local node, text
    if nodeId == "start" then
        node = graph
        local met = (type(profile.metStaff) == "table" and profile.metStaff[id])
            or (type(seen) == "table" and seen[id])
        text = met and graph["repeat"] or graph.first
    else
        node = graph.nodes and graph.nodes[nodeId]
        if type(node) ~= "table" or not allowed(node.requires, profile, snapshot, 0) then
            return nil, "Для этой темы пока недостаточно подтверждённых сведений"
        end
        text = node.text
        for _, variant in ipairs(node.variants or {}) do
            if allowed(variant.when, profile, snapshot, 0) then text = variant.text; break end
        end
    end
    if type(text) ~= "string" or text == "" then return nil, "Реплика отсутствует" end
    local choices = {}
    for _, choice in ipairs(node.options or {}) do
        local target = choice.id
        local targetNode = graph.nodes and graph.nodes[target]
        local validTarget = target == "close" or target == "back" or type(targetNode) == "table"
        if type(target) == "string" and #target <= 40 and validTarget
            and type(choice.label) == "string" and allowed(choice.requires, profile, snapshot, 0)
            and (not targetNode or allowed(targetNode.requires, profile, snapshot, 0)) then
            table.insert(choices, {id = target, label = choice.label})
        end
        if #choices >= 10 then break end
    end
    return {
        id = id, argument = id, name = person.name or id, role = person.role or "Персонал",
        node = nodeId, text = text, options = choices,
    }
end

function Dialogue.open(id, profile, snapshot, seen)
    if type(profile) ~= "table" or type(snapshot) ~= "table" then return nil, "Нет контекста разговора" end
    return render(id, "start", profile, snapshot, seen)
end

function Dialogue.refresh(id, node, profile, snapshot, seen)
    if type(node) ~= "string" or #node > 40 or type(profile) ~= "table"
        or type(snapshot) ~= "table" then return nil, "Нет контекста разговора" end
    return render(id, node, profile, snapshot, seen)
end

function Dialogue.choose(id, node, choice, profile, snapshot, seen)
    if type(node) ~= "string" or #node > 40 or type(choice) ~= "string" or #choice > 40 then
        return nil, "Недействительный вариант ответа"
    end
    if type(profile) ~= "table" or type(snapshot) ~= "table" then return nil, "Нет контекста разговора" end
    local current, reason = render(id, node, profile, snapshot, seen)
    if not current then return nil, reason end
    local selected = false
    for _, option in ipairs(current.options) do if option.id == choice then selected = true; break end end
    if not selected then return nil, "Эта тема сейчас недоступна" end
    if choice == "close" then
        return {id = id, argument = id, name = current.name, role = current.role,
                node = "closed", text = "", options = {}, closed = true}
    end
    return render(id, choice == "back" and "start" or choice, profile, snapshot, seen)
end

-- Kept private content is never included wholesale in a public payload.
function Dialogue.identity(id)
    local _, person = getGraph(id)
    return person and {id = id, name = person.name, role = person.role} or nil
end

return Dialogue
