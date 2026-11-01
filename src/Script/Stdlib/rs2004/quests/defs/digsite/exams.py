"""Ported from rs2b0t's src/bot/api/ai/quests/defs/digsite/exams.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004 import execution
from rs2004.catalogs.record import Record
from rs2004.dialogue import modals
from rs2004.items import inventory
from rs2004.quests.defs.digsite.areas import DIG_ID, DIG_LOC, DIG_NPC, DIG_TILE
from rs2004.quests.defs.digsite.common import drive_until_held, loc_by_id_action, talk_to_npc_id, use_on_npc_id, walk_to
from rs2004.quests.defs.digsite.journal import DIG_STAGE
from rs2004.quests.engine.types import has_flag
from rs2004.quests.exec.prompts import settle_scene

__all__ = ['EXAMINER_PREFER', 'talk_to_examiner', 'replace_trowel', 'stamp_letter', 'search_bush', 'DELIVER_GREEN', 'DELIVER_PURPLE', 'DELIVER_ORANGE', 'study_with_students', 'exam_ready', 'answered']

# Why: The exam only offers unlocked correct answers, so one preference list covers all nine questions without including wrong choices.
EXAMINER_PREFER = [
    'Can I take an exam?',
    'Yes, I certainly am.',
    'I am ready for the next exam.',
    'I am ready for the last exam',
    'I have lost the letter you gave me.',
    'The study of the earth, its contents, and history.',
    'All that have passed the appropriate Earth Sciences exam.',
    'Gloves and boots to be worn at all times; proper tools must be used.',
    'Samples taken in rough form; kept only in sealed containers.',
    'Finds must be carefully handled, and gloves worn.',
    'Always handle with care; strike cleanly on its cleaving point.',
    'Samples cleaned, and carried only in specimen jars.',
    'Brush carefully and slowly using short strokes.',
    'Handle bones very carefully and keep them away from other samples.',
]
TROWEL_PREFER = ['I have lost my trowel.']


def talk_to_examiner(name, prefer=None):
    if prefer is None:
        prefer = EXAMINER_PREFER
    return Record({
        'kind': 'custom',
        'name': name,
        'run': lambda log: talk_to_npc_id(DIG_NPC.EXAMINER, DIG_TILE.EXAMINER, prefer, log, True),
    })


def replace_trowel():
    return talk_to_examiner('ask the Examiner for another trowel', TROWEL_PREFER)


def stamp_letter():
    """The Curator stamps whatever letter is in the pack as soon as the conversation opens."""

    def _fn1(log):
        _w2 = yield from talk_to_npc_id(DIG_NPC.CURATOR, DIG_TILE.CURATOR, [], log)
        if not (_w2):
            return False
        _result3 = yield from drive_until_held(lambda: inventory.count_by_id(DIG_ID.STAMPED_LETTER) > 0, [], log)
        return _result3
    return Record({'kind': 'custom', 'name': 'have the Curator stamp the letter', 'run': _fn1})


def search_bush():
    """The purple student's sample lies in one named bush at the edge of the site."""

    def _fn4(log):
        if inventory.count_by_id(DIG_ID.ROCK_SAMPLE_PURPLE) > 0:
            return True
        _w5 = yield from walk_to(DIG_TILE.BUSH_STAND, 1, log)
        if not (_w5):
            return False
        yield from settle_scene()
        bush = loc_by_id_action([DIG_LOC.BUSH_SAMPLE], 'Search', 6)
        if not bush:
            log('no sample bush within six tiles of (3358,3372)')
            return False
        if not (bush.interact('Search')):
            return False
        _result6 = yield from drive_until_held(lambda: inventory.count_by_id(DIG_ID.ROCK_SAMPLE_PURPLE) > 0, [], log, 15000)
        return _result6
    return Record({'kind': 'custom', 'name': "search the bush for the purple student's sample", 'run': _fn4})


def _gone(item_id):
    return lambda: inventory.count_by_id(item_id) == 0


def deliver(item_id, npc_id, label):
    gone = _gone(item_id)
    return Record({
        'kind': 'custom',
        'name': label,
        'run': lambda log: use_on_npc_id(item_id, npc_id, DIG_TILE.STUDENTS, gone, log),
    })


def DELIVER_GREEN():
    return deliver(DIG_ID.ROCK_SAMPLE_GREEN, DIG_NPC.STUDENT_GREEN, "return the green student's rock sample")


def DELIVER_PURPLE():
    return deliver(DIG_ID.ROCK_SAMPLE_PURPLE, DIG_NPC.STUDENT_PURPLE, "return the purple student's rock sample")


def DELIVER_ORANGE():
    return deliver(DIG_ID.ROCK_SAMPLE_ORANGE, DIG_NPC.STUDENT_ORANGE, "return the orange student's rock sample")


# Why: from the second exam on, the errand is one conversation with each student; the purple student takes the third exam's opal in her own dialogue.
def study_with_students(stage):
    order = ([DIG_NPC.STUDENT_GREEN, DIG_NPC.STUDENT_ORANGE, DIG_NPC.STUDENT_PURPLE] if stage == DIG_STAGE.THIRD_EXAM else [DIG_NPC.STUDENT_GREEN, DIG_NPC.STUDENT_PURPLE, DIG_NPC.STUDENT_ORANGE])

    def _fn7(log):
        spoke = 0
        for npc in order:
            _w8 = yield from talk_to_npc_id(npc, DIG_TILE.STUDENTS, [], log)
            if _w8:
                spoke += 1
            yield from modals.close_if_open()
            yield from execution.delay_ticks(1)
        # Why: the purple student asks for the opal on the first pass and takes it on the second, so one extra turn saves an engine round trip.
        if stage == DIG_STAGE.THIRD_EXAM and inventory.count_by_id(DIG_ID.OPAL) > 0:
            _w9 = yield from talk_to_npc_id(DIG_NPC.STUDENT_PURPLE, DIG_TILE.STUDENTS, [], log)
            if _w9:
                spoke += 1
            yield from modals.close_if_open()
        if spoke == 0:
            log('none of the three students would talk')
        return spoke > 0
    return Record({'kind': 'custom', 'name': f'revise with the three students for exam {stage - 1}', 'run': _fn7})


def exam_ready(snap):
    """Whether the journal says all 3 errands are answered and the exam can be taken."""
    return has_flag(snap.progress, 'exam-ready')


def answered(snap, flag):
    return has_flag(snap.progress, flag)
