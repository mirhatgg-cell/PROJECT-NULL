"""Execute the actual deterministic V10 Lua state machine, without Roblox mocks.

Requires lupa==2.6. These checks cover game rules and authorization, not rendering
or Roblox character physics. Expected responses come from the public protocol.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
ANSWERS = {
    'P01': ['A', 'B', 'reject', 'reject', 'C'],
    'P02': ['center', 'left', 'right', 'center'],
    'P03': ['manual', 'exhaust', 'safe', 'transfer'],
    'P04': ['hold', 'move', 'hold', 'move', 'hold', 'move'],
    'P05': ['accept', 'isolate', 'repeat', 'accept', 'isolate'],
}


class Fixture:
    def __init__(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.engine = self.lua.execute((ROOT / 'src/ExperimentCore_V10.luau').read_text())
        self.state = self.engine.new()
        self.events = []

    def dispatch(self, action, arg=None, actor=101, now=None):
        value = self.engine.dispatch(self.state, action, arg, self.state.now if now is None else now, actor)
        result = value if isinstance(value, tuple) else (value,)
        return result + (None,) * (3 - len(result))

    def inputs(self, **values):
        self.engine.setInputs(self.state, self.lua.table_from(values))

    def step(self, dt=.25, now=None):
        now = self.state.now + dt if now is None else now
        events = self.engine.step(self.state, dt, now)
        items = [events[i] for i in range(1, len(events) + 1)]
        self.events.extend(items)
        return items

    def advance(self, target):
        while self.state.now < target - 1e-8:
            self.step(min(.25, target - self.state.now))

    def snapshot(self):
        return self.engine.snapshot(self.state, self.state.now)

    def begin(self, protocol, actor=101):
        assert self.dispatch('select', protocol, actor=actor)[0]
        assert self.dispatch('calibrate', actor=actor)[0]
        assert not self.dispatch('start', actor=actor)[0], 'Calibration should take real time'
        self.advance(self.state.now + 2.01)
        ok, _, event = self.dispatch('start', actor=actor)
        assert ok and event.kind == 'started'

    def respond(self, answer, actor=101):
        cue = self.snapshot().cue
        delay = cue.holdDuration + .1 if cue.kind == 'observer' and answer == 'hold' else .1
        self.advance(cue.readyAt + delay)
        if cue.kind == 'observer' and answer == 'move':
            self.inputs(ownerMoving=True)
            self.step(.01)
            self.inputs(ownerMoving=False)
        return self.dispatch('respond', answer, actor=actor)


def plain(value):
    if hasattr(value, 'items'):
        items = dict(value.items())
        if items and all(isinstance(key, int) for key in items):
            return [plain(items[i]) for i in range(1, len(items) + 1)]
        return {str(key): plain(item) for key, item in items.items()}
    if isinstance(value, float):
        assert math.isfinite(value)
    return value


def assert_public(snapshot):
    snapshot = plain(snapshot)
    encoded = json.dumps(snapshot, ensure_ascii=False, allow_nan=False)
    assert 'answer' not in encoded.lower(), 'Private cue answer leaked'
    assert 'pendingEvents' not in encoded
    return snapshot


def run():
    checks = []

    # Each protocol must complete through its own observable rule, not a forced
    # state mutation. Real elapsed steps exercise time, temperature and cues.
    for protocol, answers in ANSWERS.items():
        f = Fixture()
        f.begin(protocol)
        for index, answer in enumerate(answers, 1):
            view = assert_public(f.snapshot())
            assert view['phase'] == 'running' and view['round'] == index
            assert not f.dispatch('respond', answer)[0], 'Preview input was accepted'
            ok, reason, event = f.respond(answer)
            assert ok, (protocol, index, reason)
            if index == len(answers):
                assert event.kind == 'completed' and event.owner == 101
                assert event.record.status == 'completed'
                assert event.record.rounds == len(answers)
            else:
                assert event is None
        view = assert_public(f.snapshot())
        assert view['phase'] == 'completed'
        assert view['telemetry']['progress'] == 1
        assert len(view['records']) == 1 and view['attempts'] == 1
        assert not f.dispatch('respond', answers[-1])[0]
        assert not f.dispatch('start')[0]
        assert f.dispatch('reset')[0] and f.snapshot().owner == 0
        checks.append(protocol + ' complete / cue privacy / immutable terminal state')

    # One valid but wrong answer stops every protocol. Penalty is queued once
    # and bounded; the event contains enough information for health/log updates.
    for protocol, answers in ANSWERS.items():
        f = Fixture()
        f.begin(protocol)
        cue = f.snapshot().cue
        f.advance(cue.readyAt + 2.1)
        wrong = next(cue.options[i].id for i in range(1, len(cue.options) + 1) if cue.options[i].id != answers[0])
        ok, _, event = f.dispatch('respond', wrong)
        assert not ok and event.kind == 'failed'
        assert event.record.status == 'failed' and event.record.rounds == 0
        damage = [e for e in f.step() if e.kind == 'damage']
        assert len(damage) == 1 and damage[0].owner == 101 and 0 < damage[0].amount <= 12
        assert not f.step(), 'Failure/damage repeated after terminal state'
    checks.append('Wrong procedure stops each experiment; damage emitted once')

    f = Fixture()
    f.begin('P01')
    old_round = f.snapshot().round
    for actor in (0, 1.5, math.nan, math.inf, '101', None, 202):
        assert not f.dispatch('respond', 'A', actor=actor)[0]
    assert f.snapshot().round == old_round and f.snapshot().owner == 101
    assert not f.dispatch('reset', actor=202)[0]
    assert not f.dispatch('select', 'P02', actor=202)[0]
    f.advance(f.snapshot().cue.readyAt + .01)
    assert not f.dispatch('respond', 'made-up-answer')[0]
    assert f.snapshot().phase == 'running', 'Malformed network data damaged game state'
    assert f.dispatch('abort')[0]
    assert not f.step(), 'Safe abort should not damage a character'
    assert f.dispatch('reset')[0]
    assert f.dispatch('select', 'P02', actor=202)[0]

    # Actual Studio Start Server players have negative UserIds. They retain
    # ownership isolation; accepting -1 must not let the other test player -2
    # submit a response or steal the running console.
    f = Fixture()
    f.begin('P01', actor=-1)
    assert f.snapshot().owner == -1
    assert not f.dispatch('respond', 'A', actor=-2)[0]
    assert not f.dispatch('reset', actor=-2)[0]
    assert not f.dispatch('select', 'P02', actor=-2)[0]
    for answer in ANSWERS['P01']:
        ok, reason, event = f.respond(answer, actor=-1)
        assert ok, reason
    assert event.kind == 'completed' and event.owner == -1
    assert event.record.owner == -1
    assert f.dispatch('reset', actor=-1)[0]
    assert f.dispatch('select', 'P02', actor=-2)[0]
    checks.append('Exclusive ownership / actor validation / malformed responses / safe abort')

    # Owner absence/death does not trap the shared console in an unusable lock.
    f = Fixture()
    f.begin('P03')
    f.inputs(ownerPresent=False)
    events = f.step()
    assert len(events) == 1 and events[0].kind == 'failed'
    assert f.dispatch('reset', actor=202)[0]
    assert f.dispatch('select', 'P03', actor=202)[0]
    checks.append('Disconnected owner interruption / recovery by another player')

    # Every actually required circuit must be enforced before calibration and
    # immediately during a run. Optional amplifier power does not stop P03.
    for protocol in ANSWERS:
        probe = Fixture()
        probe.dispatch('select', protocol)
        required = [v.id for _, v in probe.snapshot().requirements.items()]
        for circuit in required:
            f = Fixture()
            f.dispatch('select', protocol)
            f.inputs(**{circuit: False})
            assert not f.dispatch('calibrate')[0]
            assert f.snapshot().telemetry.supply == 12
            f.inputs(**{circuit: True})
            f.begin(protocol)
            f.inputs(**{circuit: False})
            events = f.step()
            assert len(events) == 1 and events[0].kind == 'failed'
    f = Fixture()
    f.begin('P03')
    f.inputs(AcousticAmplifiers=False)
    assert not f.step() and f.snapshot().phase == 'running'
    checks.append('Circuit requirements match each protocol before and during a run')

    f = Fixture()
    f.begin('P02')
    cue = f.snapshot().cue
    events = f.step(.25, cue.deadline + .01)
    assert f.snapshot().phase == 'failed'
    assert {e.kind for e in events} == {'damage', 'failed'}
    assert not f.step()
    checks.append('Missed deadline trips once, including a large server time jump')

    f = Fixture()
    f.state.temperature = 44
    f.begin('P03')
    f.dispatch('cooling', False, actor=202)
    while f.snapshot().phase == 'running':
        f.step(.25)
    assert 'Перегрев' in f.snapshot().result
    damage = [e for e in f.events if e.kind == 'damage']
    assert len(damage) == 1 and damage[0].amount == 12
    assert not f.dispatch('calibrate')[0]
    assert f.dispatch('cooling', True, actor=202)[0]
    f.dispatch('reset')
    assert not f.dispatch('calibrate')[0], 'Hot equipment was calibrated'
    f.advance(f.state.now + 15)
    assert f.dispatch('calibrate')[0]
    checks.append('Thermal trip / bounded damage / cooling and safe temperature recovery')

    f = Fixture()
    for _ in range(12):
        assert f.dispatch('calibrate')[0]
        assert f.dispatch('reset')[0]
    assert not f.dispatch('calibrate')[0] and f.snapshot().supply == 0
    assert f.dispatch('resupply', actor=202)[0]
    assert f.snapshot().supply == 6
    f.state.integrity = 75
    assert f.dispatch('repair', actor=202)[0]
    assert f.snapshot().telemetry.integrity == 100 and f.snapshot().supply == 4
    assert not f.dispatch('repair')[0], 'Redundant repair consumed supplies'
    f.state.stress = 70
    ok, _, event = f.dispatch('medical')
    assert ok and event.kind == 'medical' and event.amount == 25
    assert f.snapshot().telemetry.stress == 35 and f.snapshot().supply == 3
    checks.append('Finite supplies / physical resupply / repair and medical costs')

    # P04 cannot be solved by choosing move/hold in the UI without respecting
    # actual character motion supplied by the server.
    f = Fixture()
    f.begin('P04')
    cue = f.snapshot().cue
    f.advance(cue.readyAt + .01)
    assert not f.dispatch('respond', 'hold')[0], 'Stillness interval bypassed'
    f.inputs(ownerMoving=True)
    events = f.step(.01)
    assert f.snapshot().phase == 'failed'
    assert any('движение' in e.result for e in events if e.kind == 'failed')
    f = Fixture()
    f.begin('P04')
    assert f.respond('hold')[0]
    f.advance(f.snapshot().cue.readyAt + .01)
    assert not f.dispatch('respond', 'move')[0], 'Button substituted for an actual step'
    f.inputs(ownerMoving=True)
    f.step(.01)
    f.inputs(ownerMoving=False)
    assert f.dispatch('respond', 'move')[0]
    assert f.respond('hold')[0]
    assert f.respond('move')[0]
    adaptive = f.snapshot().cue
    assert adaptive.observerMode == 'adapting' and adaptive.holdDuration == 4
    assert adaptive.observerMemory == 2
    f.advance(adaptive.readyAt + 2.1)
    assert not f.dispatch('respond', 'hold')[0], 'Adaptive observer did not extend real stillness'
    f.advance(adaptive.readyAt + 4.1)
    assert f.dispatch('respond', 'hold')[0]
    checks.append('P04 actual movement guard, real stillness and real-step requirement')

    f = Fixture()
    initial_time = f.state.now
    for dt in (math.nan, math.inf, -math.inf, -10):
        f.step(dt, math.nan)
    assert f.state.now == initial_time
    f.state.temperature = 70
    f.step(1e100, initial_time + 1)
    assert f.state.temperature >= 70 - 2 * (.18 * (70 - 24) + .25) - 1e-6, 'Unbounded elapsed time reached simulation'
    f.state.temperature = 24
    for _ in range(15):
        f.dispatch('resupply')
        f.dispatch('calibrate')
        f.dispatch('abort')
        f.dispatch('reset')
    assert len(f.snapshot().records) == 12
    view = f.snapshot()
    view.records[1].result = 'tamper'
    assert f.snapshot().records[1].result != 'tamper'
    assert_public(f.snapshot())
    checks.append('Non-finite time rejection / bounded dt / bounded copied records')

    for label in checks:
        print('PASS:', label)
    print(f'V10 experiment core: {len(checks)} scenario groups passed (actual Lua source).')


if __name__ == '__main__':
    run()
