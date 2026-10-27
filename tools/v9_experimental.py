"""P02 serviceable instruments: physical shells, working access and real contents.

Replaces the V8 solid junction/camera blocks and adds an inspectable driver rack.
The apparatus remains fictional; no clinical or real field procedure is modeled.
"""
import math

from v9_common import WHITE, METAL, DARK, BLACK, LIGHT, CYAN, BLUE, AMBER, TEAL


def build(b, parent, source_root):
    old = b.find("E10_Experimental_Equipment", under=source_root)
    assert old is not None, "V8 P02 equipment missing"
    remove_names = {
        "ReferenceJunctionBody", "ReferenceJunctionFace", "ReferenceInstrumentPlate",
        "InstrumentConnector", "ConnectorLegend", "TrackingHeadHousing", "TrackingHeadID", "TrackingYoke",
    }
    for item in list(old.iter("Item")):
        if item.findtext("Properties/string[@name='Name']") in remove_names:
            b.remove(item)
    hall = b.model(parent, "P02_Serviceable_Equipment_V9")
    b.note(hall, "Scope", "V9: collidable thin-wall junction cases, camera lids and two-door instrument rack. Covers expose drivers, power/filter assemblies, terminals and wiring. Existing experiment controls and sensor pads are retained.")

    def rig_case(cx, cz, yaw, code):
        case = b.model(hall, code + "_ServiceableJunction")
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

        def xyz(x, y, z):
            # Move the cabinet 0.24 forward from the old solid body so the
            # retained support spine contacts its back instead of its cavity.
            z -= .24
            return cx+c*x+s*z, y, cz-s*x+c*z

        b.cavity(case, xyz(0, -60.5, .25), (2.5, 2.5, 1.45), .12, "Z-",
                 matrix=((c,0,s),(0,1,0),(-s,0,c)))

        def part(label, pos, size, color=WHITE, material=1088, role="internal"):
            return b.part(case, label, xyz(*pos), size, color, material,
                          yaw=yaw, role=role)

        def wire(label, a, end, diameter=.065, color=BLACK):
            return b.segment(case, label, xyz(*a), xyz(*end), diameter, color, role="internal")

        # Six independent metal faces; the cabinet volume is not a solid Part.
        for x in (-1.19, 1.19):
            part("JunctionSide", (x, -60.5, .25), (.12, 2.5, 1.45), WHITE, role="housing")
        part("JunctionBack", (0, -60.5, .915), (2.26, 2.5, .12), WHITE, role="housing")
        for y in (-61.69, -59.31):
            part("JunctionTopBottom", (0, y, .25), (2.26, .12, 1.21), WHITE, role="housing")
        door = part("JunctionServiceDoor", (0, -60.5, -.415), (2.26, 2.5, .12), DARK, role="panel")
        handle = part("JunctionDoorHandle", (.87, -60.5, -.515), (.12, .6, .13), METAL, role="detail")
        plate = part("JunctionAssemblyID", (0, -59.85, -.49), (1.75, .65, .03), DARK, role="detail")
        b.label(plate, code + "\nДРАЙВЕР / СЕРВИС", LIGHT)
        b.service(door, xyz(-1.13, -60.5, -.415), axis="Y", angle=105,
                  label=code + " / драйвер", moving=[handle, plate])
        for y in (-61.3, -59.7):
            part("DoorHingeBlock", (-1.12, y, -.39), (.18, .25, .24), METAL, role="detail")

        # Backplane and supported modules are accessible through the front door.
        part("DriverBackplane", (0, -60.42, .66), (1.98, 1.95, .075), (46, 105, 83), 272)
        for x in (-.82, .82):
            for y in (-61.18, -59.62):
                wire("BackplaneStandoff", (x, y, .71), (x, y, .84), .10, METAL)
        for x in (-.55, .55):
            part("PowerDriverModule", (x, -59.95, .49), (.59, .49, .22), DARK, 272)
            for dx in (-.20, 0, .20):
                part("DriverHeatSinkFin", (x+dx, -59.95, .30), (.045, .46, .22), METAL)
        for x in (-.57, .07):
            wire("FilterCapacitor", (x, -61.22, .28), (x, -60.79, .28), .31, (80, 107, 119))
            wire("CapacitorTop", (x, -60.78, .28), (x, -60.75, .28), .28, METAL)
        # A segmented toroid and its center opening make the choke readable.
        for i in range(10):
            a, z = 2*math.pi*i/10, 2*math.pi*(i+1)/10
            wire("FilterChokeWinding", (.58+.28*math.cos(a), -60.91+.28*math.sin(a), .28),
                 (.58+.28*math.cos(z), -60.91+.28*math.sin(z), .28), .11, AMBER)
        for x in (-.69, -.23, .23, .69):
            part("DINOutputTerminal", (x, -61.38, .27), (.30, .27, .40), TEAL, 272)
            part("TerminalClamp", (x, -61.38, .04), (.12, .12, .05), METAL)
        wire("InputCableToFilter", (.60, -61.72, .79), (.60, -61.39, .48), .10)
        wire("FilterPowerRail", (-.69, -61.19, .49), (.69, -61.19, .49), .07, AMBER)
        for x in (-.55, .55):
            wire("DriverPowerLead", (x, -61.19, .49), (x, -60.20, .49), .065, AMBER)
        # These exit at the original supported loop-harness riser.
        wire("LoopHarnessCabinetLead", (.38, -59.55, .53), (.38, -59.30, 1.20), .10)
        for x in (-.69, .69):
            wire("OutputTerminalLead", (x, -61.24, .27), (x, -60.85, .53), .065, BLUE)
        return case

    rig_case(132, -28, -140, "EXP-P02-01")
    rig_case(178, 23, 40, "EXP-P02-02")

    def optical_case(head_x, z, side, index):
        cx = head_x+.25*side
        model = b.model(hall, f"EXP_P02_03_OpticalHead_{index:02d}")
        b.cavity(model, (cx,-46.7,z), (1.0,.85,1.7), .10, "Y+")
        # The original lenses and yoke are retained; thin walls provide an
        # inspectable body around two independent lens/sensor paths.
        b.part(model, "OpticalCaseRear", (cx-.45*side, -46.7, z), (.10, .85, 1.7), WHITE, 1088, role="housing")
        # Separate front rails leave two genuine lens apertures.
        for y in (-47.045,-46.355):
            b.part(model, "OpticalFrontHorizontal", (cx+.45*side,y,z), (.10,.16,1.5), WHITE,1088,role="housing")
        for dz,width in ((-.775,.15),(0,.22),(.775,.15)):
            b.part(model, "OpticalFrontVertical", (cx+.45*side,-46.7,z+dz), (.10,.53,width),WHITE,1088,role="housing")
        for zz in (z-.80, z+.80):
            b.part(model, "OpticalCaseSide", (cx, -46.7, zz), (.80, .85, .10), WHITE, 1088, role="housing")
        b.part(model, "OpticalCaseBottom", (cx, -47.075, z), (.80, .10, 1.5), WHITE, 1088, role="housing")
        lid = b.part(model, "OpticalServiceLid", (cx, -46.325, z), (.80, .10, 1.5), DARK, 1088, role="panel")
        tag = b.part(model, "OpticalHeadAssemblyID", (cx, -46.255, z), (.78, .025, 1.4), DARK, role="detail")
        b.label(tag, "EXP-P02-03\nДВОЙНАЯ ОПТИКА", LIGHT, face=1)
        handle = b.part(model, "OpticalLidLatch", (cx+.27*side, -46.235, z), (.14, .12, .40), METAL, 1088, role="detail")
        b.service(lid, (cx-.40*side, -46.325, z), axis="Z", angle=side*105,
                  label="Оптическая головка / крышка", moving=[tag, handle])
        # Fork and trunnions remain outside the optical cavity, unlike the
        # old single yoke that occupied the same space as the image sensors.
        b.part(model, "OpticalForkCrossbar", (head_x,-47.55,z), (.25,.20,2.15),METAL,1088,role="structure")
        for dz in (-.98,.98):
            b.part(model,"OpticalForkUpright",(head_x,-47.0,z+dz),(.25,1.10,.20),METAL,1088,role="structure")
            b.segment(model,"OpticalTrunnion",(head_x,-46.7,z+dz),(head_x,-46.7,z+(.80 if dz>0 else -.80)),.20,METAL,role="structure")
        for dz in (-.43, .43):
            # Sensor board is behind a two-element lens train along world X.
            b.part(model, "ImageSensorBoard", (cx-.19*side, -46.7, z+dz), (.045, .48, .53), (47, 110, 91), role="internal")
            b.part(model, "SensorPackage", (cx-.145*side, -46.7, z+dz), (.045, .24, .24), BLACK, role="internal")
            for offset in (.03, .24):
                x = cx+offset*side
                b.segment(model, "LensSpacerTube", (x-.07*side, -46.7, z+dz), (x+.07*side, -46.7, z+dz), .34, DARK, role="internal")
                b.segment(model, "InternalLensElement", (x+.075*side, -46.7, z+dz), (x+.09*side, -46.7, z+dz), .27, BLUE, role="internal")
            b.segment(model, "SensorBoardSignalLead", (cx-.20*side, -46.85, z+dz),
                      (head_x, -46.95, z+.55), .045, BLACK, role="internal")
        b.part(model, "OpticsInterfaceBoard", (cx, -47.005, z), (.6, .045, 1.12), (47, 110, 91), role="internal")
        for dz in (-.55, .55):
            b.part(model, "OpticsBoardConnector", (head_x, -46.96, z+dz), (.18, .09, .13), METAL, role="internal")
        b.segment(model,"OpticsCableEntryGland",(head_x,-47.18,z+.55),
                  (head_x,-46.96,z+.55),.16,DARK,role="internal")
        return model

    optical_case(128.6, 29, 1, 1)
    optical_case(179.4, -28, -1, 2)

    rack = b.model(hall, "EXP_P02_04_InstrumentServiceRack")
    cx, cz = 132.0, 4.0
    b.cavity(rack,(cx,-58.9,cz),(6.4,9.8,4.8),.16,"Z-")
    # Large collidable assembly, not a floating panel. The west-side bay is
    # clear of the original pads (which start at X=138.5) and the west wall.
    for x in (cx-2.7, cx+2.7):
        for z in (cz-1.85, cz+1.85):
            b.part(rack, "RackLevelingFoot", (x, -63.82, z), (.75, .36, .75), DARK, 1088, role="structure")
    for x in (cx-3.12, cx+3.12):
        b.part(rack, "RackSideShell", (x, -58.9, cz), (.16, 9.8, 4.8), WHITE, 1088, role="housing")
    for y in (-63.72, -54.08):
        b.part(rack, "RackBaseTop", (cx, y, cz), (6.08, .16, 4.48), WHITE, 1088, role="housing")
    b.part(rack, "RackBackShell", (cx, -58.9, cz+2.32), (6.08, 9.8, .16), WHITE, 1088, role="housing")
    for x in (cx-2.78, cx+2.78):
        for z in (cz-1.96, cz+1.96):
            b.part(rack, "RackMountingRail", (x, -58.9, z), (.15, 9.5, .15), METAL, 1088, role="structure")
    for y in (-62.65, -59.65, -56.65):
        b.part(rack, "RemovableInstrumentDeck", (cx, y, cz), (5.55, .14, 3.85), METAL, 1088, role="structure")

    for side in (-1, 1):
        x = cx+side*1.52
        door = b.part(rack, "RackServiceDoor", (x, -58.9, cz-2.32), (3.0, 9.8, .16), DARK, 1088, role="panel")
        handle = b.part(rack, "RackServiceHandle", (cx+side*.32, -58.8, cz-2.46), (.14, 1.2, .18), METAL, 1088, role="detail")
        plate = b.part(rack, "RackDoorIdentifier", (x, -55.1, cz-2.425), (2.5, .8, .04), DARK, role="detail")
        b.label(plate, "EXP-P02-04\n" + ("ПИТАНИЕ / ФИЛЬТР" if side<0 else "ДРАЙВЕР / СИГНАЛ"), LIGHT)
        b.service(door, (cx+side*3.02, -58.9, cz-2.32), axis="Y", angle=-side*100,
                  label="P02 / инструментальная стойка", moving=[handle, plate])

    # A real power bay: chassis, board, wound filter, capacitor bank, fused rail.
    power = b.model(rack, "PowerAndFilterBay")
    b.part(power, "PowerModuleBackplane", (cx-1.4, -61.35, cz+1.55), (2.3, 2.3, .10), (48, 111, 87), role="internal")
    for y in (-62.25, -60.45):
        for x in (cx-2.35, cx-.45):
            b.segment(power, "BackplaneMountStandoff", (x, y, cz+1.60), (x, y, cz+1.98), .13, METAL, role="internal")
    for i in range(12):
        a, end = 2*math.pi*i/12, 2*math.pi*(i+1)/12
        b.segment(power, "PowerFilterToroid", (cx-1.45+.68*math.cos(a), -61.3+.68*math.sin(a), cz+.85),
                  (cx-1.45+.68*math.cos(end), -61.3+.68*math.sin(end), cz+.85), .25, AMBER, role="internal")
    for x in (cx-.15, cx+.60, cx+1.35):
        b.segment(power, "BulkFilterCapacitor", (x, -62.55, cz+.65), (x, -61.1, cz+.65), .56, (80, 109, 123), role="internal")
        b.segment(power, "CapacitorEndCap", (x, -61.08, cz+.65), (x, -61.01, cz+.65), .49, METAL, role="internal")
    for x in (cx-2.1, cx-1.25, cx-.4, cx+.45, cx+1.3, cx+2.15):
        b.part(power, "FusedDistributionTerminal", (x, -62.23, cz-1.0), (.61, .65, .55), TEAL, role="internal")
        b.part(power, "FuseCarrier", (x, -62.15, cz-1.32), (.27, .38, .12), LIGHT, role="internal")
    b.segment(power, "PowerBayBus", (cx-2.1, -61.8, cz-.70), (cx+2.15, -61.8, cz-.70), .12, AMBER, role="internal")
    b.segment(power, "FilterToFusedBus", (cx-1.45, -61.3, cz+.7), (cx-1.45, -61.8, cz-.70), .11, AMBER, role="internal")

    driver = b.model(rack, "DriverAndSignalBay")
    b.part(driver, "DriverCarrierBoard", (cx, -58.25, cz+1.52), (4.75, 2.55, .10), (45, 102, 85), role="internal")
    for x in (cx-1.65, cx-.55, cx+.55, cx+1.65):
        b.part(driver, "DriverPowerPackage", (x, -58.2, cz+1.25), (.69, .8, .35), BLACK, role="internal")
        for dx in (-.24, -.08, .08, .24):
            b.part(driver, "DriverCoolingFin", (x+dx, -58.2, cz+.80), (.06, .9, .65), METAL, 1088, role="internal")
        b.segment(driver, "DriverInputLead", (x, -61.8, cz-.70), (x, -58.7, cz+1.05), .09, AMBER, role="internal")
    for x in (cx-1.5, cx+1.5):
        b.segment(driver, "SignalIsolationTransformer", (x, -58.7, cz-.4), (x, -57.6, cz-.4), .70, TEAL, role="internal")
    b.part(driver, "IsolatedSignalBoard", (cx, -59.49, cz-.35), (4.5, .10, 1.85), (45, 102, 85), role="internal")
    for x in (cx-1.9, cx-.6, cx+.6, cx+1.9):
        b.part(driver, "SignalInterfaceIC", (x, -59.35, cz-.35), (.62, .18, .65), BLACK, role="internal")

    cooling = b.model(rack, "ForcedAirAndPatchBay")
    for x in (cx-1.55, cx+1.55):
        # Internal fan frame and separate hub/shaft/blades; no opaque fan disk.
        for y in (-55.95, -54.55):
            b.part(cooling, "FanFrameHorizontal", (x, y, cz+.9), (1.65, .15, .18), DARK, role="internal")
        for xx in (x-.75, x+.75):
            b.part(cooling, "FanFrameVertical", (xx, -55.25, cz+.9), (.15, 1.4, .18), DARK, role="internal")
        b.segment(cooling, "FanShaft", (x, -55.25, cz+.45), (x, -55.25, cz+1.15), .20, METAL, role="internal")
        b.segment(cooling, "FanMotorHousing", (x, -55.25, cz+.90), (x, -55.25, cz+1.28), .48, DARK, role="internal")
        for angle in (0, 90, 180, 270):
            a=math.radians(angle)
            b.segment(cooling, "FanBlade", (x+.12*math.cos(a), -55.25+.12*math.sin(a), cz+.60),
                      (x+.65*math.cos(a+.35), -55.25+.65*math.sin(a+.35), cz+.60), .20, METAL, cylinder=False, role="internal")
    patch = b.part(cooling, "PatchPanelFrame", (cx, -55.5, cz-1.60), (5.5, 1.3, .12), WHITE, 1088, role="structure")
    b.label(patch, "EXP-P02-04 / РАСПРЕДЕЛЕНИЕ КАНАЛОВ", DARK)
    for i in range(6):
        x=cx-2.15+i*.86
        b.segment(cooling, "PatchPortBody", (x, -55.62, cz-1.65), (x, -55.62, cz-1.85), .33, DARK, role="internal")
        b.segment(cooling, "PatchPortCap", (x, -55.62, cz-1.85), (x, -55.62, cz-1.92), .28, BLUE if i<3 else AMBER, role="internal")
        b.segment(cooling, "PatchInternalLead", (x, -55.62, cz-1.45), (x, -58.35, cz-.35), .07, BLACK, role="internal")
    # A viewable supported loom joins the rack's incoming service gland to
    # the power bay; the outer conduit reaches the existing reference feed.
    b.segment(rack, "RackInputGland", (cx+2.35, -63.65, cz+1.25), (cx+2.35, -62.6, cz+1.25), .34, METAL, role="internal")
    path=[(cx+2.35,-63.85,cz+1.25),(128.0,-63.85,cz+1.25),
          (128.0,-63.85,-30.8),(132.0,-63.85,-30.8)]
    for a,end in zip(path,path[1:]):
        b.segment(rack, "RackServiceFloorFeed", a,end,.22,DARK,cylinder=False,role="detail")
    b.note(rack, "Access", "Two front leaves expose the three instrument decks. Power/filter, driver/signal and fan/patch assemblies are physically modeled. Rack occupies the west-side bay; original pads, probes and south-wall controls remain separate.")

    def maintenance_access(cx, start_z, direction, landing_x, landing_z, code):
        access=b.model(hall,code)
        width=3.5
        # Twenty 0.7-stud rises lead to a working platform at Y=-50. The
        # cameras are outside the walking envelope, reachable over the guard.
        for i in range(20):
            top=-64+(i+1)*.7
            z=start_z+direction*i*1.1
            b.part(access,"MaintenanceTread",(cx,top-.09,z),(width,.18,1.2),METAL,1088,role="walkable")
        stringer_x=(cx-1.0,cx+1.0) if direction>0 else (cx-1.0,cx+1.4)
        for x in stringer_x:
            b.segment(access,"StairStringer",(x,-63.50,start_z),(x,-50.20,start_z+direction*20.9),.28,DARK,cylinder=False,role="structure")
            b.part(access,"StairBaseFoot",(x,-63.90,start_z),(.65,.20,.8),DARK,1088,role="structure")
            b.part(access,"StairBaseRiser",(x,-63.65,start_z),(.25,.50,.30),METAL,1088,role="structure")
        for side in (-1,1):
            x=cx+side*width/2
            for i in (0,4,8,12,16,19):
                top=-64+(i+1)*.7
                z=start_z+direction*i*1.1
                b.part(access,"StairGuardPost",(x,top+1.5,z),(.13,3.0,.13),DARK,1088,role="structure")
            b.segment(access,"StairHandrail",(x,-60.30,start_z),(x,-47,start_z+direction*20.9),.15,DARK,role="structure")
            last_z=start_z+direction*20.9
            front_z=landing_z-direction*2.0
            if abs(last_z-front_z)>.001:
                b.segment(access,"StairLandingRailTransition",(x,-47,last_z),(x,-47,front_z),.15,DARK,role="structure")
        b.part(access,"MaintenancePlatform",(landing_x,-50.125,landing_z),(6.5,.25,4.0),METAL,1088,role="walkable")
        for x in (landing_x-2.85,landing_x+2.85):
            for z in (landing_z-1.55,landing_z+1.55):
                b.part(access,"PlatformSupportColumn",(x,-57.125,z),(.30,13.75,.30),WHITE,1088,role="structure")
                b.part(access,"PlatformAnchoredFoot",(x,-63.9,z),(.65,.20,.65),DARK,1088,role="structure")
        # Cross bracing stays below/outside the stair-to-landing connection.
        back_z=landing_z+direction*1.55
        b.segment(access,"PlatformDiagonalBrace",(landing_x-2.85,-63.6,back_z),
                  (landing_x+2.85,-50.4,back_z),.18,METAL,role="structure")
        b.segment(access,"PlatformDiagonalBrace",(landing_x+2.85,-63.6,back_z),
                  (landing_x-2.85,-50.4,back_z),.18,METAL,role="structure")
        # Guard both side edges and the rear. The front has a full-width
        # opening aligned with the 3.5-stud stairs, rather than a tiny gap.
        rear=landing_z+direction*2.0
        for x in (landing_x-3.25,landing_x+3.25):
            for z in (landing_z-2,landing_z+2):
                b.part(access,"LandingGuardPost",(x,-48.5,z),(.13,3,.13),DARK,1088,role="structure")
            b.segment(access,"LandingSideHandrail",(x,-47,landing_z-2),(x,-47,landing_z+2),.15,DARK,role="structure")
        b.segment(access,"LandingRearHandrail",(landing_x-3.25,-47,rear),(landing_x+3.25,-47,rear),.15,DARK,role="structure")
        front=landing_z-direction*2.0
        if direction>0:
            a,end=cx+width/2,landing_x+3.25
        else:
            a,end=landing_x-3.25,cx-width/2
        b.part(access,"LandingFrontGuardPost",(a,-48.5,front),(.13,3,.13),DARK,1088,role="structure")
        b.segment(access,"LandingFrontHandrail",(a,-47,front),(end,-47,front),.15,DARK,role="structure")
        plaque=b.part(access,"MaintenanceAccessID",(landing_x,-48, rear-direction*.12),(4.5,.75,.06),DARK,role="detail")
        b.label(plaque,code+"\nДОСТУП К ОПТИЧЕСКОЙ ГОЛОВКЕ",LIGHT,face=5 if direction>0 else 2)
        b.note(access,"Geometry","3.5-stud clear stair width; 20 rises of 0.7; 1.2-stud treads at 1.1 pitch; landing at -50. Guarded service position gives floor players access to the optical head lid without flight.")
    maintenance_access(131.5,7.8,1,133.0,31.0,"EXP-P02-MAINT-W")
    maintenance_access(177.0,-8.1,-1,175.5,-31.0,"EXP-P02-MAINT-E")
    return hall
