"""The game's interfaces, as the player sees them: the cache's components, with what the server set on them.
rs2b0t keeps this layer internal (api/ui/Modals.ts); here it's public, as what the dialogue, bank, shop and
trade facades are built on, and as the way to reach an interface no facade covers.

    interfaces.click_text('Accept')
    options = [c.text for c in interfaces.find(button='ok', root=reader.chat_modal())]
"""

import _core

__all__ = ['Component', 'interfaces']


class Component:
    """A snapshot of one component: id, root (its interface), layer (the layer it's in, or None for a
    root), type ('layer', 'inv', 'rect', 'text', 'graphic', 'model' or 'invtext'), button (None, 'ok',
    'target', 'close', 'toggle', 'select' or 'continue'), button_text, text, colour, hidden, visible, options
    (an inventory's five, None where empty), target_verb and target_name (a spell button's), x and y (from its
    interface's corner), width, height and children (ids)."""

    def click(self):
        """Clicks it as its button type says. False when it isn't visible."""
        return _core.click_component(self.id)

    def __repr__(self):
        text = f', text={repr(self.text)}' if self.text else ''
        return f'Component(id={self.id}, type={self.type}, button={self.button}{text})'


class _Interfaces:
    def component(self, id):
        """The component, or None for an id the cache doesn't have."""
        return _core.get_component(id)

    def root(self, id):
        """The interface's components, from its root down, in drawing order."""
        return _core.get_interface(id)

    def open(self):
        """The ids of the open interfaces: the main, side and chat modals, the overlay, and each tab's."""
        return _core.get_open_interfaces()

    def tab(self, n):
        """The interface in side tab n, 0 to 14, or -1."""
        return _core.get_tab_interface(n)

    def find(self, text=None, button=None, root=None):
        """Visible components with that text (whole, without regard to case) and button type, where each is
        given, in the open interfaces or only in root's."""
        return _core.find_components(text, button, root)

    def click(self, id):
        return _core.click_component(id)

    def click_text(self, text, root=None):
        """Clicks the button under the visible text, as a player clicking on the words would. False when
        there's no such text, or no button under it."""
        return _core.click_text(text, root)


interfaces = _Interfaces()
