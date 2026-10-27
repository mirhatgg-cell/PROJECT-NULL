#!/usr/bin/env python3
"""Run the V10 geometry, actual-Lua tests and byte-for-byte repeat build."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / 'artifacts/PROJECT_NULL_GAMEPLAY_V10.rbxlx'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    results = []
    checks = [
        ('static XML / oriented geometry / service motion', 'tools/validate_v10.py'),
        ('actual Lua experiment core / 14 scenario groups', 'tools/test_v10_experiment_core.py'),
        ('actual Lua server integration / 21 scenario groups', 'tools/test_v10_server_runtime.py'),
        ('actual Lua client / GUI and event doubles', 'tools/test_v10_client.py'),
    ]
    for label, script in checks:
        result = subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT,
                                text=True, capture_output=True, timeout=120)
        results.append({'name': label, 'passed': result.returncode == 0,
                        'stdout': result.stdout, 'stderr': result.stderr})
        print(('PASS' if result.returncode == 0 else 'FAIL') + ': ' + label, flush=True)
        if result.returncode:
            print(result.stdout + result.stderr)

    with tempfile.TemporaryDirectory(prefix='project-null-v10-') as temporary:
        repeated = Path(temporary) / ARTIFACT.name
        result = subprocess.run([sys.executable, str(ROOT / 'tools/build_v10.py'),
                                 '--output', str(repeated)], cwd=ROOT,
                                text=True, capture_output=True, timeout=60)
        same = result.returncode == 0 and sha(repeated) == sha(ARTIFACT)
        results.append({'name': 'byte-identical repeat build', 'passed': same,
                        'stderr': result.stderr})
        print(('PASS' if same else 'FAIL') + ': byte-identical repeat build', flush=True)

    # Evaluate the actual generated content module, not a separate mock table.
    from lupa import LuaRuntime
    import xml.etree.ElementTree as ET
    from v7_common import name
    tree = ET.parse(ARTIFACT)
    module = next(item for item in tree.iter('Item')
                  if item.get('class') == 'ModuleScript' and name(item) == 'Content')
    generated = LuaRuntime(unpack_returned_tuples=True).execute(
        module.findtext("Properties/ProtectedString[@name='Source']"))
    expected = json.loads((ROOT / 'tools/v10_content.json').read_text())
    def matches(actual, wanted):
        if isinstance(wanted, dict):
            return (set(actual.keys()) == set(wanted)
                    and all(matches(actual[key], value) for key, value in wanted.items()))
        if isinstance(wanted, list):
            return (set(actual.keys()) == set(range(1, len(wanted)+1))
                    and all(matches(actual[index+1], value) for index, value in enumerate(wanted)))
        return actual == wanted
    content_ok = matches(generated, expected)
    results.append({'name': 'embedded Content ModuleScript equals authored JSON', 'passed': content_ok})
    print(('PASS' if content_ok else 'FAIL') + ': generated content module', flush=True)

    report = {
        'result': 'PASS' if all(item['passed'] for item in results) else 'FAIL',
        'map_sha256': sha(ARTIFACT),
        'runtime_sha256': {str(p.relative_to(ROOT)): sha(p)
                           for p in sorted((ROOT / 'src').glob('*V10*.luau'))},
        'checks': results,
        'limitations': 'Tests execute real Lua with Roblox API doubles and static geometry. '
                       'No Studio rendering, character physics, real networking, live DataStore or FPS test was performed.',
    }
    (ROOT / 'artifacts/TEST_RESULTS_V10.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    if report['result'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
