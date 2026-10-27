"""V10 spatial narrative and playable stations, authored against the physical V9 map.

Every case is a set of thin physical walls; contents are spatial geometry. The
V10 interactions are metadata consumed by the server, never client-owned state.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from v7_common import name, WHITE, LIGHT, METAL, DARK, BLACK, CYAN, AMBER, RED, TEAL, BLUE
from v9_common import setprop

CONTENT = Path(__file__).with_name('v10_content.json')
PAPER = (211, 206, 181)
OLD = (96, 103, 96)
RUST = (117, 81, 62)
UNIFORM = (75, 104, 114)


def build(b, parent, root):
    interactions = []
    first_service = len(b.services)
    content = json.loads(CONTENT.read_text())
    docs = {d['id']: d for d in content['documents']}

    def group(label, description):
        model = b.model(parent, label)
        b.note(model, 'NarrativePurpose', description)
        return model

    def interact(part, action, argument, label):
        b.role(part, 'control')
        config = b.item(part, 'Folder', 'V10_Interact')
        b.note(config, 'Action', action)
        b.note(config, 'Argument', argument)
        prompt = b.item(part, 'ProximityPrompt', 'V10_Prompt')
        b.prop(prompt, 'string', 'ActionText', {
            'console': 'Открыть пульт', 'document': 'Прочитать', 'npc': 'Поговорить',
            'cooling': 'Управление охлаждением', 'repair': 'Обслужить',
            'supply': 'Получить фильтр', 'medical': 'Медицинская помощь',
            'records': 'Журнал и сохранение', 'response': 'Подтвердить путь',
        }.get(action, 'Использовать'))
        b.prop(prompt, 'string', 'ObjectText', label)
        b.prop(prompt, 'float', 'HoldDuration', .25)
        b.prop(prompt, 'float', 'MaxActivationDistance', 9)
        b.prop(prompt, 'bool', 'RequiresLineOfSight', True)
        b.prop(prompt, 'bool', 'Enabled', True)
        b.prop(prompt, 'token', 'KeyboardKeyCode', 101)
        frame = part.find("Properties/CoordinateFrame[@name='CFrame']")
        pos = tuple(float(frame.findtext(k)) for k in 'XYZ')
        interactions.append({'part': part.get('referent'), 'action': action,
                             'argument': argument, 'label': label, 'position': pos})
        return part

    def legend(part, text, color=LIGHT, face=5, status=None):
        gui = b.label(part, text, color, face)
        label = next(e for e in gui.findall('Item') if e.get('class') == 'TextLabel')
        if status:
            setprop(label, 'string', 'Name', 'V10_Status_' + status)
        return gui

    def local(model, label, center, offset, size, color, role='detail', yaw=0,
              material=1088, shape=None):
        x, y, z = center; u, v, w = offset
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        return b.part(model, label, (x+c*u+s*w, y+v, z-s*u+c*w), size,
                      color, material, yaw=yaw, role=role, shape=shape)

    def wallboard(model, label, center, title, document=None, yaw=0, width=4.5):
        board = b.model(model, label)
        local(board, 'SteelDocumentRail', center, (0, 0, .045),
              (width+.24, 2.9, .11), DARK, 'housing', yaw)
        for u in (-width/2, width/2):
            local(board, 'RailAnchor', center, (u, .95, -.045),
                  (.13, .13, .04), METAL, yaw=yaw, shape=2)
        paper = local(board, 'DocumentFace', center, (0, 0, -.035),
                      (width, 2.65, .045), PAPER, 'control' if document else 'detail', yaw,
                      material=272)
        legend(paper, title, DARK)
        for u in (-width*.36, width*.36):
            local(board, 'PaperClip', center, (u, 1.22, -.08),
                  (.34, .12, .04), METAL, yaw=yaw)
        if document:
            interact(paper, 'document', document, docs[document]['title'])
        return board

    def dossier(model, label, center, document, yaw=0):
        # Thin folder, visible edge pages and binder, not a floating UI marker.
        m = b.model(model, label)
        local(m, 'DossierBack', center, (0, 0, .055), (1.65, 2.15, .07), OLD,
              'housing', yaw)
        for i in range(3):
            local(m, 'PaperEdge', center, (.025*i, 0, .008-i*.014),
                  (1.54, 2.04, .018), PAPER, yaw=yaw, material=272)
        face = local(m, 'DossierReadFace', center, (0, 0, -.055),
                     (1.54, 2.04, .025), PAPER, 'control', yaw, material=272)
        legend(face, document.replace('DOC_', '') + '\n' + docs[document]['title'], DARK)
        local(m, 'Spine', center, (-.77, 0, -.005), (.12, 2.18, .16), METAL,
              'housing', yaw)
        interact(face, 'document', document, docs[document]['title'])
        return m

    def terminal(model, label, position, experiment=None, action=None, argument=None):
        x, y, z = position
        title='Пульт '+experiment if experiment else {
            'ShiftRecords':'Журнал смены', 'CoolingControl':'Управление охлаждением',
        }.get(label,label)
        m = b.model(model, label)
        # Front display is fixed, rear has real service access with an outward hinge.
        case, door, faces = b.shell(m, 'ServiceableTerminalCase', position,
                                    (2.55, 2.8, 1.25), METAL, .1, 'Z+', True, 100)
        b.part(m, 'TerminalFoot', (x, -63.88, z), (2.25, .24, 1.5), DARK,
               role='structure')
        post_h = y-1.4-(-63.76)
        b.part(m, 'TerminalColumn', (x, -63.76+post_h/2, z+.2),
               (.45, post_h, .45), METAL, role='structure')
        b.part(case, 'CPUBoard', (x-.45, y+.12, z+.22),
               (.9, 1.8, .07), TEAL, role='internal')
        b.part(case, 'PowerConverter', (x+.58, y-.55, z+.08),
               (.7, .8, .6), DARK, role='internal')
        for i in range(3):
            b.part(case, 'ProcessorAndMemory', (x-.45, y-.38+i*.43, z+.16),
                   (.51, .25, .12), BLACK, role='internal')
        b.segment(case, 'ScreenDataLoom', (x-.6, y+.8, z+.12),
                  (x-.6, y+.8, z-.37), .09, DARK, role='internal')
        b.segment(case, 'PowerLoom', (x+.58, y-.6, z+.05),
                  (x+.25, y-.6, z-.39), .09, AMBER, role='internal')
        screen = b.part(m, 'V10_ConsoleScreen', (x, y+.18, z-.66),
                        (2.15, 1.88, .07), BLACK, role='control')
        legend(screen, title.upper() + '\nГОТОВНОСТЬ / ОЖИДАНИЕ',
               CYAN, status=experiment or label)
        bar = b.part(m, 'ConsoleKeyboard', (x, y-1.11, z-.67),
                     (1.8, .3, .08), DARK, role='detail')
        for dx in (-.5, 0, .5):
            b.part(m, 'KeyCluster', (x+dx, y-1.11, z-.72),
                   (.29, .12, .03), METAL)
        for dx in (-1.11, 1.11):
            b.part(m, 'BezelRail', (x+dx, y+.18, z-.66),
                   (.08, 2.02, .12), DARK, role='housing')
        beacon = b.part(m, 'V10_RunBeacon', (x, y+1.69, z),
                        (.52, .46, .52), CYAN, material=288)
        light = b.item(beacon, 'PointLight', 'StatusLight')
        b.prop(light, 'float', 'Brightness', .45)
        b.prop(light, 'float', 'Range', 6)
        color = b.prop(light, 'Color3', 'Color')
        for k,v in zip('RGB', CYAN): ET.SubElement(color,k).text = str(v/255)
        b.note(m, 'Experiment', experiment or '')
        interact(screen, action or 'console', argument or experiment or '',
                 title)
        return m

    def bench(model, label, x, z, width=5, depth=2.6, y=-60.7):
        m = b.model(model, label)
        b.part(m, 'Worktop', (x, y, z), (width, .2, depth), METAL, role='structure')
        for dx in (-width/2+.22, width/2-.22):
            for dz in (-depth/2+.22, depth/2-.22):
                h = y-.1+64
                b.part(m, 'BenchLeg', (x+dx,-64+h/2,z+dz),
                       (.24,h,.24), DARK, role='structure')
        b.part(m, 'RearCrossrail', (x, y-1.65, z+depth/2-.22),
               (width-.45,.17,.17), DARK, role='structure')
        return m

    def archive(model, label, center, width=4.4, color=OLD):
        x,y,z = center
        m, door, faces = b.shell(model,label,center,(width,7.6,2.8),color,.12,'Z-',True,100)
        for shelf_y in (y-2.35,y-.1,y+2.15):
            b.part(m,'PhysicalShelf',(x,shelf_y,z),(width-.27,.12,2.5),METAL,role='structure')
            for i in range(4):
                bx=x-width/2+.55+i*(width-.95)/3
                b.part(m,'ArchiveBinder',(bx,shelf_y+.82,z+.08),(.54,1.5,1.7),
                       (OLD,BLUE,TEAL,DARK)[i],role='internal')
                stripe=b.part(m,'BinderIndex',(bx,shelf_y+.95,z-.79),(.39,.52,.025),PAPER)
                legend(stripe,f'{i+1:02d} / R',DARK)
        return m

    def patched_cable(model, center, length=6, yaw=0):
        m=b.model(model,'ELEC_SignedRepair')
        local(m,'CableTrayPatch',center,(0,0,0),(length,.25,.6),METAL,'structure',yaw)
        for i in range(3):
            local(m,'ReplacementCable',center,(0,.18,-.18+i*.18),
                  (length-.1,.09,.09),(TEAL,AMBER,DARK)[i],yaw=yaw)
        for dx in (-length/2+.3,length/2-.3):
            local(m,'RepairClamp',center,(dx,.05,0),(.12,.45,.85),DARK,'structure',yaw)
            local(m,'WallStandOff',center,(dx,0,.55),(.13,.13,.55),METAL,'structure',yaw)
        return m

    def staff(model, staff_id, x, z):
        data=content['staff'][staff_id]
        m=b.model(model,'Staff_'+staff_id)
        pieces={}
        for label,offset,size,color,role,shape in [
            ('HumanoidRootPart',(0,3.35,0),(1.8,2.1,.8),BLACK,'detail',None),
            ('Torso',(0,3.35,0),(1.8,2.1,.9),UNIFORM,'structure',None),
            ('Head',(0,5.05,0),(1.25,1.3,1.2),(172,148,128),'control',0),
            ('Left Arm',(-1.27,3.35,0),(.7,2.05,.8),UNIFORM,'detail',None),
            ('Right Arm',(1.27,3.35,0),(.7,2.05,.8),UNIFORM,'detail',None),
            ('Left Leg',(-.47,1.2,0),(.78,2.2,.82),DARK,'structure',None),
            ('Right Leg',(.47,1.2,0),(.78,2.2,.82),DARK,'structure',None),
        ]:
            p=local(m,label,(x,-64,z),offset,size,color,role,shape=shape,material=272)
            pieces[label]=p
        setprop(pieces['HumanoidRootPart'],'float','Transparency',1)
        for dx in (-.47,.47):
            b.part(m,'Boot',(x+dx,-63.86,z-.15),(.8,.28,1.12),BLACK,role='structure')
        for dx in (-.24,.24):
            b.part(m,'Eye',(x+dx,-58.84,z-.583),(.12,.1,.035),BLACK)
        b.part(m,'Mouth',(x,-59.23,z-.591),(.34,.055,.025),DARK)
        b.part(m,'UniformCollar',(x,-59.63,z-.46),(.86,.18,.08),LIGHT)
        badge=b.part(m,'StaffBadge',(x+.46,-60.3,z-.48),(.5,.7,.045),PAPER)
        legend(badge,data['role'],DARK)
        b.part(m,'UtilityBelt',(x,-61.38,z), (1.85,.17,.97),BLACK)
        b.part(m,'Radio',(x-.64,-60.15,z-.5),(.32,.72,.18),DARK)
        b.segment(m,'RadioAntenna',(x-.64,-59.8,z-.5),(x-.64,-59.38,z-.5),.045,DARK)
        humanoid=b.item(m,'Humanoid','Humanoid')
        b.prop(humanoid,'string','DisplayName',data['name'])
        b.prop(humanoid,'float','Health',100)
        b.prop(humanoid,'float','MaxHealth',100)
        b.prop(humanoid,'float','WalkSpeed',0)
        b.prop(humanoid,'token','RigType',0)
        b.prop(humanoid,'bool','RequiresNeck',False)
        b.prop(humanoid,'bool','BreakJointsOnDeath',False)
        b.prop(m,'Ref','PrimaryPart',pieces['HumanoidRootPart'].get('referent'))
        # The rig is intentionally stationed at a work post. Anchoring prevents
        # an unattended NPC from obstructing unknown navigation routes.
        for label in ('HumanoidRootPart','Head','Left Arm','Right Arm','Left Leg','Right Leg'):
            weld=b.item(pieces['Torso'],'WeldConstraint','UniformJoint_'+label.replace(' ','_'))
            b.prop(weld,'Ref','Part0',pieces['Torso'].get('referent'))
            b.prop(weld,'Ref','Part1',pieces[label].get('referent'))
        interact(pieces['Head'],'npc',staff_id,data['name']+' / '+data['role'])
        return m

    # E-01: shift handover and archive history are physically present before any
    # experimental console. The central entry and north door remain unobstructed.
    prep=group('E01_ShiftArchive','Сменный пост: журнал приёма, история допуска, техник и сохранение результатов.')
    terminal(prep,'ShiftRecords',(11.5,-59.3,-65),action='records',argument='records')
    staff(prep,'TECH',11.5,-71.3)
    wallboard(prep,'ShiftHandover',(9.7,-57.7,-48.8),
              'СМЕНА 04 / ПРОВЕРЯЙТЕ НЕЗАВИСИМЫЙ ЖУРНАЛ', 'DOC_SHIFT_HANDOVER',width=7)
    wallboard(prep,'AccessPolicy',(-9.7,-55,-75.2),
              'ДОПУСК / ЗАПИСЬ РЕЗУЛЬТАТОВ', 'DOC_ACCESS',yaw=180,width=6)
    archive(prep,'ArchiveOfWithdrawnForms',(-13.1,-59.9,-53.8),3.7)
    # Bottom of archive -63.7, real shelves carry files; it does not occupy bench.
    patched_cable(prep,(-9,-51.3,-75.05),7)

    control=group('E04_OperatorEvidence','Рабочие следы операторов: противоречивый отчёт, исправленный кабель, персональный журнал.')
    terminal(control,'P01_OperatorTerminal',(-60.9,-59.3,-6),'P01')
    wallboard(control,'P01_Protocol',(-48,-56.3,10.9),
              'P-01 / СИНХРОНИЗАЦИЯ: СЛЕДУЙТЕ ФАКТИЧЕСКОМУ СИГНАЛУ','DOC_P01_PROTOCOL',width=7)
    wallboard(control,'OfficialIncidentSummary',(-58,-56.5,10.9),
              'ИНЦИДЕНТ 03 / ОФИЦИАЛЬНАЯ СВОДКА','DOC_P03_LOG',width=4.5)
    dossier(control,'OperatorPersonalFile',(-34,-59.1,10.9),'DOC_OPERATOR')
    patched_cable(control,(-46,-51.6,10.7),10)
    # A numbered replacement connector rack sits beside the existing desks.
    for i in range(4):
        block=b.part(control,'ReplacementCableReel',(-61.2,-62.7+i*.68,7.9),(.5,.52,1.2),
                     (OLD,TEAL,AMBER,DARK)[i],role='internal')
    b.part(control,'CableReelWallRack',(-61.7,-61.65,7.9),(.18,3.2,1.5),METAL,role='structure')

    immersion=group('E03_BoundaryVerification','Независимый контроль P-05 и физические свидетельства повторной проверки.')
    terminal(immersion,'P05_BoundaryTerminal',(21.1,-59.3,-9),'P05')
    wallboard(immersion,'P05_Protocol',(-12.6,-57.5,-23.05),
              'P-05 / ЭКРАН НЕ ЯВЛЯЕТСЯ ЭТАЛОНОМ','DOC_P05_PROTOCOL',yaw=180,width=5)
    # Independent instruments have actual sensor, board and cable in a service case.
    case,door,_=b.shell(immersion,'IndependentReferenceMeter',(-20.7,-58.4,-7.8),
                        (2.6,3.1,1.15),TEAL,.09,'Z-',True,100)
    b.part(case,'ReferenceOscillator',(-20.95,-58.4,-7.5),(.68,1.4,.48),METAL,role='internal')
    b.part(case,'ReferenceBoard',(-20.7,-58.4,-7.42),(2.15,2.3,.07),TEAL,role='internal')
    b.part(case,'IndependentBattery',(-20.25,-59.2,-7.7),(.55,.62,.6),DARK,role='internal')
    for i in range(3):
        b.part(case,'ReferenceTerminal',(-21.35+i*.6,-57.2,-7.9),(.32,.23,.3),AMBER,role='internal')
    legend(door,'НЕЗАВИСИМЫЙ ЭТАЛОН\nПИТАНИЕ ОТДЕЛЕНО',LIGHT)
    b.part(immersion,'MeterMount',(-20.7,-61.93,-7.8),(.3,4.14,.3),METAL,role='structure')
    b.part(immersion,'MeterBase',(-20.7,-63.9,-7.8),(2.3,.2,1.4),DARK,role='structure')
    wallboard(immersion,'RedactedBoundaryMemo',(18,-56.8,23.05),
              'ПРЕДЕЛ ПОЛНОМОЧИЙ / NULL НЕ ОПРЕДЕЛЁН','DOC_NULL_LIMIT',width=6)

    recovery=group('E05_RecoveryAndHandover','Пост медсопровождения: передача испытуемого, личные вещи и отсутствие на рабочем месте.')
    staff(recovery,'MEDIC',76.4,-7.4)
    cart=bench(recovery,'PatientBelongingsCart',76,-19,4,2.5,-61.5)
    for dx in (-.95,.95):
        box,door,_=b.shell(cart,'PersonalPropertyCase',(76+dx,-60.65,-19),
                           (1.6,1.4,1.9),OLD,.065,'Z-',True,100)
        b.part(box,'FoldedUniform',(76+dx,-60.85,-18.9),(1.25,.4,1.25),UNIFORM,role='internal')
        b.part(box,'PersonalNotebook',(76+dx,-60.5,-18.9),(.85,.1,1.1),PAPER,role='internal')
    wallboard(recovery,'RecoveryTransfer',(76,-56.8,-23.05),
              'ПЕРЕДАЧА 03:21 / НЕ ПОВТОРЯТЬ ИСПЫТАНИЕ БЕЗ ОСМОТРА','DOC_RECOVERY',yaw=180,width=5.5)
    wallboard(recovery,'VacantPost',(45.8,-56.5,6.95),
              'ЛИЧНЫЙ ШКАФ 12 / СМЕНА НЕ ЗАКРЫТА','DOC_MISSING_SHIFT',width=5)

    medical=group('E06_MedicalRecords','Медицинский пост с доступной аптечкой, учётом расходников и карточкой наблюдения.')
    medcase,meddoor,_=b.shell(medical,'FirstAidSupplyCase',(71.5,-59.8,-65.8),
                             (2.7,4,1.5),WHITE,.1,'Z-',True,100)
    for y in (-60.9,-59.6):
        b.part(medcase,'KitShelf',(71.5,y,-65.8),(2.4,.08,1.25),METAL,role='structure')
        for dx in (-.7,0,.7):
            b.part(medcase,'SealedFirstAidPack',(71.5+dx,y+.38,-65.75),
                   (.48,.62,.9),LIGHT,role='internal')
    medcontrol=b.part(medical,'FirstAidDispenser',(71.5,-58.6,-66.61),(1.9,.82,.1),TEAL,role='control')
    legend(medcontrol,'ПЕРВАЯ ПОМОЩЬ / УЧЁТ ВЫДАЧИ')
    interact(medcontrol,'medical','kit','Медицинский комплект')
    # Control moves with door so its service access remains coherent.
    svc=b.services[-1];svc['moving'].append(medcontrol.get('referent'))
    config=next(e for e in meddoor.findall('Item') if name(e)=='V9_Service')
    ref=b.item(config,'ObjectValue','Moving_2');b.prop(ref,'Ref','Value',medcontrol.get('referent'))
    wallboard(medical,'MedicalObservation',(50.7,-56.8,-69.15),
              'КАРТА НАБЛЮДЕНИЯ / НЕ ПОДМЕНЯТЬ ПОКАЗАНИЯ','DOC_MEDICAL',yaw=180,width=5.8)
    b.part(medical,'CaseSupport',(71.5,-62.95,-65.8),(.45,2.1,.45),METAL,role='structure')
    b.part(medical,'CaseFoot',(71.5,-63.9,-65.8),(2.4,.2,1.4),DARK,role='structure')

    lab=group('E07_TimelineAndReconstruction','Подлинная временная шкала и отдельный пост P-03; отчёт можно сопоставить с независимыми следами.')
    terminal(lab,'P03_ReconstructionTerminal',(-55.6,-59.3,-45),'P03')
    wallboard(lab,'IndependentSignedLog',(-51.7,-57.4,-59.15),
              'НЕЗАВИСИМЫЙ ЖУРНАЛ / 03:14 → 03:16 → 03:18 → 03:21',
              'DOC_P03_CORRECTION',yaw=180,width=8.3)
    wallboard(lab,'CalibrationOrder',(-35.3,-54,-59.15),
              'КАЛИБРОВКА / ПОКАЗАНИЯ ВАЖНЕЕ НАЗВАНИЙ','DOC_CALIBRATION',yaw=180,width=5.6)
    # Four independent recorder cartridges remain visible, individually indexed.
    rack=bench(lab,'RecorderEvidenceRack',-54,-51.4,4,2,-61.4)
    for i in range(4):
        x=-55.35+i*.9
        b.part(rack,'TimeRecorderCartridge',(x,-60.9,-51.4),(.64,.8,1.4),DARK,role='internal')
        face=b.part(rack,'RecorderTimestamp',(x,-60.9,-52.12),(.57,.64,.03),PAPER)
        legend(face,('03:14','03:16','03:18','03:21')[i],DARK)

    supply=group('E08_WorkshopAndFilters','Выдача фильтров и реальный ремонтный стол вместо безымянного запаса ящиков.')
    table=bench(supply,'FilterAndRepairBench',62,75.6,7,4,-60.9)
    filtercase,door,_=b.shell(table,'FilterStockCabinet',(60,-58.9,75.6),
                            (2.7,3.7,2.3),TEAL,.09,'Z-',True,100)
    for i in range(4):
        b.part(filtercase,'ReplacementFilterCassette',(60,-60.1+i*.73,75.6),
               (2.3,.46,1.9),LIGHT,role='internal')
        for j in range(3):
            b.part(filtercase,'FilterPleat',(59.3+j*.7,-60.1+i*.73,74.7),
                   (.03,.38,.1),METAL,role='internal')
    pick=b.part(supply,'FilterIssuePlate',(60,-58.5,74.37),(1.9,.9,.08),TEAL,role='control')
    legend(pick,'ВЫДАЧА / ФИЛЬТР')
    interact(pick,'supply','filter','Запасной фильтр')
    # Stock label is attached to the moving front leaf, not left in the air.
    svc=b.services[-1];svc['moving'].append(pick.get('referent'))
    cfg=next(e for e in door.findall('Item') if name(e)=='V9_Service')
    ref=b.item(cfg,'ObjectValue','Moving_2');b.prop(ref,'Ref','Value',pick.get('referent'))
    repaired,repdoor,_=b.shell(table,'OpenableMaintenanceModule',(64,-59.8,75.6),
                             (2.4,1.8,2.3),OLD,.08,'Z-',True,100)
    b.part(repaired,'RepairControllerPCB',(64,-60.35,75.6),(1.9,.08,1.7),TEAL,role='internal')
    for dx in (-.55,.55):
        b.part(repaired,'ServiceContactor',(64+dx,-59.95,75.7),(.55,.65,.85),DARK,role='internal')
    repair=b.part(supply,'MaintenanceWorkOrder',(64,-58.64,75.6),(2,.5,1.8),AMBER,role='control')
    legend(repair,'ОБСЛУЖИТЬ КОНТУР',DARK,face=1)
    interact(repair,'repair','repair','Замена фильтра и сброс защиты')
    wallboard(supply,'FilterIssueLog',(62,-54.4,78.14),
              'РАСХОДНИКИ / ЗАМЕНА ПОСЛЕ СРАБАТЫВАНИЯ ЗАЩИТЫ','DOC_SUPPLY',width=7)

    used=group('E09_QuarantinedHardware','Последствия аварии: выведенный из работы драйвер, обрезанный кабель и инвентарная сверка.')
    dismantled=bench(used,'QuarantineExaminationBench',-49.1,58.8,3.8,2.5,-61.5)
    oldcase,oldcover,_=b.shell(dismantled,'WithdrawnDriver',(-49.1,-60.55,58.8),
                             (2.9,1.7,1.8),OLD,.07,'Z-',True,100)
    b.part(oldcase,'ScorchedControllerBoard',(-49.1,-61,58.8),(2.3,.07,1.3),RUST,role='internal')
    for i in range(3):
        b.part(oldcase,'FailedPowerStage',(-49.8+i*.7,-60.62,58.85),(.44,.6,.55),BLACK,role='internal')
    for i in range(3):
        b.segment(oldcase,'CutCableEnd',(-49.9+i*.65,-60.15,58.9),
                  (-49.9+i*.65,-59.9,59.25),.08,DARK,role='internal')
    legend(oldcover,'СНЯТО / НЕ ВКЛЮЧАТЬ',AMBER)
    wallboard(used,'QuarantineInventory',(-35.6,-56.3,69.15),
              'КАРАНТИН / КОМПЛЕКТ НЕ СПИСАН','DOC_QUARANTINE',width=5.2)
    for x in (-47,-38):
        patch=b.part(used,'ContainerChainOfCustody',(x,-58.67,64),(3.7,.045,2.6),PAPER)
        legend(patch,'ПЕЧАТЬ 03 / СВЕРИТЬ НОМЕР',DARK,face=1)

    hall=group('E12_PerceptionControl','Пост P-02 с независимыми измерениями и исправленной схемой залов.')
    terminal(hall,'P02_PerceptionTerminal',(215.5,-59.3,-5.8),'P02')
    wallboard(hall,'P02_Rule',(208,-56.2,-11.1),
              'P-02 / ВЫБИРАЙТЕ ПО ИЗМЕРЕНИЮ, НЕ ПО ТАБЛИЧКЕ','DOC_P02_PROTOCOL',yaw=180,width=7)
    wallboard(hall,'ObserverStaffMemo',(192,-56.2,11.1),
              'СМЕНА НАБЛЮДЕНИЯ / СРАВНИТЬ ДВА КАНАЛА','DOC_HALL_CONTROL',width=7)
    patched_cable(hall,(213.7,-51.5,5.9),8,yaw=90)
    # Physical response posts belong to the existing three hall sensor positions.
    # Their adjacent locations leave the pads, original controls and the central
    # route free. The server only accepts a response at the corresponding post.
    posts=b.model(hall,'P02_PhysicalResponsePosts')
    for route,letter,label,x,z,yaw,color in (
        ('left','L','левый',148.5,-19,-90,BLUE),
        ('center','C','центральный',169.5,-3,90,AMBER),
        ('right','R','правый',148.5,16,-90,TEAL),
    ):
        m=b.model(posts,'P02_Response_'+route)
        center=(x,-61.3,z)
        b.part(m,'ResponsePostFoot',(x,-63.88,z),(1.3,.24,1.3),DARK,role='structure')
        b.part(m,'ResponsePostColumn',(x,-62.4,z),(.4,2.72,.4),METAL,role='structure')
        local(m,'ResponseBacking',center,(0,0,0),(1.2,1.15,.24),DARK,'housing',yaw)
        target=local(m,'PhysicalResponseButton',center,(0,0,-.15),
                     (1.05,1,.07),color,'control',yaw)
        gui=legend(target,letter+' / '+label.upper()+'\nСВЕРЬТЕ ИЗМЕРЕНИЕ')
        readout=next(e for e in gui.findall('Item') if e.get('class')=='TextLabel')
        setprop(readout,'string','Name','V10_P02_Readout_'+route)
        interact(target,'response',route,'P02 / '+label+' путь')
        b.part(m,'V10_RunBeacon',(x,-60.47,z),(.32,.32,.32),color,material=288)
        for offset in (-.45,0,.45):
            local(m,'RouteFloorMarker',(x,-63.976,z),(offset,0,0),
                  (.28,.025,1.8),color,yaw=yaw,material=272)

    storage=group('E13_WithdrawnGeneration','Два поколения аппаратуры, архив смен и выведенные модули: историю можно увидеть без записки.')
    archive(storage,'LegacyRecordsCabinet',(148.4,-59.9,84.9),4.6,OLD)
    archive(storage,'CurrentRecordsCabinet',(159.6,-59.9,84.9),4.6,TEAL)
    wallboard(storage,'RetiredGeneration',(143,-55.3,87.1),
              'ПОКОЛЕНИЕ 01 / СДАТЬ ЭТАЛОНЫ ОТДЕЛЬНО','DOC_GENERATIONS',width=7)
    for x,color in ((140.5,OLD),(168,TEAL)):
        m,door,_=b.shell(storage,'SpareIndependentSensor',(x,-61.8,83),
                         (3.1,3.6,2.6),color,.1,'Z-',True,100)
        b.part(m,'SensorBoard',(x,-61.8,83.7),(2.5,2.8,.08),TEAL,role='internal')
        b.part(m,'LensBarrel',(x,-61.3,82.8),(1.2,.72,.72),METAL,shape=2,role='internal')
        b.part(m,'RecorderStorage',(x,-62.75,83.1),(1.7,.4,1.5),DARK,role='internal')
        b.part(m,'SpareModuleFoot',(x,-63.8,83),(3.1,.4,2.6),DARK,role='structure')

    apparatus=group('E16_ObserverAndCooling','P-04 наблюдатель, предсказуемые ограничения и управляющий пост связанного контура охлаждения.')
    terminal(apparatus,'P04_ObserverTerminal',(-13.6,-59.3,56.1),'P04')
    wallboard(apparatus,'P04_ObservationRules',(-7.5,-56,51.85),
              'P-04 / НАБЛЮДАТЕЛЬ СЛЕДУЕТ ИЗВЕСТНОМУ ЦИКЛУ','DOC_P04_PROTOCOL',yaw=180,width=7)
    terminal(apparatus,'CoolingControl',(26,-59.3,58.6),action='cooling',argument='toggle')
    wallboard(apparatus,'CoolingMaintenance',(-6,-55.9,74.05),
              'КОНТУР / НЕ ОБХОДИТЬ ТЕРМОЗАЩИТУ','DOC_COOLING',width=7)
    patched_cable(apparatus,(-8,-50.5,73.8),9)

    # Put the hinge pin just outside the leaf's front surface. A centerline hinge
    # on the edge of a butt-jointed case clips its own side wall past 90 degrees.
    # This offset preserves the closed poses and lets every leaf open outwards.
    indexed={e.get('referent'):e for e in root.iter('Item')}
    cavity_by_model={c['model']:c for c in b.cavities}
    parents={c:p for p in root.iter('Item') for c in p.findall('Item')}
    for service in b.services[first_service:]:
        panel=indexed[service['panel']]
        cavity=cavity_by_model.get(parents[panel].get('referent'))
        if not cavity or cavity['front'] not in ('Z-','Z+'): continue
        pivot=list(service['pivot'])
        pivot[2] += (-1 if cavity['front']=='Z-' else 1)*(cavity['thickness']/2+.045)
        service['pivot']=tuple(pivot)
        config=next(e for e in panel.findall('Item') if name(e)=='V9_Service')
        value=next(e for e in config.findall('Item') if name(e)=='Pivot')
        vector=value.find("Properties/Vector3[@name='Value']")
        for key,val in zip('XYZ',pivot): vector.find(key).text=str(val)
        # New dual-purpose cases use F for maintenance and E for their playable
        # interaction, avoiding two competing E prompts at the same screen.
        prompt=next(e for e in panel.findall('Item') if name(e)=='V9_ServicePrompt')
        setprop(prompt,'token','KeyboardKeyCode',102)
        translated={
            'ServiceableTerminalCase':'Корпус пульта',
            'ArchiveOfWithdrawnForms':'Архив отозванных бланков',
            'IndependentReferenceMeter':'Независимый эталон',
            'PersonalPropertyCase':'Контейнер личных вещей',
            'FirstAidSupplyCase':'Аптечка',
            'FilterStockCabinet':'Шкаф фильтров',
            'OpenableMaintenanceModule':'Ремонтный модуль',
            'WithdrawnDriver':'Снятый драйвер',
            'LegacyRecordsCabinet':'Архив первого поколения',
            'CurrentRecordsCabinet':'Архив второго поколения',
            'SpareIndependentSensor':'Запасной сенсор',
        }
        setprop(prompt,'string','ObjectText',translated.get(name(parents[panel]),'Сервисная панель'))

    # These all refer to physically authored evidence, not arbitrary HUD text.
    return {'interactions': interactions,
            'documents': [d['id'] for d in content['documents']],
            'staff': {key: {'name': value['name'], 'role': value['role']}
                      for key,value in content['staff'].items()},
            'groups': {name(e): sum(p.get('class') == 'Part' for p in e.iter('Item'))
                       for e in parent.findall('Item') if e.get('class') == 'Model'}}
