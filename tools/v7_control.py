"""Visible, static operator-room dressing, keeping the existing live screens clear."""
from v7_common import AMBER, BLACK, BLUE, CYAN, DARK, LIGHT, METAL, WHITE


def build(b, parent):
    room = b.model(parent, "E04_Operator_Detail")
    b.note(room, "Scope", "Static physical labels, acoustic wall treatment and desk accessories. Original live screens and controls are unchanged.")
    for x, code, title, color in [
        (-54, "OP-01", "ПРОТОКОЛ / ЖУРНАЛ", CYAN),
        (-43, "OP-02", "СЕНСОРЫ / НАБЛЮДЕНИЕ", BLUE),
        (-32, "OP-03", "ИНЖЕНЕРНЫЕ СИСТЕМЫ", AMBER),
    ]:
        desk = b.model(room, code)
        # Front apron below desk top; keyboard and screen remain exposed.
        apron = b.part(desk, "StationPlate", (x, -61.38, .965), (5.4, .48, .05), DARK)
        b.label(apron, code + "  /  " + title, color)
        b.part(desk, "IdentityInlay", (x-3.6, -60.735, 3), (.28, .025, 3.5), color)
        # Protocol holder next to, rather than in front of, the active monitor.
        b.part(desk, "ProtocolHolderBase", (x+3.4, -60.66, 3.15), (1.05, .16, 1.8), DARK)
        page = b.part(desk, "ProcedureCard", (x+3.4, -59.62, 3.8), (.9, 1.9, .09), LIGHT)
        b.label(page, code + "\nПОРЯДОК РАБОТ\n01  ПИТАНИЕ\n02  СВЯЗЬ\n03  ПРОТОКОЛ", DARK)
        b.part(desk, "BinderClip", (x+3.4, -58.66, 3.72), (.38, .16, .12), METAL, 1088)
        # A cabled intercom with a supported gooseneck microphone.
        b.part(desk, "IntercomBase", (x-3, -60.57, 3.15), (1.25, .32, 1), DARK)
        b.segment(desk, "MicStem", (x-3, -60.4, 3.5), (x-3, -59.6, 3.5), .10, METAL)
        b.segment(desk, "MicGooseneck", (x-3, -59.6, 3.5), (x-2.7, -59.25, 3.15), .1, METAL)
        b.part(desk, "MicCapsule", (x-2.7, -59.22, 3.12), (.22, .3, .4), BLACK)
        lead = [(x-3, -60.58, 3.65), (x-3, -60.58, 5.1),
                (x-2.5, -60.58, 5.1), (x-2.5, -61.4, 5.1), (x-2.5, -61.4, 4.3)]
        for i, (a, endpoint) in enumerate(zip(lead, lead[1:])):
            b.segment(desk, f"IntercomLead_{i+1}", a, endpoint, .08, BLACK)

    treatment = b.model(room, "AcousticWallAndDocumentation")
    # Rear wall only; the observation window and west entrance are left open.
    for x in (-59, -53, -47, -41, -35, -29):
        b.part(treatment, "AcousticFrame", (x, -53, 11.28), (5.15, 7.8, .24), DARK, 1088)
        b.part(treatment, "FabricInsert", (x, -53, 11.11), (4.8, 7.4, .12), (70, 90, 102), 1312)
        for dx in (-2.05, 2.05):
            b.part(treatment, "PanelFastener", (x+dx, -56.3, 11.02), (.12, .12, .06), METAL, 1088)
    # A passive procedure board; no made-up live telemetry or sensor values.
    board = b.part(treatment, "RoomProtocolBoard", (-37, -53, -11.24), (13, 6.6, .16), DARK)
    b.label(board, "PROJECT: NULL   /   E-04\nОПЕРАТОРСКАЯ\n────────────────────\n01  ПРОВЕРКА ИНЖЕНЕРНЫХ СИСТЕМ\n02  РЕГИСТРАЦИЯ ПРОТОКОЛА\n03  НАБЛЮДЕНИЕ И СВЯЗЬ\n04  ЗАВЕРШЕНИЕ И ЖУРНАЛ", LIGHT, face=2)
    b.part(treatment, "BoardAccent", (-43.7, -53, -11.13), (.16, 6.6, .10), CYAN)
    for x in (-43.1, -30.9):
        for y in (-55.9, -50.1):
            b.part(treatment, "BoardStandOff", (x, y, -11.1), (.15, .15, .12), METAL, 1088)

    # High-level containment trunk, supported from the ceiling, not floating.
    for z in (-9.8, 9.8):
        b.part(room, "CeilingServiceRail", (-44, -41.3, z), (38, .32, .28), METAL, 1088)
        for x in (-60, -48, -36, -28):
            b.segment(room, "RailCeilingHanger", (x, -40.01, z), (x, -41.3, z), .09, METAL)
    for z in (-11.34, 11.34):
        b.part(room, "Skirting", (-44, -63.6, z), (38.7, .7, .1), DARK)

