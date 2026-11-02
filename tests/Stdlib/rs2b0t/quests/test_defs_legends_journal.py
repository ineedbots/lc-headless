"""Ported from rs2b0t's test/api/ai/quests/defs/legends-journal.test.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.catalogs.record import Record
from rs2004.quests.defs.legends.areas import LQ_STAGE
from rs2004.quests.defs.legends.journal import parse_legends_journal

# Why: transcribed line for line from `legends_journal.rs2`, which is the only place these bodies exist.
# Why: a needle that drifts from the server's wording reads every stage as the one below it, and the module then repeats a leg for ever.
def journal_for(stage, pack=None):
    if pack is None:
        pack = Record({})
    out = []

    def add(line):
        out.append(line)

    if stage == LQ_STAGE.COMPLETE:
        add('@str@Radimus Erkle asked me to go to map the Kharazi Jungle. @str@In addition, he asked me to meet with the tribe of the @str@Kharazi Jungle and return with some sort of gift or token @str@to display in the Legends Guild.')
        add("@str@Radimus Erkle granted me access to the Legends' Guild|@str@facilities.")
        add('@red@QUEST COMPLETE!')
        return '|'.join(out)
    if stage == LQ_STAGE.NOT_STARTED:
        add('@dbl@I can start this quest by speaking to @dre@Radimus Erkle@dbl@ in the')
        add('@dre@Legends Guild@dbl@, North East of @dre@Ardougne@dbl@.')
        add('@dbl@To start this quest I need to complete the following:-')
        add("@dre@'Heroes Quest'")
        add('@dbl@And gain a total of @dre@107 quest points@dbl@.')
        return '|'.join(out)
    if stage >= LQ_STAGE.SWUNG_BULLROARER:
        add('@str@Radimus Erkle asked me to map the Kharazi jungle')
        add('@str@and bring back a gift to display in the Legends Guild.')
    else:
        add('@dre@Radimus Erkle@dbl@ asked me to map the @dre@Kharazi jungle@dbl@')
        add('@dbl@and bring back a @dre@gift@dbl@ to display in the @dre@Legends Guild.')
    if stage >= LQ_STAGE.MAPPED_JUNGLE:
        add('@str@I have mapped the Kharazi Jungle for Radimus Erkle.')
    else:
        add("@dbl@To get in to the @dre@Kharazi Jungle@dbl@ I'll need-:")
        add('@dbl@An @dre@axe.')
    if stage >= LQ_STAGE.SWUNG_BULLROARER:
        add('@str@A local forester took a copy of my Kharazi map and in')
        add("@str@return I got a bullroarer which I used to attract 'Gujuo'.")
    elif stage == LQ_STAGE.GOT_BULLROARER:
        add('@str@A local forester took a copy of my Kharazi map and in')
        add('@str@return I got a bullroarer which may attract a native.')
    else:
        if stage == LQ_STAGE.MAPPED_JUNGLE:
            add('@dbl@I need to make friends with a @dre@native@dbl@ and bring back a @dre@gift@dbl@ which can be displayed in the @dre@Legends Guild@dbl@.')
    if stage > LQ_STAGE.ACCEPTED_RESCUE:
        add('@str@I agreed to help Gujuo by freeing a Shaman. The shaman|@str@is in some caves in North West Kharazi.')
    elif stage == LQ_STAGE.ACCEPTED_RESCUE:
        add('@dbl@I agreed to help @dre@Gujuo@dbl@ by releasing a @dre@Shaman@dbl@ who is being held in some @dre@caves@dbl@ in @dre@North West Kharazi@dbl@.')
    else:
        if stage == LQ_STAGE.SWUNG_BULLROARER:
            add("@dbl@I've met '@dre@Gujuo@dbl@', a @dre@Kharazi Jungle native@dbl@. Perhaps I can make friends with him?")
        elif stage == LQ_STAGE.GOT_BULLROARER:
            add('@dbl@I need to make friends with a @dre@native@dbl@ and bring back a @dre@gift@dbl@ which can be displayed in the @dre@Legends Guild@dbl@.')
    if stage >= LQ_STAGE.SPOKE_UNGADULU:
        add('@str@The Shaman Ungadulu is trapped in a flaming octagon.')
    elif stage == LQ_STAGE.FOUND_ENTRANCE:
        add('@dbl@I need to get some @dre@Yommi tree seeds@dbl@ from @dre@Ungadulu@dbl@.')
    if stage > LQ_STAGE.SPOKE_UNGADULU:
        add('@str@Ungadulu acted strange and mentioned sacred water.')
    elif stage == LQ_STAGE.SPOKE_UNGADULU:
        add("@dre@Ungadulu@dbl@ is acting weird and talking a lot of nonsense, perhaps someone else can help me understand what he's talking about.")
        add('@dbl@I need to get some @dre@Yommi tree seeds@dbl@ from @dre@Ungadulu@dbl@.')
    if stage >= LQ_STAGE.SUMMONED_NEZI_FIRE:
        add('@str@I used sacred water on flames to get into octagon.')
    elif stage >= LQ_STAGE.FILLED_BOWL:
        add('@str@Gujuo said I need a blessed vessel of sun metal.')
    else:
        if stage == LQ_STAGE.ASKED_GUJUO_WATER:
            if pack.blessed_bowl:
                add('@str@Gujuo said I need a blessed vessel of sun metal.')
                add('@dbl@I have a @dre@blessed golden bowl@dbl@, now I need some @dre@sacred water@dbl@.')
            elif pack.gold_bowl:
                add('@str@Gujuo said I need a blessed vessel of sun metal.')
                add('@dbl@I have a @dre@golden bowl@dbl@, now it needs to be @dre@blessed@dbl@.')
            else:
                add('@dbl@Gujuo mentioned a @dre@blessed vessel@dbl@ made from @dre@metal@dbl@ of the @dre@sun@dbl@. Perhaps I can get some @dre@sacred water@dbl@ with this?')
    if stage >= LQ_STAGE.SUMMONED_NEZI_FIRE:
        add('@str@I used the book of binding on Ungadulu and|@str@a demon called Nezikchened appeared. I think that @str@Ungadulu is possessed by this demon.')
    elif stage == LQ_STAGE.FILLED_BOWL:
        add('@dbl@I have some @dre@sacred water@dbl@. @dre@Ungadulu@dbl@ mentioned that it may help me to get closer to him. I need get some @dre@Yommi tree seeds@dbl@ from @dre@Ungadulu@dbl@.')
        if pack.book:
            add("@dbl@I found a '@dre@book of binding@dbl@' which may give some clue as to how I can release @dre@Ungadulu@dbl@.")
    if stage >= LQ_STAGE.DEFEATED_NEZI_FIRE:
        add('@str@I used the book of binding to force the demon|@str@Nezikchened out of Ungadulu. I then slew the demon.')
    elif stage >= LQ_STAGE.SUMMONED_NEZI_FIRE:
        add('@dbl@I need to release @dre@Ungadulu@dbl@ so that I can get some @dre@Yommi tree seeds@dbl@ from him.')
    if stage >= LQ_STAGE.POOL_DRIED:
        add('@str@Ungadulu studies supernatural spirits!')
        add('@str@I used sacred water to germinate the Yommi tree seeds|@str@that Ungadulu gave me.')
    elif stage == LQ_STAGE.GERMINATED_SEEDS:
        add('@dbl@I have some @dre@germinated Yommi tree seeds@dbl@. I just need to plant them now in some @dre@fertile soil@dbl@.')
        add('@dre@Ungadulu@dbl@ studies supernatural @dre@spirits!')
    else:
        if stage == LQ_STAGE.DEFEATED_NEZI_FIRE:
            if pack.seeds:
                add('@dbl@I have some @dre@Yommi tree seeds@dbl@ from @dre@Ungadulu@dbl@. I need to @dre@germinate@dbl@ them with @dre@sacred water@dbl@ before planting them in @dre@fertile soil@dbl@.')
                add('@dre@Ungadulu@dbl@ studies supernatural @dre@spirits!')
            else:
                add('@dbl@I need to get some @dre@Yommi tree seeds@dbl@ from @dre@Ungadulu@dbl@ now that I have released him from his possession.')
    if stage >= LQ_STAGE.ENTER_LOWER_DUNGEON:
        add('@str@Gujuo said the sacred water source is in the Viyeldi caves.|@str@I had to make a bravery potion in order to enter the|@str@caves. The Viyeldi caves are under the caves where|@str@Ungadulu is.')
    elif stage == LQ_STAGE.TALK_GUJUO_POOL:
        if pack.bravery_potion:
            add('@str@Gujuo said the sacred water source is in the Viyeldi caves.')
            add('@str@I have made a bravery potion in order to enter the caves.')
            add('@dbl@I need to find the @dre@Viyeldi@dbl@ caves and the source of the @dre@sacred water@dbl@.')
        elif pack.herbs:
            add('@dbl@I need to make the @dre@bravery potion@dbl@ using the @dre@Snake weed@dbl@ and @dre@Ardrigal@dbl@ I have.')
        else:
            add('@dre@Gujuo@dbl@ said the @dre@Viyeldi caves@dbl@ might be the @dre@source@dbl@ of the @dre@sacred water@dbl@. I need to make a @dre@bravery potion@dbl@ before I can enter.')
            add('@dbl@I need to collect:-')
            add('@dre@Snake weed')
    else:
        if stage == LQ_STAGE.POOL_DRIED:
            add('@dbl@I need to get some more @dre@sacred water@dbl@ in order for the @dre@Yommi tree@dbl@ to grow.')
    if stage == LQ_STAGE.CRYSTAL_SMELTED:
        add('@str@I fixed chunks of crystal into dragon heart shape.')
    elif stage == LQ_STAGE.ENTER_LOWER_DUNGEON:
        add("@dbl@I'm able to access the @dre@Viyeldi Caves@dbl@. I need to find the source of @dre@sacred water@dbl@, which may be protected.")
    if stage == LQ_STAGE.HEART_IN_RECESS:
        add('@str@I made a glowing dragon heart stone from chunks of|@str@crystal which gave me access to a strange cave.')
    elif stage == LQ_STAGE.CRYSTAL_SMELTED:
        if pack.glow_crystal:
            add('@dbl@I have a @dre@glowing dragon heart@dbl@ crystal which might help me to gain access to the @dre@sacred water@dbl@.')
        elif pack.crystal:
            add('@dbl@I have a @dre@Dragon heart@dbl@ crystal which might help me to gain @dbl@access to the @dre@sacred water@dbl@.')
        add('@dbl@I need to find the @dre@source@dbl@ of the @dre@sacred water@dbl@.')
    if stage == LQ_STAGE.PUSHED_BOULDER:
        add('@str@A strange spirit seems to be guarding the sacred water.')
    elif stage == LQ_STAGE.HEART_IN_RECESS:
        add('@dbl@I need to find the source of the @dre@sacred water@dbl@ and collect some so I can grow a @dre@Yommi tree@dbl@.')
    if stage >= LQ_STAGE.DEFEATED_NEZI_WATER and not pack.killed_viyeldi:
        add("@str@The spirit Echnid Zeikin gave me a dagger and asked me|@str@to kill Viyeldi. The Spirit turned out to be a demon in|@str@disguise. I wasn't tricked, though and I defeated the|@str@demon with Ungadulu's help.")
    elif stage >= LQ_STAGE.RECEIVED_DAGGER:
        add('@str@The spirit gave me a dagger and said I have to kill Viyeldi|@str@with it if I want to get some sacred water.')
    if stage == LQ_STAGE.RECEIVED_DAGGER and pack.killed_viyeldi:
        if pack.given_dagger:
            add('@str@I killed Viyeldi with the black dagger and I returned it to|@str@the spirit, but it turned into the demon.')
        else:
            add("@str@I've killed Viyeldi with a dagger the spirit gave me.")
    if stage >= LQ_STAGE.DEFEATED_NEZI_WATER and pack.killed_viyeldi:
        add('@str@I was tricked by the demon into killing Viyeldi but I|@str@managed to destroy the demon in the end.')
    if stage >= LQ_STAGE.SPAWNED_NEZI_FINAL:
        add('@str@I made a Yommi tree totem pole by growing a Yommi|@str@tree and watering it with sacred water.')
    elif stage == LQ_STAGE.COLLECTED_TOTEM:
        add('@str@I collected some sacred water in order to I made a totem|@str@pole from a Yommi tree.')
    else:
        if stage == LQ_STAGE.SACRED_WATER:
            add('@str@I now have some pure sacred water.')
        elif stage == LQ_STAGE.DEFEATED_NEZI_WATER:
            add('@str@I found the source of the sacred water!')
        else:
            if stage == LQ_STAGE.PUSHED_BOULDER or stage == LQ_STAGE.RECEIVED_DAGGER:
                add('@dbl@I need to find a way to get some @dre@sacred water@dbl@.')
    if stage >= LQ_STAGE.SPAWNED_NEZI_FINAL:
        add('@str@I used the totem pole on an evil totem pole and the demon|@str@Nezikchened appeared again.')
    elif stage == LQ_STAGE.COLLECTED_TOTEM:
        add("@dbl@I've got a @dre@Yommi tree totem pole@dbl@, I need to place this somewhere so that @dre@Gujuo@dbl@ can gather his people together. Perhaps then I can make @dre@friends@dbl@ with the Kharazi tribe.")
    else:
        if stage == LQ_STAGE.SACRED_WATER:
            add('@dbl@I can now try to grow a @dre@Yommi tree@dbl@ in order to make a @dre@Yommi tree totem pole@dbl@.')
        elif stage == LQ_STAGE.DEFEATED_NEZI_WATER:
            add('@dbl@I need to collect some @dre@sacred water@dbl@ in order to grow a @dre@Yommi tree@dbl@ and make it into a @dre@totem pole@dbl@.')
    if stage >= LQ_STAGE.DEFEATED_NEZI_FINAL:
        if not pack.killed_viyeldi:
            add('@str@I fought Nezikchened and finally defeated him.')
        else:
            add('@str@Nezikchened appeared and summoned the Viyeldi fighters.')
            add('@str@I fought them all and eventually defeated Nezikchened.')
    elif stage == LQ_STAGE.SPAWNED_NEZI_FINAL:
        if pack.killed_viyeldi and pack.heroes_left:
            add('@dbl@I have to defeat the demon @dre@Nezikchened@dbl@ in order to replace the @dre@evil totem pole.')
        else:
            add('@dbl@I have to defeat the demon @dre@Nezikchened@dbl@ and the @dre@Viyeldi fighters@dbl@ in order to replace the evil totem pole.')
    if stage >= LQ_STAGE.GOT_GILDED_TOTEM:
        add('@str@I replaced the evil totem with the good one I made.')
    elif stage >= LQ_STAGE.DEFEATED_NEZI_FINAL:
        if pack.totem:
            add('@dbl@I need to replace the @dre@evil totem pole@dbl@ with the one I made.')
        else:
            add("@dbl@I don't have a totem pole, I need to make a new one.")
    if stage > LQ_STAGE.GOT_GILDED_TOTEM:
        add('@str@After mapping the Kharazi Jungle for Radimus Erkle|@str@I freed the Kharazi tribe from the power a foul demon|@str@called Nezikchened.')
        add("@str@I've handed the totem pole and map over to Radimus.")
    elif stage == LQ_STAGE.GOT_GILDED_TOTEM:
        if pack.gift:
            add("@str@Gujuo gave me a fine gilded totem pole for freeing the|@str@Kharazi Jungle from Nezikchened's demonic power.")
            add('@dbl@The @dre@gilded totem pole@dbl@ will make a find addition to the @dre@Legends Guild@dbl@.')
        else:
            add('@dbl@Perhaps @dre@Gujuo@dbl@ can call his people together now and I can make @dre@friends@dbl@ with the @dre@Kharazi Jungle tribe@dbl@.')
    remaining = ((LQ_STAGE.TRAINING_4 - stage) // 5)
    words = ['one', 'one', 'two', 'three', 'four']
    completed = 4 - remaining
    if stage > LQ_STAGE.RETURNED_TO_RADIMUS:
        add('@str@The gilded totem pole is on display in the Legends Guild @str@for all to see.')
        if completed > 0:
            add(f"@str@Radimus has given me {words[completed]} training {('session' if completed == 1 else 'sessions')} as reward.")
    elif stage == LQ_STAGE.RETURNED_TO_RADIMUS:
        add('@dre@Radimus@dbl@ asked me to join him inside the @dre@Legends Guild@dbl@ to discuss my reward.')
    if stage > LQ_STAGE.RETURNED_TO_RADIMUS:
        add('@dre@Radimus Erkle@dbl@, the @dre@Grand Vizier@dbl@ of the @dre@Legends Guild@dbl@ has offered me some @dre@training@dbl@ for completing the @dre@quest@dbl@.')
        add(f"@dbl@I still have @dre@{(words[remaining] if words[remaining] is not None else 'one')}@dbl@ training {('session' if remaining == 1 else 'sessions')} with @dre@Radimus@dbl@.")
    return '|'.join(out)


STAGES = [
    LQ_STAGE.NOT_STARTED,
    LQ_STAGE.STARTED,
    LQ_STAGE.MAPPED_JUNGLE,
    LQ_STAGE.GOT_BULLROARER,
    LQ_STAGE.SWUNG_BULLROARER,
    LQ_STAGE.ACCEPTED_RESCUE,
    LQ_STAGE.FOUND_ENTRANCE,
    LQ_STAGE.SPOKE_UNGADULU,
    LQ_STAGE.ASKED_GUJUO_WATER,
    LQ_STAGE.FILLED_BOWL,
    LQ_STAGE.SUMMONED_NEZI_FIRE,
    LQ_STAGE.DEFEATED_NEZI_FIRE,
    LQ_STAGE.GERMINATED_SEEDS,
    LQ_STAGE.POOL_DRIED,
    LQ_STAGE.TALK_GUJUO_POOL,
    LQ_STAGE.ENTER_LOWER_DUNGEON,
    LQ_STAGE.CRYSTAL_SMELTED,
    LQ_STAGE.HEART_IN_RECESS,
    LQ_STAGE.PUSHED_BOULDER,
    LQ_STAGE.RECEIVED_DAGGER,
    LQ_STAGE.DEFEATED_NEZI_WATER,
    LQ_STAGE.SACRED_WATER,
    LQ_STAGE.COLLECTED_TOTEM,
    LQ_STAGE.SPAWNED_NEZI_FINAL,
    LQ_STAGE.DEFEATED_NEZI_FINAL,
    LQ_STAGE.GOT_GILDED_TOTEM,
    LQ_STAGE.RETURNED_TO_RADIMUS,
    LQ_STAGE.TRAINING_1,
    LQ_STAGE.TRAINING_2,
    LQ_STAGE.TRAINING_3,
    LQ_STAGE.TRAINING_4,
    LQ_STAGE.COMPLETE,
]


# Why: stages 35 and 40 render the same body, the "replaced the evil totem" line is gated on 45, so 40 is expected to read back as 35 and `decide()` splits the pair by what is carried.
SAME_BODY = {LQ_STAGE.REPLACED_TOTEM: LQ_STAGE.DEFEATED_NEZI_FINAL}


def reads_back(stage):
    return lambda: expect(parse_legends_journal(journal_for(stage)).stage).to_be(SAME_BODY.get(stage, stage))


def _fn1():
    for stage in STAGES:
        test(f'server stage {stage} reads back', reads_back(stage))

    def _fn3():
        expect((parse_legends_journal(journal_for(LQ_STAGE.REPLACED_TOTEM)).stage if parse_legends_journal(journal_for(LQ_STAGE.REPLACED_TOTEM)) is not None else None)).to_be(LQ_STAGE.DEFEATED_NEZI_FINAL)
    test('stage 40 is indistinguishable from 35 and reads back as 35', _fn3)

    def _fn4():
        expect((parse_legends_journal(journal_for(LQ_STAGE.ASKED_GUJUO_WATER, Record({'gold_bowl': True}))).stage if parse_legends_journal(journal_for(LQ_STAGE.ASKED_GUJUO_WATER, Record({'gold_bowl': True}))) is not None else None)).to_be(LQ_STAGE.ASKED_GUJUO_WATER)
        expect((parse_legends_journal(journal_for(LQ_STAGE.ASKED_GUJUO_WATER, Record({'blessed_bowl': True}))).stage if parse_legends_journal(journal_for(LQ_STAGE.ASKED_GUJUO_WATER, Record({'blessed_bowl': True}))) is not None else None)).to_be(LQ_STAGE.ASKED_GUJUO_WATER)
    test('a bowl in the pack does not push stage 8 forward', _fn4)

    def _fn5():
        for pack in [Record({}), Record({'herbs': True}), Record({'bravery_potion': True})]:
            expect((parse_legends_journal(journal_for(LQ_STAGE.TALK_GUJUO_POOL, pack)).stage if parse_legends_journal(journal_for(LQ_STAGE.TALK_GUJUO_POOL, pack)) is not None else None)).to_be(LQ_STAGE.TALK_GUJUO_POOL)
    test('the bravery-potion branches all read as stage 15', _fn5)

    def _fn6():
        killed = parse_legends_journal(journal_for(LQ_STAGE.RECEIVED_DAGGER, Record({'killed_viyeldi': True})))
        expect(('killed-viyeldi' in (killed.flags if killed is not None else None))).to_be(True)
        clean = parse_legends_journal(journal_for(LQ_STAGE.RECEIVED_DAGGER))
        expect(('killed-viyeldi' in (clean.flags if clean is not None else None))).to_be(False)
    test('a killed Viyeldi is flagged from the dagger stage on', _fn6)

    def _fn7():
        given = parse_legends_journal(journal_for(LQ_STAGE.RECEIVED_DAGGER, Record({'killed_viyeldi': True, 'given_dagger': True})))
        expect(('given-dagger' in (given.flags if given is not None else None))).to_be(True)
    test('handing the dagger back is its own flag', _fn7)

    def _fn8():
        none = parse_legends_journal(journal_for(LQ_STAGE.ENTER_LOWER_DUNGEON))
        expect(('crystals-placed:0' in (none.flags if none is not None else None))).to_be(True)
        one = parse_legends_journal(journal_for(LQ_STAGE.ENTER_LOWER_DUNGEON) + "|@dbl@I've placed a @dre@crystal@dbl@ chunk in a @dre@lava furnace@dbl@.")
        expect(('crystals-placed:1' in (one.flags if one is not None else None))).to_be(True)
        two = parse_legends_journal(journal_for(LQ_STAGE.ENTER_LOWER_DUNGEON) + "|@dbl@I've place some @dre@crystal chunks@dbl@ in a @dre@lava furnace@dbl@.")
        expect(('crystals-placed:2' in (two.flags if two is not None else None))).to_be(True)
    test('crystals already in the lava furnace are counted', _fn8)

    def _fn9():
        expect(parse_legends_journal('@dbl@Something else entirely.')).to_be_undefined()
    test('an unparseable body is undefined rather than stage zero', _fn9)


describe('parseLegendsJournal', _fn1)
