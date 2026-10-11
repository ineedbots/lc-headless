"""Chat dialogues, option lists and make menus, and the main modal. Mirrors rs2b0t's api/ui/dialogue/ChatDialog.ts
and api/ui/widgets/Modals.ts (MIT, see thirdparty/rs2b0t).

    while chat_dialog.can_continue():
        yield from chat_dialog.continue_()
    yield from chat_dialog.choose_option('Yes')
    yield from chat_dialog.make_x('Long Bow', 27)

Each one is recognised by its shape, not its ids. Options are the chat box's text buttons; a make menu is a
stack of buttons, one per amount, over each product, such as fletching's "Make 1" to "Make X"; a make panel is
an inventory whose options make things, such as the anvil's.
"""

import _core
from rs2004 import execution

__all__ = ['MakeProduct', 'chat_dialog', 'modals', 'MAKE_X', 'MAKE_ALL']

# A button's amount when it asks for the count, and when it makes as many as there are materials for.
MAKE_X = -1
MAKE_ALL = 0

RESPONSE_TIMEOUT_MS = 3000
PANEL_TIMEOUT_MS = 5000
COUNT_DIALOG_TIMEOUT_MS = 5000


def _item_name(id):
    if id is None or id < 0:
        return None
    type = _core.get_item_type(id)
    return type.name if type is not None else None


def _matches(part, *names):
    if part is None:
        return True
    wanted = part.lower()
    for name in names:
        if name is not None and wanted in name.lower():
            return True
    return False


def _responded(before):
    """Waits for the server to open, close or change a modal, which is how it answers a click on a dialogue."""
    changed = yield from execution.delay_until(lambda: _core.modal_changes() != before, RESPONSE_TIMEOUT_MS)
    return changed


class MakeProduct:
    """A product in a make menu: name, item (the item drawn over its buttons, or None) and item_name, and
    amounts, what its buttons make: counts, MAKE_X for the one that asks, MAKE_ALL for one that makes all."""

    def __init__(self, name, item, buttons):
        self.name = name
        self.item = item if item >= 0 else None
        self.item_name = _item_name(self.item)
        self.amounts = [amount for amount, com in buttons]
        self._buttons = buttons

    def button(self, amount):
        """The component of the button that makes amount, or None."""
        for made, com in self._buttons:
            if made == amount:
                return com
        return None

    def largest(self):
        """The button that makes the most without asking: MAKE_ALL, else the largest count. None without one."""
        if MAKE_ALL in self.amounts:
            return self.button(MAKE_ALL)
        counts = [amount for amount in self.amounts if amount > 0]
        return self.button(max(counts)) if counts else None

    def __repr__(self):
        return f'MakeProduct(name={repr(self.name)}, item={self.item}, amounts={self.amounts})'


def _panel_items():
    items = []
    for item, product in _core.get_make_panel():
        item.product = product
        if product != item.id:
            item.name = _item_name(product)
        items.append(item)
    return items


def _panel_amount(option):
    """What an inventory make option makes: 1 for 'Make', 5 for 'Make 5'; None for one that doesn't make."""
    words = option.lower().split()
    if not words or words[0] != 'make':
        return None
    if len(words) == 1:
        return 1
    try:
        return int(words[1])
    except:
        return None


class _ChatDialog:
    """The chat box: dialogue pages, option lists and make menus. Names and options match by part, without
    regard to case, as rs2b0t's do. Each method that waits is a generator, used with yield from, and returns
    whether the server answered."""

    def is_open(self):
        return _core.get_chat_modal() != -1

    def can_continue(self):
        """A "Click here to continue" is showing and hasn't been clicked."""
        return _core.find_continue() is not None

    def continue_(self):
        """Clicks "Click here to continue" and waits for what comes next."""
        before = _core.modal_changes()
        if not _core.continue_dialogue():
            return False
        responded = yield from _responded(before)
        return responded

    def options(self):
        """The choices on offer, as the player reads them."""
        return [text for com, text in _core.get_chat_options()]

    def choose_option(self, text=None):
        """Chooses the first option containing text, or the first option, and waits for what comes next."""
        for com, option in _core.get_chat_options():
            if _matches(text, option):
                before = _core.modal_changes()
                if not _core.click_component(com):
                    return False
                responded = yield from _responded(before)
                return responded
        return False

    def texts(self):
        """The chat box's lines, such as the speaker's name and what they say."""
        return _core.get_chat_texts()

    def products(self):
        """The make menu's products, as MakeProducts."""
        return [MakeProduct(name, item, buttons) for name, item, buttons in _core.get_make_products()]

    def is_make_menu(self):
        return len(_core.get_make_products()) > 0

    def make_products(self):
        """The products' names."""
        return [product.name for product in self.products()]

    def _product(self, name):
        for product in self.products():
            if _matches(name, product.name, product.item_name):
                return product
        return None

    def _click(self, com):
        if com is None:
            return False
        before = _core.modal_changes()
        if not _core.click_component(com):
            return False
        responded = yield from _responded(before)
        return responded

    def make(self, name=None):
        """Makes as many of the product whose name contains name, or the first, as one button does without asking."""
        product = self._product(name)
        if product is None:
            return False
        made = yield from self._click(product.largest())
        return made

    def make_one(self, name=None):
        product = self._product(name)
        if product is None:
            return False
        made = yield from self._click(product.button(1))
        return made

    def make_x(self, name, count):
        """Clicks the product's X button, answers the count dialog with count, and waits for it to close."""
        product = self._product(name)
        com = product.button(MAKE_X) if product is not None else None
        if com is None or not _core.click_component(com):
            return False
        # The count dialog can come a tick after the click.
        opened = yield from execution.delay_until(lambda: _core.is_count_dialog_open(), COUNT_DIALOG_TIMEOUT_MS)
        if not opened:
            return False
        return _core.answer_count(count)

    def is_main_make_panel(self):
        return len(_core.get_make_panel()) > 0

    def main_make_products(self):
        """The panel's products' names, slot by slot."""
        return [item.name for item in _panel_items()]

    def _panel_item(self, name):
        for item in _panel_items():
            if _matches(name, item.name):
                return item
        return None

    def _use_panel(self, item, op):
        before = _core.modal_changes()
        if not item.interact(op):
            return False
        responded = yield from execution.delay_until(lambda: _core.modal_changes() != before, PANEL_TIMEOUT_MS)
        return responded

    def make_from_panel(self, name, op=None):
        """Uses option op ('Make 5'), or the first, on the panel product whose name contains name."""
        item = self._panel_item(name)
        if item is None:
            return False
        actions = item.actions()
        if op is None:
            if not actions:
                return False
            op = actions[0]
        made = yield from self._use_panel(item, op)
        return made

    def make_from_panel_max(self, name):
        """Uses the option that makes the most of the panel product whose name contains name."""
        item = self._panel_item(name)
        if item is None:
            return False
        best = None
        best_amount = 0
        for action in item.actions():
            amount = _panel_amount(action)
            if amount is not None and amount > best_amount:
                best = action
                best_amount = amount
        if best is None:
            return False
        made = yield from self._use_panel(item, best)
        return made


class _Modals:
    """The main modal: the bank, a shop, the anvil and the rest."""

    def main(self):
        return _core.get_main_modal()

    def is_open(self):
        return _core.get_main_modal() != -1

    def close(self):
        """Closes the open interfaces and waits for the main modal to go. True when there was none."""
        before = _core.get_main_modal()
        if before == -1:
            return True
        _core.close_interfaces()
        closed = yield from execution.delay_until(lambda: _core.get_main_modal() != before, RESPONSE_TIMEOUT_MS)
        return closed

    def close_if_open(self):
        if _core.get_main_modal() != -1:
            yield from self.close()


chat_dialog = _ChatDialog()
modals = _Modals()
