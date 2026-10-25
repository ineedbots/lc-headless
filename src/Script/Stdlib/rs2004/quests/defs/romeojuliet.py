"""Romeo & Juliet: rs2b0t's api/ai/quests/defs/romeojuliet.ts (MIT, see thirdparty/rs2b0t). Juliet's message to
Romeo, Father Lawrence, the Apothecary's Cadava potion from the berries south-east of Varrock, and the potion to
Juliet. The stage is read from the journal, since rjquest never reaches the client as a varp."""

from rs2004 import execution
from rs2004.dialogue import modals
from rs2004.entities import ground_items
from rs2004.geometry import Tile
from rs2004.items import inventory
from rs2004.quests.data import quest_record
from rs2004.quests.engine.types import QuestModule, quest_step
from rs2004.quests.exec.primitives import NpcStop, goto_npc, talk_strict
from rs2004.quests.journal_text import normalize_journal
from rs2004.tabs import quests
from rs2004.traversal import traversal

__all__ = [
    'ROMEO_JULIET_STAGE', 'ROMEO_JULIET_ITEM', 'ROMEO', 'JULIET', 'LAWRENCE', 'APOTHECARY', 'VARROCK_WEST_BANK',
    'parse_romeo_juliet_journal', 'read_romeo_juliet_stage', 'decide', 'romeojuliet',
]


class _Stages:
    """The server's rjquest values, read back from the journal."""
    NOT_STARTED = 0
    SPOKEN_TO_ROMEO = 10
    SPOKEN_TO_JULIET = 20
    PASSED_MESSAGE = 30
    SPOKEN_TO_FATHER = 40
    SPOKEN_TO_APOTHECARY = 50
    JULIET_IN_CRYPT = 60
    COMPLETE = 100


ROMEO_JULIET_STAGE = _Stages()

ROMEO_JULIET_ITEM = {
    'BERRIES': {'name': 'Cadava berries', 'id': 753},
    'MESSAGE': {'name': 'Message', 'id': 755},
    'POTION': {'name': 'Cadava potion', 'id': 756},
}

ROMEO = NpcStop('Romeo', Tile(3211, 3425, 0), 8, ['Can I help find her for you?'])
JULIET = NpcStop('Juliet', Tile(3158, 3425, 1), 6, [])
LAWRENCE = NpcStop('Father Lawrence', Tile(3254, 3475, 0), 6, [])
APOTHECARY = NpcStop('Apothecary', Tile(3195, 3404, 0), 6, [])

VARROCK_WEST_BANK = Tile(3185, 3440, 0)
BERRY_ANCHOR = Tile(3272, 3369, 0)
BERRY_RESPAWN_MS = 70000


def parse_romeo_juliet_journal(lines):
    """The journal as the rjquest stage, or None. Entries are cumulative, so the newest milestone is matched first."""
    text = normalize_journal(lines)
    s = ROMEO_JULIET_STAGE
    if 'quest complete!' in text:
        return s.COMPLETE
    if 'i have to find romeo' in text and "tell him what's happened" in text:
        return s.JULIET_IN_CRYPT
    # Why: content branch 274 changed the journal's "cadaver" to the item spelling "cadava", so matching the stable
    # clause resolves both revisions to the same stage.
    if 'i went to the apothecary regarding making this' in text and 'potion, and he told me to bring him some' in text:
        return s.SPOKEN_TO_APOTHECARY
    if 'i need to find the apothecary' in text:
        return s.SPOKEN_TO_FATHER
    if 'i should find father lawrence' in text:
        return s.PASSED_MESSAGE
    if 'i should take the message' in text and 'to romeo' in text:
        return s.SPOKEN_TO_JULIET
    if 'i should go and speak to juliet' in text:
        return s.SPOKEN_TO_ROMEO
    if 'i can start this quest by talking to romeo' in text:
        return s.NOT_STARTED
    return None


def read_romeo_juliet_stage():
    """The stage, from the quest list and then the journal. Use with yield from."""
    status = quests.status('Romeo & Juliet')
    if status == 'complete':
        return ROMEO_JULIET_STAGE.COMPLETE
    if status == 'not_started':
        return ROMEO_JULIET_STAGE.NOT_STARTED
    if status != 'in_progress':
        return None
    # rjquest never reaches the client as a varp; the server renders the journal from it, which makes it the oracle.
    lines = yield from quests.journal('Romeo & Juliet')
    stage = parse_romeo_juliet_journal(lines)
    if modals.main() != -1:
        yield from modals.close()
    return stage


def _held(snap, item):
    if snap.inv_ids is not None:
        return snap.inv_ids.get(item['id'], 0) > 0
    return snap.inv.get(item['name'].lower(), 0) > 0


def _banked(snap, item):
    if snap.bank_ids is not None:
        return snap.bank_ids.get(item['id'], 0)
    return snap.bank.get(item['name'].lower(), 0) if snap.bank is not None else 0


def _clear_full_pack():
    return quest_step('deposit', keep=[], keep_ids=[], bank=VARROCK_WEST_BANK, exact_keep=True)


def _withdraw_one(item):
    return quest_step('withdraw', items=[{'name': item['name'], 'id': item['id'], 'qty': 1}], bank=VARROCK_WEST_BANK)


class _TalkAtStage:
    """A talk step's run, which says which stage it's for."""

    def __init__(self, stage, action, stop):
        self.stage = stage
        self.action = action
        self.stop = stop

    def __call__(self, log):
        stage = self.stage
        stop = self.stop
        log(f'journal stage {stage}: {self.action}')
        reached = yield from goto_npc(stop, [], log)
        if not reached:
            log(f'stage {stage}: could not reach {stop.npc}')
            return False
        talked = yield from talk_strict(stop.npc, stop.prefer, log)
        if not talked:
            log(f'stage {stage}: {stop.npc} dialogue did not complete')
            return False
        log(f'stage {stage}: finished talking to {stop.npc}; re-reading the journal')
        return True


def _talk_at_stage(stage, action, stop):
    return quest_step('custom', name=f'stage {stage}: {action}', run=_TalkAtStage(stage, action, stop))


def _nearby_berries():
    return ground_items.query().where(lambda item: item.id == ROMEO_JULIET_ITEM['BERRIES']['id']).within(12).nearest()


def _berries_held():
    return inventory.count_by_id(ROMEO_JULIET_ITEM['BERRIES']['id'])


def pick_berries(log):
    """A Cadava berry from the ground spawns, waiting out a respawn. Use with yield from."""
    if inventory.is_full():
        log('stage 50: inventory is full; refusing to risk losing the berry pickup')
        return False
    before = _berries_held()
    berry = _nearby_berries()
    if berry is None:
        log('stage 50: walking to the three Cadava berry ground spawns')
        walked = yield from traversal.walk_resilient(BERRY_ANCHOR, radius=3, attempts=3, timeout_ms=120000, log=log)
        if not walked:
            log('stage 50: could not reach the Cadava berry spawn area')
            return False
        berry = _nearby_berries()
    if berry is None:
        log('stage 50: all three Cadava berry spawns are empty; waiting up to 70 seconds for a respawn')
        appeared = yield from execution.delay_until(lambda: _nearby_berries() is not None, BERRY_RESPAWN_MS)
        if not appeared:
            log('stage 50: no Cadava berry respawn appeared within 70 seconds')
            return False
        berry = _nearby_berries()
    if berry is None:
        log('stage 50: a Cadava berry appeared but another player took it first; retrying')
        return False
    log('stage 50: taking a Cadava berry from the ground spawn')
    if not berry.interact('Take'):
        log('stage 50: the Cadava berry pickup action failed or lost a player race')
        return False
    obtained = yield from execution.delay_until(lambda: _berries_held() > before, 8000)
    if not obtained:
        log('stage 50: the pickup completed without a Cadava berry entering the inventory')
    else:
        log('stage 50: acquired a Cadava berry')
    return obtained


def _stage_twenty(snap):
    message = ROMEO_JULIET_ITEM['MESSAGE']
    if _held(snap, message):
        return _talk_at_stage(20, "deliver Juliet's message to Romeo", ROMEO)
    if snap.free_slots == 0:
        return _clear_full_pack()
    # Juliet checks inventory and bank before issuing a replacement, so a restart has to know if the message is banked.
    if not snap.bank_known:
        return quest_step('scan_bank', bank=VARROCK_WEST_BANK)
    if _banked(snap, message) > 0:
        return _withdraw_one(message)
    return _talk_at_stage(20, 'ask Juliet to replace the lost message', JULIET)


def _stage_fifty(snap):
    potion = ROMEO_JULIET_ITEM['POTION']
    berries = ROMEO_JULIET_ITEM['BERRIES']
    if _held(snap, potion):
        return _talk_at_stage(50, 'deliver the Cadava potion to Juliet', JULIET)
    if _held(snap, berries):
        return _talk_at_stage(50, 'exchange Cadava berries with the Apothecary', APOTHECARY)
    if snap.free_slots == 0:
        return _clear_full_pack()
    if not snap.bank_known:
        return quest_step('scan_bank', bank=VARROCK_WEST_BANK)
    if _banked(snap, potion) > 0:
        return _withdraw_one(potion)
    if _banked(snap, berries) > 0:
        return _withdraw_one(berries)
    return quest_step('custom', name='stage 50: collect Cadava berries from their ground spawns', run=pick_berries)


def decide(snap):
    s = ROMEO_JULIET_STAGE
    if snap.journal == 'complete' or (snap.stage if snap.stage is not None else 0) >= s.COMPLETE:
        return quest_step('done')
    if snap.journal == 'unknown':
        return quest_step('wait', reason='quest journal not loaded')
    if snap.stage is None:
        return quest_step('wait', reason='Romeo & Juliet stage unavailable')
    stage = snap.stage
    if stage == s.NOT_STARTED:
        return _talk_at_stage(0, 'ask Romeo how to help find Juliet', ROMEO)
    if stage == s.SPOKEN_TO_ROMEO:
        return _clear_full_pack() if snap.free_slots == 0 else _talk_at_stage(10, "ask Juliet for Romeo's message", JULIET)
    if stage == s.SPOKEN_TO_JULIET:
        return _stage_twenty(snap)
    if stage == s.PASSED_MESSAGE:
        return _talk_at_stage(30, 'ask Father Lawrence for help', LAWRENCE)
    if stage == s.SPOKEN_TO_FATHER:
        return _talk_at_stage(40, 'ask the Apothecary for a Cadava potion', APOTHECARY)
    if stage == s.SPOKEN_TO_APOTHECARY:
        return _stage_fifty(snap)
    if stage == s.JULIET_IN_CRYPT:
        return _talk_at_stage(60, 'tell Romeo that Juliet took the potion', ROMEO)
    return quest_step('wait', reason=f'unrecognized Romeo & Juliet stage {stage}')


romeojuliet = QuestModule(
    record=quest_record('romeojuliet'),
    bank=VARROCK_WEST_BANK,
    owns_inventory=True,
    read_stage=read_romeo_juliet_stage,
    decide=decide,
)
