"""Execute the actual V10 client with focused GUI/event Roblox API doubles.

This checks UI state, protocol evidence and emitted requests, not Roblox rendering,
asset playback, layout measurement, device input or client/server networking.
Requires lupa==2.6, as used by the other V10 runtime checks.
"""
from pathlib import Path
from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
MOCK = r'''
_clock=100;_serverTime=100;_warnings={};_requests={};_soundsPlayed=0
os.clock=function() return _clock end
local function signal()
 local s={slots={}}
 function s:Connect(f)
  local slot={f=f,active=true};table.insert(self.slots,slot)
  return {Disconnect=function() slot.active=false end}
 end
 function s:Fire(...)
  for _,slot in ipairs(self.slots) do if slot.active then slot.f(...) end end
 end
 return s
end
local vectorMeta={__eq=function(a,b) return a.X==b.X and a.Y==b.Y end}
Vector2={new=function(x,y) return setmetatable({X=x,Y=y},vectorMeta) end}
UDim={new=function(scale,offset) return {Scale=scale,Offset=offset} end}
UDim2={new=function(xs,xo,ys,yo) return {X=UDim.new(xs,xo),Y=UDim.new(ys,yo)} end}
function UDim2.fromScale(x,y) return UDim2.new(x,0,y,0) end
function UDim2.fromOffset(x,y) return UDim2.new(0,x,0,y) end
Color3={new=function(r,g,b) return {R=r,G=g,B=b} end,
 fromRGB=function(r,g,b) return {R=r/255,G=g/255,B=b/255} end}
Enum=setmetatable({}, {__index=function(t,k)
 local values=setmetatable({}, {__index=function(group,key) rawset(group,key,k..'.'..key);return k..'.'..key end})
 rawset(t,k,values);return values
end})
local methods={};local instanceMeta={}
function instanceMeta.__index(o,k)
 if methods[k] then return methods[k] end
 if k=='ClassName' then return rawget(o,'_class') end
 return o._props[k]
end
function instanceMeta.__newindex(o,k,v)
 if k=='Parent' then
  local old=o._props.Parent
  if old then for i,c in ipairs(old._children) do if c==o then table.remove(old._children,i);break end end end
  if v then table.insert(v._children,o) end
 end
 o._props[k]=v
end
Instance={new=function(cls)
 local o=setmetatable({_class=cls,_children={},_props={Name=cls,Visible=true,Active=true,
  Activated=signal(),Destroying=signal(),OnClientEvent=signal(),Heartbeat=signal(),InputBegan=signal(),
  Size=UDim2.fromOffset(0,0)}},instanceMeta)
 return o
end}
function methods:IsA(cls)
 local gui={Frame=true,TextLabel=true,TextButton=true,ScrollingFrame=true}
 return cls==self.ClassName or cls=='Instance' or (cls=='GuiObject' and gui[self.ClassName])
end
function methods:FindFirstChild(n)
 for _,child in ipairs(self._children) do if child.Name==n then return child end end
end
function methods:WaitForChild(n) return self:FindFirstChild(n) end
function methods:GetChildren() local out={};for i,c in ipairs(self._children) do out[i]=c end;return out end
function methods:GetDescendants()
 local out={};local function visit(parent) for _,child in ipairs(parent:GetChildren()) do table.insert(out,child);visit(child) end end
 visit(self);return out
end
function methods:Destroy()
 self.Destroying:Fire()
 for _,child in ipairs(self:GetChildren()) do child:Destroy() end
 self.Parent=nil;self._destroyed=true
end
function methods:FireServer(action,arg) table.insert(_requests,{action=action,arg=arg}) end
function methods:Play() _soundsPlayed=_soundsPlayed+1;self.IsPlaying=true end
function methods:Stop() self.IsPlaying=false end
function methods:GetServerTimeNow() return _serverTime end
function methods:GetFocusedTextBox() return nil end
function methods:GetTextSize(text,size,font,bounds)
 local maxLines=0
 for line in string.gmatch(tostring(text)..'\n','(.-)\n') do
  maxLines=maxLines+math.max(1,math.ceil(#line*size*.5/math.max(1,bounds.X)))
 end
 return Vector2.new(bounds.X,maxLines*size)
end
local function new(cls,parent,name)
 local o=Instance.new(cls);o.Name=name or cls;o.Parent=parent;return o
end
_player=new('Player',nil,'LocalPlayer');_player.UserId=123
_playerGui=new('PlayerGui',_player,'PlayerGui')
_players=new('Players',nil,'Players');_players.LocalPlayer=_player
_rs=new('ReplicatedStorage',nil,'ReplicatedStorage')
local network=new('Folder',_rs,'ProjectNullV10')
_request=new('RemoteEvent',network,'Request');_push=new('RemoteEvent',network,'Push')
_run=new('RunService',nil,'RunService');_light=new('Lighting',nil,'Lighting')
_sound=new('SoundService',nil,'SoundService');_text=new('TextService',nil,'TextService')
_input=new('UserInputService',nil,'UserInputService')
workspace=new('Workspace',nil,'Workspace');workspace.CurrentCamera={ViewportSize=Vector2.new(1024,720)}
script=new('LocalScript',nil,'ProjectNullClient_V10')
local services={Players=_players,ReplicatedStorage=_rs,RunService=_run,Lighting=_light,SoundService=_sound,TextService=_text,UserInputService=_input}
game={GetService=function(_,n) assert(services[n],n);return services[n] end}
warn=function(message) table.insert(_warnings,tostring(message)) end
function tick_ui(seconds)
 _clock=_clock+seconds;_serverTime=_serverTime+seconds;_run.Heartbeat:Fire(seconds)
end
function find_gui(name)
 for _,child in ipairs(_playerGui:GetDescendants()) do if child.Name==name then return child end end
end
function visible_text(needle)
 for _,child in ipairs(_playerGui:GetDescendants()) do
  if (child:IsA('TextLabel') or child:IsA('TextButton')) and type(child.Text)=='string' and string.find(child.Text,needle,1,true) then
   local parent=child;local shown=true
   while parent and parent~=_playerGui do if parent.Visible==false then shown=false end;parent=parent.Parent end
   if shown then return true end
  end
 end
 return false
end
function click(text)
 for _,child in ipairs(_playerGui:GetDescendants()) do
  if child:IsA('TextButton') and child.Text==text then child.Activated:Fire();return child end
 end
 error('Button not found: '..text)
end
function snapshot(phase,experiment,cue)
 _push.OnClientEvent:Fire('snapshot',{
  phase=phase,experiment=experiment or 'P01',owner=123,objective='Проверка задания',cue=cue,
  telemetry={temperature=32,stress=25,progress=.5,cooling=true,supply=3},supply=3,
  profile={documents={},completed={},records={},saveStatus='Сохранено'},
  requirements={{id='Computers',label='Компьютеры',enabled=true},{id='Ventilation',label='Вентиляция',enabled=false}},
  round=1,totalRounds=5,
  context={kind='console',argument=experiment or 'P01',title='Операторский терминал'},
 })
end
'''


def fixture():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK)
    lua.execute((ROOT / "src/ProjectNullClient_V10.client.luau").read_text())
    return lua


def main():
    lua = fixture()
    g = lua.globals()
    assert g._requests[1].action == 'hello'
    assert len(g._warnings) == 0
    assert g.find_gui('ProjectNullV10') is not None

    # Actual modal controls emit requests without inventing local experiment state.
    lua.execute("snapshot('idle','P01');click('ВЫБРАТЬ P01')")
    assert g._requests[len(g._requests)].action == 'select'
    assert g._requests[len(g._requests)].arg == 'P01'
    lua.execute("for _,item in ipairs(_playerGui:GetDescendants()) do if item:IsA('TextButton') and item.Text=='СБРОСИТЬ ЦИКЛ' then assert(item.Active==true,'Owner can release an idle console') end end")
    assert g.visible_text('Компьютеры: ВКЛ')
    assert g.visible_text('Вентиляция: ВЫКЛ')
    lua.execute("snapshot('prepared','P01');tick_ui(.3);click('ЗАПУСТИТЬ ИСПЫТАНИЕ')")
    assert g._requests[len(g._requests)].action == 'start'
    lua.execute("for _,item in ipairs(_playerGui:GetDescendants()) do if item:IsA('TextButton') and item.Text=='АВАРИЙНО ОСТАНОВИТЬ' then assert(item.Active==true,'Prepared calibration can be aborted') end end")

    # P01 evidence must show both channels, including an audio text alternative.
    lua.execute("""snapshot('running','P01',{kind='sync',label='Сравнить каналы',visual='C',audio='A',frequency=440,
        evidence='Доступный текстовый канал',readyAt=_serverTime+2,deadline=_serverTime+12,
        options={{id='C',label='Канал C'},{id='reject',label='Отклонить импульс'}}})""")
    assert g.find_gui('Modal').Visible is False, 'Console must give the running cue space'
    assert g.visible_text('СВЕТОВОЙ КАНАЛ: C')
    assert g.visible_text('АКУСТИЧЕСКИЙ КАНАЛ: A / 440 Гц')
    assert g.visible_text('Доступный текстовый канал')
    before = len(g._requests)
    lua.execute("click('Отклонить импульс')")
    assert len(g._requests) == before, 'Preview does not allow a premature response'
    lua.execute("tick_ui(2.2);click('Отклонить импульс')")
    assert g._requests[len(g._requests)].action == 'respond'
    assert g._requests[len(g._requests)].arg == 'reject'

    # P02 physical sensors cannot be substituted with a remote HUD answer.
    lua.execute("""snapshot('running','P02',{kind='measurement',label='Измерить путь',targetDistance=6,
        measurements={9.2,6,3.5},signs={'БЛИЗКО','ДАЛЕКО','ЦЕЛЬ'},evidence='Независимый лазер',
        readyAt=_serverTime,deadline=_serverTime+25,
        options={{id='left',label='Левый путь'},{id='center',label='Центральный путь'},{id='right',label='Правый путь'}}})""")
    assert g.visible_text('ЗАДАНИЕ: 6 stud')
    assert g.visible_text('ЛЕВЫЙ: лазер 9.2 stud')
    assert g.visible_text('ЦЕНТР: лазер 6 stud')
    assert g.visible_text('ПРАВЫЙ: лазер 3.5 stud')
    assert g.visible_text('Дойдите до выбранного датчика в E-10')
    before = len(g._requests)
    lua.execute("tick_ui(.3);click('Центральный путь')")
    assert len(g._requests) == before

    # The narrative gate is visible before P03 calibration.
    lua.execute("""_push.OnClientEvent:Fire('snapshot',{phase='idle',experiment='P03',owner=123,
        profile={documents={},records={}},telemetry={},evidenceReady=false,
        evidenceRequired={{id='DOC_P03_LOG',title='Подписанный журнал',room='E-04'},{id='DOC_P03_CORRECTION',title='Исправление отчёта',room='E-07'}},
        context={kind='console',argument='P03',title='Реконструкция'}})""")
    assert g.visible_text('ПЕРЕД КАЛИБРОВКОЙ НАЙДИТЕ И ПРОЧИТАЙТЕ:')
    assert g.visible_text('Подписанный журнал / E-04')
    assert g.visible_text('Исправление отчёта / E-07')
    lua.execute("for _,item in ipairs(_playerGui:GetDescendants()) do if item:IsA('TextButton') and item.Text=='КАЛИБРОВАТЬ' then assert(item.Active==false) end end")

    # P03 reconstruction is solvable from the visible independent chronology.
    lua.execute("""snapshot('running','P03',{kind='reconstruction',label='Восстановить события',
        reconstructionStep=2,evidence='03:14 — усилители отключены вручную; 03:16 — восстановлена вытяжка',
        readyAt=_serverTime,deadline=_serverTime+18,options={{id='exhaust',label='Восстановление вытяжки'}}})""")
    assert g.visible_text('ВОССТАНОВЛЕНИЕ / СОБЫТИЕ 2')
    assert g.visible_text('03:14 — усилители отключены вручную')

    # P04 explains real movement, and hold confirmation observes its two-second gate.
    lua.execute("""snapshot('running','P04',{kind='observer',label='Следовать наблюдателю',observerMode='tracking',
        movementRequired=false,observerMemory=2,readyAt=_serverTime,deadline=_serverTime+9,
        options={{id='hold',label='Замереть'},{id='move',label='Пройти сектор'}}})""")
    assert g.visible_text('ОПТИКА ОТКРЫТА')
    assert g.visible_text('Оставайтесь неподвижны 2 сек.')
    before = len(g._requests)
    lua.execute("click('Замереть')")
    assert len(g._requests) == before
    lua.execute("tick_ui(2.1);click('Замереть')")
    assert g._requests[len(g._requests)].arg == 'hold'
    # Adaptive scanning must honor the server's longer hold duration.
    lua.execute("""snapshot('running','P04',{kind='observer',label='Продлённое сканирование',observerMode='adapting',
        movementRequired=false,holdDuration=4,readyAt=_serverTime,deadline=_serverTime+12,
        options={{id='hold',label='Замереть'}}})""")
    assert g.visible_text('Оставайтесь неподвижны 4 сек.')
    before = len(g._requests)
    lua.execute("tick_ui(2.1);click('Замереть')")
    assert len(g._requests) == before, 'Adaptive scan requires more than the normal two seconds'
    lua.execute("tick_ui(2.1);click('Замереть')")
    assert g._requests[len(g._requests)].arg == 'hold'
    assert len(g._requests) == before + 1
    lua.execute("""snapshot('running','P04',{kind='observer',label='Шторка закрыта',observerMode='occluded',
        movementRequired=true,readyAt=_serverTime,deadline=_serverTime+9,
        options={{id='move',label='Пройти сектор'}}})""")
    assert g.visible_text('ШТОРКА ЗАКРЫТА')
    assert g.visible_text('сделайте настоящий шаг рядом с пультом')

    # P05 displays independent readings and the reference-quality check.
    lua.execute("""snapshot('running','P05',{kind='boundary',label='Сверить показания',virtualReading=12,
        physicalReading=13.1,referenceQuality='unstable',tolerance=.2,evidence='Проверьте эталон',
        readyAt=_serverTime,deadline=_serverTime+14,options={{id='repeat',label='Повторить измерение'}}})""")
    assert g.visible_text('ВИРТУАЛЬНЫЙ КАНАЛ: 12')
    assert g.visible_text('НЕЗАВИСИМЫЙ КАНАЛ: 13.1')
    assert g.visible_text('ЭТАЛОН: НЕСТАБИЛЕН')

    # Viewport changes keep long evidence and every response inside a scroll body.
    lua.execute("workspace.CurrentCamera.ViewportSize=Vector2.new(390,640);tick_ui(.2)")
    panel = g.find_gui('ExperimentCue')
    assert panel.Size.X.Offset <= 366 and panel.Size.Y.Offset <= 550
    assert g.find_gui('CueBody').ClassName == 'ScrollingFrame'
    assert g.find_gui('CueBody').AutomaticCanvasSize == 'AutomaticSize.Y'
    assert g.find_gui('Telemetry').Visible is False

    # Physical movement trials leave the lower half free for the touch joystick.
    for protocol, cue_kind in [('P02', 'measurement'), ('P04', 'observer')]:
        lua.execute("""snapshot('running','%s',{kind='%s',label='Физическое перемещение',
            observerMode='occluded',movementRequired=true,evidence='Подсказка движения',
            readyAt=_serverTime,deadline=_serverTime+20,options={{id='move',label='Пройти сектор'}}})""" % (protocol, cue_kind))
        panel = g.find_gui('ExperimentCue')
        assert panel.AnchorPoint.Y == 0, 'Physical mobile cue must be anchored at the top'
        assert panel.Position.Y.Scale == 0 and panel.Position.Y.Offset == 12
        assert panel.Size.Y.Offset <= min(340, 640 * .45)
        assert panel.Position.Y.Offset + panel.Size.Y.Offset <= 640 * .55
        assert g.find_gui('CueBody').ClassName == 'ScrollingFrame'
        assert g.find_gui('Telemetry').Visible is False

    # Audio/effects toggles exercise callbacks (including local closure binding).
    lua.execute("click('ЗВУК: ВКЛ');click('ЭФФЕКТЫ: ВКЛ');tick_ui(.2)")
    assert g.visible_text('ЗВУК: ВЫКЛ')
    assert g.visible_text('ЭФФЕКТЫ: ВЫКЛ')
    assert g._light.FindFirstChild(g._light, 'ProjectNullV10_Blur').Size == 0

    # Journal is built from collected records and full server-provided documents.
    lua.execute("""_push.OnClientEvent:Fire('snapshot',{phase='completed',experiment='P05',owner=123,
        telemetry={temperature=30,stress=12,progress=1,cooling=true},profile={completed={P05=true},
        documents={DOC_A=true},journal={{id='DOC_A',title='Журнал ремонта',room='E-07',body='Независимая запись 03:14'}},
        records={{experiment='P05',result='Принято',summary='Эталон сверили'}},saveStatus='Сохранено'}})
        click('ЖУРНАЛ [J]');click('Журнал ремонта / E-07')""")
    assert g.visible_text('Независимая запись 03:14')
    lua.execute("click('К ЛИЧНОМУ ЖУРНАЛУ');click('СОХРАНИТЬ ПРОГРЕСС')")
    assert g._requests[len(g._requests)].action == 'save'
    assert g.visible_text('P05 / Принято')
    lua.execute("_push.OnClientEvent:Fire('notice','Проверка сервера');tick_ui(6)")
    assert g.find_gui('Notice').Visible is False

    # Clean shutdown removes local effects and reconnect-free UI state.
    lua.execute('script:Destroy()')
    assert g._light.FindFirstChild(g._light, 'ProjectNullV10_Blur') is None
    assert g._sound.FindFirstChild(g._sound, 'ProjectNullV10_Audio') is None
    print('PASS: actual V10 client boot, requests, all five protocol evidence views,')
    print('      preview/hold gates, P02 physical-only choices, mobile scroll, journal and cleanup.')


if __name__ == '__main__':
    main()
