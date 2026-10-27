"""Static, human-scale medical-room dressing for the V7 visual pass.

No scripts, medical procedures, collisions or interactive targets are added.
The original bed, controls, headwalls and room architecture remain untouched.
"""
from v7_common import WHITE, LIGHT, METAL, DARK, BLACK, CYAN, TEAL, BLUE, AMBER


def build(b, parent):
    medical = b.model(parent, "E06_Medical_Detail")
    b.note(medical, "VisualOnly", "Статическое оформление: вода, контейнеры и тележка не интерактивны. Медицинские процедуры не реализованы.")

    # West-wall bay: X=46.5 is the inside wall face. Sink faces east.
    sink = b.model(medical, "WallMountedHandwash")
    b.part(sink, "Splashback", (46.88, -59.6, -65), (.18, 3.4, 4.3), WHITE)
    for z in (-66.65, -63.35):
        for y in (-60.8, -58.4):
            b.segment(sink, "SplashbackWallStandoff", (46.505, y, z), (46.8, y, z), .14, METAL)
    b.part(sink, "SplashbackTopTrim", (47.01, -57.88, -65), (.12, .08, 4.3), METAL, material=1088)
    # Five separate bowl faces leave an open, visible recess.
    b.part(sink, "BasinBottom", (48.5, -61.08, -65), (2.8, .14, 3.8), WHITE)
    b.part(sink, "BasinBack", (47.18, -60.64, -65), (.16, .8, 3.8), WHITE)
    b.part(sink, "BasinFront", (49.82, -60.64, -65), (.16, .8, 3.8), WHITE)
    b.part(sink, "BasinNorth", (48.5, -60.64, -66.82), (2.48, .8, .16), WHITE)
    b.part(sink, "BasinSouth", (48.5, -60.64, -63.18), (2.48, .8, .16), WHITE)
    for z in (-66.81, -63.19):
        b.part(sink, "PolishedSideLip", (48.5, -60.2, z), (2.8, .08, .18), LIGHT)
    b.part(sink, "PolishedFrontLip", (49.82, -60.2, -65), (.18, .08, 3.8), LIGHT)
    for z in (-66.35, -63.65):
        b.segment(sink, "WallBracket", (46.58, -61.3, z), (49.4, -61.3, z), .15, METAL)
        b.segment(sink, "DiagonalBrace", (46.58, -62.05, z), (48.95, -61.3, z), .13, METAL)
        b.part(sink, "BracketWallPlate", (46.575, -61.65, z), (.14, .95, .32), METAL, material=1088)

    # Faucet, drain and visible trap terminate at the wall instead of floating.
    b.segment(sink, "TapRiser", (47.4, -60.16, -65), (47.4, -59.1, -65), .16, METAL)
    b.segment(sink, "TapSpout", (47.4, -59.1, -65), (48.25, -59.1, -65), .16, METAL)
    b.segment(sink, "TapOutlet", (48.25, -59.1, -65), (48.25, -59.38, -65), .16, METAL)
    b.part(sink, "TapLever", (47.38, -59.03, -64.58), (.18, .12, .6), METAL, material=1088)
    b.segment(sink, "WasteFlange", (48.5, -61, -65), (48.5, -60.94, -65), .42, METAL)
    b.segment(sink, "WasteOpening", (48.5, -60.93, -65), (48.5, -60.91, -65), .23, DARK)
    b.segment(sink, "DrainTail", (48.5, -61.16, -65), (48.5, -62.1, -65), .22, METAL)
    b.segment(sink, "TrapBottom", (48.5, -62.1, -65), (47.8, -62.1, -65), .24, METAL)
    b.segment(sink, "TrapReturn", (47.8, -62.1, -65), (47.8, -61.72, -65), .22, METAL)
    b.segment(sink, "WasteWallConnection", (47.8, -61.72, -65), (46.505, -61.72, -65), .22, METAL)
    b.part(sink, "WasteWallEscutcheon", (46.565, -61.72, -65), (.12, .45, .45), METAL, material=1088)
    for z, color in ((-65.65, BLUE), (-64.35, AMBER)):
        b.segment(sink, "SupplyTail", (47.35, -60.25, z), (47.35, -61.8, z), .1, METAL)
        b.segment(sink, "SupplyWallConnection", (47.35, -61.8, z), (46.505, -61.8, z), .1, METAL)
        b.part(sink, "SupplyServiceMark", (47.12, -61.8, z), (.2, .25, .25), color)
    b.part(sink, "SoapDispenser", (47.28, -58.6, -67.45), (.6, 1.2, .7), WHITE)
    b.part(sink, "SoapMount", (46.74, -58.6, -67.45), (.47, .8, .4), METAL, material=1088)
    b.part(sink, "SoapInspectionStrip", (47.6, -58.62, -67.45), (.05, .7, .15), TEAL)
    b.part(sink, "SoapOutlet", (47.43, -59.25, -67.45), (.35, .15, .25), DARK)
    b.part(sink, "PaperTowelCabinet", (47.14, -57.55, -62.7), (.85, 1.65, 1.3), WHITE)
    b.part(sink, "TowelCabinetMount", (46.61, -57.55, -62.7), (.21, 1.1, .8), METAL, material=1088)
    b.part(sink, "PaperOutlet", (47.59, -58.25, -62.7), (.04, .18, .9), DARK)
    b.part(sink, "PaperEdge", (47.6, -58.43, -62.7), (.05, .3, .65), LIGHT)
    plaque = b.part(sink, "HandwashProcedurePlaque", (46.87, -55.95, -65), (.12, 1.45, 4.3), TEAL)
    b.label(plaque, "ГИГИЕНА РУК\nПЕРЕД И ПОСЛЕ КОНТАКТА", face=0)
    for z in (-66.6, -63.4):
        b.segment(sink, "PlaqueWallMount", (46.505, -55.95, z), (46.82, -55.95, z), .12, METAL)

    waste = b.model(medical, "ClosedGeneralWaste")
    b.part(waste, "ClosedBinBody", (47.65, -62.6, -60.9), (1.8, 2.65, 1.65), WHITE)
    b.part(waste, "BinFloorFoot", (47.65, -63.96, -60.9), (1.5, .08, 1.35), DARK)
    b.part(waste, "SeparateClosedLid", (47.65, -61.21, -60.9), (1.95, .16, 1.8), TEAL)
    b.part(waste, "FootPedal", (48.62, -63.72, -60.9), (.42, .12, .65), METAL, material=1088)
    b.part(waste, "LidHinge", (46.77, -61.19, -60.9), (.12, .16, .75), METAL, material=1088)
    waste_label = b.part(waste, "WasteLegend", (48.56, -62.3, -60.9), (.03, .9, 1.3), DARK)
    b.label(waste_label, "ОБЩИЕ\nОТХОДЫ", face=0)

    # Surveyed clear bay between desk and storage: trolley X=[68.3,71.7],
    # Z=[-57.7,-54.3]. The bed is west at X~55 and does not intersect.
    trolley = b.model(medical, "ClosedInstrumentTrolley")
    cx, cz = 70, -56
    for x in (cx-1.35, cx+1.35):
        for z in (cz-1.2, cz+1.2):
            b.segment(trolley, "Upright", (x, -63.15, z), (x, -59.65, z), .12, METAL)
            b.part(trolley, "CasterFork", (x, -63.37, z), (.14, .45, .45), METAL, material=1088)
            b.segment(trolley, "CasterWheel", (x-.13, -63.69, z), (x+.13, -63.69, z), .58, DARK)
            b.part(trolley, "BrakeTab", (x+.12, -63.42, z+.24), (.18, .08, .3), AMBER)
    for y in (-62.6, -61.25, -59.9):
        b.part(trolley, "RolledShelf", (cx, y, cz), (2.8, .1, 2.55), METAL, material=1088)
        for x in (cx-1.4, cx+1.4):
            b.part(trolley, "ShelfSideRim", (x, y+.12, cz), (.08, .2, 2.55), METAL, material=1088)
        b.part(trolley, "ShelfRearRim", (cx, y+.12, cz+1.27), (2.8, .2, .08), METAL, material=1088)
    for z in (cz-1.2, cz+1.2):
        b.segment(trolley, "HandleSupport", (cx+1.35, -60.1, z), (cx+1.65, -59.7, z), .12, METAL)
    b.segment(trolley, "PushHandle", (cx+1.65, -59.7, cz-1.2), (cx+1.65, -59.7, cz+1.2), .16, DARK)
    # Sealed boxes and a lidded tray avoid portraying exposed instruments.
    for y, z in ((-62.19, cz), (-60.84, cz+.25)):
        b.part(trolley, "SealedSupplyBox", (cx, y, z), (2.25, .65, 1.8), WHITE)
        b.part(trolley, "SupplyBoxLid", (cx, y+.35, z), (2.32, .08, 1.87), TEAL)
        legend = b.part(trolley, "SupplyBoxLabel", (cx, y, z-.92), (1.4, .35, .03), DARK)
        b.label(legend, "ЗАПЕЧАТАНО / E-06")
    b.part(trolley, "ClosedInstrumentTray", (cx-.15, -59.61, cz), (2.1, .42, 1.75), METAL, material=1088)
    b.part(trolley, "InstrumentTrayLid", (cx-.15, -59.37, cz), (2.16, .06, 1.81), LIGHT)
    b.part(trolley, "TrayLatch", (cx-.15, -59.58, cz-.91), (.38, .2, .06), DARK)
    tray_label = b.part(trolley, "TrayInventoryLegend", (cx-.15, -59.57, cz-.95), (1.3, .22, .03), TEAL)
    b.label(tray_label, "ИНСТРУМЕНТЫ / ОПИСЬ")
    b.note(trolley, "Scope", "Тележка припаркована вне прохода; неподвижный декор без открываемых ящиков и инструмента.")
    return medical
