"""Physical immersion machinery and accessible medical storage for V9."""
import xml.etree.ElementTree as ET

from v9_common import WHITE,LIGHT,METAL,DARK,BLACK,CYAN,BLUE,AMBER,RED,TEAL,name


def board(b,parent,label,center,size=(1.2,.07,.8),chips=3):
    x,y,z=center
    group=b.model(parent,label)
    b.part(group,'PCB_Substrate',(x,y,z),size,(39,100,81),role='internal')
    for i in range(chips):
        px=x-size[0]*.28+i*size[0]*.56/max(1,chips-1)
        b.part(group,'SignalModule',(px,y+.09,z),(.22,.12,.25),BLACK,role='internal')
        b.segment(group,'SignalTrace',(px,y+.042,z-.28),(px,y+.042,z-.1),.025,METAL,role='internal')
    return group


def build(b,parent,source_root):
    root=b.model(parent,'E03_Immersion_Machinery_V9')
    b.note(root,'Purpose','Hollow serviceable neural-interface hardware, actuator base, control cabinet and actual acoustic emergency stop. Fictional machinery, without clinical procedures.')
    old=b.find('GantrySignalAndSupply',under=b.find('Visual_Detail_V7',under=source_root))
    b.remove_named(old,{'InterfaceEnclosure','EnclosureFront','InterfaceIDPlate','EnclosureFastener','SocketMount','ConnectorBody','ConnectorIndex','UnusedPortCap','HarnessStrainRelief'})
    case,door,_=b.shell(root,'NIF_ConnectionCabinet',(6.25,-56.9,6),(2.5,4.1,1.34),WHITE,thickness=.09,service=False)
    for y in (-58.35,-57.15,-55.95):
        board(b,case,'NIF_SignalCard',(6.25,y,6.12),(1.7,.08,.75),3)
    b.part(case,'IsolatedPowerModule',(5.55,-58.35,6.1),(.4,.6,.7),DARK,role='internal')
    for y in (-58.45,-57.75,-57.05):
        b.segment(case,'HarnessInternalTermination',(5.55,y,6.08),(5.9,y,6.08),.07,BLACK,role='internal')
    b.part(case,'HeatSinkBase',(6.95,-56.6,6.3),(.34,1.8,.25),METAL,1088,role='internal')
    for y in (-57.25,-56.95,-56.65,-56.35,-56.05):
        b.part(case,'HeatSinkFin',(6.95,y,6.1),(.38,.08,.6),METAL,1088,role='internal')
    for x in (5.6,6.25,6.9):
        b.part(case,'TerminalRailBlock',(x,-58.6,6.22),(.4,.25,.6),AMBER,role='internal')
    b.segment(case,'SupplyConnection',(6.25,-58.9,7.35),(6.25,-58.9,6.45),.18,BLACK,role='internal')
    badge=b.part(case,'NIF_CabinetPlate',(6.25,-56.6,5.265),(1.9,1.2,.05),DARK)
    b.label(badge,'NIF / E-03\nПОДКЛЮЧЕНИЯ\nСЕРВИСНЫЙ ДОСТУП')
    handle=b.part(case,'NIF_DoorHandle',(7.1,-57.6,5.16),(.13,.7,.2),METAL,1088)
    b.service(door,(5.09,-56.9,5.375),angle=100,label='NIF: разъёмы и карты',moving=[badge,handle])

    gantry=b.find('NeuralSensorGantry',under=source_root)
    b.remove_named(gantry,{'UpperSensorHousing'})
    head,hd,_=b.shell(root,'NIF_UpperSensor',(0,-54.56,3.12),(1.4,.46,.75),WHITE,thickness=.04,front='Z+',service=False)
    board(b,head,'SensorADC',(0,-54.62,3.12),(.95,.04,.42),2)
    b.part(head,'SensorOpticsMount',(0,-54.65,2.92),(.45,.12,.14),DARK,role='internal')
    b.service(hd,(.66,-54.56,3.475),angle=95,label='NIF: верхний сенсор')

    # Replace the original filled pedestal with a supported real actuator bay.
    chair=b.find('E03_ImmersionSystem',under=source_root)
    b.remove_named(chair,{'ChairPedestal'})
    base,bd,_=b.shell(root,'Chair_ActuatorBase',(0,-62.7,0),(3,1.7,4),DARK,thickness=.1,front='X+',service=False)
    for x in (-1.1,1.1):
        for z in (-1.5,1.5):
            b.part(base,'PedestalIsolationFoot',(x,-63.595,z),(.45,.09,.45),BLACK,role='structure')
    b.segment(base,'LinearActuatorCylinder',(0,-63.35,0),(0,-62.45,0),.7,METAL,role='internal')
    b.segment(base,'ActuatorPiston',(0,-62.5,0),(0,-61.96,0),.32,METAL,role='internal')
    b.part(base,'SeatLoadPlate',(0,-61.98,0),(1.2,.14,1.8),METAL,1088,role='internal')
    b.segment(base,'ActuatorDriveMotor',(-.7,-63.05,-1),(.25,-63.05,-1),.55,DARK,role='internal')
    b.part(base,'DriveGearbox',(.55,-63.05,-1),(.5,.55,.55),METAL,1088,role='internal')
    board(b,base,'PositionController',(-.8,-63.28,.75),(.8,.06,1),3)
    b.segment(base,'DrivePowerLead',(-.8,-63.18,.75),(-.6,-63.18,-1),.08,BLACK,role='internal')
    b.service(bd,(1.45,-62.7,-1.9),angle=95,label='Кресло: привод и опора')

    # A substantial floor-standing 4-channel service cabinet beside the chamber.
    cab,cd,_=b.shell(root,'EXP_NIF_FourChannelCabinet',(21,-59,10.6),(3.8,10,2.4),WHITE,service=False)
    for x in (19.55,22.45):
        b.part(cab,'CabinetFoot',(x,-63.94,10.6),(.6,.12,1.7),DARK,role='structure')
    for i,y in enumerate((-62.4,-60.6,-58.8,-57),1):
        b.part(cab,'ModuleShelf',(21,y-.55,10.65),(3.1,.12,1.8),METAL,1088,role='structure')
        module=b.model(cab,f'Channel_{i}')
        board(b,module,'DriverBoard',(21,y-.3,10.7),(2.5,.08,1.1),4)
        b.part(module,'ChannelTransformer',(20.1,y,10.8),(.65,.6,.6),DARK,role='internal')
        for x in (20.8,21.3,21.8):
            b.segment(module,'DC_LinkCapacitor',(x,y-.22,10.8),(x,y+.3,10.8),.28,BLUE,role='internal')
        b.part(module,'OutputTerminal',(22.15,y,10),(.3,.65,.55),AMBER,role='internal')
        b.segment(module,'OutputHarness',(22.15,y,10.15),(22.15,-54.3,10.15),.09,BLACK,role='internal')
    b.part(cab,'MainIsolator',(21,-55.4,10.6),(1.1,.85,1),DARK,role='internal')
    for x in (20,22):
        b.part(cab,'VentilationSlot',(x,-54.8,10.3),(.7,.15,.65),BLACK,role='internal')
    plate=b.part(cab,'FourChannelCabinetLegend',(21,-56.3,9.335),(3.1,2,.06),DARK)
    b.label(plate,'EXP-NIF / 4 КАНАЛА\nПИТАНИЕ • ДРАЙВЕРЫ\nДОСТУП К МОДУЛЯМ')
    hand=b.part(cab,'CabinetHandle',(22.4,-60,9.22),(.16,1.4,.2),METAL,1088)
    b.service(cd,(19.22,-59,9.46),angle=95,label='NIF: силовые модули',moving=[plate,hand])
    for y in (-54.0,-45):
        b.segment(root,'NIF_RoutedSupply',(21,y,10.6),(6.25,y,7.35),.2,DARK)
    b.segment(root,'CabinetUpperFeed',(21,-54.1,10.6),(21,-45,10.6),.2,DARK)
    b.segment(root,'GantryUpperFeed',(6.25,-45,7.35),(6.25,-50,7.35),.2,DARK)
    for x,z in ((21,10.6),(14,9.18),(6.25,7.35)):
        b.segment(root,'OverheadRouteSuspension',(x,-38.01,z),(x,-45,z),.08,METAL,role='structure')

    # Turn the old mock-up into an actual cut-off for the existing amplifier circuit.
    stop=b.find('EmergencyStopVisualPrototype',under=source_root)
    b.remove_named(stop,{'StopBackingBox','StopLegend','PrototypeLegend'})
    stem=b.find('PedestalStem',under=stop)
    stem.find("Properties/Vector3[@name='size']/Y").text='3.075'
    stem.find("Properties/CoordinateFrame[@name='CFrame']/Y").text='-61.8625'
    sb,sd,_=b.shell(root,'NIF_EmergencyStopContacts',(7,-59.5,-3.4),(1.65,1.65,.72),AMBER,thickness=.06,front='Z+',service=False)
    b.part(sb,'NormallyClosedContactBlock',(7,-59.5,-3.4),(.65,.8,.25),BLACK,role='internal')
    for x in (6.6,7.4):
        b.part(sb,'ContactTerminal',(x,-59.65,-3.4),(.15,.4,.18),METAL,1088,role='internal')
        b.segment(sb,'ContactInternalLead',(x,-59.65,-3.4),(7,-60.15,-3.4),.06,BLACK,role='internal')
    b.segment(root,'EmergencyStopStemHarness',(7,-60.2,-3.4),(7,-63.6,-3.4),.08,BLACK,role='internal')
    b.segment(root,'EmergencyStopPlatformHarness',(7,-63.6,-3.4),(7,-63.6,7.35),.08,BLACK,role='internal')
    b.segment(root,'EmergencyStopPowerTermination',(7,-63.6,7.35),(6.25,-63.6,7.35),.08,BLACK,role='internal')
    b.service(sd,(7.765,-59.5,-3.07),angle=95,label='Аварийный пост: контакты')
    button=b.find('RedMushroomHead',under=stop)
    b.role(button,'control')
    prompt=b.item(button,'ProximityPrompt','V9_EStopPrompt')
    for key,value in [('ActionText','Отключить усилители'),('ObjectText','Аварийный стоп NIF')]:b.prop(prompt,'string',key,value)
    b.prop(prompt,'float','MaxActivationDistance',9);b.prop(prompt,'float','HoldDuration',.1)
    b.prop(prompt,'bool','RequiresLineOfSight',True)
    legend=b.part(root,'EmergencyStopLegend',(7,-58.45,-3.8),(2.4,.55,.06),DARK)
    b.label(legend,'АВАРИЙНЫЙ СТОП\nУСИЛИТЕЛИ NIF')
    indicator=b.part(root,'AmplifierCircuitIndicator',(7,-57.95,-3.8),(.28,.2,.12),CYAN,role='control')
    status=b.item(root,'Folder','V9_CircuitStatus')
    circuits=b.find('Circuits',under=b.find('Controls',under=source_root))
    circuit=b.find('AcousticAmplifiers',under=circuits)
    text=next(e for e in legend.iter('Item') if e.get('class')=='TextLabel')
    for label,target in [('Circuit',circuit),('Indicator',indicator),('Text',text)]:
        value=b.item(status,'ObjectValue',label);b.prop(value,'Ref','Value',target.get('referent'))
    b.note(status,'Caption','NIF / УСИЛИТЕЛИ')

    medical=b.model(parent,'E06_Serviceable_Storage_V9')
    old_med=b.find('E06_Medical_Detail',under=source_root)
    waste=b.find('ClosedGeneralWaste',under=old_med)
    b.remove_named(waste,{'ClosedBinBody','SeparateClosedLid','LidHinge','WasteLegend'})
    container=b.model(medical,'WasteLinerContainer')
    open_box(b,container,(47.65,-62.6,-60.9),(1.8,2.65,1.65),WHITE)
    b.cavity(container,(47.65,-62.6,-60.9),(1.8,2.65,1.65),.08,'Y+')
    lid=b.part(container,'V9_ServiceDoor',(47.65,-61.21,-60.9),(1.95,.16,1.8),TEAL,role='panel')
    for z in (-61.25,-60.55):
        b.part(container,'ClosedWastePouch',(47.65,-63.3,z),(1.1,.3,.45),BLACK,role='internal')
    b.service(lid,(46.75,-61.21,-60.9),axis='Z',angle=95,label='Урна: сменный вкладыш')
    trolley=b.find('ClosedInstrumentTrolley',under=old_med)
    b.remove_named(trolley,{'SealedSupplyBox','SupplyBoxLid','SupplyBoxLabel','ClosedInstrumentTray','InstrumentTrayLid','TrayLatch','TrayInventoryLegend'})
    for index,y,z in ((1,-62.19,-56),(2,-60.84,-55.75),(3,-59.61,-56)):
        size=(2.25,.65,1.8) if index<3 else (2.1,.42,1.75)
        drawer=b.model(medical,f'TrolleyDrawer_{index}')
        pieces=open_box(b,drawer,(70 if index<3 else 69.85,y,z),size,WHITE if index<3 else METAL)
        cx=70 if index<3 else 69.85
        contents=[]
        for dx in (-.55,.55):
            contents.append(b.part(drawer,'SealedInstrumentPouch',(cx+dx,y-.05,z),(.8,.12,1.1),LIGHT,role='internal'))
            contents.append(b.segment(drawer,'InstrumentSilhouette',(cx+dx,y+.03,z-.3),(cx+dx,y+.03,z+.3),.06,METAL,role='internal'))
        b.cavity(drawer,(cx,y,z),size,.06,'Z-')
        b.slide(pieces[-1],(0,0,-1.25),label=f'Тележка: ящик {index}',moving=pieces[:-1]+contents)

    # Dispenser/holder are also real small shells with replaceable contents.
    for label,center,size,front,content in (
        ('SoapDispenser',(47.28,-58.6,-67.45),(.6,1.2,.7),'X+','SoapCartridge'),
        ('PaperTowelCabinet',(47.14,-57.55,-62.7),(.85,1.65,1.3),'X+','PaperRoll'),
    ):
        part=b.find(label,under=old_med);b.remove(part)
        shell,door,_=b.shell(medical,label+'_Serviceable',center,size,WHITE,thickness=.045,front=front,service=False)
        sx,sy,sz=size;x,y,z=center
        b.part(shell,content,center,(sx*.55,sy*.7,sz*.65),LIGHT,role='internal')
        b.service(door,(x+sx/2-.0225,y,z-sz/2+.045),angle=95,label=label+': расходники')
    return root


def open_box(b,parent,center,size,color):
    x,y,z=center;sx,sy,sz=size;t=.06
    parts=[b.part(parent,'ContainerBottom',(x,y-sy/2+t/2,z),(sx,t,sz),color,1088,role='housing')]
    parts.append(b.part(parent,'ContainerLeft',(x-sx/2+t/2,y,z),(t,sy,sz),color,1088,role='housing'))
    parts.append(b.part(parent,'ContainerRight',(x+sx/2-t/2,y,z),(t,sy,sz),color,1088,role='housing'))
    parts.append(b.part(parent,'ContainerBack',(x,y,z+sz/2-t/2),(sx-2*t,sy,t),color,1088,role='housing'))
    parts.append(b.part(parent,'ContainerFront',(x,y,z-sz/2+t/2),(sx-2*t,sy,t),color,1088,role='housing'))
    return parts
