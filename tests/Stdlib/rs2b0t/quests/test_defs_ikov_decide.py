"""Ported from rs2b0t's test/api/ai/quests/defs/ikov-decide.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot
from rs2004.quests.defs.ikov import decide, ikov
from rs2004.quests.defs.ikov.areas import ARROWS_WANTED, IKOV_NAME, IKOV_OBJ, ROOTS_WANTED
from rs2004.quests.defs.ikov.journal import IKOV_STAGE

ARROWS = IKOV_NAME.ICE_ARROWS.lower()


def snap(stage, inv=None, bank=None, inv_names=None, bank_names=None, worn=None, tile=None, bank_known=None, bank_coins=None):
    inv_ids = {_k: _v for _k, _v in (inv if inv is not None else [])}
    bank_ids = {_k: _v for _k, _v in (bank if bank is not None else [])}
    return QuestSnapshot(**{
        'journal': ('complete' if stage == IKOV_STAGE.COMPLETE else ('not_started' if stage == IKOV_STAGE.NOT_STARTED else 'in_progress')),
        'inv': {_k: _v for _k, _v in (inv_names if inv_names is not None else [])},
        'inv_ids': inv_ids,
        'worn': set((worn if worn is not None else [])),
        'worn_ids': set(),
        'no_progress': 0,
        'bank_coins': (bank_coins if bank_coins is not None else 5000),
        'stage': stage,
        'bank': {_k: _v for _k, _v in (bank_names if bank_names is not None else [])},
        'bank_ids': bank_ids,
        'bank_known': (bank_known if bank_known is not None else True),
        'tile': (tile if tile is not None else Record({'x': 2677, 'z': 3406, 'level': 0})),
        'free_slots': 20,
    })


KIT = [
    [IKOV_OBJ.LIT_CANDLE, 1],
    [IKOV_OBJ.TINDERBOX, 1],
    [IKOV_OBJ.KNIFE, 1],
    [IKOV_OBJ.YEW_SHORTBOW, 1],
    [IKOV_OBJ.PENDANT_LUCIEN, 1],
]


def label(step):
    return (f'custom:{step.name}' if step.kind == 'custom' else step.kind)


def _fn1():
    def _fn2():
        s = snap(IKOV_STAGE.NOT_STARTED)
        s.journal = 'unknown'
        expect(decide(s).kind).to_be('wait')
    test('an unloaded journal waits rather than restarting the quest', _fn2)

    def _fn3():
        expect(decide(snap(IKOV_STAGE.COMPLETE)).kind).to_be('done')
    test('a complete journal is done', _fn3)

    def _fn4():
        step = decide(snap(IKOV_STAGE.NOT_STARTED))
        expect(step.kind).to_be('talk')
        expect(step.kind == 'talk' and step.stop.npc).to_be('Lucien')
    test('not started walks to Lucien at the inn', _fn4)

    def _fn5():
        expect(decide(snap(IKOV_STAGE.STARTED, bank_known=False)).kind).to_be('scan_bank')
    test('an unread bank is scanned before anything is judged missing', _fn5)

    def _fn6():
        step = decide(snap(IKOV_STAGE.STARTED, bank=[(id, _2) for id, _2 in KIT if id != IKOV_OBJ.PENDANT_LUCIEN]))
        expect(step.kind).to_be('talk')
    test('a lost pendant sends the bot back to Lucien for another', _fn6)

    # Why: `obj_gettotal` counts the bank, so Lucien refuses to replace a pendant sitting in a booth. It has to be withdrawn instead.
    def _fn8():
        step = decide(snap(IKOV_STAGE.STARTED, bank=KIT))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and any([i['id'] == IKOV_OBJ.PENDANT_LUCIEN for i in step.items])).to_be(True)
    test('a banked pendant is withdrawn rather than begged for', _fn8)

    # Why: the Armoury sits on Ardougne's doorstep and the rest of the kit is a Catherby-Seers loop, so the axe is bought before the bot leaves.
    def _fn9():
        step = decide(snap(IKOV_STAGE.STARTED, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1]]))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.item).to_be(IKOV_NAME.IRON_AXE)
    test('the axe is the first purchase', _fn9)

    def _fn10():
        step = decide(snap(IKOV_STAGE.STARTED, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1]], bank=[[IKOV_OBJ.IRON_AXE, 1]]))
        expect(step.kind == 'buy' and step.item).to_be(IKOV_NAME.TINDERBOX)
    test('with an axe banked the tinderbox is next', _fn10)

    def _fn11():
        step = decide(snap(IKOV_STAGE.STARTED, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1]], bank=[[IKOV_OBJ.IRON_AXE, 1], [IKOV_OBJ.TINDERBOX, 1]]))
        expect(step.kind == 'buy' and step.item).to_be(IKOV_NAME.CANDLE)
    test('with a tinderbox banked the candle is next', _fn11)

    def _fn12():
        step = decide(snap(IKOV_STAGE.STARTED, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1], [IKOV_OBJ.IRON_AXE, 1]], bank=[[IKOV_OBJ.TINDERBOX, 1], [IKOV_OBJ.UNLIT_CANDLE, 1]]))
        expect(label(step)).to_be('custom:chop a yew log')
    test('the bow chain starts at the yew once the candle is covered', _fn12)

    def _fn13():
        step = decide(snap(IKOV_STAGE.STARTED, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1], [IKOV_OBJ.IRON_AXE, 1], [IKOV_OBJ.YEW_LOGS, 1]], bank=[[IKOV_OBJ.TINDERBOX, 1], [IKOV_OBJ.UNLIT_CANDLE, 1]]))
        expect(step.kind).to_be('grab_ground')
        expect(step.kind == 'grab_ground' and step.item).to_be(IKOV_NAME.KNIFE)
    test('with logs cut the chain moves on to the knife', _fn13)

    def _fn14():
        step = decide(snap(IKOV_STAGE.STARTED, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1], [IKOV_OBJ.YEW_LOGS, 1], [IKOV_OBJ.KNIFE, 1]], bank=[[IKOV_OBJ.TINDERBOX, 1], [IKOV_OBJ.UNLIT_CANDLE, 1]]))
        expect(label(step)).to_be('custom:pick flax')
    test('with logs and a knife the flax is next', _fn14)

    def _fn15():
        step = decide(snap(IKOV_STAGE.STARTED, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1], [IKOV_OBJ.YEW_LOGS, 1], [IKOV_OBJ.KNIFE, 1], [IKOV_OBJ.BOW_STRING, 1]], bank=[[IKOV_OBJ.TINDERBOX, 1], [IKOV_OBJ.UNLIT_CANDLE, 1]]))
        expect(label(step)).to_be('custom:fletch a yew shortbow')
    test('with a bow string spun the logs are fletched', _fn15)

    def _fn16():
        step = decide(snap(IKOV_STAGE.STARTED, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1], [IKOV_OBJ.UNSTRUNG_YEW_SHORTBOW, 1], [IKOV_OBJ.BOW_STRING, 1]], bank=[[IKOV_OBJ.TINDERBOX, 1], [IKOV_OBJ.UNLIT_CANDLE, 1]]))
        expect(label(step)).to_be('custom:string the yew shortbow')
    test('a stave and a string are strung together', _fn16)

    def _fn17():
        step = decide(snap(IKOV_STAGE.STARTED, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1]], bank=KIT))
        # Why: the pack is empty, so the candle and the knife are withdrawn before the descent.
        expect(step.kind).to_be('withdraw')
    test('the whole kit banked sends the bot down for the boots', _fn17)

    # Why: `fetchBoots` returns true for arriving in the boots room, a leg before it holds anything, so a step that
    # Why: chains straight on from it walks the gate check while standing in a pocket the ice-cavern half-plane covers.
    def _fn18():
        step = decide(snap(IKOV_STAGE.STARTED, inv=KIT, inv_names=[['lit candle', 1], ['tinderbox', 1], ['knife', 1], ['pendant of lucien', 1]]))
        expect(label(step)).to_be('custom:fetch the boots of lightness')
    test('kit in the pack, boots unfound: the boots leg runs on its own', _fn18)

    # Why: the bridge weighs the pack in grams and gives way at anything but negative, so the bow and the axe are banked before the bot goes underground.
    def _fn19():
        step = decide(snap(IKOV_STAGE.STARTED, inv=KIT, inv_names=[['lit candle', 1], ['knife', 1], ['iron axe', 1], ['yew shortbow', 1], ['lobster', 8]]))
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and step.keep).to_contain('lobster')
        expect(step.kind == 'deposit' and step.keep).to_contain('boots of lightness')
    test('the axe and the bow are banked before the dungeon', _fn19)

    def _fn20():
        step = decide(snap(IKOV_STAGE.STARTED, inv=KIT, inv_names=[
        ['lit candle', 1],
        ['tinderbox', 1],
        ['knife', 1],
        ['pendant of lucien', 1],
        ['lobster', 8],
        ['coins', 1000],
    ]))
        expect(step.kind).not_.to_be('deposit')
    test('a pack of nothing but the crossing kit is not trimmed', _fn20)

    # Why: the south gate is untransmitted, so a session that has never stood past it plans for the lava crossing rather than for the chests.
    def _fn21():
        step = decide(snap(IKOV_STAGE.STARTED, inv=list(KIT) + [[IKOV_OBJ.BOOTS, 1]]))
        expect(label(step)).to_be('custom:unlock the south gate')
    test('boots in hand but no arrows: the gate is unlocked before the chests', _fn21)

    # Why: the crossing gives way at any non-negative weight, so the leg that takes the lever carries no armour however much the bank holds.
    def _fn22():
        step = decide(snap(IKOV_STAGE.STARTED, inv=list(KIT) + [[IKOV_OBJ.BOOTS, 1]], bank_names=[['studded body', 1], ['studded chaps', 1]]))
        expect(label(step)).to_be('custom:unlock the south gate')
    test('banked armour does not ride along on the crossing leg', _fn22)

    # Why: a banked pair read as "done", so nothing withdrew them, the gate check descended for a
    # second pair without a candle, and failed in 2ms forever, a failing step feeds no watchdog.
    def _fn23():
        step = decide(snap(IKOV_STAGE.STARTED, inv=KIT, bank=[[IKOV_OBJ.BOOTS, 1]]))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and [i['id'] for i in step.items]).to_contain(IKOV_OBJ.BOOTS)
    test('boots in the bank are withdrawn, not descended for a second time', _fn23)

    # Why: the candle cannot be bought underground, so the kit is sourced before the descent is
    # chosen, and that ordering is what keeps `fetchBoots` from being reached without one.
    def _fn24():
        step = decide(snap(IKOV_STAGE.STARTED, inv=[(id, _2) for id, _2 in KIT if id != IKOV_OBJ.LIT_CANDLE and id != IKOV_OBJ.TINDERBOX]))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.item).to_be(IKOV_NAME.TINDERBOX)
    test('the candle kit is bought before the descent is chosen', _fn24)

    def _fn26():
        step = decide(snap(IKOV_STAGE.STARTED, inv=list(KIT) + [[IKOV_OBJ.BOOTS, 1]], inv_names=[[ARROWS, ARROWS_WANTED]]))
        expect(label(step)).to_be('custom:disarm and pull the trap lever')
    test('arrows in hand at stage 10: the trap lever is next', _fn26)

    def _fn27():
        step = decide(snap(IKOV_STAGE.PULLED_LEVER, inv=list(KIT) + [[IKOV_OBJ.BOOTS, 1]], inv_names=[[ARROWS, ARROWS_WANTED]]))
        expect(label(step)).to_be('custom:shoot the Fire Warrior of Lesarkus')
    test('arrows in hand past the lever: the Fire Warrior is next', _fn27)

    def _fn28():
        step = decide(snap(IKOV_STAGE.PULLED_LEVER, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1], [IKOV_OBJ.BOOTS, 1]], bank=[[IKOV_OBJ.YEW_SHORTBOW, 1]], inv_names=[[ARROWS, ARROWS_WANTED]]))
        expect(step.kind).to_be('withdraw')
    test('a banked bow is withdrawn before the Fire Warrior', _fn28)

    # Why: the ice-chest circuit spends the engine's one-shot float, and the bot walked up to his door on an empty pack and stood there.
    def _fn29():
        step = decide(snap(IKOV_STAGE.PULLED_LEVER, inv=list(KIT) + [[IKOV_OBJ.BOOTS, 1]], inv_names=[[ARROWS, ARROWS_WANTED]], bank_names=[[IKOV_NAME.LOBSTER.lower(), 20]]))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be(IKOV_NAME.LOBSTER)
    test('an empty pack is refilled before the Fire Warrior', _fn29)

    def _fn30():
        step = decide(snap(IKOV_STAGE.PULLED_LEVER, inv=list(KIT) + [[IKOV_OBJ.BOOTS, 1]], inv_names=[[ARROWS, ARROWS_WANTED], [IKOV_NAME.LOBSTER.lower(), 4]], bank_names=[[IKOV_NAME.LOBSTER.lower(), 20]]))
        expect(label(step)).to_be('custom:shoot the Fire Warrior of Lesarkus')
    test('food in the pack goes straight to the Fire Warrior', _fn30)

    # Why: the candle only lights the stairs to the boots, so demanding one after they are found sends the bot shopping mid-dungeon.
    def _fn31():
        step = decide(snap(IKOV_STAGE.PULLED_LEVER, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1], [IKOV_OBJ.BOOTS, 1], [IKOV_OBJ.YEW_SHORTBOW, 1]], inv_names=[[ARROWS, ARROWS_WANTED]]))
        expect(label(step)).to_be('custom:shoot the Fire Warrior of Lesarkus')
    test('boots in hand stop the candle being part of the kit', _fn31)

    def _fn32():
        step = decide(snap(IKOV_STAGE.KILLED_WARRIOR, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1]]))
        expect(label(step)).to_be('custom:ask Winelda for the ferry across the lava')
    test('the warrior down sends the bot to Winelda', _fn32)

    # Why: with money in the bank an axeless bot buys one first, so the farm itself is only reachable once it is both unarmed and broke.
    def _fn33():
        step = decide(snap(IKOV_STAGE.SPOKEN_WINELDA, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1]], inv_names=[[IKOV_NAME.LOBSTER.lower(), 6]], bank_coins=0))
        expect(label(step)).to_be(f'custom:farm limpwurt roots (0/{ROOTS_WANTED})')
    test('Winelda asked and no roots: the hobgoblin farm runs', _fn33)

    # Why: the crossing kit leaves the bot bare-handed, and the farm is a hundred-odd level-42 hobgoblins.
    def _fn34():
        banked = decide(snap(IKOV_STAGE.SPOKEN_WINELDA, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1]], bank=[[IKOV_OBJ.IRON_AXE, 1]]))
        expect(banked.kind).to_be('withdraw')
        held = decide(snap(IKOV_STAGE.SPOKEN_WINELDA, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1], [IKOV_OBJ.IRON_AXE, 1]]))
        expect(held.kind).to_be('equip')
        expect(held.kind == 'equip' and held.item).to_be(IKOV_NAME.IRON_AXE)
    test('a banked axe is withdrawn and wielded before the farm', _fn34)

    # Why: a run resumed past the sourcing leg never bought the axe it would have banked, and Aemad sells one for pocket change.
    def _fn35():
        step = decide(snap(IKOV_STAGE.SPOKEN_WINELDA, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1]]))
        expect(step.kind).to_be('buy')
        expect(step.kind == 'buy' and step.item).to_be(IKOV_NAME.IRON_AXE)
        expect(step.kind == 'buy' and step.shop.npc).to_be('Aemad')
    test('a bot resumed at the ferry with no axe buys one from Aemad', _fn35)

    # Why: the engine's food float is provisioned once, and this grind outlasts it, the last live run starved at the camp and dropped the kit on the floor.
    def _fn36():
        step = decide(snap(IKOV_STAGE.SPOKEN_WINELDA, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1]], bank_names=[[IKOV_NAME.LOBSTER.lower(), 10]], bank_coins=0))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['name']).to_be(IKOV_NAME.LOBSTER)
    test('an empty larder is restocked before the farm', _fn36)

    def _fn37():
        step = decide(snap(IKOV_STAGE.SPOKEN_WINELDA, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1]], inv_names=[[IKOV_NAME.LOBSTER.lower(), 6]], bank_names=[[IKOV_NAME.LOBSTER.lower(), 10]], bank_coins=0))
        expect(label(step)).to_be(f'custom:farm limpwurt roots (0/{ROOTS_WANTED})')
    test('a stocked pack keeps the farm running', _fn37)

    # Why: hobgoblins are aggressive, so a bot that stops fighting with nothing to eat dies where it stands.
    def _fn38():
        step = decide(snap(IKOV_STAGE.SPOKEN_WINELDA, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1]], bank_coins=0))
        expect(label(step)).to_be('custom:leave the hobgoblin camp')
    test('no food anywhere leaves the camp rather than fighting on', _fn38)

    # Why: twenty unstackable roots plus coins and food fill the pack, so the withdraw cannot land on a pack still holding the dungeon kit.
    def _fn39():
        step = decide(snap(IKOV_STAGE.SPOKEN_WINELDA, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1], [IKOV_OBJ.IRON_AXE, 1]], inv_names=[['pendant of lucien', 1], ['knife', 1], ['lit candle', 1], ['iron axe', 1]], bank=[[IKOV_OBJ.LIMPWURT_ROOT, ROOTS_WANTED]]))
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and step.keep).to_contain('limpwurt root')
    test('the dungeon kit is banked before the roots are withdrawn', _fn39)

    def _fn40():
        step = decide(snap(IKOV_STAGE.SPOKEN_WINELDA, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1]], bank=[[IKOV_OBJ.LIMPWURT_ROOT, ROOTS_WANTED]]))
        expect(step.kind).to_be('withdraw')
        expect(step.kind == 'withdraw' and step.items[0]['qty']).to_be(ROOTS_WANTED)
    test('roots banked are withdrawn before the hand-over', _fn40)

    def _fn41():
        step = decide(snap(IKOV_STAGE.SPOKEN_WINELDA, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1], [IKOV_OBJ.LIMPWURT_ROOT, ROOTS_WANTED]]))
        expect(label(step)).to_be('custom:pay Winelda her twenty limpwurt roots')
    test('roots in the pack pay Winelda', _fn41)

    # Why: the farm's own lobsters are what fill the pack, and a twenty-root withdraw into nineteen free slots retries until the watchdog gives up.
    def _fn42():
        step = decide(snap(IKOV_STAGE.SPOKEN_WINELDA, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1]], inv_names=[['pendant of lucien', 1], [IKOV_NAME.LOBSTER.lower(), 15]], bank=[[IKOV_OBJ.LIMPWURT_ROOT, ROOTS_WANTED]], bank_names=[[IKOV_NAME.LOBSTER.lower(), 40]]))
        expect(step.kind).to_be('deposit')
        expect(step.kind == 'deposit' and step.keep).not_.to_contain(IKOV_NAME.LOBSTER.lower())
    test('the farm food is banked before the twenty roots are drawn', _fn42)

    # Why: past the ferry the roots are gone, and re-reading them as missing would send the bot back to the hobgoblins forever.
    def _fn43():
        step = decide(snap(IKOV_STAGE.PAID_WINELDA, inv=[]))
        expect(label(step)).to_be('custom:join the Guardians of Armadyl')
    test('the spent roots never re-open the farm', _fn43)

    def _fn44():
        step = decide(snap(IKOV_STAGE.HELPING_ARMADYL, inv=[[IKOV_OBJ.PENDANT_ARMADYL, 1]]))
        expect(label(step)).to_be('custom:leave the temple and banish Lucien')
    test('the guardians joined ends in Lucien', _fn44)

    # Why: past the ferry there is no walking back to Lucien, so a missing pendant must not become a talk step.
    def _fn45():
        step = decide(snap(IKOV_STAGE.PAID_WINELDA, tile=Record({'x': 2664, 'z': 9876, 'level': 0})))
        expect(label(step)).to_be('custom:join the Guardians of Armadyl')
    test('a missing pendant on the far side of the lava does not walk back to Lucien', _fn45)

    def _fn46():
        step = decide(snap(IKOV_STAGE.PULLED_LEVER, inv=list(KIT) + [[IKOV_OBJ.BOOTS, 1]], worn=[ARROWS]))
        expect(label(step)).to_be('custom:shoot the Fire Warrior of Lesarkus')
    test('worn arrows count as secured', _fn46)


describe('Temple of Ikov decide', _fn1)


def resumes_in_the_pockets():
    boots_room = Record({'x': 2645, 'z': 9763, 'level': 0})
    expect(ikov.resume_at(boots_room)).to_be(True)
    expect(ikov.resume_at(Record({'x': 2677, 'z': 3406, 'level': 0}))).to_be(False)
    step = decide(snap(IKOV_STAGE.STARTED, tile=boots_room, bank_known=False))
    expect(step.name).to_be('climb out of the temple pocket')
    expect(decide(snap(IKOV_STAGE.PAID_WINELDA, tile=Record({'x': 2664, 'z': 9876, 'level': 0}), bank_known=False)).name).to_be('join the Guardians of Armadyl')


test('a restart in a temple pocket climbs out, and one past the ferry carries on, before any bank scan', resumes_in_the_pockets)


def boots_errand_fetches_its_knife():
    step = decide(snap(IKOV_STAGE.PULLED_LEVER, inv=[[IKOV_OBJ.PENDANT_LUCIEN, 1], [IKOV_OBJ.LIT_CANDLE, 1], [IKOV_OBJ.YEW_SHORTBOW, 1]]))
    expect(step.kind).to_be('grab_ground')
    expect(step.item).to_be(IKOV_NAME.KNIFE)


test('a death that took the boots and the knife fetches a knife before the web', boots_errand_fetches_its_knife)
