"""E07 rebuild: physical bench, accessible instruments and a modular test rack.

Only the former V8 E07 addon is removed. The V6 workstation, calibration dock,
cabinet and room remain unchanged. Major structure has real collision; internals
are separately modeled and visible through four independent service openings.
"""
import math

from v9_common import WHITE, LIGHT, METAL, DARK, BLACK, CYAN, AMBER, BLUE, RED, TEAL

PCB = (48, 96, 72)
COPPER = (171, 113, 61)


def build(b, parent, source_root):
    old = b.find("E07_Metrology", under=source_root)
    assert old is not None, "The prior E07 addon was not found"
    b.remove(old)
    room = b.model(parent, "E07_Serviceable_V9")
    b.note(room, "EngineeringScope", "Replanned east bench X=-35.9..-30.7 leaves a 4.1-stud aisle to the original desk. Hollow analyzer, two optical heads and a split-door floor rack have modeled internals. The original V6 dock, workstation, cabinet and west entrance are preserved.")

    def part(p, n, pos, size, color=WHITE, role="detail", material=272, **kw):
        return b.part(p, n, pos, size, color, material, role=role, **kw)

    def wire(p, n, points, color=BLACK, diameter=.06, role="internal"):
        for a, endpoint in zip(points, points[1:]):
            b.segment(p, n, a, endpoint, diameter, color, role=role)

    # East-side bench: the former 1.7-stud slot is widened to 4.1 studs.
    bench = b.model(room, "LAB_CAL_02_PhysicalBench")
    cx, cz = -33.3, -49.4
    part(bench, "LaboratoryCountertop", (cx, -60.75, cz), (5.2, .26, 11.4), LIGHT, "walkable")
    for x in (-35.45, -31.15):
        for z in (-54.3, -44.5):
            part(bench, "LevelingFoot", (x, -63.86, z), (.74, .28, .74), DARK, "structure", 1088)
            part(bench, "BenchUpright", (x, -62.3, z), (.32, 2.84, .32), WHITE, "structure", 1088)
        part(bench, "UpperFrameRail", (x, -61.04, cz), (.26, .32, 10.05), WHITE, "structure", 1088)
        part(bench, "LowerFrameRail", (x, -63.30, cz), (.22, .22, 10.05), METAL, "structure", 1088)
    for z in (-54.3, -44.5):
        part(bench, "CrossFrame", (cx, -61.04, z), (4.3, .32, .26), WHITE, "structure", 1088)
    part(bench, "LowerShelf", (cx, -62.76, cz), (4.1, .14, 9.5), METAL, "structure", 1088)
    plate=part(bench,"BenchAssemblyPlate",(-35.93,-61.16,-52.7),(.05,.65,2.1),DARK)
    b.label(plate,"LAB-CAL-02\nОБСЛУЖИВАЕМЫЙ СТЕНД",CYAN,face=3)

    rail=b.model(room,"DualGuideTranslationStage")
    hx=-32.65
    for x in (hx-.65,hx+.65):
        for z in (-53.3,-45.7):
            part(rail,"RailMount",(x,-60.52,z),(.55,.2,.7),METAL,"structure",1088)
        part(rail,"LinearGuide",(x,-60.35,-49.5),(.2,.18,8.5),DARK,"structure",1088)
    b.segment(rail,"LeadScrew",(hx+1.05,-60.08,-54.1),(hx+1.05,-60.08,-45.1),.105,METAL,role="detail")
    for z in (-53.5,-45.4):
        part(rail,"ScrewBearingBlock",(hx+1.05,-60.33,z),(.45,.54,.35),WHITE,"structure",1088)
    b.segment(rail,"TranslationHandwheel",(hx+1.05,-60.08,-54.18),(hx+1.05,-60.08,-54.34),.56,DARK,role="detail")
    part(rail,"ReferenceScaleBed",(hx+1.61,-60.3,-49.5),(.48,.12,8.2),WHITE,"detail")
    for i in range(13):
        part(rail,"ScaleTick",(hx+1.62,-60.227,-53.1+i*.6),(.36 if i%3==0 else .2,.02,.04),DARK)

    def optical_head(code,z,direction):
        head=b.model(room,"OpticalHead_"+code)
        b.cavity(head,(hx,-59,z),(1.1,1.2,1.15),thickness=.08,front="Y+")
        part(head,"GuideCarriage",(hx,-60.14,z),(2.1,.32,1.3),METAL,"structure",1088)
        part(head,"SupportStem",(hx,-59.52,z),(.28,1.04,.28),WHITE,"structure",1088)
        # Six thin sides, not the former solid block.
        for x in (hx-.51,hx+.51):
            part(head,"HeadSidePanel",(x,-59,z),(.08,1.2,1.15),WHITE,"housing",1088)
        part(head,"HeadBase",(hx,-59.56,z),(.94,.08,.99),METAL,"housing",1088)
        rear=z-direction*.535
        part(head,"HeadRearPanel",(hx,-59,rear),(.94,1.04,.08),WHITE,"housing",1088)
        front=z+direction*.535
        # Four border pieces leave a real optical aperture.
        for x in (hx-.39,hx+.39):
            part(head,"OpticalApertureSide",(x,-59,front),(.16,1.04,.08),DARK,"housing",1088)
        for y in (-59.43,-58.57):
            part(head,"OpticalApertureRail",(hx,y,front),(.62,.18,.08),DARK,"housing",1088)
        lid=part(head,"OpticalHeadServiceLid",(hx,-58.44,z),(.94,.08,1.0),WHITE,"panel",1088)
        lid_handle=part(head,"LidLiftTab",(hx-.36,-58.37,z),(.15,.08,.35),DARK)
        b.service(lid,pivot=(hx+.47,-58.44,z),axis="Z",angle=-100,label="Оптическая головка "+code,moving=[lid_handle])
        inner=b.model(head,"LensTrainAndSensorElectronics")
        for zz in (z-direction*.22,z+direction*.18):
            part(inner,"LensSupportYoke",(hx,-59.22,zz),(.78,.12,.12),METAL,"internal",1088)
            b.segment(inner,"LensRetainingRing",(hx,-59,zz-.035),(hx,-59,zz+.035),.58,DARK,role="internal")
            b.segment(inner,"GlassElement",(hx,-59,zz-.012),(hx,-59,zz+.012),.43,BLUE,role="internal")
        sensor_z=z-direction*.36
        part(inner,"SensorBoard",(hx,-59,sensor_z),(.72,.64,.055),PCB,"internal")
        part(inner,"EmitterDie" if code=="REF" else "Photodetector",(hx,-59,sensor_z+direction*.05),(.24,.22,.055),BLACK,"internal")
        for x in (hx-.24,hx+.24):
            part(inner,"BoardStandoff",(x,-59.2,sensor_z-direction*.045),(.08,.08,.08),METAL,"internal",1088)
        part(inner,"SignalConditioner",(hx+.22,-59.35,sensor_z+direction*.07),(.18,.14,.09),DARK,"internal")
        part(inner,"ShieldPartition",(hx,-59.45,z-direction*.13),(.85,.06,.4),METAL,"internal",1088)
        socket=part(head,"SignalSocket",(hx-.565,-59.25,z),(.13,.30,.30),DARK,"detail")
        wire(inner,"SensorRibbon",[(hx-.50,-59.25,z),(hx-.30,-59.25,z-direction*.30),(hx-.12,-59.1,sensor_z)],CYAN,.035)
        nameplate=part(head,"HeadID",(hx-.565,-58.69,z),(.03,.30,.8),DARK)
        b.label(nameplate,code+" / CAL-02",LIGHT,face=3)
        return hx-.63,-59.25,z

    ref_socket=optical_head("REF",-52,1)
    dut_socket=optical_head("DUT",-46.5,-1)

    # Analyzer: full separate shell faces and an actual top-access lid.
    analyzer=b.model(room,"LAB_CAL_02_ServiceableAnalyzer")
    ax,ay,az=-35.05,-59.79,-48.6
    b.cavity(analyzer,(ax,ay,az),(1.28,1.58,3.0),thickness=.08,front="Y+")
    part(analyzer,"AnalyzerBase",(ax,-60.54,az),(1.12,.08,2.84),METAL,"housing",1088)
    part(analyzer,"AnalyzerFront",(ax-.60,ay,az),(.08,1.5,3.0),DARK,"housing",1088)
    for z in (-50.06,-47.14):
        part(analyzer,"AnalyzerEndPanel",(ax,ay,z),(1.12,1.5,.08),WHITE,"housing",1088)
    # Rear aperture exposes the actual fan. Border faces replace a solid wall.
    for z,sizez in ((-49.825,.55),(-47.975,1.75)):
        part(analyzer,"RearVentSide",(ax+.60,ay,z),(.08,1.5,sizez),WHITE,"housing",1088)
    for y,height in ((-60.22,.64),(-59.07,.14)):
        part(analyzer,"RearVentBorder",(ax+.60,y,-49.20),(.08,height,.70),WHITE,"housing",1088)
    lid=part(analyzer,"AnalyzerServiceLid",(ax,-59.04,az),(1.12,.08,2.84),WHITE,"panel",1088)
    handle=part(analyzer,"LidHandle",(ax-.40,-58.96,az),(.12,.12,.8),DARK)
    b.service(lid,pivot=(ax+.56,-59.04,az),axis="Z",angle=-100,label="LAB-CAL-02: внутренние модули",moving=[handle])
    front=part(analyzer,"AnalyzerIdentification",(ax-.655,-59.55,az),(.03,.9,2.6),BLACK)
    b.label(front,"LAB-CAL-02\nREF → СРАВНЕНИЕ ← DUT\nСЕРВИС: ВЕРХНЯЯ КРЫШКА",CYAN,face=3)
    for z in (-49.55,-47.65):
        b.segment(analyzer,"RangeSelector",(ax-.66,-60.25,z),(ax-.84,-60.25,z),.23,METAL,role="detail")
    for z in (-49.75,-48.6):
        part(analyzer,"OutputConnectorBlock",(ax+.65,-59.92,z),(.12,.37,.37),WHITE)
        b.segment(analyzer,"OutputConnectorBarrel",(ax+.69,-59.92,z),(ax+.86,-59.92,z),.23,METAL,role="detail")
    for z in (-49.85,-47.35):
        for x in (ax-.40,ax+.40):
            part(analyzer,"InstrumentIsolationFoot",(x,-60.59,z),(.24,.06,.26),BLACK,"structure")

    guts=b.model(analyzer,"PowerAcquisitionAndThermalInternals")
    for index,z in enumerate((-49.5,-48.35),1):
        part(guts,"AcquisitionPCB_"+str(index),(ax,-60.34,z),(.91,.06,.88),PCB,"internal")
        for x in (ax-.32,ax+.32):
            part(guts,"BoardStandoff",(x,-60.40,z),(.10,.12,.10),METAL,"internal",1088)
        part(guts,"AnalogFrontEnd",(ax-.10,-60.19,z),(.28,.24,.27),DARK,"internal")
        part(guts,"Isolator",(ax+.28,-60.21,z+.22),(.18,.20,.18),LIGHT,"internal")
        part(guts,"ADCModule",(ax-.12,-60.18,z-.26),(.32,.20,.17),BLACK,"internal")
        for dz in (-.14,0,.14):
            part(guts,"HeatSinkFin",(ax-.10,-59.94,z+dz),(.34,.25,.035),METAL,"internal",1088)
        for dx in (-.28,.22):
            b.segment(guts,"FilterCapacitor",(ax+dx,-60.29,z-.25),(ax+dx,-60.06,z-.25),.13,BLUE,role="internal")
    psu=b.model(guts,"IsolatedLowVoltageSupply")
    part(psu,"PowerBoard",(ax,-60.34,-47.48),(.92,.06,.50),PCB,"internal")
    part(psu,"TransformerCore",(ax-.15,-60.10,-47.48),(.28,.38,.29),DARK,"internal")
    for x in (ax-.30,ax):
        part(psu,"TransformerWinding",(x,-60.10,-47.48),(.10,.29,.31),COPPER,"internal")
    part(psu,"InputFuseCarrier",(ax+.24,-60.17,-47.60),(.15,.20,.17),LIGHT,"internal")
    part(psu,"TerminalBarrier",(ax+.22,-60.14,-47.30),(.18,.24,.16),TEAL,"internal")
    wire(guts,"SupplyInput",[(ax-.05,-60.57,-48.6),(ax-.05,-60.40,-47.48),(ax+.20,-60.27,-47.48)],RED,.045)
    for z in (-49.5,-48.35):
        wire(guts,"SupplyDistribution",[(ax+.27,-60.22,-47.3),(ax+.40,-60.17,z),(ax+.22,-60.27,z)],RED,.04)
    for z in (-49.75,-48.6):
        wire(guts,"ConnectorToAcquisitionBoard",[(ax+.86,-59.92,z),(ax+.42,-59.92,z),(ax+.22,-60.25,z+.18)],CYAN,.04)
    # Fan shaft, motor and four pitched blades can be inspected through the lid.
    b.segment(guts,"FanMotor",(ax+.23,-59.55,-49.2),(ax+.40,-59.55,-49.2),.26,DARK,role="internal")
    b.segment(guts,"FanShaft",(ax+.40,-59.55,-49.2),(ax+.56,-59.55,-49.2),.08,METAL,role="internal")
    for i in range(4):
        theta=i*math.pi/2
        matrix=((1,0,0),(0,math.cos(theta),-math.sin(theta)),(0,math.sin(theta),math.cos(theta)))
        part(guts,"FanImpellerBlade",(ax+.50,-59.55+.18*math.cos(theta),-49.2+.18*math.sin(theta)),(.04,.23,.13),BLACK,"internal",matrix=matrix)
    for y in (-59.75,-59.55,-59.35):
        part(analyzer,"FanGuardSlat",(ax+.66,y,-49.2),(.04,.04,.62),METAL)

    routing=b.model(room,"BenchSignalAndPowerRoutes")
    for z,socket in ((-49.75,ref_socket),(-48.6,dut_socket)):
        wire(routing,"ShieldedSignalLead",[(ax+.86,-59.92,z),(ax+1.05,-60.38,z),(ax+1.05,-60.38,socket[2]),(socket[0],socket[1],socket[2])],BLACK,.085,role="detail")
        part(routing,"BenchCableClip",(ax+1.05,-60.49,(z+socket[2])/2),(.18,.26,.20),WHITE)
    supply=part(routing,"InstrumentSupplyWallPlate",(-30.57,-61.7,-44.2),(.12,.9,1.5),WHITE,"housing")
    b.label(supply,"LAB-CAL-02\nПИТАНИЕ",DARK,face=3)
    wire(routing,"UnderBenchSupplyConduit",[(-30.64,-61.7,-44.2),(-33.1,-61.7,-44.2),(ax,-61.7,-44.2),(ax,-61.7,-48.6),(ax,-60.58,-48.6)],METAL,.18,role="detail")
    for x in (-31.8,-34.8):
        part(routing,"ConduitFrameBracket",(x,-61.4,-44.2),(.12,.65,.36),WHITE,"structure",1088)
    b.segment(routing,"EnclosureCableGrommet",(ax,-60.64,-48.6),(ax,-60.54,-48.6),.38,DARK,role="detail")

    # Larger new room-scale instrument rack in the surveyed north-central bay.
    rack=b.model(room,"LAB_CAL_03_ModularServiceRack")
    rx,rz=-44,-40
    b.cavity(rack,(rx,-57.1,rz),(5.8,13.8,4),thickness=.12,front="Z-")
    for x in (rx-2.84,rx+2.84):
        part(rack,"RackSideShell",(x,-57.1,rz),(.12,13.8,4),WHITE,"housing",1088)
    part(rack,"RackBackShell",(rx,-57.1,-38.06),(5.56,13.56,.12),METAL,"housing",1088)
    for y in (-63.94,-50.26):
        part(rack,"RackFloorOrRoof",(rx,y,rz),(5.56,.12,3.76),METAL,"housing",1088)
    for x in (rx-2.55,rx+2.55):
        for z in (-41.65,-38.35):
            part(rack,"RackLoadUpright",(x,-57.1,z),(.18,13.56,.18),DARK,"structure",1088)
    for x,pivot,angle in ((rx-1.405,rx-2.78,105),(rx+1.405,rx+2.78,-105)):
        door=part(rack,"RackServiceDoor",(x,-57.1,-41.94),(2.75,13.56,.12),DARK,"panel",1088)
        handle=part(rack,"DoorHandle",(rx+(-.24 if x<rx else .24),-57.1,-42.1),(.12,1.25,.20),METAL)
        plate=part(rack,"DoorAssemblyID",(x,-51.1,-42.03),(2.4,.7,.04),BLACK)
        b.label(plate,"LAB-CAL-03\nМОДУЛЬНЫЙ СТЕНД",CYAN)
        b.service(door,pivot=(pivot,-57.1,-41.94),axis="Y",angle=angle,label="LAB-CAL-03: внутренняя стойка",moving=[handle,plate])
    # Five open trays carry discrete modules and connector-level wiring.
    for index,y in enumerate((-62.9,-60.5,-58.1,-55.7,-53.3),1):
        module=b.model(rack,f"InstrumentModule_{index:02d}")
        part(module,"ModuleLoadTray",(rx,y,rz),(4.8,.12,3.25),METAL,"structure",1088)
        part(module,"ModuleFrontPlate",(rx,y+.48,-41.70),(4.8,.85,.10),WHITE,"housing",1088)
        module_id=part(module,"ModuleIdentifier",(rx,y+.48,-41.765),(3.0,.55,.025),DARK)
        titles=("ИСТОЧНИК ПИТАНИЯ","СИГНАЛЬНЫЙ ГЕНЕРАТОР","СРАВНЕНИЕ / АЦП","КОММУТАЦИЯ КАНАЛОВ","РЕГИСТРАТОР")
        b.label(module_id,f"CAL-03 / M{index:02d}\n"+titles[index-1],LIGHT)
        for x in (rx-1.85,rx+1.85):
            part(module,"ModulePullHandle",(x,y+.46,-41.82),(.12,.48,.12),DARK)
        part(module,"ModulePCB",(rx-.55,y+.19,-39.9),(2.6,.10,2.45),PCB,"internal")
        part(module,"FunctionalController",(rx-.65,y+.45,-39.9),(.75,.42,.8),DARK,"internal")
        for z in (-40.7,-40.2,-39.7):
            part(module,"ControllerHeatSink",(rx-.65,y+.82,z),(.9,.25,.08),METAL,"internal",1088)
        part(module,"PowerConverter",(rx+1.35,y+.48,-39.25),(.8,.60,1.1),WHITE,"internal")
        part(module,"RearConnectorBlock",(rx+1.25,y+.36,-38.45),(.9,.35,.18),TEAL,"internal")
        for z in (-40.6,-39.3):
            b.segment(module,"FilterCapacitor",(rx+.75,y+.25,z),(rx+.75,y+.75,z),.28,BLUE,role="internal")
        wire(module,"ModuleInternalBus",[(rx-.35,y+.28,-40.8),(rx+1.15,y+.28,-40.8),(rx+1.25,y+.36,-38.45)],RED,.09)
        wire(module,"FrontPanelHarness",[(rx-1.2,y+.48,-41.66),(rx-1.2,y+.48,-40.2),(rx-.65,y+.56,-39.9)],CYAN,.08)
    # Rear vertical distribution is actually connected to each module tray.
    part(rack,"RearPowerDistributionRail",(rx+2.18,-57.1,-38.4),(.20,12.4,.20),DARK,"internal")
    for y in (-62.42,-60.02,-57.62,-55.22,-52.82):
        wire(rack,"RearModulePowerLead",[(rx+2.18,y,-38.4),(rx+1.25,y,-38.45)],RED,.09)
    source=part(rack,"RackSupplyWallPlate",(rx,-61.2,-36.59),(1.6,1.1,.16),WHITE,"housing")
    b.label(source,"LAB-CAL-03\nСИЛОВОЙ ВВОД",DARK,face=5)
    wire(rack,"RackSupplyCable",[(rx,-61.2,-36.69),(rx,-63.75,-36.8),(rx,-63.75,-38.25),(rx+2.18,-63.35,-38.4),(rx+2.18,-62.7,-38.4)],BLACK,.22,role="detail")
    b.note(rack,"ServiceAccess", "The two 2.75-stud doors open toward the working aisle, leaving more than 4.3 studs to the unchanged original workstation. Modules have open trays; power and signal routes are modeled behind their faceplates. No fabricated live telemetry is displayed.")
    return room
