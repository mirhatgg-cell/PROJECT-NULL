#!/usr/bin/env python3
"""Verify authored V11 geometry, real Lua modules and reproducible packaging inputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/'artifacts/PROJECT_NULL_OCEAN_V11.rbxlx'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    results=[]
    for label,script in [
        ('V11 XML / geometry / preserved laboratory rules','tools/validate_v11.py'),
        ('Original five protocol rules','tools/test_v10_experiment_core.py'),
        ('Existing server integration regressions','tools/test_v10_server_runtime.py'),
        ('V11 server/dialogue/profile integration','tools/test_v11_integration.py'),
        ('Conditional dialogue module','tools/test_v11_dialogue.py'),
        ('Six articulated rigs and actual NPC director','tools/test_v11_npcs.py'),
        ('Native ocean bootstrap and circuit-light adapter','tools/test_v11_environment.py'),
        ('Single HUD / procedures / dialogue / mobile layouts','tools/test_v10_client.py'),
    ]:
        run=subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,text=True,capture_output=True,timeout=180)
        passed=run.returncode==0
        results.append({'name':label,'passed':passed,'stdout':run.stdout,'stderr':run.stderr})
        print(('PASS' if passed else 'FAIL')+': '+label,flush=True)
        if not passed:print(run.stdout+run.stderr,flush=True)
    with tempfile.TemporaryDirectory(prefix='null-v11-') as directory:
        output=Path(directory)/MAP.name
        run=subprocess.run([sys.executable,str(ROOT/'tools/build_v11.py'),'--output',str(output)],cwd=ROOT,text=True,capture_output=True,timeout=90)
        same=run.returncode==0 and sha(output)==sha(MAP)
        results.append({'name':'Byte-identical repeat build','passed':same,'stderr':run.stderr})
        print(('PASS' if same else 'FAIL')+': byte-identical build',flush=True)
    from lupa import LuaRuntime
    tree=ET.parse(MAP)
    lua=LuaRuntime(unpack_returned_tuples=True)
    modules={e.findtext("Properties/string[@name='Name']"):e for e in tree.iter('Item') if e.get('class')=='ModuleScript'}
    generated=lua.execute(modules['Content'].findtext("Properties/ProtectedString[@name='Source']"))
    expected=json.loads((ROOT/'tools/v11_content.json').read_text())
    def equal(actual,wanted):
        if isinstance(wanted,dict):return set(actual.keys())==set(wanted) and all(equal(actual[k],v) for k,v in wanted.items())
        if isinstance(wanted,list):return set(actual.keys())==set(range(1,len(wanted)+1)) and all(equal(actual[i+1],v) for i,v in enumerate(wanted))
        return actual==wanted
    results.append({'name':'Generated Content equals authored narrative','passed':equal(generated,expected)})
    # Run the actual generated ShipConfig through the real environment module.
    from test_v11_environment import fixture
    env=fixture()
    env.globals()._actualConfig=env.execute(modules['ShipConfig'].findtext("Properties/ProtectedString[@name='Source']"))
    state=env.globals()._env.setup(env.globals()._actualConfig)
    ocean_ok=state.waterReady and state.filled==len(env.globals()._actualConfig.water.fill_boxes)
    results.append({'name':'Actual embedded ocean fill configuration accepted','passed':bool(ocean_ok),'fill_boxes':state.filled})
    report={'result':'PASS' if all(r['passed'] for r in results) else 'FAIL',
            'map_sha256':sha(MAP),'checks':results,
            'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'src').glob('*.luau'))},
            'limitations':'Real Lua executed with Roblox API doubles. No Studio rendering, character physics, navigation mesh, animation replication, terrain voxel performance, real networking, live DataStore or FPS test.'}
    (ROOT/'artifacts/TEST_RESULTS_V11.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if report['result']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
