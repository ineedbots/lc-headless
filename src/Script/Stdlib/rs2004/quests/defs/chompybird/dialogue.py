"""Ported from rs2b0t's src/bot/api/ai/quests/defs/chompybird/dialogue.ts (MIT, see thirdparty/rs2b0t)."""

import _core
from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.execution import event_signal
from rs2004.game import reader
from rs2004.quests.exec.primitives import open_dialogue, pick_by_line, pick_preferred

__all__ = ['clear_box', 'box_text', 'talk_boxes']

CONTINUE_LABEL = 'Click here to continue'


# Why: `~objbox` and `~mesbox` build a main modal and suspend the script on `p_pausebutton`, and neither ChatDialog nor driveUntil can see one.
# Why: Rantz uses main-modal boxes throughout the quest, which the chat-only driver cannot see.
def clear_box():
    """Click through an objbox sitting on main. False when nothing was up."""
    if reader.modals().main == -1:
        return False
    cont = reader.main_modal_button_near_text(CONTINUE_LABEL)
    # Why: rs2b0t sends the pause button and falls back to the plain button; click_component sends whichever the
    # component is.
    if cont > 0:
        _core.click_component(cont)
    else:
        _core.close_interfaces()
    yield from execution.delay_ticks(1)
    return True


def box_text():
    """The text the main modal is showing, flattened and lower-cased."""
    return ' '.join(' '.join(reader.main_modal_texts()).split()).lower()


# Why: several of Rantz's option lists offer a refusal first ("Er, make you're own 'stabbers'!"), so an unmatched fall-through is worse than stopping.
# Why: a scripted chain leaves silent gaps, so quiet only counts as the end after several polls.
QUIET_POLLS = 6


def drive_boxes(drive, log):
    """Drive a chain of chat pages, option lists and objboxes until the goal lands."""
    deadline = _core.step_time() + ((drive.ms if drive.ms is not None else 30000))
    done = (drive.expect if drive.expect is not None else (lambda: False))
    spent = set()

    def available():
        return [p for p in ((drive.prefer if drive.prefer is not None else [])) if not (p in spent)]

    spoken = []
    acted = False
    quiet = 0
    while _core.step_time() < deadline:
        if done():
            return True
        # Why: a random event or a death has to end the conversation, or the step sits out its window before the host can act.
        if event_signal.pending():
            return done()
        opts = chat_dialog.options()
        if len(opts) == 0 and chat_dialog.is_open():
            texts = chat_dialog.texts()
            if len(texts) > 0:
                spoken = texts
        if len(opts) > 0:
            _v1 = pick_by_line(spoken, opts, (drive.rules if drive.rules is not None else []))
            pick = (_v1 if _v1 is not None else pick_preferred(opts, available()))
            if not pick:
                if drive.strict != False:
                    log(f"no rule or preference matched [{' | '.join(opts)}] after \"{' '.join(spoken)}\"")
                    return done()
                yield from chat_dialog.choose_option(opts[len(opts) - 1])
            else:
                one_shot = ([p for p in ((drive.once if drive.once is not None else [])) if (p.lower() in pick.lower())] or [None])[0]
                if one_shot is not None:
                    spent.add(one_shot)
                yield from chat_dialog.choose_option(pick)
            # Why: an option that opens an objbox needs the box seen before the next page is read.
            spoken = []
            acted = True
            quiet = 0
            yield from execution.delay_ticks(2)
            continue
        if chat_dialog.can_continue():
            yield from chat_dialog.continue_()
            acted = True
            quiet = 0
            yield from execution.delay_ticks(1)
            continue
        _w2 = yield from clear_box()
        if _w2:
            acted = True
            quiet = 0
            continue
        if acted:
            quiet += 1
        if acted and quiet >= QUIET_POLLS:
            return (done() if drive.expect else True)
        yield from execution.delay_ticks(1)
    return (done() if drive.expect else acted)


def talk_boxes(npc, drive, log):
    """Open a conversation, then drive it to a goal through whatever boxes it raises."""
    if drive.expect is not None and drive.expect():
        return True
    # Why: a box left up by the last step swallows the talk click outright.
    yield from clear_box()
    _w4 = yield from open_dialogue(npc, log)
    if not (_w4):
        return False
    _result5 = yield from drive_boxes(drive, log)
    return _result5
