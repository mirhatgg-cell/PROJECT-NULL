"""E16 structured-data and cooling infrastructure for the experimental block.

The three V6 racks, their active hinged front covers and existing power feeds
remain unchanged. Added equipment describes static installation, not telemetry.
"""
from v7_common import AMBER, BLACK, BLUE, CYAN, DARK, LIGHT, METAL, TEAL, WHITE


def build(b, parent):
    room = b.model(parent, "E16_Server_Infrastructure")
    b.note(room, "Scope", "IT-016: supported structured-data tray, three rack drops and identifiers, side-wall recirculating fan-coil concept with closed primary-fluid connections. Original rack fronts and power feeds are unchanged. All equipment is static visual hardware.")

    tray = b.model(room, "IT_016_SupportedDataLadder")
    # Rear high-level data route is separated from the existing power feeds
    # at Y=-44. The rack lids are at Y=-52, leaving working clearance above.
    for z in (72.25, 73.35):
        b.part(tray, "LadderSideRail", (0, -48.7, z), (28.8, .3, .14), METAL, 1088)
    for x in range(-14, 15, 2):
        b.part(tray, "LadderCrossRung", (x, -48.84, 72.8), (.15, .12, 1.24), METAL, 1088)
    for x in (-13.5, -6.75, 0, 6.75, 13.5):
        b.part(tray, "CeilingAnchorPlate", (x, -40.08, 72.8), (1.1, .14, 1.6), METAL, 1088)
        for z in (72.2, 73.4):
            b.segment(tray, "ThreadedSuspensionRod", (x, -40.15, z), (x, -48.96, z), .09, METAL)
        b.part(tray, "TraySupportChannel", (x, -48.93, 72.8), (.35, .16, 1.6), DARK, 1088)
    for z, color in ((72.45, CYAN), (72.8, BLUE), (73.15, TEAL)):
        b.segment(tray, "StructuredDataBundle", (-14.35, -48.65, z), (14.7, -48.65, z), .105, color)
        # All three enter an explicit wall sleeve, instead of ending in air.
        b.segment(tray, "WallEntryTail", (14.7, -48.65, z), (15.47, -48.65, z), .105, color)
    b.part(tray, "DataWallSleeve", (15.41, -48.65, 72.8), (.17, .85, 1.45), DARK, 1088)
    inlet = b.part(tray, "DataEntryIdentifier", (15.29, -47.75, 72.8), (.07, .62, 2.9), DARK)
    b.label(inlet, "IT-016 / DATA\nРАЗДЕЛЁННЫЙ ВВОД", CYAN, face=3)
    b.segment(tray, "EntryLegendStandoff", (15.49, -47.75, 72.8), (15.33, -47.75, 72.8), .12, METAL)

    for index, rack_x in enumerate((-10, 0, 10), 1):
        rack = b.model(room, f"IT_016_RackDrop_{index:02d}")
        harness_x = rack_x-2.7
        # Top entry follows the original rear cable harness, not the moving
        # front ServiceCover. The lead terminates in the top-entry gland;
        # the existing closed lid conceals its continuation to the harness.
        b.segment(rack, "DataBranch", (harness_x, -48.65, 72.8), (harness_x, -48.65, 71.2), .11, CYAN)
        b.segment(rack, "RackDataDrop", (harness_x, -48.65, 71.2), (harness_x, -51.99, 71.2), .11, CYAN)
        b.part(rack, "LidCableGland", (harness_x, -51.94, 71.2), (.38, .14, .4), DARK, 1088)
        for y in (-49.5, -51.1):
            b.part(rack, "DropClip", (harness_x, y, 71.2), (.27, .14, .27), WHITE)
        # Labels stand above the lid and cannot remain on a cover when it opens.
        for dx in (-1.3, 1.3):
            b.segment(rack, "RackTagSupport", (rack_x+dx, -51.99, 67.1), (rack_x+dx, -50.55, 66.78), .10, METAL)
        plate = b.part(rack, "RackAssemblyIdentifier", (rack_x, -50.55, 66.7), (3.1, .85, .10), DARK)
        b.label(plate, f"IT-016 / R{index:02d}\nДАННЫЕ / ПИТАНИЕ РАЗДЕЛЕНЫ", LIGHT)
        for dx in (-1.3, 1.3):
            b.part(rack, "TagFaceFastener", (rack_x+dx, -50.55, 66.63), (.12, .12, .05), METAL, 1088)

    coil = b.model(room, "THERM_016_WallFanCoil")
    # Side-wall bay X>12.5, Z~58 is outside the rack-cover swing envelopes
    # (their moving panels are at Z~61..66.6 and X<=12.95).
    b.part(coil, "IsolatedFloorPlinth", (14, -63.8, 58), (2.6, .4, 5.9), DARK, 1088)
    b.part(coil, "FanCoilCasing", (14, -60, 58), (2.5, 7.2, 5.6), WHITE, 1088)
    b.part(coil, "ServiceFaceFrame", (12.71, -60.05, 58), (.12, 6.7, 5.2), METAL, 1088)
    b.part(coil, "ServiceFaceInsert", (12.62, -60.05, 58), (.08, 6.25, 4.85), DARK)
    for y in (-58.7, -61.25):
        b.segment(coil, "FanGuardRim", (12.54, y, 58), (12.43, y, 58), 2.1, METAL)
        b.segment(coil, "FanGuardRecess", (12.42, y, 58), (12.38, y, 58), 1.82, BLACK)
        # Human-scale protective grille: a few slats, no hidden motor microdetail.
        for dy in (-.6, -.3, 0, .3, .6):
            half_width = (max(.1, .86*.86-dy*dy))**.5
            b.part(coil, "FanGuardSlat", (12.34, y+dy, 58), (.06, .07, half_width*2), METAL, 1088)
        b.part(coil, "GuardCenterSpine", (12.30, y, 58), (.06, 1.65, .08), METAL, 1088)
    plate = b.part(coil, "CoolingAssemblyIdentifier", (12.53, -56.95, 58), (.06, .85, 4.4), DARK)
    b.label(plate, "THERM-016 / FCU\nОХЛАЖДЕНИЕ АППАРАТНОЙ", LIGHT, face=3)
    for y in (-57.15, -62.9):
        for z in (55.65, 60.35):
            b.part(coil, "CaptiveServiceFastener", (12.53, y, z), (.08, .15, .15), METAL, 1088)
    for z in (55.5, 60.5):
        b.part(coil, "CasingCornerProtection", (12.65, -60, z), (.16, 7.0, .18), DARK)
    # Primary coolant connections stop at actual wall penetration fittings.
    for z, color, legend in ((56.6, BLUE, "ПОДАЧА"), (59.4, AMBER, "ОБРАТНЫЙ КОНТУР")):
        b.part(coil, "PrimaryWallEscutcheon", (15.43, -54.5, z), (.14, .7, .7), METAL, 1088)
        b.segment(coil, "PrimaryWallTail", (15.49, -54.5, z), (14.7, -54.5, z), .22, METAL)
        b.segment(coil, "PrimaryVerticalTail", (14.7, -54.5, z), (14.7, -56.45, z), .22, METAL)
        b.part(coil, "PipeIdentificationBand", (14.7, -55.1, z), (.31, .25, .31), color)
        b.segment(coil, "IsolationValveBody", (14.7, -55.5, z), (14.7, -55.85, z), .38, METAL)
        b.part(coil, "IsolationValveHandle", (14.35, -55.68, z), (.8, .12, .22), color)
        pipe_label = b.part(coil, "PrimaryCircuitLabel", (15.37, -53.6, z), (.08, .7, 2.2), DARK)
        b.label(pipe_label, "THERM-016\n"+legend, color, face=3)
        b.segment(coil, "PipeLabelWallMount", (15.49, -53.6, z), (15.41, -53.6, z), .14, METAL)
    # Short lateral anchors tie the housing to the wall while keeping its face
    # clear for inspection and preserving the central entry route.
    for z in (56, 60):
        b.part(coil, "WallRestraintBracket", (15.375, -58.8, z), (.25, .35, .65), METAL, 1088)

    board = b.model(room, "IT_016_ServiceAccess")
    plaque = b.part(board, "InfrastructureProcedureBoard", (-15.32, -57.3, 58), (.12, 4.2, 7.2), DARK)
    b.label(plaque, "IT-016 / АППАРАТНАЯ\nDATA — ОТДЕЛЬНЫЙ ВЕРХНИЙ ЛОТОК\nPWR — СУЩЕСТВУЮЩИЙ ВВОД\nTHERM — БОКОВОЙ КОНТУР\nСОХРАНЯТЬ ДОСТУП К ПАНЕЛЯМ", LIGHT, face=0)
    for z in (55.1, 60.9):
        for y in (-58.9, -55.7):
            b.segment(board, "ProcedureBoardMount", (-15.49, y, z), (-15.37, y, z), .12, METAL)
    b.part(board, "RackServiceLimitLine", (0, -63.96, 62.6), (28.5, .02, .13), AMBER)
    service = b.part(board, "ServiceFloorLegend", (0, -63.95, 63.7), (7.0, .025, 1.0), DARK)
    b.label(service, "IT-016 / СЕРВИСНЫЙ ДОСТУП", AMBER, face=1)
    b.note(board, "ServiceClearance", "Central door approach X=-6..6 remains open. Rack fronts remain clear at floor level; fan-coil occupies only the right-side bay. Floor markings are visual labels, not collision barriers.")
    return room
