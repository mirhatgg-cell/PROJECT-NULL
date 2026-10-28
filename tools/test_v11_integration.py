"""Execute the actual V11 server and dialogue with controlled Roblox API doubles.

The established experiment core and dialogue module are real source. Director
and ocean setup are dependency spies here; their own tests execute those actual
modules. No navigation, rig physics, rendering or live DataStore is claimed.
"""
from __future__ import annotations

import json

from test_v10_server_runtime import (ROOT, SEED, fixture, open_station,
                                     python_value, send, snapshot, state)


def options(payload):
    return {item.id for item in payload.options.values()}


def dialogue(lua):
    return lua.globals().last_message('dialogue', lua.globals()._player)


def test_branching_dialogue_preserves_conversation_greeting():
    content = json.loads((ROOT/'tools/v11_content.json').read_text())
    lua = fixture()
    open_station(lua, '_npc')
    first = dialogue(lua)
    assert first.node == 'start' and first.text == content['dialogues']['TECH']['first']
    assert {'job','world','incident','close'} <= options(first)
    assert 'evidence' not in options(first) and 'after' not in options(first)
    lua.globals().advance(2.1)
    assert dialogue(lua).text == first.text, 'First greeting changed to repeat while reading'
    open_station(lua, '_npc')
    assert dialogue(lua).text == first.text, 'Duplicate prompt restarted an active conversation'
    send(lua, 'dialogue', 'job')
    assert dialogue(lua).node == 'job' and dialogue(lua).text != first.text
    send(lua, 'dialogue', 'back')
    assert dialogue(lua).node == 'start' and dialogue(lua).text == first.text
    send(lua, 'dialogue', 'close')
    assert dialogue(lua).closed and snapshot(lua).context is None
    open_station(lua, '_npc')
    assert dialogue(lua).text == content['dialogues']['TECH']['repeat']


def test_dialogue_conditions_are_server_owned():
    lua = fixture()
    open_station(lua, '_npc')
    before = dialogue(lua)
    send(lua, 'dialogue', 'evidence')
    assert dialogue(lua).node == before.node and 'evidence' not in options(dialogue(lua))
    # A forged nested client table cannot inject a node, document or completion.
    lua.execute("request('dialogue',{node='start',choice='evidence',documents={DOC_P03_CORRECTION=true}})")
    assert dialogue(lua).node == 'start'
    send(lua, 'dialogue', 'after')
    assert dialogue(lua).node == 'start' and not snapshot(lua).profile.completed.P03
    open_station(lua, '_correctionDocument')
    open_station(lua, '_npc')
    assert 'evidence' in options(dialogue(lua)) and 'after' not in options(dialogue(lua))
    send(lua, 'dialogue', 'evidence')
    assert dialogue(lua).node == 'evidence'
    assert '03:14' in dialogue(lua).text or 'журнал' in dialogue(lua).text.lower()
    assert snapshot(lua).profile.documents.DOC_P03_CORRECTION
    # A hidden branch remains rejected even after visiting a different branch.
    send(lua, 'dialogue', 'after')
    assert dialogue(lua).node == 'evidence'


def test_dialogue_access_close_death_and_range():
    lua = fixture()
    send(lua, 'dialogue', 'job')
    assert dialogue(lua) is None, 'Remote choice started a conversation without an NPC prompt'
    open_station(lua, '_npc')
    before = dialogue(lua).node
    send(lua, 'dialogue', 'job', player=lua.globals()._other)
    assert dialogue(lua).node == before, 'Another player selected the first player\'s branch'
    lua.execute('_rayTarget=_wall')
    send(lua, 'dialogue', 'job')
    assert dialogue(lua).node != 'job', 'A dialogue choice was accepted through a wall'
    lua.globals().advance(1.2)
    assert dialogue(lua).closed and snapshot(lua).context is None
    open_station(lua, '_npc')
    lua.execute('_head.CFrame=CFrame.new(1000,0,0)')
    lua.globals().advance(1.2)
    assert dialogue(lua).closed, 'Walking away left the conversation open'
    open_station(lua, '_npc')
    lua.execute('_humanoid.Health=0')
    lua.globals().advance(1.2)
    assert dialogue(lua).closed, 'Death left the dialogue input active'
    assert len(lua.globals()._taskErrors) == 0


def test_dialogue_choice_cooldown_and_close_action():
    lua = fixture()
    open_station(lua, '_npc')
    send(lua, 'dialogue', 'job', delay=.3)
    assert dialogue(lua).node == 'job'
    # Same-frame input cannot step multiple pages or reopen a closed context.
    lua.execute("request('dialogue','back');request('dialogue','world')")
    assert dialogue(lua).node == 'job'
    send(lua, 'close')
    assert snapshot(lua).context is None
    last_calls = list(lua.globals()._directorCalls.talk.values())
    assert last_calls and last_calls[-1].active is False
    count = len(lua.globals()._messages)
    send(lua, 'dialogue', 'world')
    assert not any(m.kind == 'dialogue' and m.payload.node == 'world'
                   for m in list(lua.globals()._messages.values())[count:])


def test_document_gates_and_private_content():
    setup = r'''
_gated=fixture_station('CommsLog','document','DOC_COMMS_LOG',180)
_index=fixture_station('Index','document','DOC_ADMIN_INDEX',190)
_late=fixture_station('Observation','document','DOC_OBSERVATION',200)
'''
    lua = fixture(setup)
    before = snapshot(lua)
    encoded = json.dumps(python_value(before), ensure_ascii=False)
    source = json.loads((ROOT/'tools/v11_content.json').read_text())
    late_body = next(d['body'] for d in source['documents'] if d['id'] == 'DOC_OBSERVATION')
    assert late_body not in encoded
    open_station(lua, '_gated')
    assert not snapshot(lua).profile.documents.DOC_COMMS_LOG
    open_station(lua, '_late')
    assert not snapshot(lua).profile.documents.DOC_OBSERVATION
    open_station(lua, '_correctionDocument')
    open_station(lua, '_gated')
    assert snapshot(lua).profile.documents.DOC_COMMS_LOG
    open_station(lua, '_late')
    assert not snapshot(lua).profile.documents.DOC_OBSERVATION
    open_station(lua, '_index')
    open_station(lua, '_late')
    assert snapshot(lua).profile.documents.DOC_OBSERVATION
    assert lua.globals().last_message('document', lua.globals()._player).body == late_body


def test_met_staff_uses_existing_save_merge():
    lua = fixture(SEED + "_store.u_101.metStaff={ARCHIVIST=true,unknownStaff=true}")
    before = snapshot(lua).profile
    assert before.metStaff.ARCHIVIST and before.metStaff.unknownStaff is None
    open_station(lua, '_npc')
    send(lua, 'save')
    saved = lua.globals()._store.u_101
    assert saved.metStaff.TECH and saved.metStaff.ARCHIVIST
    assert saved.documents.DOC_P03_LOG and saved.completed.P02 and saved.attempts.P01 == 3
    assert saved.records[1].id == 'existing-record'
    assert lua.globals()._storeName == 'PROJECT_NULL_PROGRESS_V10', 'V11 forked the save store'
    # A delayed load cannot erase a first contact made during the request.
    lua = fixture(SEED + "_store.u_101.metStaff={ARCHIVIST=true};_getDelay=4")
    open_station(lua, '_npc')
    lua.globals().advance(4.5)
    send(lua, 'save')
    assert lua.globals()._store.u_101.metStaff.TECH and lua.globals()._store.u_101.metStaff.ARCHIVIST
    lua = fixture(SEED + '_getFailure=true')
    open_station(lua, '_npc')
    send(lua, 'save')
    lua.globals().advance(61)
    assert lua.globals()._updates == 0 and lua.globals()._writes == 0


def test_director_and_ocean_lifecycle_wiring():
    lua = fixture()
    calls = lua.globals()._directorCalls
    assert calls.new == 1 and lua.globals()._environmentCalls.setup == 1
    open_station(lua, '_npc')
    assert any(c.id == 'TECH' and c.active for c in calls.talk.values())
    talk_count = len(calls.talk)
    lua.globals().advance(47)
    assert dialogue(lua).closed is not True
    assert calls.step > 0 and len(calls.talk) > talk_count + 20, 'Open conversation did not renew its NPC talk lease'
    send(lua, 'close')
    assert list(calls.talk.values())[-1].active is False
    lua.globals().close_server()
    lua.globals().advance(.2)
    assert calls.destroy == 1 and lua.globals()._environmentCalls.destroy == 1
    assert len(lua.globals()._taskErrors) == 0


def main():
    checks = [test_branching_dialogue_preserves_conversation_greeting,
              test_dialogue_conditions_are_server_owned,
              test_dialogue_access_close_death_and_range,
              test_dialogue_choice_cooldown_and_close_action,
              test_document_gates_and_private_content,
              test_met_staff_uses_existing_save_merge,
              test_director_and_ocean_lifecycle_wiring]
    for check in checks:
        check()
        print('PASS:', check.__name__)
    print('V11 integration: actual server, experiment core and dialogue passed; '
          'NPC Director and ocean bootstrap were lifecycle spies, not engine simulations.')


if __name__ == '__main__':
    main()
