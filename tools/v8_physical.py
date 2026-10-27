"""Stage-3 P02 reference instruments, following the existing fictional field test.

These static reference-loop and tracking assemblies dress the already-working
three-pad experiment. They introduce neither measurements nor new game actions.
"""
import math

from v7_common import AMBER, BLACK, BLUE, CYAN, DARK, LIGHT, METAL, WHITE


def build(b, parent):
    hall = b.model(parent, "E10_Experimental_Equipment")
    b.note(hall, "Scope", "EXP-P02: static reference-loop instruments and optical tracking heads for the existing fictional coupled-field test. Original probes, tuners, displays and doors are unchanged; no new live measurements or interactions.")

    def rig(cx, cz, yaw, code, accent):
        group = b.model(hall, code)
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

        def xyz(x, y, z):
            return cx+c*x+s*z, y, cz-s*x+c*z

        def part(label, pos, size, color=WHITE, material=272):
            return b.part(group, label, xyz(*pos), size, color, material, yaw=yaw)

        def link(label, a, endpoint, diameter=.12, color=METAL):
            return b.segment(group, label, xyz(*a), xyz(*endpoint), diameter, color)

        # A large footplate and visible isolators carry the whole instrument.
        part("ReferenceBasePlate", (0, -63.88, .15), (3.6, .24, 3.5), DARK, 1088)
        for x in (-1.25, 1.25):
            for z in (-1.05, 1.35):
                part("IsolationFoot", (x, -63.62, z), (.48, .28, .48), BLACK)
                part("FoundationBolt", (x, -63.45, z), (.22, .09, .22), METAL, 1088)
        part("IsolatedLowerFrame", (0, -63.38, .15), (3.2, .22, 2.9), METAL, 1088)
        for x in (-1.35, 1.35):
            part("ReferenceUpright", (x, -57.55, .7), (.26, 11.7, .36), WHITE, 1088)
        for y in (-62.8, -56.1, -52.6, -51.8):
            part("CrossSupport", (0, y, .7), (3.0, .28, .42), METAL, 1088)
        part("InstrumentBackbone", (0, -56.65, .92), (.58, 10.1, .48), DARK, 1088)

        # Two visible annular reference loops. Twelve supported segments each,
        # rather than hidden circuit boards or dozens of cosmetic screw pins.
        for index, y in enumerate((-56.1, -52.6), 1):
            for i in range(12):
                t0 = 2*math.pi*i/12
                t1 = 2*math.pi*(i+1)/12
                link(f"ReferenceLoop_{index}", (1.1*math.cos(t0), y+1.1*math.sin(t0), -.35),
                     (1.1*math.cos(t1), y+1.1*math.sin(t1), -.35), .19, accent)
            for x in (-1.0, 1.0):
                link("LoopSupportStandoff", (x, y, .7), (x, y, -.35), .15)
            part("ReferenceLoopDatum", (0, y-1.1, -.5), (.5, .22, .1), LIGHT)

        part("ReferenceJunctionBody", (0, -60.5, .25), (2.5, 2.5, 1.45), WHITE, 1088)
        part("ReferenceJunctionFace", (0, -60.5, -.515), (2.25, 2.25, .08), DARK)
        plate = part("ReferenceInstrumentPlate", (0, -60.12, -.585), (2.0, 1.15, .04), DARK)
        b.label(plate, code + "\nОПОРНЫЕ КОНТУРЫ\nФИЗИЧЕСКИЙ СТЕНД", LIGHT)
        for x in (-.62, .62):
            link("InstrumentConnector", (x, -61.2, -.57), (x, -61.2, -.81), .3)
            part("ConnectorLegend", (x, -61.48, -.59), (.36, .1, .06), accent)
        # Both loop feeds run along the supported spine into the junction box.
        link("LoopHarnessRiser", (.38, -59.3, .96), (.38, -52.6, .96), .12, BLACK)
        for y in (-56.1, -52.6):
            link("LoopHarnessBranch", (.38, y, .96), (1.0, y, .96), .10, BLACK)
            link("LoopHarnessTermination", (1.0, y, .96), (1.0, y, -.25), .10, BLACK)
        part("BaseCableGland", (.6, -63.68, .55), (.5, .15, .5), METAL, 1088)
        link("InstrumentCableRiser", (.6, -63.6, .55), (.6, -61.7, .55), .16, BLACK)
        return xyz(.6, -63.65, .55)

    endpoint_a = rig(132, -28, -140, "EXP-P02-01", BLUE)
    endpoint_b = rig(178, 23, 40, "EXP-P02-02", CYAN)

    tracking = b.model(hall, "EXP-P02-03_OpticalReferenceHeads")
    # Wall-supported tracking heads stand above the main controls. Their lenses
    # face into the hall and remain clear of the east observation window.
    for wall_x, head_x, z, side in ((126.505, 128.6, 29, 1), (181.495, 179.4, -28, -1)):
        b.part(tracking, "TrackingWallPlate", (wall_x+.07*side, -47.5, z), (.14, 2.5, 1.7), DARK, 1088)
        b.segment(tracking, "TrackingBracket", (wall_x+.14*side, -47.5, z), (head_x, -47.5, z), .22, METAL)
        b.segment(tracking, "TrackingBracketBrace", (wall_x+.14*side, -48.35, z), (head_x, -47.5, z), .16, METAL)
        b.part(tracking, "TrackingYoke", (head_x, -46.95, z), (.25, 1.3, 1.5), METAL, 1088)
        b.part(tracking, "TrackingHeadHousing", (head_x+.25*side, -46.7, z), (1.0, .85, 1.7), WHITE)
        for dz in (-.43, .43):
            b.segment(tracking, "TrackingLensBarrel", (head_x+.72*side, -46.7, z+dz),
                      (head_x+.97*side, -46.7, z+dz), .42, DARK)
            b.segment(tracking, "TrackingLensFace", (head_x+.98*side, -46.7, z+dz),
                      (head_x+1.01*side, -46.7, z+dz), .31, BLUE)
        b.segment(tracking, "TrackingWallSignalLead", (head_x, -47.85, z+.55),
                  (wall_x+.15*side, -47.85, z+.55), .08, BLACK)
        b.segment(tracking, "TrackingSignalTail", (head_x, -47.85, z+.55),
                  (head_x, -47.10, z+.55), .08, BLACK)
        plate = b.part(tracking, "TrackingHeadID", (head_x+.25*side, -46.16, z), (1.15, .04, 1.4), DARK)
        b.label(plate, "EXP-P02-03\nОПТИЧЕСКИЙ РЕПЕР", LIGHT, face=1)

    routes = b.model(hall, "ReferenceInstrumentFloorFeeds")
    # Each feed has a named source/termination. The cable itself is contained
    # in shallow floor trunk, joining the already-present sensor curb at x175.
    paths = [
        [endpoint_a, (132, -63.91, -30.8), (177.8, -63.91, -30.8), (177.8, -63.91, 29), (175.5, -63.91, 29)],
        [endpoint_b, (178.7, -63.91, 23), (178.7, -63.91, 29), (175.5, -63.91, 29)],
    ]
    for index, path in enumerate(paths, 1):
        for i, (a, endpoint) in enumerate(zip(path, path[1:]), 1):
            b.segment(routes, f"ReferenceFeed_{index}_{i}", a, endpoint, .18, DARK, cylinder=False)
    b.note(routes, "Connections", "Reference instruments 01/02 terminate beside existing P02 DAQ cabinet at (175,29). Wall tracking heads terminate at west/east wall service entries; signal continuation beyond the wall is not modeled.")
    return hall
