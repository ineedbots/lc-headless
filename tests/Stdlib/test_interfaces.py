import rs2004.interfaces as ui


class Piece:
    def __init__(self, id, type, text, button, x, y, width=10, height=10):
        self.id = id
        self.type = type
        self.text = text
        self.button = button
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class FakeCore:
    def __init__(self, shown):
        self.shown = shown

    def find_components(self, text, button, root):
        return self.shown


def near(shown, label):
    real = ui._core
    ui._core = FakeCore(shown)
    found = ui.interfaces.button_near_text(label)
    ui._core = real
    return found


def test_a_map_button_is_the_one_nearest_its_place_name():
    glider_map = [Piece(1, 'text', 'Ta Quir Priw', None, 100, 100), Piece(2, 'text', 'Sindarpos', None, 300, 50),
                  Piece(21, 'graphic', None, 'ok', 105, 120), Piece(23, 'graphic', None, 'ok', 300, 70), Piece(9, 'graphic', None, 'close', 101, 101)]
    assert near(glider_map, 'ta quir') == 21
    assert near(glider_map, 'Sindarpos') == 23
    assert near(glider_map, 'Gandius') is None
    assert near([Piece(1, 'text', 'Sindarpos', None, 0, 0)], 'Sindarpos') is None
