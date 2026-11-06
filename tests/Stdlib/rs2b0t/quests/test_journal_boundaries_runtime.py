"""Journal readers honor quest-list status, close their modal and recover from unreadable pages."""

from rs2004.tabs import quests
import rs2004.quests.defs.digsite.journal as digsite
import rs2004.quests.defs.dwarfcannon.journal as dwarfcannon
import rs2004.quests.defs.elementalworkshop.journal as elementalworkshop
import rs2004.quests.defs.familycrest.journal as familycrest
import rs2004.quests.defs.fightarena.journal as fightarena
import rs2004.quests.defs.fishingcontest.journal as fishingcontest
import rs2004.quests.defs.fremenniktrials.journal as fremenniktrials
import rs2004.quests.defs.heroquest.journal as heroquest
import rs2004.quests.defs.holygrail.journal as holygrail
import rs2004.quests.defs.ikov.journal as ikov
import rs2004.quests.defs.legends.journal as legends
import rs2004.quests.defs.observatory.journal as observatory
import rs2004.quests.defs.regicide.journal as regicide
import rs2004.quests.defs.scorpcatcher.journal as scorpcatcher
import rs2004.quests.defs.seaslug.journal as seaslug
import rs2004.quests.defs.sheepherder.journal as sheepherder
import rs2004.quests.defs.treegnome.journal as treegnome
import rs2004.quests.defs.upass.journal as upass
import rs2004.quests.defs.watchtower.journal as watchtower
import rs2004.quests.defs.witchshouse.journal as witchshouse


CASES = [
    ['digsite', digsite.read_digsite_progress, digsite.DIG_STAGE.NOT_STARTED, digsite.DIG_STAGE.COMPLETE, False, True],
    ['dwarfcannon', dwarfcannon.read_dwarf_cannon_progress, dwarfcannon.MC_STAGE.NOT_STARTED, dwarfcannon.MC_STAGE.COMPLETE, False, False],
    ['elementalworkshop', elementalworkshop.read_elemental_workshop_progress, elementalworkshop.EW_STAGE.NOT_STARTED, elementalworkshop.EW_STAGE.COMPLETE, False, False],
    ['familycrest', familycrest.read_family_crest_progress, familycrest.FC_STAGE.NOT_STARTED, familycrest.FC_STAGE.COMPLETE, False, True],
    ['fightarena', fightarena.read_fight_arena_stage, fightarena.FA_STAGE.NOT_STARTED, fightarena.FA_STAGE.COMPLETE, True, True],
    ['fishingcontest', fishingcontest.read_fishing_contest_stage, fishingcontest.FC_STAGE.NOT_STARTED, fishingcontest.FC_STAGE.COMPLETE, True, False],
    ['fremenniktrials', fremenniktrials.read_fremennik_progress, fremenniktrials.FT_STAGE.NOT_STARTED, fremenniktrials.FT_STAGE.COMPLETE, False, True],
    ['heroquest', heroquest.read_hero_quest_progress, heroquest.HERO_STAGE.NOT_STARTED, heroquest.HERO_STAGE.COMPLETE, False, True],
    ['holygrail', holygrail.read_holy_grail_progress, holygrail.GRAIL_STAGE.NOT_STARTED, holygrail.GRAIL_STAGE.COMPLETE, False, True],
    ['ikov', ikov.read_ikov_stage, ikov.IKOV_STAGE.NOT_STARTED, ikov.IKOV_STAGE.COMPLETE, True, True],
    ['legends', legends.read_legends_progress, legends.LQ_STAGE.NOT_STARTED, legends.LQ_STAGE.COMPLETE, False, True],
    ['observatory', observatory.read_observatory_stage, observatory.OBS_STAGE.NOT_STARTED, observatory.OBS_STAGE.COMPLETE, True, False],
    ['regicide', regicide.read_regicide_progress, regicide.RG_STAGE.NOT_STARTED, regicide.RG_STAGE.COMPLETE, False, False],
    ['scorpcatcher', scorpcatcher.read_scorpion_progress, scorpcatcher.SC_STAGE.NOT_STARTED, scorpcatcher.SC_STAGE.COMPLETE, False, False],
    ['seaslug', seaslug.read_sea_slug_progress, seaslug.SS_STAGE.NOT_STARTED, seaslug.SS_STAGE.COMPLETE, False, False],
    ['sheepherder', sheepherder.read_sheep_herder_progress, sheepherder.SH_STAGE.NOT_STARTED, sheepherder.SH_STAGE.COMPLETE, False, False],
    ['treegnome', treegnome.read_tree_gnome_progress, treegnome.TG_STAGE.NOT_STARTED, treegnome.TG_STAGE.COMPLETE, False, False],
    ['upass', upass.read_upass_progress, upass.UP_STAGE.NOT_STARTED, upass.UP_STAGE.COMPLETE, False, False],
    ['watchtower', watchtower.read_watchtower_progress, watchtower.WATCHTOWER_STAGE.NOT_STARTED, watchtower.WATCHTOWER_STAGE.COMPLETE, False, False],
    ['witchshouse', witchshouse.read_witchs_house_progress, witchshouse.WH_STAGE.NOT_STARTED, witchshouse.WH_STAGE.COMPLETE, False, False],
]


def stage_of(value, scalar):
    return value if scalar or value is None else value.stage


def journal_boundary(name, read, initial, complete, scalar, cached):
    scene = Scene()
    scene.pages = []

    def page(quest):
        expect(type(quest)).to_be(str)
        return list(scene.pages)
        yield

    reads = spy_on(quests, 'journal', impl=page)
    scene.status = 'unknown'
    expect(run_wait(read())).to_be_null()
    scene.status = 'in_progress'
    expect(run_wait(read())).to_be_null()
    scene.status = 'not_started'
    expect(stage_of(run_wait(read()), scalar)).to_be(initial)
    scene.status = 'complete'
    expect(stage_of(run_wait(read()), scalar)).to_be(complete)
    scene.status = 'in_progress'
    scene.pages = ['@gre@Quest complete!']
    scene.main_modal = 123
    before = len(reads.calls)
    expect(stage_of(run_wait(read()), scalar)).to_be(complete)
    expect(len(reads.calls)).to_be(before + 1)
    expect(scene.main_modal).to_be(-1)
    expect(scene.ticks).to_be(1)
    scene.pages = ['Loading...']
    expect(stage_of(run_wait(read()), scalar)).to_be(complete if cached else None)
    expect(scene.ticks).to_be(1)


test_each(CASES)('%s journal status, modal cleanup and unreadable-page recovery', journal_boundary)
