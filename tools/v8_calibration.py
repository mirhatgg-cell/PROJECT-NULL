"""E07 metrology bench: a reference rail and supported signal instrument.

This is static, fictional sensor-test hardware. It adds no experiment logic,
clinical procedure, live values or remote assets. The original three-channel
calibration dock, computer, cabinet and door remain unchanged.
"""
from v7_common import WHITE, LIGHT, METAL, DARK, BLACK, CYAN, AMBER, BLUE


def build(b, parent):
    room = b.model(parent, "E07_Metrology")
    b.note(room, "Scope", "LAB-CAL-02: static reference rail and signal-comparison instrument. Scale marks are normalized fixture positions, not live measurements. Existing V7 controls and original calibration dock are untouched.")

    bench = b.model(room, "LAB_CAL_02_MetrologyBench")
    cx, cz = -35.0, -49.4
    # East-side bay, clear of the original bench and the west entrance.
    b.part(bench, "LaboratoryCountertop", (cx, -60.75, cz), (6.6, .26, 11.4), LIGHT)
    for x in (-37.7, -32.3):
        for z in (-54.3, -44.5):
            b.part(bench, "FloorLevelingFoot", (x, -63.86, z), (.74, .28, .74), DARK, 1088)
            b.part(bench, "BenchUpright", (x, -62.3, z), (.32, 2.84, .32), WHITE, 1088)
    for x in (-37.7, -32.3):
        b.part(bench, "LongitudinalFrame", (x, -61.10, cz), (.26, .32, 10.05), WHITE, 1088)
        b.part(bench, "LowerFrameRail", (x, -63.30, cz), (.22, .22, 10.05), METAL, 1088)
    for z in (-54.3, -44.5):
        b.part(bench, "CrossFrame", (cx, -61.10, z), (5.4, .32, .26), WHITE, 1088)
    b.part(bench, "LowerShelf", (cx, -62.76, cz), (5.2, .14, 9.5), (125, 145, 151), 1088)
    asset = b.part(bench, "BenchAssemblyPlate", (-38.105, -61.18, -52.7), (.05, .65, 2.1), DARK)
    b.label(asset, "LAB-CAL-02\nСТЕНД СРАВНЕНИЯ", CYAN, face=3)

    rail = b.model(room, "DualGuideReferenceRail")
    for x in (-35.65, -34.35):
        for z in (-53.3, -45.7):
            b.part(rail, "RailMount", (x, -60.52, z), (.55, .2, .7), METAL, 1088)
        b.part(rail, "LinearGuide", (x, -60.35, -49.5), (.2, .18, 8.5), DARK, 1088)
    # Lead screw, bearing blocks and handwheel form one supported assembly.
    b.segment(rail, "LeadScrew", (-33.95, -60.08, -54.10), (-33.95, -60.08, -45.1), .105, METAL)
    for z in (-53.5, -45.4):
        b.part(rail, "ScrewBearingBlock", (-33.95, -60.33, z), (.45, .54, .35), WHITE, 1088)
    b.segment(rail, "TranslationHandwheel", (-33.95, -60.08, -54.18), (-33.95, -60.08, -54.34), .56, DARK)
    b.part(rail, "HandwheelIndex", (-33.95, -59.9, -54.37), (.08, .17, .035), LIGHT)
    b.part(rail, "ReferenceScaleBed", (-33.39, -60.3, -49.5), (.48, .12, 8.2), WHITE)
    for i in range(13):
        b.part(rail, "PositionScaleTick", (-33.38, -60.227, -53.1+i*.6), (.36 if i % 3 == 0 else .2, .02, .04), DARK)
    scale = b.part(rail, "NormalizedScaleLegend", (-32.8, -60.59, -47.15), (.72, .035, 1.5), DARK)
    b.label(scale, "ПОЗИЦИЯ\nУСЛ. ШКАЛА", LIGHT, face=1)

    heads = b.model(room, "ReferenceEmitterAndReceiver")
    for code, z, direction in (("REF", -52.0, 1), ("DUT", -46.5, -1)):
        head = b.model(heads, "CalibrationHead_" + code)
        b.part(head, "GuideCarriage", (-35, -60.14, z), (2.1, .32, 1.3), METAL, 1088)
        b.part(head, "HeadSupportStem", (-35, -59.52, z), (.28, 1.04, .28), WHITE, 1088)
        b.part(head, "InstrumentHeadHousing", (-35, -59, z), (1.1, 1.2, 1.15), WHITE, 1088)
        face_z = z + direction*.61
        b.part(head, "LensMountPlate", (-35, -59, face_z), (.95, .95, .08), DARK)
        b.segment(head, "LensBarrel", (-35, -59, face_z), (-35, -59, face_z+direction*.24), .59, METAL)
        b.segment(head, "OpticalWindow", (-35, -59, face_z+direction*.245), (-35, -59, face_z+direction*.27), .44, BLUE)
        b.segment(head, "CarriageLockKnob", (-34.10, -60.02, z), (-33.76, -60.02, z), .27, DARK)
        b.part(head, "SignalSocket", (-35.62, -59.25, z), (.15, .3, .3), DARK)
        legend = b.part(head, "HeadIdentification", (-35.565, -58.65, z), (.03, .34, .85), DARK)
        b.label(legend, code + " / CAL-02", LIGHT, face=3)

    analyzer = b.model(room, "SignalComparisonInstrument")
    # Front faces west toward the working aisle. The display is a passive
    # wiring schematic; there is no fabricated live response or test result.
    b.part(analyzer, "InstrumentEnclosure", (-37.25, -59.79, -48.6), (1.28, 1.58, 3.0), DARK, 1088)
    b.part(analyzer, "EnclosureTopCover", (-37.25, -58.96, -48.6), (1.3, .08, 3.02), WHITE)
    face = b.part(analyzer, "ComparisonSchematicPlate", (-37.92, -59.68, -48.6), (.06, 1.24, 2.7), BLACK)
    b.label(face, "LAB-CAL-02\nREF → СРАВНЕНИЕ ← DUT\nСХЕМА ПОДКЛЮЧЕНИЯ", CYAN, face=3)
    for z in (-49.55, -47.65):
        b.segment(analyzer, "RangeSelector", (-37.98, -60.30, z), (-38.15, -60.30, z), .25, METAL)
        b.part(analyzer, "SelectorIndex", (-38.17, -60.23, z), (.025, .12, .04), LIGHT)
    for z in (-49.75, -48.6):
        b.part(analyzer, "OutputConnectorBlock", (-36.565, -59.92, z), (.12, .37, .37), WHITE)
        b.segment(analyzer, "OutputConnectorBarrel", (-36.53, -59.92, z), (-36.39, -59.92, z), .23, METAL)
    for z in (-49.85, -47.35):
        for x in (-37.65, -36.85):
            b.part(analyzer, "InstrumentIsolationFoot", (x, -60.59, z), (.24, .06, .26), BLACK)
    for z in (-49.5, -49.05, -48.6, -48.15, -47.7):
        b.part(analyzer, "PassiveCoolingSlot", (-36.60, -59.15, z), (.025, .14, .27), BLACK)

    routing = b.model(room, "SupportedSignalAndPowerRouting")
    for z, head_z in ((-49.75, -52.0), (-48.6, -46.5)):
        points = [(-36.39, -59.92, z), (-36.2, -60.38, z),
                  (-36.2, -60.38, head_z), (-35.75, -59.25, head_z),
                  (-35.695, -59.25, head_z)]
        for a, end in zip(points, points[1:]):
            b.segment(routing, "ShieldedSignalLead", a, end, .085, BLACK)
        b.part(routing, "SignalLeadBenchClip", (-36.2, -60.49, (z+head_z)/2), (.18, .26, .2), WHITE)
    # Wall-bound conduit below the worktop. The riser passes through a small
    # grommet directly into the enclosure, with supports to the bench frame.
    wall = b.part(routing, "InstrumentSupplyWallPlate", (-30.57, -61.7, -44.2), (.12, .9, 1.5), WHITE)
    b.label(wall, "LAB-CAL-02\nПИТАНИЕ", DARK, face=3)
    power = [(-30.64, -61.7, -44.2), (-32.7, -61.7, -44.2),
             (-37.3, -61.7, -44.2), (-37.3, -61.7, -48.6),
             (-37.3, -60.58, -48.6)]
    for a, end in zip(power, power[1:]):
        b.segment(routing, "UnderBenchSupplyConduit", a, end, .18, METAL)
    for x in (-33.6, -36.8):
        b.part(routing, "ConduitFrameBracket", (x, -61.4, -44.2), (.12, .65, .36), WHITE, 1088)
    b.segment(routing, "EnclosureCableGrommet", (-37.3, -60.64, -48.6), (-37.3, -60.59, -48.6), .42, DARK)

    reference = b.model(room, "LabeledReferenceFixtures")
    for code, z in (("A", -53.7), ("B", -51.8), ("C", -49.9)):
        b.part(reference, "ReferenceFixtureBase", (-32.45, -60.52, z), (.9, .2, .8), DARK)
        plate = b.part(reference, "ReferenceFixture", (-32.45, -59.96, z), (.68, .92, .09), WHITE)
        b.label(plate, "REF-" + code + "\nCAL-02", DARK)

    return room
