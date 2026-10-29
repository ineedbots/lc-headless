"""Clue execution selects exact search targets and handles incomplete rewards and key hunts."""

import rs2004.clues.executor as clues
from rs2004.geometry import Tile
from helpers import FakeModule
from clue_world import ClueWorld
from quest_world import QuestObject


class ExecutorWorld(ClueWorld):
    def __enter__(self):
        ClueWorld.__enter__(self)
        self.install(clues)
        self.patch(clues, '_now_ms', lambda: self.now)
        self.patch(clues, 'sustain', FakeModule(run=lambda: self.reply()))
        self.patch(clues, 'sustain_until', self.sustain_until)
        self.patch(clues, 'crosses_tirannwn', lambda t: False)
        self.patch(clues, 'crosses_clue_duel', lambda t: False)
        self.patch(clues, 'crosses_kharazi', lambda t: False)
        self.patch(clues, 'reader', FakeModule(count_dialog_open=lambda: self.count_open,
            main_modal=self.get_main_modal, item_type=lambda id: FakeModule(stackable=False)))
        self.traversal.last_missing_gate_items = []
        self.bot = clues.ClueExecutor()
        return self

    def sustain_until(self, expect, ms):
        from rs2004 import execution
        result = yield from execution.delay_until(expect, ms)
        return result


def test_clue_search_prefers_nearest_search_over_open_and_ignores_wrong_floor():
    with ExecutorWorld() as w:
        tile = w.position
        opened = QuestObject(w, 'Chest', ops=['Open'])
        search = QuestObject(w, 'Crate', ops=['Search'])
        w.scene = [QuestObject(w, 'Upstairs', ops=['Search'], at=Tile(tile.x, tile.z, 1)),
                   QuestObject(w, 'Far away', ops=['Search'], at=Tile(tile.x + 5, tile.z)),
                   QuestObject(w, 'Scenery', ops=[]), opened, search]
        assert clues._pick_search_loc(tile) == (search, 'Search')
        step = {'id': 123, 'obj': 'test', 'type': 'search', 'coord': tile}
        assert w.run(w.bot._dispatch(step, w.logs.append, None)) is None
        assert w.actions == [('Crate', 'Search')]
        w.scene = []
        w.run(w.bot._dispatch(step, w.logs.append, None))
        assert 'no searchable' in w.logs[-1]
        w.can_walk = False
        assert w.run(w.bot._dispatch(step, w.logs.append, None)) is None
        assert w.run(w.bot._dispatch({'id': 123, 'type': 'search'}, w.logs.append, None)) is None


def test_clue_frees_room_only_when_food_leaves_pack_and_unknown_challenges_stay_open():
    with ExecutorWorld() as w:
        assert not w.run(clues._eat_one_for_room())
        food = w.hold('Lobster', effect=lambda: setattr(w, 'pack', []))
        food.ops = ['Eat']
        assert w.run(clues._eat_one_for_room()) and not w.pack
        w.count_open = True
        assert not w.run(clues._answer_challenge_if_open({'id': -1, 'type': 'talk'}, w.logs.append))
        assert w.count_open
        assert w.run(clues._answer_challenge_if_open({'id': 2853, 'type': 'talk'}, w.logs.append))
        assert w.answers and 'never opened' in w.logs[-1]


def test_clue_key_hunt_handles_unreachable_missing_respawn_full_pack_and_distant_key():
    for mode in ['walk_failed', 'event', 'no_respawn', 'full', 'key']:
        with ExecutorWorld() as w:
            w.can_walk = mode != 'walk_failed'
            w.interrupted = mode == 'event'
            w.patch(clues, 'KEY_HUNT_MS', 1000 if mode == 'full' else 120000)
            if mode == 'full':
                w.pack = [QuestObject(w, 'Junk') for i in range(28)]
            if mode in ['full', 'key']:
                key = QuestObject(w, 'Key', 999, at=Tile(3005, 3000), effect=lambda: w.hold('Key', id=999))
                w.scene = [key]
            assert w.run(w.bot._acquire_riddle_key({'key_id': 999, 'npc': 'Keeper'}, w.position, w.logs.append)) == (mode == 'key')


def test_clue_talk_dispatch_drives_existing_chat_or_reach_and_solved_puzzle():
    with ExecutorWorld() as w:
        id = [id for id in clues.TALK_ANCHORS if id != clues.PILOT_CLUE][0]
        step = {'id': id, 'type': 'talk', 'npc': 'Keeper', 'puzzle': {'id': 9000}}
        w.hold('Puzzle box', id=9000)
        calls = []
        def talk(*a):
            calls.append('talk')
            yield from w.reply()
            return True
        w.patch(clues, 'primitives', FakeModule(talk_through=talk))
        w.patch(clues, 'puzzle_box', FakeModule(solve_held=lambda *a: w.reply(True)))
        w.patch(clues, 'reach', FakeModule(npc_dialog=lambda *a, **kw: w.reply('done')))
        w.pages = [('continue', ['Well done'])]
        assert w.run(w.bot._dispatch(step, w.logs.append, None)) is None
        w.pages = []
        assert w.run(w.bot._dispatch(step, w.logs.append, None)) is None
        assert calls == ['talk', 'talk']
        assert w.run(w.bot._dispatch({'id': -1, 'type': 'talk'}, w.logs.append, None)) is None


def test_clue_casket_dispatch_distinguishes_missing_silent_completed_and_next_scroll():
    for mode in ['missing', 'silent', 'complete', 'next']:
        with ExecutorWorld() as w:
            step = {'id': 123, 'type': 'open-casket', 'casket_id': 999, 'casket_obj': 'Casket'}
            next_id = list(clues.CLUE_DB.keys())[0]
            def opened():
                w.pack = []
                if mode == 'next':
                    w.hold('Clue scroll', id=next_id)
                elif mode == 'complete':
                    w.messages.append(clues.TRAIL_COMPLETE)
            if mode != 'missing':
                w.hold('Casket', id=999, effect=opened)
            w.respond = mode != 'silent'
            assert w.run(w.bot._dispatch(step, w.logs.append, None)) is None
            if mode == 'complete':
                assert w.logs[-1] == 'the trail is complete'


def test_clue_requirements_acquisition_and_guardian_halts_propagate():
    with ExecutorWorld() as w:
        w.patch(clues, 'quests', FakeModule(status=lambda n: 'complete'))
        assert 'no anchor' in w.bot._block_reason({'id': -1, 'type': 'talk'})
        w.hold('Spade')
        step = {'id': -1, 'type': 'dig', 'needs_sextant': True}
        assert 'Sextant' in w.bot._block_reason(step)
        w.patch(clues, 'ensure_coord_tools', lambda *a: w.reply(True))
        assert w.run(w.bot._try_acquire(step, w.logs.append))
        assert not w.run(w.bot._try_acquire({'type': 'open-casket'}, w.logs.append))
        w.bot.guardian_halt = 'dead'
        assert w.run(w.bot._solve_step({'id': 123, 'type': 'search'}, w.logs.append, lambda n: None, None)) == 'dead'


def test_clue_reward_cleanup_rejects_no_position_and_closes_reward_scroll():
    with ExecutorWorld() as w:
        w.position = None
        assert not w.run(w.bot._collect_reward(w.logs.append))
        w.position = Tile(3000, 3000)
        w.pages = [('main', ['Treasure!'])]
        assert w.run(w.bot._dismiss_reward_modal())
        assert not w.pages
        reward = QuestObject(w, 'Coins', 995)
        reward.accept = False
        w.scene = [reward]
        assert not w.run(w.bot._collect_reward(w.logs.append))
