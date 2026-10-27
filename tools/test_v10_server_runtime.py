"""Exercise the real V10 server and experiment module in Lua API doubles.

Requires lupa==2.6. These are logic/integration checks, not Studio physics,
networking, rendering or live DataStore acceptance tests.
"""
from __future__ import annotations

import json
from pathlib import Path

from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


def lua_value(lua, value):
    if isinstance(value, dict):
        return lua.table_from({key: lua_value(lua, item) for key, item in value.items()})
    if isinstance(value, list):
        return lua.table_from([lua_value(lua, item) for item in value])
    return value


def python_value(value):
    if hasattr(value, "items"):
        return {key: python_value(item) for key, item in value.items()}
    return value


def fixture(preload: str | None = None):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute((ROOT / "tools/v10_runtime_mock.lua").read_text())
    lua.globals()._content = lua_value(lua, json.loads((ROOT / "tools/v10_content.json").read_text()))
    lua.globals()._engine = lua.execute((ROOT / "src/ExperimentCore_V10.luau").read_text())
    # Observe actual state created by the real constructor; no transition is mocked.
    lua.execute("local new=_engine.new;_engine.new=function(...) _engineState=new(...);return _engineState end")
    if preload:
        lua.execute(preload)
    lua.execute((ROOT / "src/ProjectNullServer_V10.server.luau").read_text())
    lua.execute("flush_tasks()")
    return lua


def state(lua):
    return lua.globals()._engineState


def send(lua, action: str, arg=None, player=None, delay=.6):
    lua.globals().advance(delay)
    lua.globals().request(action, arg, player or lua.globals()._player)


def open_station(lua, station="_console", player=None):
    lua.globals().advance(.6)
    lua.globals().interact(lua.globals()[station], player or lua.globals()._player)


def start(lua, station="_console"):
    open_station(lua, station)
    send(lua, "calibrate")
    assert state(lua).phase == "prepared"
    lua.globals().advance(2.2)
    send(lua, "start")
    assert state(lua).phase == "running"


def snapshot(lua, player=None):
    lua.globals().advance(1.1)
    result = lua.globals().last_message("snapshot", player or lua.globals()._player)
    assert result is not None
    return result


def test_prompt_authorization():
    for setup in (
        "_rayTarget=_wall",
        "_rayTarget=nil",
        "_rayTarget=_console;_head.CFrame=CFrame.new(100,0,0)",
        "_rayTarget=_console;_humanoid.Health=0",
        "_rayTarget=_console;_console.V10_Prompt.Enabled=false",
    ):
        lua = fixture()
        lua.execute(setup + ";_console.V10_Prompt.Triggered:Fire(_player);flush_tasks()")
        assert state(lua).owner is None, setup
        assert state(lua).phase == "idle", setup
    lua = fixture()
    open_station(lua)
    assert state(lua).owner == 101 and state(lua).experiment == "P01"


def test_remote_context_and_owner():
    lua = fixture()
    send(lua, "calibrate")
    assert state(lua).phase == "idle", "Remote mutation without local console"
    open_station(lua)
    send(lua, "select", "P02")
    assert state(lua).experiment == "P01", "A console cannot impersonate another experiment"
    lua.execute("_rayTarget=_wall")
    send(lua, "calibrate")
    assert state(lua).phase == "idle", "Terminal action through a wall"
    lua.execute("_rayTarget=_console;_head.CFrame=CFrame.new(100,0,0)")
    send(lua, "calibrate")
    assert state(lua).phase == "idle", "Terminal action outside activation distance"
    open_station(lua)
    send(lua, "calibrate")
    assert state(lua).phase == "prepared"
    open_station(lua, player=lua.globals()._other)
    send(lua, "abort", player=lua.globals()._other)
    assert state(lua).phase == "prepared", "Another player aborted an owned experiment"
    send(lua, "reset", player=lua.globals()._other)
    assert state(lua).owner == 101
    # A modal close preserves the local authorization anchor, not a global bypass.
    lua.execute("place_player(_player,_console)")
    send(lua, "close")
    send(lua, "start", delay=2.3)
    assert state(lua).phase == "running"
    send(lua, "abort")
    assert state(lua).phase == "failed"
    send(lua, "reset")
    assert state(lua).phase == "idle" and state(lua).owner is None


def test_untrusted_payloads_and_supply():
    lua = fixture()
    open_station(lua)
    send(lua, "calibrate")
    supply = state(lua).supply
    for action, arg in (("resupply", None), ("supply", None), ("cooling", False), ("medical", None), ("repair", None)):
        send(lua, action, arg)
    assert state(lua).supply == supply, "Remote resource actions bypassed station authorization"
    assert state(lua).cooling is True
    send(lua, "A" * 10000)
    lua.execute("request({},{});request('respond',{deep={deep={}}});request('respond',string.rep('x',50000))")
    assert state(lua).phase == "prepared" and state(lua).supply == supply
    send(lua, "abort")
    send(lua, "reset")
    open_station(lua, "_supply")
    send(lua, "supply")
    after = state(lua).supply
    assert after == 12
    for _ in range(20):
        lua.globals()._supply.V10_Prompt.Triggered.Fire(lua.globals()._supply.V10_Prompt.Triggered, lua.globals()._player)
    assert state(lua).supply == after
    assert len(lua.globals()._taskErrors) == 0


def test_documents_are_discovered_locally():
    lua = fixture()
    public = python_value(snapshot(lua))
    encoded = json.dumps(public, ensure_ascii=False)
    assert "DOC_P03_LOG" not in encoded
    content = json.loads((ROOT / "tools/v10_content.json").read_text())
    secret = next(d["body"] for d in content["documents"] if d["id"] == "DOC_P03_LOG")
    assert secret not in encoded
    lua.execute("place_player(_player,_document);_rayTarget=_wall;_document.V10_Prompt.Triggered:Fire(_player)")
    assert lua.globals().last_message("document", lua.globals()._player) is None
    open_station(lua, "_document")
    document = lua.globals().last_message("document", lua.globals()._player)
    assert document.id == "DOC_P01_PROTOCOL" and len(document.body) > 20
    profile = snapshot(lua).profile
    assert "DOC_P01_PROTOCOL" in json.dumps(python_value(profile), ensure_ascii=False)
    assert "DOC_P03_LOG" not in json.dumps(python_value(profile), ensure_ascii=False)


def test_circuit_trip_death_and_bounded_damage():
    lua = fixture()
    start(lua)
    lua.execute("_circuits.AcousticAmplifiers.Value=false")
    lua.globals().advance(.3)
    assert state(lua).phase == "failed"
    assert len(lua.globals()._damage) == 0
    lua = fixture()
    start(lua)
    lua.execute("_humanoid.Health=0")
    lua.globals().advance(.3)
    assert state(lua).phase == "failed", "Dead owner left the apparatus running"
    lua = fixture()
    start(lua)
    lua.globals().advance(14)
    assert state(lua).phase == "failed"
    damage = list(lua.globals()._damage.values())
    assert len(damage) == 1 and 0 < damage[0].amount <= 12
    health = lua.globals()._humanoid.Health
    lua.globals().advance(10)
    assert lua.globals()._humanoid.Health == health, "Failure damage repeated indefinitely"


def test_staff_reacts_to_actual_state():
    lua = fixture()
    open_station(lua, "_npc")
    initial = lua.globals().last_message("dialogue", lua.globals()._player)
    assert initial is not None and initial.name and initial.text
    start(lua)
    lua.globals().advance(14)
    open_station(lua, "_npc")
    failed = lua.globals().last_message("dialogue", lua.globals()._player)
    assert failed is not None and failed.text != initial.text, "Staff ignores failed protocol state"


def test_p02_requires_physical_sensor():
    lua = fixture()
    start(lua, "_console2")
    lua.globals().advance(1.7)
    send(lua, "respond", "center")
    assert state(lua).round == 1 and state(lua).phase == "running", "P02 accepted remote-only route choice"
    open_station(lua, "_laneCenter", lua.globals()._other)
    assert state(lua).round == 1, "Another player completed the owner's physical task"
    # Correct lane cannot be triggered through a wall, even with a forged Prompt event.
    lua.execute("place_player(_player,_laneCenter);_rayTarget=_wall;_laneCenter.V10_Prompt.Triggered:Fire(_player)")
    assert state(lua).round == 1
    open_station(lua, "_laneCenter")
    assert state(lua).round == 2 and state(lua).phase == "running"
    lua.globals().advance(1.6)
    open_station(lua, "_laneLeft")
    assert state(lua).round == 3 and state(lua).phase == "running"


def test_p04_observes_real_movement():
    lua = fixture()
    start(lua, "_console4")
    lua.globals().advance(4.1)
    send(lua, "respond", "hold")
    assert state(lua).round == 2
    lua.globals().advance(2.1)
    send(lua, "respond", "move")
    assert state(lua).round == 2, "Claiming movement without actual displacement was accepted"
    lua.execute("_player.Character.HumanoidRootPart.CFrame=CFrame.new(26,0,-4)")
    lua.globals().advance(.1)
    send(lua, "respond", "move", delay=.1)
    assert state(lua).round == 3
    lua.globals().advance(2.1)
    lua.execute("_player.Character.HumanoidRootPart.CFrame=CFrame.new(27,0,-4)")
    lua.globals().advance(.1)
    assert state(lua).phase == "failed", "Moving under open optics did not stop P04"
    assert 0 < sum(d.amount for d in lua.globals()._damage.values()) <= 12


SEED = r'''
_store.u_101={version=10,documents={DOC_P03_LOG=true},completed={P02=true},attempts={P01=3},
records={{id='existing-record',experiment='P02',title='Preserved',status='completed',result='old',timestamp=1}}}
'''


def test_persistence_merge_and_idempotent_save():
    lua = fixture(SEED)
    loaded = snapshot(lua).profile
    assert loaded.documents.DOC_P03_LOG and loaded.completed.P02 and loaded.attempts.P01 == 3
    open_station(lua, "_document")
    start(lua)
    send(lua, "abort")
    send(lua, "save")
    saved = lua.globals()._store.u_101
    assert saved.documents.DOC_P03_LOG and saved.documents.DOC_P01_PROTOCOL and saved.completed.P02
    assert saved.attempts.P01 == 4 and len(saved.records) == 2
    assert len({record.id for record in saved.records.values()}) == 2
    writes = lua.globals()._writes
    send(lua, "save", delay=11)
    assert lua.globals()._writes == writes and lua.globals()._store.u_101.attempts.P01 == 4
    assert "сохранён" in snapshot(lua).profile.saveStatus.lower()


def test_persistence_read_failure_never_overwrites():
    lua = fixture(SEED + "_getFailure=true")
    open_station(lua, "_document")
    send(lua, "save")
    lua.globals().advance(61)
    assert lua.globals()._writes == 0 and lua.globals()._updates == 0
    assert lua.globals()._store.u_101.documents.DOC_P03_LOG
    assert not lua.globals()._store.u_101.documents.DOC_P01_PROTOCOL
    assert "сохранён" not in snapshot(lua).profile.saveStatus.lower()
    lua.execute("_getFailure=false")
    send(lua, "save")  # Successful retry loads the unknown profile first.
    send(lua, "save", delay=11)
    assert lua.globals()._store.u_101.documents.DOC_P03_LOG
    assert lua.globals()._store.u_101.documents.DOC_P01_PROTOCOL


def test_persistence_delayed_load_merges_discovery():
    lua = fixture(SEED + "_getDelay=5")
    open_station(lua, "_document")
    assert snapshot(lua).profile.documents.DOC_P01_PROTOCOL
    lua.globals().advance(5)
    loaded = snapshot(lua).profile
    assert loaded.documents.DOC_P03_LOG and loaded.documents.DOC_P01_PROTOCOL
    send(lua, "save")
    assert lua.globals()._store.u_101.documents.DOC_P03_LOG
    assert lua.globals()._store.u_101.documents.DOC_P01_PROTOCOL


def test_persistence_write_failure_and_autosave():
    lua = fixture(SEED + "_updateFailure=true")
    open_station(lua, "_document")
    send(lua, "save")
    assert lua.globals()._writes == 0
    assert "ошибка" in snapshot(lua).profile.saveStatus.lower()
    lua.execute("_updateFailure=false")
    lua.globals().advance(61)
    assert lua.globals()._writes == 1
    assert lua.globals()._store.u_101.documents.DOC_P03_LOG
    assert lua.globals()._store.u_101.documents.DOC_P01_PROTOCOL


def test_persistence_departure_and_shutdown():
    lua = fixture(SEED)
    open_station(lua, "_document")
    start(lua)
    lua.globals().remove_player(lua.globals()._player)
    assert state(lua).phase == "idle" and state(lua).owner is None
    saved = lua.globals()._store.u_101
    assert saved.documents.DOC_P01_PROTOCOL and saved.attempts.P01 == 4
    assert len(saved.records) == 2, "Departure interruption record was not persisted"
    lua = fixture(SEED)
    open_station(lua, "_document")
    lua.globals().close_server()
    lua.globals().advance(.3)
    assert lua.globals()._store.u_101.documents.DOC_P01_PROTOCOL


def test_delayed_load_departure_and_shutdown():
    for mode in ("departure", "shutdown"):
        lua = fixture(SEED + "_getDelay=5")
        open_station(lua, "_document")
        if mode == "departure":
            lua.globals().remove_player(lua.globals()._player)
        else:
            lua.globals().close_server()
        assert lua.globals()._writes == 0
        lua.globals().advance(9)
        saved = lua.globals()._store.u_101
        assert lua.globals()._writes == 1, mode
        assert saved.documents.DOC_P01_PROTOCOL and saved.documents.DOC_P03_LOG, mode


def test_completion_record_and_pending_save_changes():
    lua = fixture(SEED)
    start(lua)
    for answer in ("A", "B", "reject", "reject", "C"):
        lua.globals().advance(2.1)
        send(lua, "respond", answer, delay=.1)
    assert state(lua).phase == "completed"
    profile = snapshot(lua).profile
    assert profile.completed.P01 and profile.completed.P02
    assert profile.records[1].status == "completed" and profile.attempts.P01 == 4
    lua.execute("_updateDelay=3")
    send(lua, "save")
    # Discover a new document while UpdateAsync is yielding with an older payload.
    open_station(lua, "_document")
    lua.globals().advance(3.2)
    assert not lua.globals()._store.u_101.documents.DOC_P01_PROTOCOL
    assert snapshot(lua).profile.documents.DOC_P01_PROTOCOL
    lua.execute("_updateDelay=0")
    send(lua, "save", delay=11)
    saved = lua.globals()._store.u_101
    assert saved.completed.P01 and saved.completed.P02 and saved.documents.DOC_P01_PROTOCOL
    assert saved.attempts.P01 == 4 and len(saved.records) == 2


def test_offline_status_is_honest():
    lua = fixture("game.GameId=0")
    open_station(lua, "_document")
    send(lua, "save")
    status = snapshot(lua).profile.saveStatus.lower()
    assert "локаль" in status and "сохранён" not in status
    assert lua.globals()._writes == 0


def test_p03_requires_discovered_independent_evidence():
    lua = fixture()
    open_station(lua, "_console3")
    missing = snapshot(lua).evidenceRequired
    assert {item.id for item in missing.values()} == {"DOC_P03_LOG", "DOC_P03_CORRECTION"}
    for item in missing.values():
        assert set(item.keys()) == {"id", "title", "room"}, "Missing evidence leaked undiscovered document content"
    send(lua, "calibrate")
    assert state(lua).phase == "idle"
    open_station(lua, "_secretDocument")
    open_station(lua, "_console3")
    missing = snapshot(lua).evidenceRequired
    assert len(missing) == 1 and missing[1].id == "DOC_P03_CORRECTION"
    send(lua, "calibrate")
    assert state(lua).phase == "idle", "One of two contradictory records incorrectly unlocked reconstruction"
    open_station(lua, "_correctionDocument")
    open_station(lua, "_console3")
    assert snapshot(lua).evidenceReady is True
    send(lua, "calibrate")
    assert state(lua).phase == "prepared"


def test_physical_experiment_feedback():
    lua = fixture()
    start(lua)
    assert not any(part.PointLight.Enabled for part in lua.globals()._p01Lights.values())
    lua.globals().advance(2.2)
    assert lua.globals()._p01Lights.A.PointLight.Enabled
    assert not lua.globals()._p01Lights.B.PointLight.Enabled
    assert not lua.globals()._p01Lights.C.PointLight.Enabled
    assert "answer" not in python_value(snapshot(lua).cue)
    send(lua, "respond", "A", delay=.1)
    assert not any(part.PointLight.Enabled for part in lua.globals()._p01Lights.values())
    lua.globals().advance(2.2)
    assert lua.globals()._p01Lights.B.PointLight.Enabled
    assert not lua.globals()._p01Lights.A.PointLight.Enabled

    lua = fixture()
    start(lua, "_console2")
    expected = {"left": ("БЛИЗКО", "9.2"), "center": ("ДАЛЕКО", "6.0"), "right": ("ЦЕЛЬ", "3.5")}
    for lane, (sign, distance) in expected.items():
        text = lua.globals()._p02Readouts[lane].Text
        assert sign in text and distance + " stud" in text and "ЗАДАНИЕ: 6.0" in text

    lua = fixture()
    assert lua.globals()._shutter.Position.Y == 3
    start(lua, "_console4")
    assert lua.globals()._shutter.Position.Y == 5, "Tracking optics did not retract physical shutter"
    lua.globals().advance(4.1)
    send(lua, "respond", "hold")
    assert state(lua).cue.observerMode == "occluded"
    assert lua.globals()._shutter.Position.Y == 3, "Occluded observer did not close physical shutter"

    lua = fixture()
    start(lua, "_console5")
    assert "10.08" in lua.globals()._p05Reference.Text and "СТАБИЛЕН" in lua.globals()._p05Reference.Text
    lua.globals().advance(1.7)
    send(lua, "respond", "accept", delay=.1)
    assert "13.10" in lua.globals()._p05Reference.Text, "Independent reference display failed to follow actual reading"


def test_unused_console_reservation_releases_safely():
    lua = fixture()
    open_station(lua)
    lua.globals().advance(20)
    assert state(lua).owner == 101, "Occupied console reservation expired"
    lua.execute("_head.CFrame=CFrame.new(100,0,0)")
    lua.globals().advance(17)
    assert state(lua).owner is None and state(lua).phase == "idle"
    assert state(lua).attempts == 0 and len(state(lua).records) == 0 and len(lua.globals()._damage) == 0
    open_station(lua, "_console2", lua.globals()._other)
    assert state(lua).owner == 202 and state(lua).experiment == "P02"
    lua = fixture()
    open_station(lua)
    send(lua, "calibrate")
    lua.execute("_head.CFrame=CFrame.new(100,0,0)")
    lua.globals().advance(17)
    assert state(lua).owner == 101 and state(lua).phase == "prepared", "Idle reservation timeout interrupted a prepared protocol"


def test_terminal_reservation_release_preserves_results():
    for terminal in ("completed", "failed"):
        lua = fixture()
        start(lua)
        if terminal == "completed":
            for answer in ("A", "B", "reject", "reject", "C"):
                lua.globals().advance(2.1)
                send(lua, "respond", answer, delay=.1)
        else:
            lua.globals().advance(2.1)
            send(lua, "respond", "B", delay=.1)
        assert state(lua).phase == terminal
        before = snapshot(lua).profile
        record_id = before.records[1].id
        lua.execute("_head.CFrame=CFrame.new(100,0,0)")
        lua.globals().advance(17)
        assert state(lua).phase == "idle" and state(lua).owner is None, terminal
        profile = snapshot(lua).profile
        assert len(profile.records) == 1 and profile.records[1].id == record_id, terminal
        assert profile.records[1].status == terminal and profile.attempts.P01 == 1, terminal
        if terminal == "completed":
            assert profile.completed.P01, "Automatic release erased an earned completion"


def test_studio_negative_userids_play_without_persistent_writes():
    lua = fixture("_player.UserId=-1;_other.UserId=-2;_isStudio=true")
    assert lua.globals()._reads == 0 and lua.globals()._updates == 0
    start(lua)
    assert state(lua).owner == -1
    lua.globals().advance(2.1)
    open_station(lua, player=lua.globals()._other)
    send(lua, "respond", "A", player=lua.globals()._other, delay=.1)
    assert state(lua).owner == -1 and state(lua).round == 1 and state(lua).phase == "running"
    lua.execute("place_player(_player,_console)")
    send(lua, "respond", "A", delay=.1)
    assert state(lua).round == 2
    for answer in ("B", "reject", "reject", "C"):
        lua.globals().advance(2.1)
        send(lua, "respond", answer, delay=.1)
    assert state(lua).phase == "completed"
    profile = snapshot(lua).profile
    assert profile.completed.P01 and profile.attempts.P01 == 1
    send(lua, "save")
    lua.globals().advance(61)
    status = snapshot(lua).profile.saveStatus.lower()
    assert "локаль" in status and "сохранён" not in status
    assert lua.globals()._reads == 0 and lua.globals()._updates == 0 and lua.globals()._writes == 0


def main():
    checks = [test_prompt_authorization, test_remote_context_and_owner,
              test_untrusted_payloads_and_supply, test_documents_are_discovered_locally,
              test_circuit_trip_death_and_bounded_damage, test_staff_reacts_to_actual_state,
              test_p02_requires_physical_sensor, test_p04_observes_real_movement,
              test_persistence_merge_and_idempotent_save,
              test_persistence_read_failure_never_overwrites,
              test_persistence_delayed_load_merges_discovery,
              test_persistence_write_failure_and_autosave,
              test_persistence_departure_and_shutdown,
              test_delayed_load_departure_and_shutdown,
              test_completion_record_and_pending_save_changes, test_offline_status_is_honest,
              test_p03_requires_discovered_independent_evidence,
              test_physical_experiment_feedback, test_unused_console_reservation_releases_safely,
              test_terminal_reservation_release_preserves_results,
              test_studio_negative_userids_play_without_persistent_writes]
    for check in checks:
        check()
        print("PASS:", check.__name__)
    print("PASS: actual V10 server + core integration in mocked Roblox APIs; Studio acceptance remains necessary.")


if __name__ == "__main__":
    main()
