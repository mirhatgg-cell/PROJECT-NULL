#!/usr/bin/env python3
"""Create a portable, verified V11 review archive with its V10 build baseline."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
DESTINATION=ROOT/'artifacts/PROJECT_NULL_V11_REVIEW.zip'
START='''PROJECT: NULL / V11

ОСНОВНАЯ КАРТА: artifacts/PROJECT_NULL_OCEAN_V11.rbxlx
Открыть через File -> Open from File в Roblox Studio, затем Play.
Все игровые модули встроены. Старые лаборатории сохранены.

Вода Terrain появляется при запуске Play. Чтобы сохранить её прямо
в редакторе, остановить Play и выполнить весь текст
artifacts/BAKE_OCEAN_V11_COMMAND_BAR.luau через View -> Command Bar.
После этого сохранить место через File -> Save to File.
Для обычной игры эта дополнительная команда не нужна.

НОВЫЕ ПОМЕЩЕНИЯ: из западной галереи лабораторий пройти через новый
проём возле X=-93,Z=0 и подняться по трём маршам на верхнюю палубу.
Дальше центральный коридор ведёт к C01-C10 и носовому мостику.

E — взаимодействие/разговор. F — новые сервисные крышки/двери.
J — журнал. X — закрыть окно. Прежние панели V9 остаются на E.
NPC имеют полноценные R6-риги; движения процедурные, без внешних ID.

ИНСТРУКЦИЯ И ОТЧЁТ: docs/OCEAN_V11.md
ИЗОБРАЖЕНИЯ: artifacts/PROJECT_NULL_V11_EXTERIOR.png,
PROJECT_NULL_V11_INTERIORS.png, PROJECT_NULL_V11_CREW.png.
OPEN_INSPECTION — копия с открытыми сервисными доступами для осмотра.

Выполнены статические проверки и тесты настоящего Lua с двойниками API.
В Roblox Studio нужны проверки физики, маршрутов NPC, воды и FPS.
Постоянный прогресс использует прежний DataStore опубликованной игры;
неопубликованное место хранит прогресс до выхода из сессии.

V10 включена как воспроизводимая основа; для игры открывать V11.
'''


def add(archive,label,data):
    info=zipfile.ZipInfo(label,date_time=(2026,1,1,0,0,0))
    info.compress_type=zipfile.ZIP_DEFLATED
    info.external_attr=0o644<<16
    archive.writestr(info,data,compresslevel=9)


def main():
    files=[ROOT/'README.md']
    for directory in ('src','tools','docs'):
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts
                     and p.suffix in ('.py','.lua','.luau','.json','.md','.txt'))
    for filename in ('PROJECT_NULL_OCEAN_V11.rbxlx','PROJECT_NULL_V11_OPEN_INSPECTION.rbxlx',
                     'PROJECT_NULL_GAMEPLAY_V10.rbxlx','V9_MANIFEST.json','V10_MANIFEST.json',
                     'V11_MANIFEST.json','V11_AUDIT.json','TEST_RESULTS_V11.json',
                     'PROJECT_NULL_V11_EXTERIOR.png','PROJECT_NULL_V11_INTERIORS.png',
                     'PROJECT_NULL_V11_CREW.png','BAKE_OCEAN_V11_COMMAND_BAR.luau'):
        files.append(ROOT/'artifacts'/filename)
    assert all(p.is_file() for p in files),'Build, verify and render before packaging'
    audit=json.loads((ROOT/'artifacts/V11_AUDIT.json').read_text())
    tests=json.loads((ROOT/'artifacts/TEST_RESULTS_V11.json').read_text())
    map_sha=hashlib.sha256((ROOT/'artifacts/PROJECT_NULL_OCEAN_V11.rbxlx').read_bytes()).hexdigest()
    assert audit['result']==tests['result']=='PASS'
    assert audit['target_sha256']==tests['map_sha256']==map_sha,'Verification report belongs to another map'
    for filename,expected in tests['source_sha256'].items():
        assert hashlib.sha256((ROOT/filename).read_bytes()).hexdigest()==expected, 'Source changed since verification: '+filename
    with zipfile.ZipFile(DESTINATION,'w') as archive:
        add(archive,'START_HERE.txt',START.encode())
        for path in sorted(set(files)):add(archive,str(path.relative_to(ROOT)),path.read_bytes())
    with zipfile.ZipFile(DESTINATION) as archive:
        assert archive.testzip() is None
        print('ZIP integrity: PASS;',len(archive.namelist()),'files;',DESTINATION.stat().st_size,'bytes')
    print('Map SHA256:',map_sha)


if __name__=='__main__':main()
