"""Execute the actual V11 dialogue evaluator and verify authored evidence gates."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


def to_lua(lua, value):
    if isinstance(value, dict):
        return lua.table_from({key: to_lua(lua, item) for key, item in value.items()})
    if isinstance(value, list):
        return lua.table_from([to_lua(lua, item) for item in value])
    return value


def first(result):
    return result[0] if isinstance(result, tuple) else result


def option_ids(payload):
    return [payload.options[i].id for i in range(1, len(payload.options) + 1)]


def main():
    content = json.loads((ROOT / 'tools/v11_content.json').read_text())
    old = json.loads((ROOT / 'tools/v10_content.json').read_text())
    current_documents = {document['id']: document for document in content['documents']}
    assert len(current_documents) == 29
    for document in old['documents']:
        assert all(current_documents[document['id']][key] == value for key, value in document.items())
    assert len(content['staff']) == len(content['dialogues']) == 6
    for document in content['documents'][19:]:
        assert all(document.get(key) for key in ('id', 'title', 'author', 'period', 'room', 'body', 'claims'))
        assert isinstance(document['hypotheses'], list)
    print('PASS: all 19 legacy documents preserved; 10 new documents have provenance and bounded claims')

    lua = LuaRuntime(unpack_returned_tuples=True)
    dialogue = lua.execute((ROOT / 'src/Dialogue_V11.luau').read_text())
    dialogue.configure(to_lua(lua, content))
    profile = {'documents': {}, 'completed': {}, 'metStaff': {}}
    snapshot = {'phase': 'idle'}

    for staff_id in content['staff']:
        p, s = to_lua(lua, profile), to_lua(lua, snapshot)
        opened = first(dialogue.open(staff_id, p, s))
        assert opened.id == staff_id and opened.node == 'start'
        assert opened.name == content['staff'][staff_id]['name']
        assert opened.text == content['dialogues'][staff_id]['first']
        assert 'job' in option_ids(opened) and 'evidence' not in option_ids(opened)
        assert 'after' not in option_ids(opened)
        # No graph structure, conditions, or hidden answers are sent to the UI.
        assert set(opened.keys()) == {'id', 'argument', 'name', 'role', 'node', 'text', 'options'}
        job = first(dialogue.choose(staff_id, 'start', 'job', p, s))
        assert job.node == 'job' and job.text == content['dialogues'][staff_id]['nodes']['job']['text']
        assert option_ids(job) == ['back', 'close']
        back = first(dialogue.choose(staff_id, 'job', 'back', p, s))
        assert back.node == 'start'
        closed = first(dialogue.choose(staff_id, 'job', 'close', p, s))
        assert closed.closed and closed.node == 'closed' and len(closed.options) == 0
        p.metStaff[staff_id] = True
        repeated = first(dialogue.open(staff_id, p, s))
        assert repeated.text == content['dialogues'][staff_id]['repeat']
        assert first(dialogue.choose(staff_id, 'start', 'evidence', p, s)) is None
        assert first(dialogue.choose(staff_id, 'start', 'after', p, s)) is None
        p.documents.DOC_P03_CORRECTION = True
        unlocked = first(dialogue.open(staff_id, p, s))
        assert 'evidence' in option_ids(unlocked)
        assert first(dialogue.choose(staff_id, 'start', 'evidence', p, s)).node == 'evidence'
        p.completed.P03 = True
        assert 'after' in option_ids(first(dialogue.open(staff_id, p, s)))
    print('PASS: all six staff support first/repeat meetings, topics, return, close and private evidence branches')

    for phase in ('idle', 'prepared', 'running', 'completed', 'failed'):
        result = first(dialogue.choose('ENGINEER', 'start', 'world',
                      to_lua(lua, profile), to_lua(lua, {'phase': phase})))
        assert result is not None and result.node == 'world'
        if phase == 'running':
            assert 'идёт серия' in result.text
        elif phase == 'failed':
            assert 'остановлена' in result.text
    print('PASS: dialogue reactions follow the current procedure phase')

    p, s = to_lua(lua, profile), to_lua(lua, snapshot)
    for malformed in (None, '', 'x' * 41, {}, 123):
        assert first(dialogue.choose('TECH', 'start', to_lua(lua, malformed), p, s)) is None
    assert first(dialogue.open('MISSING', p, s)) is None
    assert first(dialogue.choose('TECH', 'MISSING', 'job', p, s)) is None
    assert first(dialogue.choose('TECH', 'job', 'evidence', p, s)) is None
    assert not dialogue.allowed(to_lua(lua, {'any': []}), p, s)
    assert not dialogue.allowed(to_lua(lua, {'all': []}), p, s)
    lua.globals()._dialogue, lua.globals()._profile, lua.globals()._snapshot = dialogue, p, s
    assert not lua.execute('local rule={};rule.all={rule};return _dialogue.allowed(rule,_profile,_snapshot)')
    print('PASS: forged nodes/options, malformed choices and cyclic/deep rules are rejected')

    docs = to_lua(lua, current_documents)
    assert dialogue.canRead(docs.DOC_CREW_SHIFT, p, s)
    assert not dialogue.canRead(docs.DOC_COMMS_LOG, p, s)
    assert not dialogue.canRead(docs.DOC_OBSERVATION, p, s)
    p.documents.DOC_P03_CORRECTION = True
    assert dialogue.canRead(docs.DOC_COMMS_LOG, p, s)
    assert not dialogue.canRead(docs.DOC_OBSERVATION, p, s)
    p.documents.DOC_ADMIN_INDEX = True
    assert dialogue.canRead(docs.DOC_OBSERVATION, p, s)
    p.documents.DOC_P03_CORRECTION = None
    p.documents.DOC_ADMIN_INDEX = None
    p.completed.P03 = True
    assert dialogue.canRead(docs.DOC_COMMS_LOG, p, s) and dialogue.canRead(docs.DOC_OBSERVATION, p, s)
    print('PASS: later documents need context, with two valid exploration routes')

    # The pure graph evaluator does not grant documents, meetings or completions.
    untouched = copy.deepcopy(profile)
    lua_profile = to_lua(lua, profile)
    dialogue.open('TECH', lua_profile, s)
    assert len(lua_profile.documents) == 0 and len(lua_profile.metStaff) == 0 and len(lua_profile.completed) == 0
    assert profile == untouched
    print('PASS: evaluator does not mutate profile or impersonate a completed game action')


if __name__ == '__main__':
    main()
