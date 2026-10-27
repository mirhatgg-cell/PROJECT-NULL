"""Static E03 sensor equipment, supported on the existing immersion platform.

This deliberately adds no scripts, sensors or clinical claims. The original
chair, acoustic towers, tower supplies and room architecture remain intact.
"""
from v7_common import AMBER, BLACK, BLUE, CYAN, DARK, LIGHT, METAL, RED, WHITE


def build(b, parent):
    room = b.model(parent, "E03_Immersion_Detail")
    b.note(room, "Scope", "Static fictional neural-interface concept and supported sensor gantry. No operational or medical function is implemented. Original room, chair, acoustic towers and supply routes are preserved.")

    gantry = b.model(room, "NeuralSensorGantry")
    # The platform top is -63.64. Two rear posts leave the approach from the
    # south door, the side door and the west observation window unobstructed.
    for x in (-6.25, 6.25):
        b.part(gantry, "BoltedBasePlate", (x, -63.51, 7), (2.0, .26, 3.0), DARK, 1088)
        b.part(gantry, "IsolationPad", (x, -63.365, 7), (1.25, .10, 1.2), BLACK)
        b.part(gantry, "GantryUpright", (x, -56.95, 7), (.62, 12.75, .75), WHITE, 1088)
        b.part(gantry, "InnerGuideRail", (x*.95, -56.6, 6.48), (.13, 10.8, .16), METAL, 1088)
        for dx in (-.7, .7):
            for z in (5.95, 8.05):
                b.part(gantry, "BaseAnchorHead", (x+dx, -63.33, z), (.19, .11, .19), METAL, 1088)
        b.segment(gantry, "RearDiagonalBrace", (x, -63.30, 8.3), (x, -59.8, 7), .28, METAL)
        for y in (-60.0, -53.2):
            b.part(gantry, "PostClamp", (x, y, 7), (.85, .32, .95), DARK, 1088)
            b.part(gantry, "ClampFaceBolt", (x, y, 6.48), (.18, .18, .09), METAL, 1088)
    b.part(gantry, "GantryCrossMember", (0, -50.4, 7), (13.2, .85, .95), WHITE, 1088)
    b.part(gantry, "CrossMemberRail", (0, -50.98, 6.61), (12, .16, .22), METAL, 1088)
    for x in (-6.25, 6.25):
        b.part(gantry, "BeamEndCover", (x, -50.4, 7), (.9, 1.05, 1.12), DARK)
    b.part(gantry, "FixedSensorCarriage", (0, -51.09, 7), (2.4, .78, 1.58), DARK, 1088)
    b.part(gantry, "CarriageIndex", (0, -51.09, 6.17), (1.25, .35, .08), CYAN)
    for x in (-.86, .86):
        b.part(gantry, "CarriageBolt", (x, -51.09, 6.17), (.17, .17, .10), METAL, 1088)
    b.part(gantry, "SensorBoom", (0, -51.15, 5.18), (.52, .55, 3.35), METAL, 1088)
    b.segment(gantry, "BoomHingeAxle", (-.62, -51.15, 3.6), (.62, -51.15, 3.6), .68, DARK)
    b.segment(gantry, "SensorDropLink", (0, -51.15, 3.6), (0, -54.15, 3.25), .34, METAL)
    b.part(gantry, "SensorBridge", (0, -54.18, 3.22), (4.7, .38, .55), WHITE, 1088)
    b.part(gantry, "UpperSensorHousing", (0, -54.56, 3.12), (1.4, .46, .75), DARK)
    b.part(gantry, "UpperSensorFace", (0, -54.82, 2.98), (.72, .09, .44), BLUE)

    # The headrest extends to x=+/-1.5. Contact pads terminate at its sides;
    # the new support forks stay outside the original headrest and chair back.
    for side in (-1, 1):
        x = side*2.12
        b.segment(gantry, "SensorFork", (x, -54.18, 3.22), (x, -55.55, 2.7), .19, METAL)
        b.segment(gantry, "PadAdjustmentAxle", (side*1.74, -55.55, 2.7), (side*2.36, -55.55, 2.7), .30, DARK)
        b.part(gantry, "HeadrestSensorPad", (side*1.69, -55.55, 2.7), (.25, 1.15, .82), BLACK)
        b.part(gantry, "SensorPadInsert", (side*1.535, -55.55, 2.7), (.06, .68, .48), BLUE)
        b.part(gantry, "PatientLeadSocket", (side*2.14, -55.90, 3.10), (.34, .40, .30), WHITE)
        b.part(gantry, "LeadStrainRelief", (side*2.14, -55.88, 3.32), (.20, .28, .24), BLACK)

    supply = b.model(room, "GantrySignalAndSupply")
    # Side-mounted enclosure: labels identify hardware, not simulated status.
    b.part(supply, "InterfaceEnclosure", (6.25, -56.9, 7.17), (2.50, 4.10, 1.34), DARK, 1088)
    b.part(supply, "EnclosureFront", (6.25, -56.9, 6.46), (2.26, 3.88, .08), WHITE)
    legend = b.part(supply, "InterfaceIDPlate", (6.25, -55.86, 6.395), (2.00, .92, .05), DARK)
    b.label(legend, "NIF / E-03\nСЕНСОРНЫЙ УЗЕЛ", LIGHT)
    for x in (5.45, 7.05):
        for y in (-55.30, -58.50):
            b.part(supply, "EnclosureFastener", (x, y, 6.37), (.12, .12, .10), METAL, 1088)
    for x, color in ((5.55, BLUE), (6.25, CYAN), (6.95, AMBER)):
        b.part(supply, "SocketMount", (x, -57.93, 6.36), (.47, .47, .12), DARK)
        b.segment(supply, "ConnectorBody", (x, -57.93, 6.24), (x, -57.93, 6.37), .28, METAL)
        b.part(supply, "ConnectorIndex", (x, -58.34, 6.36), (.36, .12, .07), color)
    # Two capped ports and one attached harness. There are no floating leads.
    for x in (6.25, 6.95):
        b.segment(supply, "UnusedPortCap", (x, -57.93, 6.16), (x, -57.93, 6.26), .25, BLACK)
    b.segment(supply, "HarnessStrainRelief", (5.55, -57.93, 6.08), (5.55, -57.93, 6.24), .24, BLACK)
    harness = [(5.55, -57.93, 6.08), (5.55, -56.4, 6.08),
               (5.55, -52.0, 6.08), (.65, -52.0, 6.08),
               (.38, -51.5, 5.85), (.38, -51.5, 3.6),
               (.28, -53.65, 3.37), (.28, -54.18, 3.37)]
    for a, c in zip(harness, harness[1:]):
        b.segment(supply, "SupportedSensorHarness", a, c, .13, BLACK)
    for x in (1.6, 3.6, 5.55):
        b.part(supply, "HarnessBeamHanger", (x, -51.52, 6.68), (.16, 1.40, .18), WHITE)
        b.part(supply, "HarnessSupportFoot", (x, -52.12, 6.36), (.16, .18, .78), WHITE)
    b.part(supply, "BoomHarnessClip", (.20, -51.38, 4.75), (.58, .28, .20), WHITE)
    b.part(supply, "DropHarnessClip", (.16, -52.8, 3.43), (.55, .16, .22), WHITE)
    for side in (-1, 1):
        lead = [(.28, -54.18, 3.37), (side*1.45, -54.38, 3.65),
                (side*2.52, -54.85, 3.70), (side*2.52, -55.45, 3.55),
                (side*2.14, -55.88, 3.43)]
        for a, c in zip(lead, lead[1:]):
            b.segment(supply, "SensorLead", a, c, .085, BLACK)
    b.part(supply, "PlatformSupplyGland", (6.25, -63.56, 7.35), (.86, .15, .88), METAL, 1088)
    b.segment(supply, "EnclosureSupplySleeve", (6.25, -63.48, 7.35), (6.25, -58.90, 7.35), .24, DARK)
    for y in (-60.7, -62.6):
        b.part(supply, "SupplySleeveClamp", (6.25, y, 7.35), (.60, .18, .52), WHITE)

    markings = b.model(room, "PlatformIdentification")
    for x in (-7.58, 7.58):
        b.part(markings, "PlatformEdgeInlay", (x, -63.625, -.6), (.10, .02, 16.8), CYAN)
    for x in (-6.4, 6.4):
        b.part(markings, "ApproachCornerInlay", (x, -63.625, -9.35), (2.5, .02, .10), CYAN)
        for dx in (-.8, 0, .8):
            b.part(markings, "ServiceKeepClearDash", (x+dx, -63.625, -8.8), (.24, .02, .6), AMBER, yaw=35)
    floor_plate = b.part(markings, "PlatformAssemblyID", (-5.35, -63.615, -4.7), (3.0, .025, 2.2), DARK)
    b.label(floor_plate, "E-03\nNIF ASSEMBLY", LIGHT, face=1)

    stop = b.model(room, "EmergencyStopVisualPrototype")
    b.note(stop, "VisualOnly", "Static button geometry for visual review. It is not wired to any gameplay or emergency-stop behavior.")
    b.part(stop, "PedestalBase", (7.0, -63.515, -3.4), (1.45, .25, 1.6), DARK, 1088)
    b.part(stop, "PedestalStem", (7.0, -61.45, -3.4), (.32, 3.90, .38), METAL, 1088)
    b.part(stop, "StopBackingBox", (7.0, -59.5, -3.4), (1.65, 1.65, .72), AMBER)
    b.segment(stop, "StopBezel", (7.0, -59.35, -3.81), (7.0, -59.35, -3.98), .82, DARK)
    b.segment(stop, "RedMushroomHead", (7.0, -59.35, -3.98), (7.0, -59.35, -4.15), .62, RED)
    title = b.part(stop, "StopLegend", (7.0, -58.45, -3.78), (1.9, .42, .06), DARK)
    b.label(title, "АВАРИЙНЫЙ СТОП", LIGHT)
    note = b.part(stop, "PrototypeLegend", (7.0, -60.35, -3.80), (2.1, .49, .06), DARK)
    b.label(note, "ВИЗУАЛЬНЫЙ МАКЕТ", AMBER)

    return room
