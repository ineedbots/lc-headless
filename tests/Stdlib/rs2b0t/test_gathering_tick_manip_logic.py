"""rs2b0t's test/scripts/GatheringBot/TickManipLogic.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect."""

from rs2004.catalogs import Record
from bots.gathering.tick_manip import FISH_TICK_MANIP_OPTIONS, FLETCHABLE_LOG_NAMES, MINE_TICK_MANIP_OPTIONS, TANNERFISH_EAT_HP, TICK_MANIP_SHIPPED, WC_TICK_MANIP_OPTIONS, combat_breaks_gather, extra_delay_logs_to_drop, farmer_willow_phase, fish_tick_manip_profile, is_fletchable_log_name, is_shortbow_name, knife_delay_phase, mining_rate_for_pickaxe, next_gather_click_tick, parse_fish_tick_manip, parse_mine_tick_manip, parse_wc_tick_manip, profile_for_setting, should_cook_for_tannerfish, should_eat_for_tannerfish, tick_manip_ui_options, wc_tick_manip_profile


def _fn1():
    def _fn2():
        expect(parse_fish_tick_manip('Off')).to_be('off')
        expect(parse_fish_tick_manip('4t fly reclick')).to_be('4t-fly')
        expect(parse_fish_tick_manip('Knife delay (+2)')).to_be('knife-delay')
        expect(parse_fish_tick_manip('Tannerfishing')).to_be('tannerfish')
    test('maps UI labels', _fn2)

    def _fn3():
        for o in FISH_TICK_MANIP_OPTIONS:
            expect(isinstance(parse_fish_tick_manip(o), str)).to_be(True)
    test('every dropdown option parses stably', _fn3)


describe('parseFishTickManip', _fn1)


def _fn4():
    def _fn5():
        expect(parse_mine_tick_manip('Off')).to_be('off')
        expect(parse_mine_tick_manip('Iron cadence (pick-aware)')).to_be('iron-cadence')
        expect(parse_mine_tick_manip('4t iron')).to_be('iron-cadence')
        for o in MINE_TICK_MANIP_OPTIONS:
            expect(isinstance(parse_mine_tick_manip(o), str)).to_be(True)
    test('mine labels', _fn5)

    def _fn6():
        expect(parse_wc_tick_manip('Off')).to_be('off')
        expect(parse_wc_tick_manip('Knife delay (+2)')).to_be('knife-delay')
        expect(parse_wc_tick_manip('2t retaliate oaks')).to_be('2t-oaks')
        expect(parse_wc_tick_manip('3t farmer willows')).to_be('3t-farmer')
        expect(parse_wc_tick_manip('3t willows shortbow rapid')).to_be('3t-shortbow')
        for o in WC_TICK_MANIP_OPTIONS:
            expect(isinstance(parse_wc_tick_manip(o), str)).to_be(True)
    test('wc labels', _fn6)


describe('parseMineTickManip / parseWcTickManip', _fn4)


def _fn7():
    def _fn8():
        if TICK_MANIP_SHIPPED:
            expect(len(tick_manip_ui_options(FISH_TICK_MANIP_OPTIONS))).to_be_greater_than(1)
        else:
            expect(tick_manip_ui_options(FISH_TICK_MANIP_OPTIONS)).to_equal(['Off'])
            expect(tick_manip_ui_options(MINE_TICK_MANIP_OPTIONS)).to_equal(['Off'])
            expect(tick_manip_ui_options(WC_TICK_MANIP_OPTIONS)).to_equal(['Off'])
    test('UI options are Off-only until shipped', _fn8)

    def _fn9():
        if TICK_MANIP_SHIPPED:
            expect(profile_for_setting('wc', 'Knife delay (+2)').use_knife_delay).to_be(True)
            return
        expect(profile_for_setting('fish', 'Tannerfishing').method).to_be('off')
        expect(profile_for_setting('wc', 'Knife delay (+2)').method).to_be('off')
        expect(profile_for_setting('mine', 'Iron cadence (pick-aware)').method).to_be('off')
        expect(profile_for_setting('fish', 'Off').method).to_be('off')
    test('profileForSetting ignores non-Off labels while unshipped', _fn9)


describe('product gate (TICK_MANIP_SHIPPED)', _fn7)


def _fn10():
    def _fn11():
        p = fish_tick_manip_profile('off')
        expect(p.method).to_be('off')
        expect(p.combat).to_be('flee')
        expect(p.allow_combat).to_be(False)
        expect(p.may_die).to_be(False)
    test('Off defaults flee and no combat gather', _fn11)

    def _fn12():
        p = fish_tick_manip_profile('4t-fly')
        expect(p.timed_reclick).to_be(True)
        expect(p.native_cycle_ticks).to_be(4)
        expect(p.allow_combat).to_be(False)
        expect(p.use_knife_delay).to_be(False)
    test('4t fly is timed reclick without combat', _fn12)

    def _fn13():
        p = wc_tick_manip_profile('knife-delay')
        expect(p.use_knife_delay).to_be(True)
        expect(p.allow_combat).to_be(False)
    test('knife delay flags inventory delay', _fn13)

    def _fn14():
        expect(wc_tick_manip_profile('2t-oaks').allow_combat).to_be(True)
        expect(wc_tick_manip_profile('3t-farmer').may_die).to_be(True)
        expect(wc_tick_manip_profile('3t-shortbow').combat).to_be('retaliate-may-die')
        expect(fish_tick_manip_profile('tannerfish').allow_combat).to_be(True)
        expect(fish_tick_manip_profile('tannerfish').may_die).to_be(True)
    test('retaliate methods allow combat and may die', _fn14)

    def _fn15():
        expect(wc_tick_manip_profile('3t-shortbow').shortbow_rapid).to_be(True)
        expect(wc_tick_manip_profile('2t-oaks').shortbow_rapid).to_be(False)
    test('shortbow rapid only on 3t shortbow method', _fn15)

    def _fn16():
        expect(wc_tick_manip_profile('3t-farmer').farmer_willow_cycle).to_be(True)
        expect(wc_tick_manip_profile('3t-farmer').native_cycle_ticks).to_be(6)
    test('farmer cycle flag', _fn16)

    def _fn17():
        p = fish_tick_manip_profile('tannerfish')
        expect(p.cook_eat_interleave).to_be(True)
    test('tannerfish cook/eat interleave', _fn17)


describe('profiles', _fn10)


def _fn18():
    def _fn19():
        expect(mining_rate_for_pickaxe('Bronze pickaxe')).to_be(7)
        expect(mining_rate_for_pickaxe('Iron pickaxe')).to_be(6)
        expect(mining_rate_for_pickaxe('Steel pickaxe')).to_be(5)
        expect(mining_rate_for_pickaxe('Mithril pickaxe')).to_be(4)
        expect(mining_rate_for_pickaxe('Adamant pickaxe')).to_be(3)
        expect(mining_rate_for_pickaxe('Rune pickaxe')).to_be(2)
    test('matches server pickaxes.obj rates', _fn19)


describe('miningRateForPickaxe', _fn18)


def _fn20():
    def _fn21():
        expect(next_gather_click_tick(100, 4)).to_be(104)
        expect(next_gather_click_tick(100, 4, 1)).to_be(105)
        expect(next_gather_click_tick(100, 0)).to_be(101)
    test('nextGatherClickTick adds cycle length', _fn21)

    def _fn22():
        expect(knife_delay_phase(50, 50)).to_be('delay-action')
        expect(knife_delay_phase(51, 50)).to_be('reclick')
        expect(knife_delay_phase(55, 50)).to_be('delay-action')
    test('knifeDelayPhase roll / +1 / late', _fn22)

    def _fn23():
        start = 10
        expect(farmer_willow_phase(10, start)).to_be('click-tree')
        expect(farmer_willow_phase(11, start)).to_be('wait')
        expect(farmer_willow_phase(14, start)).to_be('cut-log')
        expect(farmer_willow_phase(15, start)).to_be('drop-log')
        expect(farmer_willow_phase(16, start)).to_be('click-tree')
    test('farmerWillowPhase 6-tick machine', _fn23)


describe('cycle planners', _fn20)


def _fn24():
    def _fn25():
        expect(combat_breaks_gather(True, False)).to_be(True)
        expect(combat_breaks_gather(False, False)).to_be(False)
    test('default AFK yields on combat', _fn25)

    def _fn26():
        expect(combat_breaks_gather(True, True)).to_be(False)
        expect(combat_breaks_gather(False, True)).to_be(False)
    test('retaliate methods ignore combat alone', _fn26)


describe('combatBreaksGather', _fn24)


def _fn27():
    def _fn28():
        expect(is_fletchable_log_name('Oak logs')).to_be(True)
        expect(is_fletchable_log_name('Teak logs')).to_be(False)
        expect(len(FLETCHABLE_LOG_NAMES)).to_be(6)
    test('fletchable log names', _fn28)

    def _fn29():
        expect(extra_delay_logs_to_drop(0)).to_be(0)
        expect(extra_delay_logs_to_drop(1)).to_be(0)
        expect(extra_delay_logs_to_drop(5)).to_be(4)
        expect(extra_delay_logs_to_drop(5, 2)).to_be(3)
    test('extraDelayLogsToDrop keeps one', _fn29)

    def _fn30():
        expect(is_shortbow_name('Maple shortbow')).to_be(True)
        expect(is_shortbow_name('Maple longbow')).to_be(False)
    test('shortbow detect', _fn30)


describe('delay log helpers', _fn27)


def _fn31():
    def _fn32():
        expect(should_eat_for_tannerfish(TANNERFISH_EAT_HP - 0.01, True)).to_be(True)
        expect(should_eat_for_tannerfish(TANNERFISH_EAT_HP, True)).to_be(False)
        expect(should_eat_for_tannerfish(0.1, False)).to_be(False)
    test('eat when HP below threshold and cooked held', _fn32)

    def _fn33():
        expect(should_cook_for_tannerfish(1, 0, 2, 1)).to_be(True)
        expect(should_cook_for_tannerfish(1, 0, 10, 0.8)).to_be(True)
        expect(should_cook_for_tannerfish(4, 1, 10, 1)).to_be(True)
        expect(should_cook_for_tannerfish(0, 0, 0, 0.2)).to_be(False)
        expect(should_cook_for_tannerfish(1, 4, 10, 1)).to_be(False)
    test('cook when pack tight or building food buffer', _fn33)


describe('tannerfish heuristics', _fn31)
