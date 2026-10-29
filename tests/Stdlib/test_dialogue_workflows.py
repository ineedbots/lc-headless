"""Dialogue and crafting interactions over delayed modal and count-dialog updates."""

import rs2004.dialogue as dialogue
from rs2004 import execution
from helpers import FakeModule


class PanelItem:
    def __init__(self, world, id, name, actions):
        self.world = world
        self.id = id
        self.name = name
        self.ops = actions

    def actions(self):
        return self.ops

    def interact(self, op):
        self.world.clicks.append((self.id, op))
        if self.world.accept_click:
            self.world.pending = 'page'
        return self.world.accept_click


class DialogueWorld:
    def __init__(self):
        self.pages = []
        self.products = []
        self.panel = []
        self.item_names = {50: 'Oak longbow', 51: 'Bronze dagger'}
        self.count_buttons = []
        self.now = 0
        self.generation = 0
        self.accept_click = True
        self.accept_answer = True
        self.respond = True
        self.count_open = False
        self.pending = None
        self.clicks = []
        self.answers = []
        self.waits = []
        self.logs = []

    def __enter__(self):
        self.saved = (dialogue._core, execution._core)
        dialogue._core = self
        execution._core = self
        return self

    def __exit__(self, *args):
        dialogue._core, execution._core = self.saved

    def kind(self):
        return self.pages[0][0] if self.pages else 'closed'

    def step_time(self):
        return self.now

    def modal_changes(self):
        return self.generation

    def get_chat_modal(self):
        return 100 if self.kind() in ['continue', 'options', 'waiting', 'goal'] else -1

    def get_main_modal(self):
        return 200 if self.kind() == 'main' else -1

    def find_continue(self):
        return 101 if self.kind() == 'continue' else None

    def continue_dialogue(self):
        self.clicks.append('continue')
        if not self.accept_click or self.kind() != 'continue':
            return False
        self.pending = 'page'
        return True

    def get_chat_options(self):
        return list(enumerate(self.pages[0][1], 110)) if self.kind() == 'options' else []

    def get_chat_texts(self):
        return self.pages[0][1] if self.pages else []

    def click_component(self, com):
        self.clicks.append(com)
        if not self.accept_click:
            return False
        self.pending = 'count' if com in self.count_buttons else 'page'
        return True

    def close_interfaces(self):
        self.clicks.append('close')
        self.pending = 'page'

    def get_make_products(self):
        return self.products

    def get_make_panel(self):
        return self.panel

    def get_item_type(self, id):
        name = self.item_names.get(id)
        return FakeModule(name=name) if name is not None else None

    def is_count_dialog_open(self):
        return self.count_open

    def answer_count(self, count):
        self.answers.append(count)
        if self.accept_answer:
            self.count_open = False
        return self.accept_answer

    def advance(self):
        if self.respond and self.pending is not None:
            if self.pending == 'count':
                self.count_open = True
            else:
                if self.pages:
                    self.pages.pop(0)
                self.generation += 1
            self.pending = None

    def run(self, task):
        for guard in range(200):
            try:
                wait = next(task)
            except StopIteration as stopped:
                return stopped.value
            assert isinstance(wait, execution.Update) or isinstance(wait, execution.Ticks)
            self.waits.append(wait)
            self.now += 500
            self.advance()
        assert False, 'dialogue exceeded its simulated update budget'


def test_continue_waits_for_modal_update_and_reports_server_timeout():
    for responds in [True, False]:
        with DialogueWorld() as world:
            world.pages = [('continue', ['Hello'])]
            world.respond = responds
            assert dialogue.chat_dialog.is_open() and dialogue.chat_dialog.can_continue()
            assert world.run(dialogue.chat_dialog.continue_()) == responds
            assert world.clicks == ['continue']
            assert len(world.waits) >= 1
            if not responds:
                assert world.now >= dialogue.RESPONSE_TIMEOUT_MS


def test_refused_continue_does_not_wait_or_dismiss_page():
    with DialogueWorld() as world:
        world.pages = [('continue', ['Hello'])]
        world.accept_click = False
        assert world.run(dialogue.chat_dialog.continue_()) is False
        assert world.waits == []
        assert dialogue.chat_dialog.texts() == ['Hello']


def test_option_selection_matches_fragment_without_case_and_waits_for_reply():
    with DialogueWorld() as world:
        world.pages = [('options', ['No thanks', 'Yes, please!'])]
        assert dialogue.chat_dialog.options() == ['No thanks', 'Yes, please!']
        assert world.run(dialogue.chat_dialog.choose_option('PLEASE'))
        assert world.clicks == [111]
        assert not dialogue.chat_dialog.is_open()


def test_missing_option_does_not_fall_back_to_first_choice():
    with DialogueWorld() as world:
        world.pages = [('options', ['Refuse', 'Leave'])]
        assert world.run(dialogue.chat_dialog.choose_option('Yes')) is False
        assert world.clicks == []
        assert world.run(dialogue.chat_dialog.choose_option()) is True
        assert world.clicks == [110]


def test_rejected_option_click_leaves_dialogue_unchanged():
    with DialogueWorld() as world:
        world.pages = [('options', ['Yes'])]
        world.accept_click = False
        assert world.run(dialogue.chat_dialog.choose_option('yes')) is False
        assert world.waits == [] and dialogue.chat_dialog.is_open()


def test_make_prefers_all_over_fixed_counts_and_matches_item_name():
    with DialogueWorld() as world:
        world.products = [('String bow', 50, [(1, 301), (10, 310), (dialogue.MAKE_ALL, 399)])]
        assert dialogue.chat_dialog.is_make_menu()
        assert dialogue.chat_dialog.make_products() == ['String bow']
        assert world.run(dialogue.chat_dialog.make('OAK'))
        assert world.clicks == [399]


def test_make_chooses_largest_fixed_count_when_all_is_absent():
    with DialogueWorld() as world:
        world.products = [('Bow', -1, [(1, 301), (10, 310), (5, 305)])]
        assert world.run(dialogue.chat_dialog.make())
        assert world.clicks == [310]
        product = dialogue.chat_dialog.products()[0]
        assert product.item is None and product.item_name is None
        assert 'MakeProduct' in repr(product)


def test_make_one_uses_single_button_and_does_not_fall_back_to_bulk():
    with DialogueWorld() as world:
        world.products = [('Bow', 50, [(1, 301), (10, 310)])]
        assert world.run(dialogue.chat_dialog.make_one('bow'))
        assert world.clicks == [301]
        world.products = [('Bow', 50, [(10, 310)])]
        assert world.run(dialogue.chat_dialog.make_one('bow')) is False
        assert world.clicks == [301]


def test_unknown_product_and_only_make_x_menu_do_not_send_bulk_clicks():
    with DialogueWorld() as world:
        world.products = [('Bow', 50, [(dialogue.MAKE_X, 350)])]
        assert world.run(dialogue.chat_dialog.make('dagger')) is False
        assert world.run(dialogue.chat_dialog.make_one('dagger')) is False
        assert world.run(dialogue.chat_dialog.make('bow')) is False
        assert world.clicks == []


def test_make_x_waits_for_count_dialog_before_answering():
    with DialogueWorld() as world:
        world.products = [('Bow', 50, [(dialogue.MAKE_X, 350)])]
        world.count_buttons = [350]
        assert world.run(dialogue.chat_dialog.make_x('bow', 27))
        assert world.clicks == [350] and world.answers == [27]
        assert len(world.waits) == 1 and not world.count_open


def test_make_x_never_answers_when_count_dialog_does_not_arrive():
    with DialogueWorld() as world:
        world.products = [('Bow', 50, [(dialogue.MAKE_X, 350)])]
        world.respond = False
        assert world.run(dialogue.chat_dialog.make_x('bow', 27)) is False
        assert world.now >= dialogue.COUNT_DIALOG_TIMEOUT_MS
        assert world.answers == []


def test_make_x_missing_button_or_rejected_click_does_not_wait():
    with DialogueWorld() as world:
        assert world.run(dialogue.chat_dialog.make_x('bow', 27)) is False
        world.products = [('Bow', 50, [(dialogue.MAKE_X, 350)])]
        world.accept_click = False
        assert world.run(dialogue.chat_dialog.make_x('bow', 27)) is False
        assert world.waits == [] and world.answers == []


def test_answer_count_requires_open_dialog_and_reports_rejected_answer():
    with DialogueWorld() as world:
        assert not dialogue.chat_dialog.answer_count(5)
        assert world.answers == []
        world.count_open = True
        world.accept_answer = False
        assert not dialogue.chat_dialog.answer_count(5)
        assert world.answers == [5] and world.count_open


def test_panel_uses_product_name_instead_of_displayed_material_name():
    with DialogueWorld() as world:
        item = PanelItem(world, 2349, 'Bronze bar', ['Make', 'Make 5', 'Make 10'])
        world.panel = [(item, 51)]
        assert dialogue.chat_dialog.is_main_make_panel()
        assert dialogue.chat_dialog.main_make_products() == ['Bronze dagger']
        assert world.run(dialogue.chat_dialog.make_from_panel_max('DAGGER'))
        assert world.clicks == [(2349, 'Make 10')]
        assert item.product == 51


def test_panel_default_or_explicit_option_is_sent_to_selected_item():
    for op in [None, 'Make 5']:
        with DialogueWorld() as world:
            item = PanelItem(world, 51, 'Bronze dagger', ['Make', 'Make 5'])
            world.panel = [(item, 51)]
            assert world.run(dialogue.chat_dialog.make_from_panel('dagger', op))
            assert world.clicks == [(51, 'Make' if op is None else op)]


def test_panel_max_ignores_unrelated_and_nonnumeric_options():
    with DialogueWorld() as world:
        item = PanelItem(world, 51, 'Bronze dagger', ['Examine', 'Make X', 'Make', 'Make 5'])
        world.panel = [(item, 51)]
        assert world.run(dialogue.chat_dialog.make_from_panel_max('dagger'))
        assert world.clicks == [(51, 'Make 5')]


def test_panel_missing_product_or_make_option_never_sends_click():
    with DialogueWorld() as world:
        item = PanelItem(world, 51, 'Bronze dagger', [])
        world.panel = [(item, 51)]
        assert world.run(dialogue.chat_dialog.make_from_panel('bow')) is False
        assert world.run(dialogue.chat_dialog.make_from_panel_max('bow')) is False
        assert world.run(dialogue.chat_dialog.make_from_panel('dagger')) is False
        assert world.run(dialogue.chat_dialog.make_from_panel_max('dagger')) is False
        assert world.clicks == []


def test_panel_rejected_click_or_missing_response_returns_failure():
    for refused in [True, False]:
        with DialogueWorld() as world:
            item = PanelItem(world, 51, 'Bronze dagger', ['Make'])
            world.panel = [(item, 51)]
            world.accept_click = not refused
            world.respond = refused
            assert world.run(dialogue.chat_dialog.make_from_panel('dagger')) is False
            if not refused:
                assert world.now >= dialogue.PANEL_TIMEOUT_MS


def test_close_modal_waits_for_change_and_handles_absent_modal():
    with DialogueWorld() as world:
        assert world.run(dialogue.modals.close())
        assert world.clicks == []
        world.pages = [('main', ['Message'])]
        assert dialogue.modals.main() == 200 and dialogue.modals.is_open()
        world.run(dialogue.modals.close_if_open())
        assert not dialogue.modals.is_open()
        assert world.clicks == ['close']
        world.run(dialogue.modals.close_if_open())
        assert world.clicks == ['close']
