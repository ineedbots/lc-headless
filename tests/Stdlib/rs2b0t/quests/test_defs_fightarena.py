"""Ported from rs2b0t's src/bot/../../test/api/ai/quests/defs/fightarena.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.fightarena import decide, fightarena
from rs2004.quests.defs.fightarena.areas import FA_OBJ, FA_TILE
from rs2004.quests.defs.fightarena.journal import FA_STAGE
from rs2004.quests.defs import QUEST_DEFS
from rs2004.geometry import Tile
from rs2004.quests.engine.types import QuestSnapshot

def counts(names):
    out = {}
    for name in names:
        key = name.lower()
        _v1 = out.get(key)
        out[key] = ((_v1 if _v1 is not None else 0)) + 1
    return out


def snap(o=None):
    if o is None:
        o = Record({})
    inv_ids = {}
    for id in (o.inv_ids if o.inv_ids is not None else []):
        _v2 = inv_ids.get(id)
        inv_ids[id] = ((_v2 if _v2 is not None else 0)) + 1
    return QuestSnapshot(**{
        'journal': (o.journal if o.journal is not None else 'in_progress'),
        'inv': {_k: _v for _k, _v in list(counts((o.inv if o.inv is not None else []))) + [['mind rune', 150], ['air rune', 150]]},
        'inv_ids': inv_ids,
        'worn': set([n.lower() for n in ((o.worn if o.worn is not None else []))]),
        'worn_ids': set((o.worn_ids if o.worn_ids is not None else [])),
        'no_progress': 0,
        'bank_coins': 0,
        'stage': o.stage,
        'bank': counts((o.bank if o.bank is not None else [])),
        'bank_known': (o.bank_known if o.bank_known is not None else True),
        'tile': ((o.tile if o.tile is not None else None)),
        'free_slots': 20,
    })


RUNE_KIT = ['Rune scimitar', 'Rune chainbody', 'Rune platelegs', 'Rune full helm', 'Rune kiteshield']


def name(step):
    return ((f'custom:{step.name}' if step.kind == 'custom' else step.kind))


RUNE_FULL_HELM = 1163


def _fn3():
    def _fn4():
        expect(decide(snap(Record({'journal': 'complete'}))).kind).to_be('done')
    test('a complete journal is done', _fn4)

    def _fn5():
        expect(decide(snap(Record({'journal': 'unknown'}))).kind).to_be('wait')
    test('an unloaded journal waits rather than restarting the quest', _fn5)

    def _fn6():
        expect(decide(snap(Record({'stage': None}))).kind).to_be('wait')
    test('an unreadable stage waits', _fn6)

    def _fn7():
        step = decide(snap(Record({'journal': 'not_started', 'stage': FA_STAGE.NOT_STARTED, 'tile': FA_TILE.YANILLE_BANK})))
        expect(step.kind).to_be('talk')
    test('not started walks to Lady Servil', _fn7)

    def _fn8():
        step = decide(snap(Record({'stage': FA_STAGE.STARTED, 'tile': FA_TILE.YANILLE_BANK})))
        expect(name(step)).to_be("custom:search the guards' chest")
    test('started searches the chest', _fn8)

    def _fn9():
        step = decide(snap(Record({
        'stage': FA_STAGE.OBTAINED_ARMOUR,
        'inv_ids': [FA_OBJ.HELMET, FA_OBJ.ARMOUR],
        'tile': FA_TILE.CHEST_STAND,
    })))
        expect(name(step)).to_be('custom:wear the Khazard disguise')
    test('holding the armour but not wearing it puts it on', _fn9)

    def _fn10():
        step = decide(snap(Record({
        'stage': FA_STAGE.OBTAINED_ARMOUR,
        'worn_ids': [FA_OBJ.HELMET, FA_OBJ.ARMOUR],
        'tile': FA_TILE.CHEST_STAND,
    })))
        expect(name(step)).to_be('custom:enter the arena building')
    test('wearing the disguise on the mainland knocks at the guard door', _fn10)

    def _fn11():
        step = decide(snap(Record({
        'stage': FA_STAGE.OBTAINED_ARMOUR,
        'worn_ids': [FA_OBJ.HELMET, FA_OBJ.ARMOUR],
        'tile': FA_TILE.DOOR1_INSIDE,
    })))
        expect(name(step)).to_be('custom:talk to the drunk guard')
    test('inside the building at stage 2 talks to the drunk guard', _fn11)

    def _fn12():
        step = decide(snap(Record({
        'stage': FA_STAGE.SPOKEN_DRUNKGUARD,
        'worn_ids': [FA_OBJ.HELMET, FA_OBJ.ARMOUR],
        'tile': FA_TILE.DOOR1_INSIDE,
    })))
        expect(name(step)).to_be('custom:leave the arena building')
    test('stage 3 without the brew leaves the building to buy one', _fn12)

    def _fn13():
        step = decide(snap(Record({
        'stage': FA_STAGE.SPOKEN_DRUNKGUARD,
        'worn_ids': [FA_OBJ.HELMET, FA_OBJ.ARMOUR],
        'tile': FA_TILE.YANILLE_BANK,
    })))
        expect(name(step)).to_be('custom:buy a Khali brew')
    test('stage 3 on the mainland without the brew buys one from the barman', _fn13)

    def _fn14():
        step = decide(snap(Record({
        'stage': FA_STAGE.SPOKEN_DRUNKGUARD,
        'worn_ids': [FA_OBJ.HELMET, FA_OBJ.ARMOUR],
        'inv_ids': [FA_OBJ.BREW],
        'tile': FA_TILE.DOOR1_INSIDE,
    })))
        expect(name(step)).to_be('custom:talk to the drunk guard')
    test('stage 3 holding the brew goes back to the drunk guard', _fn14)

    def _fn15():
        step = decide(snap(Record({
        'stage': FA_STAGE.GIVEN_KHALI_BREW,
        'worn_ids': [FA_OBJ.HELMET, FA_OBJ.ARMOUR],
        'inv_ids': [FA_OBJ.KEYS, RUNE_FULL_HELM],
        'tile': FA_TILE.DOOR1_INSIDE,
    })))
        expect(name(step)).to_be("custom:unlock Jeremy's cell")
    test('stage 5 keeps the disguise until Jeremy is unlocked', _fn15)

    def _fn16():
        step = decide(snap(Record({
        'stage': FA_STAGE.GIVEN_KHALI_BREW,
        'inv_ids': [FA_OBJ.KEYS, FA_OBJ.HELMET, FA_OBJ.ARMOUR],
        'tile': FA_TILE.DOOR1_INSIDE,
    })))
        expect(name(step)).to_be("custom:unlock Jeremy's cell")
    test("stage 5 in combat gear unlocks Jeremy's cell", _fn16)

    def _fn17():
        step = decide(snap(Record({
        'stage': FA_STAGE.GIVEN_KHALI_BREW,
        'worn_ids': [FA_OBJ.HELMET, FA_OBJ.ARMOUR],
        'tile': FA_TILE.DOOR1_INSIDE,
    })))
        expect(name(step)).to_be('custom:talk to the drunk guard')
    test('stage 5 with the keys lost reclaims them from the drunk guard', _fn17)

    def _fn18():
        step = decide(snap(Record({'stage': FA_STAGE.ENTERED_OGRE_FIGHT, 'tile': FA_TILE.ARENA_CENTRE})))
        expect(name(step)).to_be('custom:fight Khazard Ogre')
    test('stage 6 in the arena fights the ogre', _fn18)

    def _fn19():
        step = decide(snap(Record({'stage': FA_STAGE.SENT_JAIL, 'tile': Tile(2600, 3142, 0)})))
        expect(name(step)).to_be('custom:talk to Hengrad')
    test('stage 9 in the prison cell talks to Hengrad', _fn19)

    def _fn20():
        step = decide(snap(Record({'stage': FA_STAGE.SENT_JAIL, 'tile': FA_TILE.ARENA_CENTRE})))
        expect(name(step)).to_be('custom:fight Khazard Scorpion')
    test('stage 9 in the arena fights the scorpion', _fn20)

    def _fn21():
        step = decide(snap(Record({'stage': FA_STAGE.DEFEATED_SCORPION, 'tile': FA_TILE.ARENA_CENTRE})))
        expect(name(step)).to_be('custom:fight Bouncer')
    test('stage 10 in the arena fights Bouncer', _fn21)

    def _fn22():
        step = decide(snap(Record({'stage': FA_STAGE.DEFEATED_BOUNCER, 'tile': FA_TILE.ARENA_CENTRE})))
        expect(name(step)).to_be('custom:ask the Servils about Khazard')
    test('stage 11 in the arena asks the Servils what Khazard wants', _fn22)

    def _fn23():
        step = decide(snap(Record({'stage': FA_STAGE.FREED_SERVILS, 'tile': FA_TILE.ARENA_CENTRE})))
        expect(name(step)).to_be('custom:run from General Khazard')
    test('stage 12 in the arena runs for the door instead of fighting', _fn23)

    def _fn24():
        step = decide(snap(Record({'stage': FA_STAGE.FREED_SERVILS, 'tile': FA_TILE.YANILLE_BANK})))
        expect(step.kind).to_be('talk')
    test('stage 12 on the mainland reports back to Lady Servil', _fn24)

    def _fn25():
        expect(name(decide(snap(Record({'stage': FA_STAGE.DEFEATED_KHAZARD, 'tile': FA_TILE.ARENA_CENTRE}))))).to_be('custom:run from General Khazard')
        expect(decide(snap(Record({'stage': FA_STAGE.DEFEATED_KHAZARD, 'tile': FA_TILE.YANILLE_BANK}))).kind).to_be('talk')
    test('stage 13 behaves like stage 12 — the kill path is reachable by hand', _fn25)

    def _fn26():
        step = decide(snap(Record({'stage': FA_STAGE.SENT_JAIL, 'tile': FA_TILE.YANILLE_BANK})))
        expect(name(step)).to_be('custom:knock for the arena guard')
    test('after a death at stage 9 the mainland re-entry is the guard door', _fn26)

    def _fn27():
        step = decide(snap(Record({'stage': FA_STAGE.ENTERED_OGRE_FIGHT, 'tile': FA_TILE.YANILLE_BANK})))
        expect(name(step)).to_be("custom:search the guards' chest")
    test('after a death at stage 6 the disguise is re-fetched before the door', _fn27)

    def _fn28():
        expect(decide(snap(Record({'stage': FA_STAGE.GIVEN_KHALI_BREW, 'tile': Tile(2616, 3168, 0)}))).kind).to_be('wait')
    test("inside Jeremy's cell nothing routes out, so it waits", _fn28)


describe('Fight Arena decide', _fn3)


def _fn29():
    def _fn30():
        state = snap(Record({'stage': FA_STAGE.STARTED, 'bank_known': False, 'tile': FA_TILE.YANILLE_BANK}))
        state.inv.clear()
        expect(decide(state).kind).to_be('scan_bank')
        _fn31 = getattr(fightarena, 'food_ready', None)
        expect((_fn31(state) if _fn31 is not None else None)).to_be(False)
    test('an empty pack scans the bank before buying runes', _fn30)

    def _fn32():
        state = snap(Record({'stage': FA_STAGE.STARTED, 'bank': RUNE_KIT, 'tile': FA_TILE.YANILLE_BANK}))
        _fn33 = getattr(fightarena, 'food_ready', None)
        expect((_fn33(state) if _fn33 is not None else None)).to_be(True)
        expect(name(decide(state))).to_be("custom:search the guards' chest")
    test('a complete Strike batch releases the food and continues the quest', _fn32)

    def _fn34():
        state = snap(Record({'stage': FA_STAGE.DEFEATED_BOUNCER}))
        state.inv.clear()
        _fn35 = getattr(fightarena, 'food_ready', None)
        expect((_fn35(state) if _fn35 is not None else None)).to_be(True)
    test('a resume after Bouncer can provision escape food without more runes', _fn34)

    def _fn36():
        for rune in ['mind rune', 'air rune', 'fire rune']:
            expect(fightarena.tools).to_contain(rune)
    test('runes remain protected from spillover banking', _fn36)


describe('Strike supplies before entering the arena', _fn29)


def _fn37():
    def _fn38():
        expect(any([d.record.id == 'arena' for d in QUEST_DEFS])).to_be(True)
    test('is registered with the engine', _fn38)

    def _fn39():
        expect(fightarena.bank).to_equal(FA_TILE.YANILLE_BANK)
        expect(fightarena.food).to_be_greater_than(0)
    test('banks at Yanille and carries food', _fn39)

    def _fn40():
        expect(fightarena.tools).to_contain('khazard cell keys')
        expect(fightarena.tools).to_contain('coins')
    test('keeps the quest items off the spillover deposit', _fn40)


describe('the Fight Arena module', _fn37)
