"""Run the real AIOQuester, report its outcome, and log out when its queue stops."""

import json
from result_policy import completion_passed
from bots.aio_quester import AIOQuester, AIO_SETTINGS
from bots.aioquester.logic import queue_summary
from rs2004 import execution
from rs2004.dialogue import chat_dialog
from rs2004.entities import npcs, ground_items
from rs2004.game import chat, game, reader, skills
from rs2004.items import inventory, equipment
from rs2004.tabs import prayer, quests
from rs2004.quests.defs import record_by_id


class AcceptanceQuester(AIOQuester):
    def on_start(self):
        yield from AIOQuester.on_start(self)
        self.e2e_records = [record_by_id(id) for id in self.picked_ids()]
        self.e2e_initial_done = [r.id for r in self.e2e_records if quests.status(r.name) == 'complete']
        if self.settings.bool('e2e_infinite_run', True):
            chat.command('infiniterun')
            yield from execution.delay_ticks(2)

    def finish(self, reason):
        self.e2e_finish_reason = str(reason)
        stop_account()

    def on_stop(self, reason):
        case = self.settings.str('e2e_case', '')
        summary = queue_summary(getattr(self, 'rows', []))
        deaths = getattr(self, 'deaths', 0)
        completed = getattr(self, 'completed', 0)
        records = getattr(self, 'e2e_records', [])
        initial = getattr(self, 'e2e_initial_done', [])
        journal = {r.id: quests.status(r.name) for r in records}
        complete = len(records) > 0 and all([status == 'complete' for status in journal.values()])
        expected_qp = self.settings.num('e2e_expected_qp', 0)
        passed = completion_passed(journal, initial, completed, deaths, summary, quests.points(), expected_qp)
        AIOQuester.on_stop(self, reason)
        self.log('E2E_RESULT ' + json.dumps({'case': case, 'name': game.my_name(), 'passed': passed,
                                          'quest_complete': complete, 'completed': completed, 'deaths': deaths,
                                          'journal': journal, 'initial_done': initial,
                                          'queue': summary, 'qp': quests.points(), 'tile': str(game.tile()),
                                          'reason': getattr(self, 'e2e_finish_reason', str(reason))}))


def inspect_state(command):
    log('INSPECT tile', game.tile(), 'modals', reader.modals(), 'hp', skills.effective('hitpoints'), 'prayer', prayer.points())
    log('INSPECT chat', chat_dialog.texts(), 'options', chat_dialog.options(), 'continue', chat_dialog.can_continue())
    log('INSPECT main', reader.main_modal_texts())
    log('INSPECT pack', [(i.id, i.name, i.count) for i in inventory.items()])
    log('INSPECT worn', [(i.id, i.name) for i in equipment.items()])
    log('INSPECT ground', [(i.id, i.name, i.count, i.tile()) for i in ground_items.query().within(12).results()])
    log('INSPECT npcs', [(i.id, i.name, i.tile(), i.health, i.max_health) for i in npcs.query().within(15).results()])


console.command('inspect', inspect_state, 'Inspect the live acceptance character')
SCHEMA = {key: value for key, value in AIO_SETTINGS.items()}
SCHEMA['e2e_case'] = SettingDef('string', '')
SCHEMA['e2e_expected_qp'] = SettingDef('number', 0)
SCHEMA['e2e_infinite_run'] = SettingDef('boolean', True)
BOT = define_bot(name='AIOQuester', create=AcceptanceQuester, settings_schema=SCHEMA)
