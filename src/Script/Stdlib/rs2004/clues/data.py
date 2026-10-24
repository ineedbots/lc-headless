"""The clue database and what goes with it: rs2b0t's api/ai/clues/data/ (cluedb.ts, puzzlePieces.ts, talkAnchors.ts,
killAnchors.ts, digAnchors.ts, challengeAnswers.ts, unreachable.ts, clueGates.ts) and ClueLogic.ts (MIT, see
thirdparty/rs2b0t). The tables are generated into rs2004.catalogs._clues by tools/catalogs/export_rs2b0t.ts.

A clue row is a dict: obj, id, type ('search', 'dig' or 'talk'), and as the row needs them coord (a Tile),
casket_obj and casket_id, npc, needs_sextant, key_from (npc, key_obj, key_id), items, guardian and puzzle (obj,
id)."""

from rs2004.catalogs._clues import CASKET_IDS, CHALLENGE_ANSWERS, CLUE_DB, DIG_ANCHORS, KILL_ANCHORS, PACK_UNREACHABLE, PUZZLE_PIECE_SLOT
from rs2004.catalogs._clues import TALK_ANCHORS

_ANSWER_BY_ID = {}
for _answer in CHALLENGE_ANSWERS:
    _ANSWER_BY_ID[_answer['id']] = _answer['answer']


def challenge_answer(clue_id):
    """The number a challenge scroll's question wants, or None."""
    return _ANSWER_BY_ID.get(clue_id)


# Why: the journal is read at solve time, so an account that has finished the quest walks the clue instead of
# abandoning it, and a clue belongs here only when a quest seals its destination.
CLUE_GATES = {
    3564: {'quest': 'Regicide', 'reason': 'Lord Iorwerth is in the elf camp'},
    3560: {'quest': 'Regicide', 'reason': 'dig site is in Isafdar'},
    3562: {'quest': 'Regicide', 'reason': 'dig site is in Isafdar'},
}


def clue_gate(id, status):
    """Why a quest seals this clue's destination, or None. status(quest) is quests.status; only 'complete'
    opens the gate, since an unloaded tab reads 'unknown'."""
    gate = CLUE_GATES.get(id)
    if gate is None:
        return None
    journal = status(gate['quest'])
    return None if journal == 'complete' else f"{gate['reason']} ({gate['quest']} reads {journal})"


def open_casket_step(casket_obj, casket_id):
    return {'type': 'open-casket', 'casket_obj': casket_obj, 'casket_id': casket_id}


def identify_step(held_ids, db=None, casket_ids=None):
    """The step the held items say comes next: a casket to open first, then a clue row, or None."""
    rows = db if db is not None else CLUE_DB
    caskets = casket_ids if casket_ids is not None else CASKET_IDS
    for id in held_ids:
        casket = caskets.get(id)
        if casket is not None:
            return open_casket_step(casket, id)
    for id in held_ids:
        row = rows.get(id)
        if row is not None:
            return row
    return None
