"""Trail tools, tolls, teleports and special travel report concrete acquisition outcomes."""

import rs2004.clues.acquire as acquire
import rs2004.clues.bank_access as access
import rs2004.clues.teleports as teleports
import rs2004.clues.travel as travel
import rs2004.clues.executor as executor
import rs2004.clues.solve as solve
from rs2004.catalogs.record import Record
from rs2004.geometry import Tile
from helpers import FakeModule
from quest_world import QuestObject
from clue_world import ClueWorld


def crossing(value):
    return lambda dest: value


def test_clue_bank_uses_npc_chest_or_booth_and_reopen_propagates_failure():
    for near in [{'npcAccess': {'id': 1}}, {'access': {'id': 2}}, None]:
        with ClueWorld() as w:
            w.install(access)
            w.patch(access, 'nearest_bank', lambda tile: near)
            assert w.run(access.open_clue_bank())
            assert w.run(access.reopen_clue_bank())
            w.accept_bank = False
            assert not w.run(access.reopen_clue_bank())


def test_teleport_kit_ignores_current_runes_slots_and_levers_but_checks_magic():
    state = {'members': False, 'skills': {'magic': 25}, 'inventory': [], 'equipment': [], 'quests': {}}
    catalog = [
        {'family': 'lever', 'teleportId': 'lever'},
        {'family': 'spell', 'teleportId': 'varrock', 'requires': {'skills': [{'name': 'magic', 'level': 25}],
            'items': [{'name': 'Law rune', 'count': 1}], 'freeSlots': 5}},
        {'family': 'spell', 'teleportId': 'blocked', 'requires': {'skills': [{'name': 'magic', 'level': 50}]}},
        {'family': 'jewellery', 'itemNameMatch': ['Ring of dueling'],
            'requires': {'items': [{'name': 'Law rune', 'count': 2}]}}]
    kit = teleports.teleport_kit_for(state, catalog)
    assert kit.usable == ['varrock'] and kit.runes == [('Law rune', 2)]
    assert teleports.is_teleport_item('Ring of dueling(8)', kit)


def test_coordinate_chain_refuses_missing_clue_and_handles_each_missing_npc_tool():
    for mode in ['no_clue', 'event', 'deadline', 'no_sextant', 'no_watch', 'no_chart', 'done']:
        with ClueWorld() as w:
            w.install(acquire)
            coordinate = [id for id, row in acquire.CLUE_DB.items() if row.get('needs_sextant')][0]
            if mode != 'no_clue':
                w.hold('Clue scroll', id=coordinate)
            w.interrupted = mode == 'event'
            w.patch(acquire, '_now_ms', lambda: w.now * (1000000 if mode == 'deadline' else 1))
            w.patch(acquire, 'goto_npc', lambda *a: w.reply(True))
            def talk(name, prefer, log):
                yield from w.reply()
                if name == acquire.MURPHY.npc and mode != 'no_sextant':
                    w.hold('Sextant')
                elif name == acquire.KOJO.npc and mode != 'no_watch':
                    w.hold('Watch')
                elif name == acquire.PROFESSOR.npc and w.first('Watch') is not None and mode != 'no_chart':
                    w.hold('Chart')
                return True
            w.patch(acquire, 'talk_through', talk)
            assert w.run(acquire.ensure_coord_tools(w.logs.append)) == (mode == 'done')
            if mode == 'done':
                assert acquire.KOJO_EXIT in w.walks


def test_clue_shop_purchase_waits_for_delivery_and_preserves_partial_progress():
    for mode in ['event', 'walk_failed', 'shop_failed', 'no_stock', 'bought']:
        with ClueWorld() as w:
            w.install(acquire)
            w.interrupted = mode == 'event'
            w.can_walk = mode != 'walk_failed'
            delivered = lambda: w.hold('Rope')
            w.patch(acquire, 'shop', FakeModule(open=lambda n: w.reply(mode != 'shop_failed'),
                buy=lambda name, count: w.reply(1 if mode == 'bought' else 0, delivered if mode == 'bought' else None),
                close=lambda: w.reply()))
            source = FakeModule(stand=Tile(3000, 3000), npc='Shop keeper')
            assert w.run(acquire._buy(source, 'Rope', 1, w.logs.append)) == (1 if mode == 'bought' else 0)
            assert not w.run(acquire.ensure_gate_items([Record({'name': 'Coins', 'count': 10})], w.logs.append))
            assert not w.run(acquire.ensure_extra_items(['Unobtainable'], w.logs.append))


def test_clue_extra_items_buy_rope_once_and_report_unknown_or_unaffordable_tolls():
    with ClueWorld() as w:
        w.install(acquire)
        w.hold('Coins', 100)
        got_rope = lambda: w.hold('Rope')
        w.patch(acquire, 'shop', FakeModule(open=lambda n: w.reply(True),
            buy=lambda n, count: w.reply(1, got_rope), close=lambda: w.reply()))
        assert w.run(acquire.ensure_extra_items(['Rope'], w.logs.append))
        assert not w.run(acquire.ensure_extra_items(['Rope'], w.logs.append))
        assert w.count('Rope') == 1
        assert not w.run(acquire.ensure_gate_items([Record({'name': 'Unknown toll', 'count': 1})], w.logs.append))
        w.pack = []
        assert not w.run(acquire.ensure_gate_items([Record({'name': 'Shantay pass', 'count': 1})], w.logs.append))


def test_spade_collection_closes_distance_and_requires_inventory_arrival():
    with ClueWorld() as w:
        w.install(acquire)
        spade = QuestObject(w, 'Spade', 952, at=Tile(3005, 3000), effect=lambda: w.hold('Spade', id=952))
        w.scene = [spade]
        assert w.run(acquire.ensure_spade(w.logs.append))
        assert spade.at in w.walks


def test_clue_special_travel_routes_are_dispatched_and_unsupported_seams_report_failure():
    for name in ['duel', 'tirannwn', 'kharazi']:
        with ClueWorld() as w:
            for module in [executor, solve]:
                w.install(module)
                for region in ['clue_duel', 'tirannwn', 'kharazi']:
                    active = region == {'duel': 'clue_duel', 'tirannwn': 'tirannwn', 'kharazi': 'kharazi'}[name]
                    w.patch(module, 'crosses_' + region, crossing(active))
                for region in ['clue_duel', 'tirannwn', 'kharazi']:
                    w.patch(module, 'walk_across_' + region, lambda *a: w.reply(True))
            assert w.run(executor.ClueExecutor().walk_leg(Tile(3000, 3000), w.logs.append))
            assert w.run(solve.walk_to_bank(Tile(3000, 3000), w.logs.append))
    with ClueWorld() as w:
        w.install(travel)
        assert w.run(travel._walk(w.position, {}))
        assert not w.run(travel.walk_across_kharazi(Tile(2800, 2900), 1, w.logs.append))
        assert not w.run(travel.walk_across_tirannwn(Tile(2200, 3200), 1, w.logs.append, {}))
