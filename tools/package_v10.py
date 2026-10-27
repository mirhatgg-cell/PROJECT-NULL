#!/usr/bin/env python3
"""Package the verified V10 place, V9 build baseline, source and instructions."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / 'artifacts/PROJECT_NULL_V10_REVIEW.zip'
START = '''PROJECT: NULL / V10

ОСНОВНОЙ ФАЙЛ: artifacts/PROJECT_NULL_GAMEPLAY_V10.rbxlx
Открыть в Roblox Studio через File -> Open from File, затем Play.
Все скрипты уже внутри. Command Bar и дополнительные модели не нужны.

Начать с E01 и пульта P01 в E04. E — игровые действия; F — новые
сервисные панели; J — журнал; X — закрыть окно. Прежние панели V9 — E.
Копия PROJECT_NULL_V10_OPEN_INSPECTION.rbxlx предназначена для осмотра
содержимого корпусов с уже открытыми доступами.

ПОЛНАЯ ИНСТРУКЦИЯ: docs/STAGES_4_5_V10.md
СХЕМА ПОСТОВ: artifacts/PROJECT_NULL_V10_STATIONS.png
ИЗМЕНЕНИЯ: artifacts/PROJECT_NULL_V10_OVERVIEW.png
ВНУТРЕННОСТИ: artifacts/PROJECT_NULL_V10_CONTENTS.png

В неопубликованном файле прогресс хранится до выхода. Постоянные
сохранения требуют опубликованной игры с доступным DataStore.
Выполнены статические проверки и тесты реального Lua с двойниками API.
Roblox Studio в среде сборки отсутствует; нужен проход в самом движке.

V9 включена как основа воспроизводимой сборки. Играть начать с V10.
'''


def add(archive, label, data):
    info = zipfile.ZipInfo(label, date_time=(2026, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, data, compresslevel=9)


def main():
    files = [ROOT / 'README.md']
    for directory in ('src', 'tools', 'docs'):
        files.extend(path for path in (ROOT / directory).rglob('*')
                     if path.is_file() and '__pycache__' not in path.parts
                     and path.suffix in ('.py', '.lua', '.luau', '.json', '.md', '.txt'))
    for filename in (
        'PROJECT_NULL_GAMEPLAY_V10.rbxlx', 'PROJECT_NULL_V10_OPEN_INSPECTION.rbxlx',
        'PROJECT_NULL_ENGINEERING_V9.rbxlx', 'V9_MANIFEST.json',
        'V10_MANIFEST.json', 'V10_AUDIT.json', 'TEST_RESULTS_V10.json',
        'PROJECT_NULL_V10_OVERVIEW.png', 'PROJECT_NULL_V10_STATIONS.png',
        'PROJECT_NULL_V10_CONTENTS.png',
    ):
        files.append(ROOT / 'artifacts' / filename)
    assert all(p.is_file() for p in files), 'Run build, verification and rendering before packaging'
    audit = json.loads((ROOT / 'artifacts/V10_AUDIT.json').read_text())
    tests = json.loads((ROOT / 'artifacts/TEST_RESULTS_V10.json').read_text())
    sha = hashlib.sha256((ROOT / 'artifacts/PROJECT_NULL_GAMEPLAY_V10.rbxlx').read_bytes()).hexdigest()
    assert audit['result'] == tests['result'] == 'PASS', 'Only package a verified build'
    assert audit['target_sha256'] == tests['map_sha256'] == sha, 'Reports refer to a different map'
    with zipfile.ZipFile(DESTINATION, 'w') as archive:
        add(archive, 'START_HERE.txt', START.encode('utf-8'))
        for path in sorted(set(files)):
            add(archive, str(path.relative_to(ROOT)), path.read_bytes())
    with zipfile.ZipFile(DESTINATION) as archive:
        assert archive.testzip() is None
        print('ZIP integrity: PASS;', len(archive.namelist()), 'files;', DESTINATION.stat().st_size, 'bytes')
    print('Map SHA256:', sha)


if __name__ == '__main__':
    main()
