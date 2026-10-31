"""The quests, in the order the queue runs them: rs2b0t's api/ai/quests/defs/index.ts (MIT, see thirdparty/rs2b0t).
A quest's module is rs2004.quests.defs.<file>, exporting a QuestModule of the same name. It's imported the first time
the queue asks for it, so an account running one quest compiles one."""

from rs2004.quests.data import quest_record


__all__ = ['ORDER', 'QuestDef', 'QUEST_DEFS', 'def_by_id', 'record_by_id']

# rs2b0t's order, by file. Why: Hero's Quest follows Dragon Slayer; it's gated at 55 quest points and on Lost City,
# Merlin's Crystal, Dragon Slayer and Shield of Arrav. Dragon Slayer is gated at 32 quest points, so the queue earns
# them first. Death Plateau comes before Troll Stronghold, which requires it complete. Plague City comes before Family
# Crest, whose Ardougne legs ride the teleport it unlocks, and before Biohazard, which requires it. Shield of Arrav sits
# late among the free quests since it stalls without a partner or a banked certificate. Tribal Totem, Hazeel Cult and
# Sheep Herder sit with the other Ardougne quests. Big Chompy Bird Hunting follows Fight Arena, where the melee kit its
# wolves need is proven. Fishing Contest follows Vampire Slayer, the other quest that empties Morgan's cupboard. Tai
# Bwo Wannai Trio follows Jungle Potion, which it requires. Holy Grail follows Merlin's Crystal, its prerequisite and
# the only source of the Excalibur its one fight needs. Shades of Mort'ton follows Nature Spirit, whose gate-guard
# unlock opens Mort Myre. The Grand Tree sits beside Tree Gnome Village. Scorpion Catcher follows Horror from the Deep,
# the other barcrawl quest. Eadgar's Ruse follows Troll Stronghold. Temple of Ikov sits near the end for its
# Woodcutting 60 and Fletching 65. The Observatory follows Clock Tower. Underground Pass follows Biohazard, and
# Regicide follows Underground Pass. The Fremennik Trials runs after the skilling quests. Legends is last, gated at 107
# quest points and 4 other quests.
ORDER = [
    'runemysteries', 'doric', 'knightssword', 'sheepshearer', 'restlessghost', 'cooksassistant', 'impcatcher', 'ernest',
    'hetty', 'romeojuliet', 'princeali', 'piratestreasure', 'shieldofarrav', 'gertrudescat', 'waterfall',
    'goblindiplomacy', 'demonslayer', 'witchshouse', 'dwarfcannon', 'clocktower', 'observatory', 'monksfriend',
    'merlinscrystal', 'holygrail', 'priestperil', 'druidspirit', 'mortton', 'blackknight', 'druidicritual', 'lostcity',
    'touristtrap', 'watchtower', 'vampireslayer', 'fishingcontest', 'junglepotion', 'tbwt', 'shilo',
    'elementalworkshop', 'deathplateau', 'trollstronghold', 'eadgar', 'plaguecity', 'biohazard', 'hazeelcult',
    'tribaltotem', 'sheepherder', 'familycrest', 'horror', 'scorpcatcher', 'fightarena', 'chompybird', 'seaslug',
    'murder', 'treegnome', 'grandtree', 'ikov', 'digsite', 'upass', 'regicide', 'fremenniktrials', 'dragonslayer',
    'heroquest', 'legends',
]


def _runemysteries():
    from rs2004.quests.defs.runemysteries import runemysteries
    return runemysteries


def _sheepshearer():
    from rs2004.quests.defs.sheepshearer import sheepshearer
    return sheepshearer


def _restlessghost():
    from rs2004.quests.defs.restlessghost import restlessghost
    return restlessghost


def _cooksassistant():
    from rs2004.quests.defs.cooksassistant import cooksassistant
    return cooksassistant


def _hetty():
    from rs2004.quests.defs.hetty import hetty
    return hetty


def _romeojuliet():
    from rs2004.quests.defs.romeojuliet import romeojuliet
    return romeojuliet


def _blackknight():
    from rs2004.quests.defs.blackknight import blackknight
    return blackknight


def _demonslayer():
    from rs2004.quests.defs.demonslayer import demonslayer
    return demonslayer


def _doric():
    from rs2004.quests.defs.doric import doric
    return doric


def _impcatcher():
    from rs2004.quests.defs.impcatcher import impcatcher
    return impcatcher


def _goblindiplomacy():
    from rs2004.quests.defs.goblindiplomacy import goblindiplomacy
    return goblindiplomacy


def _vampireslayer():
    from rs2004.quests.defs.vampireslayer import vampireslayer
    return vampireslayer


def _knightssword():
    from rs2004.quests.defs.knightssword import knightssword
    return knightssword


def _ernest():
    from rs2004.quests.defs.ernest import ernest
    return ernest


def _piratestreasure():
    from rs2004.quests.defs.piratestreasure import piratestreasure
    return piratestreasure


def _princeali():
    from rs2004.quests.defs.princeali import princeali
    return princeali


def _shieldofarrav():
    from rs2004.quests.defs.shieldofarrav import shieldofarrav
    return shieldofarrav


def _dragonslayer():
    from rs2004.quests.defs.dragonslayer import dragonslayer
    return dragonslayer


def _druidicritual():
    from rs2004.quests.defs.druidicritual import druidicritual
    return druidicritual


def _monksfriend():
    from rs2004.quests.defs.monksfriend import monksfriend
    return monksfriend


def _gertrudescat():
    from rs2004.quests.defs.gertrudescat import gertrudescat
    return gertrudescat


def _junglepotion():
    from rs2004.quests.defs.junglepotion import junglepotion
    return junglepotion


def _clocktower():
    from rs2004.quests.defs.clocktower import clocktower
    return clocktower


def _hazeelcult():
    from rs2004.quests.defs.hazeelcult import hazeelcult
    return hazeelcult


def _witchshouse():
    from rs2004.quests.defs.witchshouse import witchshouse
    return witchshouse


def _fishingcontest():
    from rs2004.quests.defs.fishingcontest import fishingcontest
    return fishingcontest


def _murder():
    from rs2004.quests.defs.murder import murder
    return murder


def _seaslug():
    from rs2004.quests.defs.seaslug import seaslug
    return seaslug


def _priestperil():
    from rs2004.quests.defs.priestperil import priestperil
    return priestperil


def _tribaltotem():
    from rs2004.quests.defs.tribaltotem import tribaltotem
    return tribaltotem


def _dwarfcannon():
    from rs2004.quests.defs.dwarfcannon import dwarfcannon
    return dwarfcannon


def _sheepherder():
    from rs2004.quests.defs.sheepherder import sheepherder
    return sheepherder


def _treegnome():
    from rs2004.quests.defs.treegnome import treegnome
    return treegnome


def _waterfall():
    from rs2004.quests.defs.waterfall import waterfall
    return waterfall


def _scorpcatcher():
    from rs2004.quests.defs.scorpcatcher import scorpcatcher
    return scorpcatcher


def _observatory():
    from rs2004.quests.defs.observatory import observatory
    return observatory


def _fightarena():
    from rs2004.quests.defs.fightarena import fightarena
    return fightarena


def _merlinscrystal():
    from rs2004.quests.defs.merlinscrystal import merlinscrystal
    return merlinscrystal


def _lostcity():
    from rs2004.quests.defs.lostcity import lostcity
    return lostcity


# The ported quests: file, record id, loader.
_PORTED = {
    'dwarfcannon': ('mcannon', _dwarfcannon),
    'sheepherder': ('sheepherder', _sheepherder),
    'treegnome': ('tree', _treegnome),
    'waterfall': ('waterfall', _waterfall),
    'scorpcatcher': ('scorpcatcher', _scorpcatcher),
    'observatory': ('itgronigen', _observatory),
    'fightarena': ('arena', _fightarena),
    'merlinscrystal': ('arthur', _merlinscrystal),
    'lostcity': ('zanaris', _lostcity),
    'witchshouse': ('ball', _witchshouse),
    'fishingcontest': ('fishingcompo', _fishingcontest),
    'murder': ('murder', _murder),
    'seaslug': ('seaslug', _seaslug),
    'priestperil': ('priestperil', _priestperil),
    'tribaltotem': ('totem', _tribaltotem),
    'clocktower': ('cog', _clocktower),
    'hazeelcult': ('hazeelcult', _hazeelcult),
    'junglepotion': ('junglepotion', _junglepotion),
    'gertrudescat': ('fluffs', _gertrudescat),
    'druidicritual': ('druid', _druidicritual),
    'monksfriend': ('drunkmonk', _monksfriend),
    'shieldofarrav': ('blackarmgang', _shieldofarrav),
    'dragonslayer': ('dragon', _dragonslayer),
    'demonslayer': ('demon', _demonslayer),
    'doric': ('doric', _doric),
    'impcatcher': ('imp', _impcatcher),
    'goblindiplomacy': ('gobdip', _goblindiplomacy),
    'vampireslayer': ('vampire', _vampireslayer),
    'knightssword': ('squire', _knightssword),
    'ernest': ('haunted', _ernest),
    'piratestreasure': ('hunt', _piratestreasure),
    'princeali': ('prince', _princeali),

    'runemysteries': ('runemysteries', _runemysteries),
    'sheepshearer': ('sheep', _sheepshearer),
    'restlessghost': ('priest', _restlessghost),
    'cooksassistant': ('cook', _cooksassistant),
    'hetty': ('hetty', _hetty),
    'romeojuliet': ('romeojuliet', _romeojuliet),
    'blackknight': ('blackknight', _blackknight),
}


class QuestDef:
    """A quest in the list: its file, its record, and its module, loaded on first use."""

    def __init__(self, file, id, load):
        self.file = file
        self.record = quest_record(id)
        self._load = load
        self._module = None

    def module(self):
        if self._module is None:
            self._module = self._load()
        return self._module


QUEST_DEFS = [QuestDef(file, _PORTED[file][0], _PORTED[file][1]) for file in ORDER if file in _PORTED]


def def_by_id(id):
    """The QuestModule for a record id, loading it, or None."""
    for d in QUEST_DEFS:
        if d.record.id == id:
            return d.module()
    return None


def record_by_id(id):
    """A listed quest's record, without loading its module, or None."""
    for d in QUEST_DEFS:
        if d.record.id == id:
            return d.record
    return None
