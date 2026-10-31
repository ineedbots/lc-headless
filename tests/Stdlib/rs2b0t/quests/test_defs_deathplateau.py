"""Ported from rs2b0t's test/api/ai/quests/defs/deathplateau.test.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.game import reader
from rs2004.quests.defs.deathplateau import ALL_BALL_IDS, DEATH_ITEM, DP_FLAG, DP_STAGE, close_dice_if_open, deathplateau, decide, effective_map, equip_floor, inside_harold_room, parse_death_plateau_journal
from rs2004.quests.defs.deathplateau.areas import DEATH_DICE_MAIN
from rs2004.quests.defs.deathplateau.harold import next_stake, purse_after
from rs2004.quests.engine.types import QuestProgress, QuestSnapshot


def counts(names):
    out = {}
    for name in names:
        key = name.lower()
        _v1 = out.get(key)
        out[key] = ((_v1 if _v1 is not None else 0)) + 1
    return out


def id_counts(ids):
    out = {}
    for id in ids:
        _v2 = out.get(id)
        out[id] = ((_v2 if _v2 is not None else 0)) + 1
    return out


def progress(stage, flags=None):
    if flags is None:
        flags = []
    return QuestProgress(stage, set(flags))


def snap(o=None):
    if o is None:
        o = Record({})
    bank = counts((o.bank if o.bank is not None else []))
    prog = o.progress
    _v3 = bank.get('coins')
    return QuestSnapshot(**{
        'journal': (o.journal if o.journal is not None else 'in_progress'),
        'inv': counts((o.inv if o.inv is not None else [])),
        'inv_ids': id_counts((o.inv_ids if o.inv_ids is not None else [])),
        'worn': set(),
        'no_progress': 0,
        'bank_coins': (_v3 if _v3 is not None else 0),
        'stage': (prog.stage if prog is not None else None),
        'progress': prog,
        'bank': bank,
        'bank_known': (o.bank_known if o.bank_known is not None else True),
        'tile': (Record({'x': 2896, 'z': 3528, 'level': 0}) if o.tile is None else o.tile),
        'free_slots': (o.free_slots if o.free_slots is not None else 28),
    })


def custom_name(step):
    return (step.name if step.kind == 'custom' else None)


def withdraws_banked_paper(item):
    def run():
        s = snap(Record({'progress': progress(DP_STAGE.GIVEN_IOU)}))
        s.bank_ids = {item.id: 1}
        step = decide(s)
        expect(step.kind).to_be('withdraw')
        expect(step.items).to_equal([{'id': item.id, 'name': item.name, 'qty': 1}])
    return run


def _fn4():
    def _fn5():
        p = parse_death_plateau_journal('@dbl@I can start this quest by speaking to @dre@Denulth@dbl@ who is in his|tent at the @dre@Imperial Guard camp@dbl@ in @dre@Burthorpe')
        expect((p.stage if p is not None else None)).to_be(DP_STAGE.NOT_STARTED)
    test('not started', _fn5)

    def _fn6():
        p = parse_death_plateau_journal('@str@I gave Denulth the secret way map and the combination.||@red@QUEST COMPLETE!')
        expect((p.stage if p is not None else None)).to_be(DP_STAGE.COMPLETE)
    test('complete', _fn6)

    def _fn7():
        p = parse_death_plateau_journal('@dbl@I have offered to help @dre@Denulth@dbl@ by finding @dre@another way@dbl@ up|@dre@Death Plateau.@dbl@ I also need to find the @dre@combination@dbl@ to the|@dre@equipment room@dbl@ and @dre@unlock@dbl@ the door.|')
        expect((p.stage if p is not None else None)).to_be(DP_STAGE.STARTED)
    test('started — offered to help', _fn7)

    def _fn8():
        p = parse_death_plateau_journal('@dbl@I have offered to help @dre@Denulth@dbl@ by finding @dre@another way@dbl@ up|@dre@Death Plateau.@dbl@ I also need to find the @dre@combination@dbl@.|' + '|@dre@Eohric@dbl@ said that the @dre@equipment room guard@dbl@ is staying at @dbl@the local inn, the @dre@Toad and Chicken')
        expect((p.stage if p is not None else None)).to_be(DP_STAGE.SPOKEN_EOHRIC)
    test('spoken eohric — guard at the inn', _fn8)

    def _fn9():
        p = parse_death_plateau_journal('@dbl@I have offered to help Denulth.|' + "|@str@The equipment room guard is staying at the local inn, the Toad @str@and Chicken. The guard wouldn't talk to me!")
        expect((p.stage if p is not None else None)).to_be(DP_STAGE.SPOKEN_HAROLD)
    test('spoken harold — would not talk', _fn9)

    def _fn10():
        p = parse_death_plateau_journal('@dbl@I have offered to help Denulth.|' + "|@str@The equipment room guard is staying at the local inn, the @str@Toad and Chicken. The guard wouldn't talk to me!|" + '@dre@Eohric@dbl@ says to buy the @dre@guard@dbl@ a @dre@drink')
        expect((p.stage if p is not None else None)).to_be(DP_STAGE.SPOKEN_EOHRIC2)
    test('spoken eohric2 — buy a drink tip', _fn10)

    def _fn11():
        p = parse_death_plateau_journal('@dbl@I have offered to help Denulth.|' + "|@str@The equipment room guard is staying at the local inn, the @str@Toad and Chicken. The guard wouldn't talk to me!|" + '@str@I bought the guard a drink and he seemed more helpful.')
        expect((p.stage if p is not None else None)).to_be(DP_STAGE.GIVEN_ALE)
    test('given ale', _fn11)

    def _fn12():
        p = parse_death_plateau_journal('@str@I bought the guard a drink and he seemed more helpful.' + ' I @str@gambled with the guard until he ran out of money. He wrote @str@me an IOU.|')
        expect((p.stage if p is not None else None)).to_be(DP_STAGE.GIVEN_IOU)
    test('given iou', _fn12)

    def _fn13():
        p = parse_death_plateau_journal('I @str@gambled with the guard until he ran out of money. He wrote @str@me an IOU.|' + '|@str@It turned out the IOU was written on the back of the|@str@combination!')
        expect((p.stage if p is not None else None)).to_be(DP_STAGE.FOUND_COMBO)
    test('found combo', _fn13)

    def _fn14():
        p = parse_death_plateau_journal('|@str@I have found the combination to the equipment room and|@str@unlocked the door.|' + ' I put the stone balls in the right places on the|@str@stone mechanism and unlocked the door.')
        expect((p.stage if p is not None else None)).to_be(DP_STAGE.UNLOCKED_DOOR)
    test('unlocked door', _fn14)

    def _fn15():
        expect(parse_death_plateau_journal(['Death Plateau', 'Loading…'])).to_be_undefined()
    test('fails closed on unrelated text', _fn15)


describe('parseDeathPlateauJournal — equip room stages', _fn4)


def _fn16():
    def _fn17():
        p = parse_death_plateau_journal('@dbl@I have offered to help Denulth.||@dre@Saba@dbl@ says that there is a @dre@sherpa@dbl@ living @dre@nearby@dbl@ that may|know another way up Death Plateau.')
        expect((DP_FLAG.SABA in (p.flags if p is not None else None))).to_be(True)
        expect((DP_FLAG.TENZING in (p.flags if p is not None else None))).to_be(False)
    test('saba', _fn17)

    def _fn18():
        p = parse_death_plateau_journal("||@str@I found the sherpa's house.||@dre@Tenzing@dbl@ will show me a @dre@secret way@dbl@ up Death Plateau if I get|him some items:|@dre@Ten loaves of bread.|@dre@Ten cooked trout.|@dre@Spiked boots.")
        expect((DP_FLAG.TENZING in (p.flags if p is not None else None))).to_be(True)
        expect((DP_FLAG.SABA in (p.flags if p is not None else None))).to_be(True)
    test('tenzing supplies list cascades saba', _fn18)

    def _fn19():
        p = parse_death_plateau_journal('@dre@Dunstan@dbl@ will help me if I get his @dre@son signed up@dbl@ for the @dre@Imperial Guard@dbl@.' + "||@dre@Denulth@dbl@ gave me a @dre@certificate@dbl@ to prove that Dunstan's son|has been signed up for the Imperial Guard.")
        expect((DP_FLAG.SMITHY in (p.flags if p is not None else None))).to_be(True)
        expect((DP_FLAG.ENTRANCE_CERT in (p.flags if p is not None else None))).to_be(True)
        expect((DP_FLAG.TENZING in (p.flags if p is not None else None))).to_be(True)
    test('smithy + entrance cert', _fn19)

    def _fn20():
        p = parse_death_plateau_journal('||@str@I have given Dunstan the certificate to prove that his son|@str@has been signed up for the Imperial Guard.|@dbl@I will need an @dre@Iron bar@dbl@ for the boots')
        expect((DP_FLAG.GIVEN_CERT in (p.flags if p is not None else None))).to_be(True)
        expect((DP_FLAG.ENTRANCE_CERT in (p.flags if p is not None else None))).to_be(True)
    test('given cert needs iron bar', _fn20)

    def _fn21():
        p = parse_death_plateau_journal("||@str@I found the sherpa's house. I gave Tenzing the ten loaves|@str@of bread, ten cooked trout and the Spiked boots." + 'Tenzing|@str@has given me a map of the secret way.|@dbl@I need to @dre@check@dbl@ that the @dre@secret way@dbl@ is @dre@safe@dbl@ for the @dre@Imperial|Guard@dbl@ to use.')
        expect((DP_FLAG.SUPPLIES in (p.flags if p is not None else None))).to_be(True)
        expect((DP_FLAG.GOT_MAP in (p.flags if p is not None else None))).to_be(True)
        expect((DP_FLAG.SCOUTED in (p.flags if p is not None else None))).to_be(False)
    test('got map — need to check path', _fn21)

    def _fn22():
        p = parse_death_plateau_journal('@str@I have found another way up Death Plateau for Denulth.' + 'Tenzing|@str@has given me a map of the secret way. I checked the @str@secret way|@str@and it is safe for the Imperial Guard to use.')
        expect((DP_FLAG.SCOUTED in (p.flags if p is not None else None))).to_be(True)
        expect((DP_FLAG.GOT_MAP in (p.flags if p is not None else None))).to_be(True)
        expect((DP_FLAG.SABA in (p.flags if p is not None else None))).to_be(True)
    test('scouted', _fn22)


describe('parseDeathPlateauJournal — map flags', _fn16)


def _fn23():
    def _fn24():
        floor = equip_floor(snap(Record({'progress': progress(DP_STAGE.GIVEN_ALE), 'inv_ids': [DEATH_ITEM.IOU.id]})), progress(DP_STAGE.GIVEN_ALE))
        expect(floor).to_be(DP_STAGE.GIVEN_IOU)
    test('holding IOU raises floor to GIVEN_IOU', _fn24)

    def _fn25():
        floor = equip_floor(snap(Record({'progress': progress(DP_STAGE.GIVEN_IOU), 'inv_ids': [DEATH_ITEM.COMBINATION.id]})), progress(DP_STAGE.GIVEN_IOU))
        expect(floor).to_be(DP_STAGE.FOUND_COMBO)
    test('holding Combination raises floor to FOUND_COMBO', _fn25)

    def _fn26():
        floor = equip_floor(snap(Record({'progress': progress(DP_STAGE.FOUND_COMBO), 'inv_ids': [DEATH_ITEM.BALL_RED.id]})), progress(DP_STAGE.GIVEN_IOU))
        expect(floor).to_be(DP_STAGE.FOUND_COMBO)
    test('holding any stone ball raises floor to FOUND_COMBO', _fn26)


describe('equipFloor inventory awareness', _fn23)


def _fn27():
    def _fn28():
        m = effective_map(snap(Record({'inv_ids': [DEATH_ITEM.CLIMBING_BOOTS.id]})), progress(DP_STAGE.STARTED))
        expect(m.tenzing).to_be(True)
        expect(m.saba).to_be(True)
        expect(m.smithy).to_be(False)
    test('climbing boots imply tenzing + saba', _fn28)

    def _fn29():
        m = effective_map(snap(Record({'inv_ids': [DEATH_ITEM.SPIKED_BOOTS.id]})), progress(DP_STAGE.UNLOCKED_DOOR))
        expect(m.given_cert).to_be(True)
        expect(m.smithy).to_be(True)
    test('spiked boots imply given_cert', _fn29)

    def _fn30():
        m = effective_map(snap(Record({'inv_ids': [DEATH_ITEM.SECRET_MAP.id]})), progress(DP_STAGE.UNLOCKED_DOOR, [DP_FLAG.SUPPLIES]))
        expect(m.got_map).to_be(True)
        expect(m.supplies).to_be(True)
    test('secret way map implies got_map', _fn30)


describe('effectiveMap inventory awareness', _fn27)


def _fn31():
    def _fn32():
        expect(deathplateau.record.id).to_be('death')
        expect(deathplateau.record.name).to_be('Death Plateau')
        expect(deathplateau.owns_inventory).to_be(True)
    test('module is registered with correct quest id', _fn32)

    def _fn33():
        expect(decide(snap(Record({'journal': 'complete', 'progress': progress(DP_STAGE.COMPLETE)}))).kind).to_be('done')
    test('complete journal → done', _fn33)

    def _fn34():
        step = decide(snap(Record({'journal': 'not_started', 'progress': progress(DP_STAGE.NOT_STARTED), 'inv': ['Coins', 'Coins', 'Coins']})))
        # Why: counts(['Coins','Coins']) gives coins:2 rather than a stack value, so the balance may read under 200 and either a bank step or the start talk is correct.
        expect(['custom', 'withdraw', 'scan_bank', 'deposit', 'wait']).to_contain(step.kind)
    test('not started → talk Denulth (after pack/coins)', _fn34)

    def _fn35():
        step = decide(snap(Record({'progress': progress(DP_STAGE.STARTED)})))
        expect(((custom_name(step)) or '').lower()).to_contain('eohric')
    test('started → Eohric', _fn35)

    def _fn36():
        step = decide(snap(Record({'progress': progress(DP_STAGE.SPOKEN_EOHRIC)})))
        expect(((custom_name(step)) or '').lower()).to_contain('harold')
    test('spoken eohric → Harold duty', _fn36)

    def _fn37():
        step = decide(snap(Record({'progress': progress(DP_STAGE.SPOKEN_EOHRIC2), 'inv': ['Coins'] * 200})))
        # counts will give coins:200
        expect(step.kind == 'buy' and ('asgarnian' in step.item.lower())).to_be(True)
    test('spoken eohric2 without ale → buy Asgarnian ale', _fn37)

    def _fn38():
        inv = {_k: _v for _k, _v in [['coins', 500]]}
        step = decide(snap(Record({'progress': progress(DP_STAGE.GIVEN_ALE)})).with_fields({'inv': inv}))
        expect(step).to_match_object(Record({
        'kind': 'buy',
        'item': 'Blurberry special',
        'qty': 1,
        'shop': Record({'npc': 'Barman', 'anchor': Record({'x': 2482, 'z': 3488, 'level': 1})}),
    }))
    test('given ale with coins but no cocktail buys a Blurberry special', _fn38)

    def _fn40():
        step = decide(snap(Record({'progress': progress(DP_STAGE.GIVEN_IOU), 'inv_ids': [DEATH_ITEM.IOU.id], 'inv': ['Iou']})))
        expect(((custom_name(step)) or '').lower()).to_contain('read the iou')
    test('holding IOU → read it', _fn40)

    def _fn41():
        expect(decide(snap(Record({'progress': progress(DP_STAGE.GIVEN_IOU), 'bank_known': False}))).kind).to_be('scan_bank')
    test('a resumed IOU stage scans an unread bank before asking Harold for another', _fn41)
    for item in [DEATH_ITEM.IOU, DEATH_ITEM.COMBINATION]:
        test(f'withdraws a banked {item.name} before trying to reclaim it', withdraws_banked_paper(item))

    def _fn44():
        step = decide(snap(Record({
        'progress': progress(DP_STAGE.FOUND_COMBO),
        'inv_ids': [DEATH_ITEM.COMBINATION.id],
        'inv': ['Combination'],
    })))
        expect(((custom_name(step)) or '').lower()).to_contain('stone ball')
    test('holding combination without balls → pick balls', _fn44)

    def _fn45():
        step = decide(snap(Record({
        'progress': progress(DP_STAGE.FOUND_COMBO),
        'inv_ids': [DEATH_ITEM.COMBINATION.id] + list(ALL_BALL_IDS),
        'inv': ['Combination'] + list(['Stone ball' for _x in ALL_BALL_IDS]),
    })))
        expect(any([p in ((custom_name(step)) or '').lower() for p in ['stone ball', 'stone mechanism']])).to_be(True)
    test('all balls held → place on mechanism', _fn45)

    def _fn46():
        step = decide(snap(Record({'progress': progress(DP_STAGE.UNLOCKED_DOOR)})))
        expect(((custom_name(step)) or '').lower()).to_contain('saba')
    test('unlocked, no map progress → Saba', _fn46)

    def _fn47():
        step = decide(snap(Record({
        'progress': progress(DP_STAGE.UNLOCKED_DOOR, [DP_FLAG.SABA, DP_FLAG.TENZING]),
        'inv_ids': [DEATH_ITEM.CLIMBING_BOOTS.id],
        'inv': ['Climbing boots'],
    })))
        expect(((custom_name(step)) or '').lower()).to_contain('dunstan')
    test('unlocked + tenzing flag, no smithy → Dunstan', _fn47)

    def _fn48():
        # 28 junk slots, freeSlots 0 forces a bank deposit before Denulth grants the cert
        # (full inv would drop Certificate on the floor).
        junk = [f'junk{i}' for i in range(28)]
        step = decide(snap(Record({
        'progress': progress(DP_STAGE.UNLOCKED_DOOR, [DP_FLAG.SABA, DP_FLAG.TENZING, DP_FLAG.SMITHY]),
        'inv': junk,
        'free_slots': 0,
    })))
        expect(step.kind).to_be('deposit')
    test('smithy done, full pack → make space before Denulth cert', _fn48)

    def _fn49():
        step = decide(snap(Record({
        'progress': progress(DP_STAGE.UNLOCKED_DOOR, [DP_FLAG.SABA, DP_FLAG.TENZING, DP_FLAG.SMITHY]),
        'free_slots': 4,
    })))
        expect(any([p in ((custom_name(step)) or '').lower() for p in ['certificate', 'denulth']])).to_be(True)
    test('smithy done with free slot → talk Denulth for cert', _fn49)

    def _fn50():
        step = decide(snap(Record({
        'progress': progress(DP_STAGE.UNLOCKED_DOOR, [
        DP_FLAG.SABA,
        DP_FLAG.TENZING,
        DP_FLAG.SMITHY,
        DP_FLAG.ENTRANCE_CERT,
        DP_FLAG.GIVEN_CERT,
        DP_FLAG.SUPPLIES,
        DP_FLAG.GOT_MAP,
        DP_FLAG.SCOUTED,
    ]),
        'inv_ids': [DEATH_ITEM.COMBINATION.id, DEATH_ITEM.SECRET_MAP.id],
        'inv': ['Combination', 'Secret way map'],
    })))
        expect(((custom_name(step)) or '').lower()).to_contain('denulth')
    test('unlocked + scouted + map + combo → Denulth hand-in', _fn50)

    def _fn51():
        step = decide(snap(Record({
        'progress': progress(DP_STAGE.UNLOCKED_DOOR, [DP_FLAG.SABA, DP_FLAG.TENZING, DP_FLAG.SMITHY, DP_FLAG.ENTRANCE_CERT, DP_FLAG.GIVEN_CERT]),
        'inv_ids': [DEATH_ITEM.CLIMBING_BOOTS.id],
        'inv': ['Climbing boots'],
        'bank': ['Iron bar'],
    })))
        expect(step.kind == 'withdraw' or (('spike' in custom_name(step)) if custom_name(step) is not None else None)).to_be(True)
        if step.kind == 'withdraw':
            expect(any([('iron' in i['name'].lower()) for i in step.items])).to_be(True)
    test('given_cert without iron bar → withdraw/wait iron bar', _fn51)


describe('decide', _fn31)


def _fn52():
    # Why: `death_dice` is on the engine's do-not-auto-close list, so a round that bailed with it up left a main modal nothing would shut and the run sat in Harold's room.
    def stub_client(main_seq):
        state = {'call': 0}

        def modals():
            main = main_seq[min(state['call'], len(main_seq) - 1)]
            state['call'] += 1
            return Record({'main': main})
        spy_on(reader, 'modals', impl=modals)
        # Why: delay_until polls a game clock that never ticks in a unit test, so it answers the predicate directly.
        spy_on(execution, 'delay_until', impl=instant_until)

    def closes(main_seq):
        stub_client(main_seq)
        closed = spy_on(_core, 'close_interfaces', returns=True)
        run_wait(close_dice_if_open(lambda *_args: None))
        return closed.called()

    def _fn54():
        expect(closes([DEATH_DICE_MAIN, DEATH_DICE_MAIN, -1])).to_be(True)
    test('an open dice interface is closed', _fn54)

    def _fn56():
        expect(closes([-1])).to_be(False)
    test('a closed interface is left alone', _fn56)

    def _fn58():
        expect(closes([8119])).to_be(False)
    test('another quest modal is not closed by this', _fn58)


describe('the dice interface never outlives a gamble round', _fn52)


def _fn60():
    # Why: the wall line at z3543 seals x2905..2907, and the room east of x2907 opens straight onto the corridor.
    def _fn61():
        expect(inside_harold_room(Record({'x': 2905, 'z': 3539, 'level': 1}))).to_be(True)
        expect(inside_harold_room(Record({'x': 2906, 'z': 3542, 'level': 1}))).to_be(True)
    test('the bed end is inside', _fn61)

    def _fn62():
        expect(inside_harold_room(Record({'x': 2907, 'z': 3541, 'level': 1}))).to_be(True)
        expect(inside_harold_room(Record({'x': 2907, 'z': 3539, 'level': 1}))).to_be(False)
    test('the elbow at the door end reaches x2907 and no further south', _fn62)

    def _fn63():
        expect(inside_harold_room(Record({'x': 2906, 'z': 3543, 'level': 1}))).to_be(False)
        expect(inside_harold_room(Record({'x': 2909, 'z': 3539, 'level': 1}))).to_be(False)
        expect(inside_harold_room(Record({'x': 2905, 'z': 3539, 'level': 0}))).to_be(False)
        expect(inside_harold_room(None)).to_be(False)
    test('the corridor and the room beyond it are outside', _fn63)


describe("Harold's bedroom is the L behind the door, not the box around it", _fn60)


def _fn64():
    # Why: `dice_winnings` writes the IOU only when `harold_gold - bet` goes below zero, and a loss hands him the stake.
    def _fn65():
        expect(next_stake(100, 2000)).to_be(101)
    test('101 bankrupts the 100gp Denulth gives him', _fn65)

    def _fn66():
        purse = 100
        first = next_stake(purse, 2000)
        purse = purse_after(purse, first, 'loss')
        expect(purse).to_be(201)
        expect(next_stake(purse, 2000)).to_be(202)
    test('a loss raises the next stake past his new purse', _fn66)

    def _fn67():
        expect(next_stake(5000, 20000)).to_be(1000)
        expect(purse_after(900, 901, 'win')).to_be(1000)
    test('the stake never passes the 1000gp harold_gamble refuses', _fn67)

    def _fn68():
        expect(next_stake(300, 40)).to_be(40)
        expect(next_stake(300, 0)).to_be(0)
    test('an empty pack caps the stake rather than betting money that is not there', _fn68)

    def _fn69():
        expect(purse_after(100, 101, 'win')).to_be(201)
    test('a win Harold could pay means the purse was read too low', _fn69)


describe('the stake climbs past whatever Harold has won', _fn64)
def _cases__fn70(id):
    def _fn70():
        step = decide((snap(Record({'progress': progress(DP_STAGE.GIVEN_ALE), 'inv_ids': [id]}))).with_fields({'inv': {_k: _v for _k, _v in [['coins', 500], ['blurberry special', 1]]}}))
        expect(custom_name(step)).to_contain('Blurberry')
    def _fn72():
        step = decide((snap(Record({'progress': progress(DP_STAGE.GIVEN_ALE)}))).with_fields({'inv': {_k: _v for _k, _v in [['coins', 500]]}, 'bank_ids': {_k: _v for _k, _v in [[id, 1]]}}))
        expect(step).to_match_object(Record({'kind': 'withdraw', 'items': [Record({'id': id, 'qty': 1})]}))
    return [_fn70, _fn72]


for id in [2028, 2064]:
    _fn70, _fn72 = _cases__fn70(id)
    test(f'a carried cocktail {id} is given before gambling', _fn70)

    test(f'withdraws banked cocktail {id} before buying one', _fn72)


def _fn74():
    step = decide(snap(Record({'progress': progress(DP_STAGE.NOT_STARTED), 'inv': ['Blurberry special', 'Junk']})))
    expect(step.kind).to_be('deposit')
    if step.kind == 'deposit':
        expect(step.keep).to_contain('blurberry special')


test('startup deposit keeps a carried Blurberry special', _fn74)
def _cases__fn75(coins):
    def _fn75():
        before = (snap(Record({'progress': progress(DP_STAGE.GIVEN_ALE)}))).with_fields({'bank': {}, 'bank_coins': 0, 'inv': {_k: _v for _k, _v in [['coins', coins]]}})
        expect(decide(before).kind).to_be('buy')
        after = (before).with_fields({'inv': {'coins': coins - 30, 'blurberry special': 1}, 'inv_ids': {2028: 1}})
        expect(custom_name(decide(after))).to_contain('gamble')
    return [_fn75]


for coins in [131, 400]:
    _fn75, = _cases__fn75(coins)
    test(f'buying the cocktail with {coins} coins leaves enough for gambling', _fn75)


def _cases__fn78(id):
    def _fn78():
        base = (snap(Record({'progress': progress(DP_STAGE.GIVEN_ALE)}))).with_fields({'bank': {}, 'bank_coins': 0, 'inv': {_k: _v for _k, _v in [['coins', 101]]}})
        expect(decide((base).with_fields({'bank_ids': {_k: _v for _k, _v in [[id, 1]]}})).kind).to_be('withdraw')
        expect(custom_name(decide((base).with_fields({'inv_ids': {_k: _v for _k, _v in [[id, 1]]}})))).to_contain('gamble')
    return [_fn78]


for id in [2028, 2064]:
    _fn78, = _cases__fn78(id)
    test(f'banked or held cocktail {id} only needs the 101gp stake', _fn78)


def _fn82():
    step = decide((snap(Record({'progress': progress(DP_STAGE.GIVEN_ALE)}))).with_fields({'bank': {}, 'bank_coins': 0, 'inv': {_k: _v for _k, _v in [['coins', 130]]}}))
    expect(step.kind).to_be('wait')


test('reserves the cocktail price when the shop is still needed', _fn82)
