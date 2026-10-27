"""Serviceable fan-coil and connected cooling skid with physical housings.

Only the V8 fan-coil is replaced. Original racks, AHU, electrical distribution,
architecture and controllers remain present. Covers expose modeled components.
"""
import math

from v9_common import WHITE, LIGHT, METAL, DARK, BLACK, CYAN, BLUE, AMBER, RED, TEAL


def build(b, parent, source_root):
    old_group = b.find("E16_Server_Infrastructure", under=source_root)
    if old_group is not None:
        b.remove(b.find("THERM_016_WallFanCoil", under=old_group))

    thermal = b.model(parent, "Thermal_Serviceable_V9")
    b.note(thermal, "Purpose", "THERM-016: collidable hollow fan-coil, service doors, complete fan/motor/filter/coil/drive internals, connected twin-pump cooling skid. Fine internal components are noncolliding; structural housings and service covers are solid.")

    fcu = b.model(thermal, "THERM_016_FanCoil")
    b.part(fcu, "FloorIsolationPlinth", (13.975,-63.8,58), (2.9,.4,5.9), DARK,1088,role='structure')
    case, door, faces = b.shell(fcu,"FanCoilPhysicalShell",(13.975,-60,58),(2.75,7.2,5.6),WHITE,.12,front='X-',service=False)
    moving=[]
    # A hollow case, not an opaque solid box surrounding a hidden interior.
    for z in (55.45,60.55):
        b.part(fcu,"InternalMountingRail",(15.12,-60,z),(.16,6.5,.18),METAL,1088,role='structure')
    for y in (-63.25,-56.75):
        b.part(fcu,"CoilSupportCrossmember",(14.85,y,58),(.35,.18,5.0),METAL,1088,role='structure')
    b.part(case,"MotorCarrierBackplate",(15.17,-60,58),(.16,5.7,2.4),METAL,1088,role='structure')
    for y in (-62.7,-57.3):
        for z in (55.45,60.55):
            moving.append(b.part(fcu,"DoorCaptiveFastener",(12.51,y,z),(.12,.18,.18),METAL,1088,role='detail'))
    moving.append(b.part(fcu,"ServiceDoorPull",(12.35,-60,60.25),(.35,1.25,.16),DARK,1088,role='detail'))
    plate=b.part(fcu,"FanCoilAssemblyPlate",(12.51,-57.0,58),(.05,.7,3.8),DARK)
    b.label(plate,"THERM-016 / FCU\nФИЛЬТР · ВЕНТИЛЯТОРЫ · ТЕПЛООБМЕННИК",LIGHT,face=3);moving.append(plate)
    # The filter cassette is mounted to the inside of the service cover and
    # moves with it, exposing the fan impellers and downstream heat exchanger.
    for z in (55.55,60.45):
        moving.append(b.part(fcu,"DoorFilterCassetteSide",(12.82,-60,z),(.18,5.8,.16),METAL,1088,role='internal'))
    for y in (-62.85,-57.15):
        moving.append(b.part(fcu,"DoorFilterCassetteEnd",(12.82,y,58),(.18,.16,4.9),METAL,1088,role='internal'))
    for i in range(13):
        moving.append(b.part(fcu,"ReplaceableFilterPleat",(12.83,-60,55.72+i*.38),(.18,5.45,.16), (146,163,160),1312,role='internal'))
    for z in (55.9,60.1):
        moving.append(b.part(fcu,"FilterRetentionLatch",(12.96,-60,z),(.18,.7,.24),AMBER,1088,role='internal'))
    b.service(door,pivot=(12.66,-60,55.32),axis='Y',angle=-100,label='THERM-016: фильтр и вентиляторы',moving=moving)

    fans=b.model(case,"TwinFanMotorAssemblies")
    for index,y in enumerate((-61.25,-58.75),1):
        fan=b.model(fans,f"Fan_{index:02d}")
        # Support ring is segmented, so a solid cylinder cannot obscure blades.
        for i in range(12):
            a=2*math.pi*i/12;c=2*math.pi*(i+1)/12
            b.segment(fan,"ImpellerShroudSegment",(13.1,y+1.03*math.cos(a),58+1.03*math.sin(a)),
                      (13.1,y+1.03*math.cos(c),58+1.03*math.sin(c)),.14,METAL,role='internal')
        b.segment(fan,"MotorShaft",(12.98,y,58),(14.34,y,58),.17,METAL,role='internal')
        b.segment(fan,"ImpellerHub",(13.02,y,58),(13.24,y,58),.42,DARK,role='internal')
        for i in range(6):
            a=2*math.pi*i/6
            # Two segments describe each blade, with a real hub-to-tip path.
            b.segment(fan,"ImpellerBlade",(13.11,y+.18*math.cos(a),58+.18*math.sin(a)),
                      (13.16,y+.85*math.cos(a+.25),58+.85*math.sin(a+.25)),.19,METAL,cylinder=False,role='internal')
        b.segment(fan,"MotorStatorCore",(13.65,y,58),(14.17,y,58),.75,DARK,role='internal')
        for dz in (-.24,.24):
            b.segment(fan,"MotorWindingBundle",(13.66,y+.18,58+dz),(14.10,y+.18,58+dz),.19,AMBER,role='internal')
        for x in (13.54,14.29):
            b.segment(fan,"ShaftBearingCarrier",(x-.06,y,58),(x+.06,y,58),.39,METAL,role='internal')
            b.part(fan,"BearingSupportBracket",(x,y-.69,58),(.2,.65,.46),METAL,1088,role='internal')
            b.segment(fan,"MotorMountTie",(x,y-1.00,58),(15.1,y-1.00,58),.16,METAL,role='internal')
        label=b.part(fan,"MotorIdentification",(13.85,y+.48,58),(.55,.06,.65),DARK)
        b.label(label,f"M{index} / FCU-016",LIGHT,face=1)

    coil=b.model(case,"FinnedCoolingCoil")
    for z in (55.5,60.5):
        b.part(coil,"CoilSupportSideChannel",(14.9,-60,z),(.3,6.3,.3),METAL,1088,role='internal')
    for i in range(17):
        b.part(coil,"HeatTransferFin",(14.78,-60,55.66+i*.29),(.62,5.7,.035),METAL,1088,role='internal')
    for y in (-62.5,-61.7,-60.9,-60.1,-59.3,-58.5,-57.7):
        b.segment(coil,"CoilCopperTube",(14.93,y,55.45),(14.93,y,60.55),.13,AMBER,role='internal')
    for z in (55.45,60.55):
        b.segment(coil,"CoilVerticalHeader",(14.93,-62.65,z),(14.93,-57.15,z),.24,AMBER,role='internal')
    for z,portz,color in ((55.45,56.6,BLUE),(60.55,59.4,AMBER)):
        b.segment(coil,"CoilHeaderToRoof",(14.93,-57.15,z),(14.93,-56.25,z),.24,METAL,role='internal')
        b.segment(coil,"CoilRoofManifold",(14.93,-56.25,z),(14.93,-56.25,portz),.24,METAL,role='internal')
        b.segment(coil,"ExternalCoilRiser",(14.93,-56.25,portz),(14.93,-48.5,portz),.26,METAL,role='housing')
        b.part(coil,"SupplyReturnIdentification",(14.93,-54.8,portz),(.34,.35,.34),color)

    drive=b.model(case,"InternalFanDriveAndTerminals")
    b.part(drive,"DriveMountingPlate",(14.65,-62.25,60.25),(.14,1.8,.85),METAL,1088,role='internal')
    b.part(drive,"DrivePowerBoard",(14.52,-62.25,60.25),(.08,1.5,.64),TEAL,role='internal')
    for y in (-62.75,-62.20,-61.65):
        b.part(drive,"FusedTerminal",(14.38,y,60.25),(.22,.27,.45),WHITE,role='internal')
    for index,y in enumerate((-61.25,-58.75),1):
        points=[(14.34,y,58),(14.40,y,59.8),(14.40,-62.20,59.8),(14.40,-62.20,60.25)]
        for a,c in zip(points,points[1:]): b.segment(drive,f"Motor_{index}_InternalHarness",a,c,.075,BLACK,role='internal')
    b.note(fcu,"ServiceInspection","Opening the real front service panel moves its filter cassette out of the case, exposing two impellers, shafts, bearings, motor windings, copper tubes, fin stack and the fan drive. Major shell faces collide; internal components do not create avatar snags.")

    skid=b.model(thermal,"THERM_017_ConnectedCoolingSkid")
    # This surveyed bay was empty in V8. Side aisles remain outside X29..39.
    b.part(skid,"PhysicalSkidBase",(34,-63.8,71),(10,.4,10),DARK,1088,role='structure')
    for x in (29.25,38.75):
        for z in (66.25,75.75):
            b.part(skid,"SkidCornerPost",(x,-57.0,z),(.3,13.2,.3),METAL,1088,role='structure')
            b.part(skid,"FoundationAnchor",(x,-63.45,z),(.65,.28,.65),DARK,1088,role='structure')
    for y in (-63.35,-50.55):
        for z in (66.25,75.75):b.part(skid,"SkidFrameCrossmember",(34,y,z),(9.5,.28,.3),METAL,1088,role='structure')
        for x in (29.25,38.75):b.part(skid,"SkidFrameLongitudinal",(x,y,71),(.3,.28,9.5),METAL,1088,role='structure')
    b.part(skid,"SkidRearPanel",(34,-57.0,75.8),(9.2,12.5,.12),WHITE,1088,role='housing')
    for x in (29.3,38.7):b.part(skid,"SkidSideLowerPanel",(x,-61.2,71),(.12,4.2,9.2),WHITE,1088,role='housing')
    doors=b.model(skid,"OpeningSkidFrontPanels")
    b.part(doors,"FrontCentreMullion",(34,-58.5,66.15),(.3,10,.3),METAL,1088,role='structure')
    for x in (33.78,34.22):b.part(doors,"CentralDoorGasket",(x,-58.5,66.055),(.14,9.8,.08),BLACK)
    for side,x,pivotx,angle in ((1,31.55,29.4,85),(-1,36.45,38.6,-85)):
        # Bottom clearance is above the foundation anchors and the lower
        # frame, so the physical leaf does not scrape them while opening.
        panel=b.part(doors,"SkidServiceDoor",(x,-58.35,66.15),(4.3,9.7,.14),WHITE,1088,role='panel')
        handle=b.part(doors,"SkidDoorPull",(x+side*1.65,-58.5,65.94),(.16,1.1,.32),DARK,1088)
        plate=b.part(doors,"SkidDoorIdentification",(x,-55.5,66.035),(3.5,1.1,.05),DARK)
        b.label(plate,"THERM-017\nНАСОСЫ / ТЕПЛООБМЕН / БАК",LIGHT)
        b.service(panel,pivot=(pivotx,-58.35,66.15),axis='Y',angle=angle,label='THERM-017: внутренние узлы',moving=[handle,plate])
    title=b.part(skid,"CoolingSkidAssemblyID",(34,-51.6,66.07),(8.7,1.1,.06),DARK)
    b.label(title,"THERM-017 / ХОЛОДОСНАБЖЕНИЕ АППАРАТНОЙ\nОТКРЫВАЕМЫЕ ПАНЕЛИ · ДВА НАСОСА · ТЕПЛООБМЕННИК",CYAN)

    pumps=b.model(skid,"DutyStandbyPumpAssemblies")
    for index,x in enumerate((31.6,36.2),1):
        pump=b.model(pumps,f"P{index:02d}_PumpMotor")
        # The rear-set mounting plinth still carries both bearing feet and
        # most of the volute footprint, but leaves the front cover sweep free.
        b.part(pump,"PumpMotorPlinth",(x,-63.35,68.6),(3.4,.5,2.0),METAL,1088,role='structure')
        motor_case,motor_door,motor_faces=b.shell(pump,f"M{index:02d}_HollowMotorCase",(x-.53,-62.35,68.25),(1.3,1.15,1.15),METAL,.08,front='Z-',service=False)
        motor_handle=b.part(pump,"MotorInspectionPull",(x-.22,-62.35,67.59),(.14,.28,.17),DARK,1088)
        b.service(motor_door,pivot=(x-1.10,-62.35,67.715),axis='Y',angle=85,label=f'M{index:02d}: статор и ротор',moving=[motor_handle])
        volute,volute_door,volute_faces=b.shell(pump,f"P{index:02d}_HollowVoluteCase",(x+.84,-62.35,68.25),(.98,1.85,1.85),WHITE,.08,front='Z-',service=False)
        volute_pull=b.part(pump,"VoluteInspectionPull",(x+1.1,-62.35,67.23),(.14,.4,.16),DARK,1088)
        b.service(volute_door,pivot=(x+.43,-62.35,67.365),axis='Y',angle=85,label=f'P{index:02d}: крыльчатка и уплотнение',moving=[volute_pull])
        # Motor and pressure casing are hollow and independently inspectable.
        b.segment(pump,"MotorShaft",(x-1.25,-62.35,68.25),(x+1.25,-62.35,68.25),.18,METAL,role='internal')
        b.segment(motor_case,"MotorRotor",(x-.9,-62.35,68.25),(x-.1,-62.35,68.25),.66,DARK,role='internal')
        for z in (67.96,68.54):
            b.segment(motor_case,"MotorCopperWindings",(x-.9,-62.20,z),(x-.15,-62.20,z),.20,AMBER,role='internal')
        for dx in (-1.05,.05):
            b.segment(pump,"MotorEndBearing",(x+dx-.07,-62.35,68.25),(x+dx+.07,-62.35,68.25),.43,METAL,role='internal')
            b.part(pump,"MotorBearingFoot",(x+dx,-62.85,68.25),(.3,.6,.8),DARK,1088,role='internal')
        b.segment(pump,"FlexibleCoupling",(x+.13,-62.35,68.25),(x+.45,-62.35,68.25),.38,TEAL,role='internal')
        for a in range(8):
            t=2*math.pi*a/8;u=2*math.pi*(a+1)/8
            b.segment(volute,"PumpVoluteRim",(x+.84,-62.35+.7*math.cos(t),68.25+.7*math.sin(t)),
                      (x+.84,-62.35+.7*math.cos(u),68.25+.7*math.sin(u)),.15,METAL,role='internal')
        b.segment(volute,"PumpImpellerHub",(x+.68,-62.35,68.25),(x+1.02,-62.35,68.25),.35,DARK,role='internal')
        for i in range(5):
            a=2*math.pi*i/5
            b.segment(volute,"PumpImpellerVane",(x+.84,-62.35+.14*math.cos(a),68.25+.14*math.sin(a)),
                      (x+.84,-62.35+.57*math.cos(a+.25),68.25+.57*math.sin(a+.25)),.13,METAL,cylinder=False,role='internal')
        b.segment(pump,"PumpDischargePort",(x+.84,-61.65,68.25),(x+.84,-61.1,68.25),.3,METAL,role='internal')
        b.segment(pump,"PumpSuctionPort",(x+.84,-62.35,68.95),(x+.84,-62.35,69.55),.3,METAL,role='internal')
        plate=b.part(pump,"DutyStandbyNameplate",(x,-63.35,67.56),(2.8,.35,.04),DARK)
        b.label(plate,f"P{index:02d} / "+("РАБОЧИЙ" if index==1 else "РЕЗЕРВ"),LIGHT)

    tank=b.model(skid,"BufferReservoirWithInspectionLid")
    for x in (29.98,32.22):
        for z in (71.72,74.88):
            b.part(tank,"ReservoirSupportFoot",(x,-63.225,z),(.25,.75,.25),METAL,1088,role='structure')
    tank_case,lid,tank_faces=b.shell(tank,"HollowBufferTank",(31.1,-59.0,73.3),(2.7,7.7,3.6),WHITE,.12,front='Z-',service=False)
    tank_faces['Z-'].find("Properties/string[@name='Name']").text='ReservoirFixedFrontWall'
    # Pressure vessel front remains fixed; a separate hinged top reveals its
    # level float, pickup tube, return diffuser and low-level coolant volume.
    top=tank_faces['Y+']
    top.find("Properties/string[@name='Name']").text='ReservoirInspectionLid'
    handle=b.part(tank,"InspectionLidHandle",(31.1,-55.04,73.3),(.9,.18,.2),DARK,1088)
    b.service(top,pivot=(29.87,-55.21,73.3),axis='Z',angle=95,label='THERM-017: осмотр буферного бака',moving=[handle])
    b.part(tank_case,"CoolantInReservoir",(31.1,-61.55,73.3),(2.25,2.2,3.15),TEAL,role='internal')
    b.segment(tank_case,"TankPickupStandpipe",(31.7,-62.3,74.0),(31.7,-55.7,74.0),.22,METAL,role='internal')
    b.segment(tank_case,"ReturnDiffuserTube",(30.55,-61.3,74.0),(30.55,-55.7,74.0),.2,METAL,role='internal')
    b.segment(tank_case,"LevelFloatGuide",(30.8,-62.4,72.3),(30.8,-55.8,72.3),.08,METAL,role='internal')
    b.part(tank_case,"LevelFloat",(30.8,-60.3,72.3),(.6,.24,.7),AMBER,role='internal')
    tank_plate=b.part(tank,"TankAssemblyID",(31.1,-57.2,71.435),(2.25,.85,.05),DARK)
    b.label(tank_plate,"BT-017\nБУФЕР / УРОВЕНЬ",LIGHT)

    hx=b.model(skid,"PlateHeatExchanger")
    for x in (33.5,36.1):
        b.part(hx,"ExchangerEndPlate",(x,-59.0,73.2),(.28,5.2,2.9),DARK,1088,role='internal')
    for i in range(15):b.part(hx,"SeparateHeatExchangerPlate",(33.72+i*.15,-59.0,73.2),(.065,4.8,2.6),METAL,1088,role='internal')
    for y in (-61.1,-56.9):
        for z in (72.0,74.4):
            b.segment(hx,"ExchangerTieRod",(33.3,y,z),(36.3,y,z),.12,METAL,role='internal')
    for y,z,color in ((-57.4,72.4,BLUE),(-60.5,72.4,AMBER),(-57.4,74,TEAL),(-60.5,74,BLUE)):
        b.segment(hx,"ExchangerPort",(36.1,y,z),(36.6,y,z),.3,color,role='internal')
    for x in (33.8,35.7):b.part(hx,"ExchangerFoot",(x,-62.6,73.2),(.5,2.0,2.2),METAL,1088,role='structure')
    hxplate=b.part(hx,"HeatExchangerID",(34.8,-56.25,71.71),(2.8,.6,.04),DARK)
    b.label(hxplate,"HX-017 / ПЛАСТИНЧАТЫЙ",LIGHT)

    controls=b.model(skid,"PumpDriveControlCabinet")
    cabinet,cabdoor,cabfaces=b.shell(controls,"PumpDriveHollowCabinet",(37.5,-56.7,73.25),(2.0,6.0,3.5),WHITE,.1,front='Z-',service=False)
    for x in (36.8,38.2):
        for y in (-58.8,-54.6):
            b.part(controls,"DriveCabinetRearStandoff",(x,y,75.37),(.3,.3,.74),METAL,1088,role='structure')
    handle=b.part(controls,"DriveCabinetPull",(38.25,-56.7,71.41),(.12,.8,.26),DARK,1088)
    b.part(cabinet,"ElectricalBackplate",(37.5,-56.7,74.85),(1.55,5.5,.12),METAL,1088,role='internal')
    for x in (37.05,37.95):
        b.part(cabinet,"PumpVariableSpeedDrive",(x,-55.8,74.35),(.64,2.35,.8),DARK,role='internal')
        for i in range(5):b.part(cabinet,"DriveHeatsinkFin",(x-.24+i*.12,-55.8,73.87),(.05,2.0,.17),METAL,1088,role='internal')
    for x in (36.95,37.5,38.05):
        b.part(cabinet,"DINRailTerminal",(x,-58.7,74.25),(.35,.55,.65),WHITE,role='internal')
        b.segment(cabinet,"DriveInternalWire",(x,-58.4,74.1),(x,-57.0,74.1),.065,BLUE,role='internal')
    b.part(cabinet,"SafetyContactor",(37.5,-57.6,74.3),(.8,.8,.75),DARK,role='internal')
    cbplate=b.part(controls,"ControlCabinetID",(37.5,-54.3,71.40),(1.65,.65,.04),DARK)
    b.label(cbplate,"DRV-017\nПРИВОДЫ P01 / P02",LIGHT)
    b.service(cabdoor,pivot=(36.6,-56.7,71.55),axis='Y',angle=85,label='THERM-017: привод и клеммы',moving=[handle,cbplate])

    piping=b.model(thermal,"ContinuousCoolingAndPowerConnections")
    # Coolant lines connect FCU headers, over-wall sleeves and skid HX ports.
    # They intentionally pass through designated utility sleeves in the old
    # wall at X=16; there is no new pedestrian opening in that wall.
    for z,color,hy,rx,drop_z in ((56.6,BLUE,-57.4,34.0,71.5),(59.4,AMBER,-60.5,34.65,74.9)):
        points=[(14.93,-48.5,z),(rx,-48.5,z),(rx,-48.5,drop_z),
                (36.37,-48.5,drop_z),(36.37,hy,drop_z),
                (36.37,hy,72.4),(36.1,hy,72.4)]
        for a,c in zip(points,points[1:]):b.segment(piping,"ContinuousPrimaryPipe",a,c,.24,METAL,role='housing')
        b.part(piping,"WallPenetrationSleeve",(16,-48.5,z),(.75,.58,.58),DARK,1088,role='housing')
        # The service corridor has no modeled ceiling. These beams span the
        # existing E16 and supply-room walls, so there are no floating hangers.
        b.part(piping,"WallToWallPipeBridge",(31,-47.95,z),(28.98,.35,.3),METAL,1088,role='structure')
        for x in (16.54,45.46):
            b.part(piping,"PipeBridgeWallAnchor",(x,-47.95,z),(.08,1.0,1.0),METAL,1088,role='structure')
        for x in (18,25,32):
            b.segment(piping,"BridgePipeHanger",(x,-48.12,z),(x,-48.5,z),.08,METAL,role='detail')
        b.part(piping,"ExternalIsolationHandle",(36.37,-51.2,drop_z),(.65,.15,.2),color,role='detail')
    for x in (34,36.5):
        for z in (66.25,75.75):
            b.part(piping,"SkidRoofPipeMast",(x,-49.3,z),(.22,2.5,.22),METAL,1088,role='structure')
        b.part(piping,"SkidRoofPipeRail",(x,-47.95,71),(.22,.2,9.5),METAL,1088,role='structure')
    for z in (66.25,75.75):
        b.part(piping,"SkidRoofPipeCrossmember",(35.25,-47.95,z),(2.5,.2,.22),METAL,1088,role='structure')
    for x,z in ((34,66.25),(34.65,66.25),(34,71.5),(34.65,74.9),(36.37,71.5),(36.37,74.9)):
        b.segment(piping,"SkidRoofPipeSupportClip",(x,-48.05,z),(x,-48.5,z),.08,METAL,role='detail')
    # Closed local circuit: reservoir -> two suction branches -> pumps -> HX
    # secondary ports -> return diffuser. This is modeled piping, not a fluid
    # simulator or a claim of calculated heat-transfer capacity.
    b.segment(piping,"ReservoirSuctionHeader",(31.7,-62.35,74),(31.7,-62.35,69.55),.28,METAL,role='internal')
    b.segment(piping,"TwinPumpSuctionManifold",(31.7,-62.35,69.55),(37.04,-62.35,69.55),.28,METAL,role='internal')
    for x in (32.44,37.04):
        b.segment(piping,"PumpSuctionBranch",(x,-62.35,69.55),(x,-62.35,68.95),.28,METAL,role='internal')
        b.segment(piping,"PumpDeliveryBranch",(x,-61.1,68.25),(x,-60.5,68.25),.28,METAL,role='internal')
    b.segment(piping,"TwinPumpDeliveryManifold",(32.44,-60.5,68.25),(37.04,-60.5,68.25),.28,METAL,role='internal')
    for a,c in zip([(37.04,-60.5,68.25),(37.04,-60.5,74),(36.6,-60.5,74)],[(37.04,-60.5,74),(36.6,-60.5,74),(36.1,-60.5,74)]):
        b.segment(piping,"PumpToHeatExchanger",a,c,.27,METAL,role='internal')
    return_points=[(36.6,-57.4,74),(36.6,-55.7,74),(30.55,-55.7,74)]
    for a,c in zip(return_points,return_points[1:]):b.segment(piping,"HeatExchangerReservoirReturn",a,c,.27,METAL,role='internal')
    supply=[(23.15,-47.72,63),(25,-47.72,63),(25,-47.72,59.4),
            (34,-47.72,59.4),(34,-47.72,74.3),(37.5,-47.72,74.3),(37.5,-53.75,74.3)]
    for a,c in zip(supply,supply[1:]):b.segment(piping,"SkidElectricalSupplyConduit",a,c,.16,DARK,role='detail')
    for z in (68,73):b.part(piping,"ElectricalRoofClip",(34,-47.82,z),(.3,.18,.2),WHITE,1088,role='detail')
    b.part(piping,"SkidDriveCableGland",(37.5,-53.64,74.3),(.34,.12,.34),DARK,1088,role='detail')
    b.note(piping,"Routing", "Two continuous primary lines connect the FCU coil headers to HX-017 through marked wall sleeves. The local skid loop models reservoir, suction/delivery manifolds, duty/standby pumps, plate heat exchanger and reservoir return. Electrical conduit begins beside the existing DB upper feed; operation and pressure/temperature simulation are handled separately.")
    return thermal
