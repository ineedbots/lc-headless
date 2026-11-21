"""The selected spell varp may arrive before the restored combat tab."""
import _core
from rs2004.tabs import autocast


def restored_staff_tab():
    state = {'root': 328, 'varp': 0}
    clicks = []

    def choose(text, root):
        assert text == 'Choose' and root == 328
        clicks.append('choose')
        state['root'] = 1829
        return True

    def components(root):
        if root == 1829:
            return [Fake(id=id, button='ok', varp=None) for id in range(1830, 1846)]
        return [Fake(id=349, button='select', varp=108)]

    def click(id):
        if id == 1837:
            clicks.append('spell')
            state['varp'] = 2
        else:
            assert id == 349 and state['root'] == 328
            clicks.append('toggle')
            state['varp'] = 3
        return True

    def wait(condition, timeout):
        if condition():
            return True
        assert state['root'] == 1829 and state['varp'] == 2
        clicks.append('restore')
        state['root'] = 328
        return condition()
        yield

    spy_on(_core, 'get_tab_interface', impl=lambda tab: state['root'])
    spy_on(_core, 'get_texts', returns=['Choose'])
    spy_on(_core, 'get_interface', impl=components)
    spy_on(_core, 'get_varp', impl=lambda varp: state['varp'])
    spy_on(_core, 'click_text', impl=choose)
    spy_on(_core, 'click_component', impl=click)
    spy_on(execution, 'delay_until', impl=wait)
    armed = yield from autocast.arm('Fire Bolt')
    expect(armed).to_be(True)
    expect(clicks).to_equal(['choose', 'spell', 'restore', 'toggle'])


test('autocast waits for the staff tab after the selected-spell varp arrives', restored_staff_tab)
