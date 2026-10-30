"""Tab controls wait for prayer, journal, special and autocast server updates."""

import rs2004.tabs as tabs
from helpers import FakeModule
from coverage_world import PatchWorld


def piece(id, **fields):
    values = {'id': id, 'type': 'graphic', 'button': None, 'button_text': None, 'text': '', 'visible': True,
              'varp': None, 'value': None, 'x': 0, 'y': 0, 'height': 20, 'width': 20, 'layer': 1, 'target_name': None}
    values.update(fields)
    return FakeModule(**values)


class TabWorld(PatchWorld):
    def __init__(self):
        PatchWorld.__init__(self)
        self.values = {tabs.SA_ENERGY_VARP: 500, tabs.QUEST_POINTS_VARP: 7}
        self.points, self.max_points = 50, 50
        self.accept, self.arrives, self.staff = True, True, True
        self.combat_root, self.main = 100, -1
        self.pending_tab = None
        self.components = {
            100: [piece(1, button='select', varp=tabs.ATTACKSTYLE_MAGIC_VARP),
                  piece(2, button='ok', button_text='Special Attack')],
            200: [piece(20 + i, button='toggle', varp=1000 + i) for i in range(len(tabs.PRAYER_NAMES))],
            300: [piece(50, type='text', text="Cook's Assistant", button='ok', colour=0x00FF00)],
            400: [piece(60, button='target', target_name='Wind strike'), piece(61, button='ok', button_text='Cast Varrock teleport')],
            500: [piece(70, button='ok')],
        }
        self.clicks = []
        self.interface_reads = 0
        self.quest_root = 300

    def __enter__(self):
        PatchWorld.__enter__(self)
        self.patch(tabs, '_core', self)
        self.patch(tabs, 'equipment', FakeModule(items=lambda: []))
        return self

    def get_tab_interface(self, tab):
        return {0: self.combat_root, 2: self.quest_root, 5: 200, 6: 400}.get(tab, -1)

    def get_open_interfaces(self):
        return [self.combat_root, 200, 300, 400]

    def get_interface(self, root):
        self.interface_reads += 1
        return self.components.get(root, [])

    def get_texts(self, root):
        if root == 100:
            return ['Choose'] if self.staff else []
        return ['Quest complete'] if root == 600 else []

    def get_varp(self, id):
        return self.values.get(id, 0)

    def get_current_stat(self, id):
        return self.points

    def get_max_stat(self, id):
        return self.max_points

    def get_main_modal(self):
        return self.main

    def click_text(self, text, root):
        assert text == 'Choose' and root == 100
        self.clicks.append(text)
        if self.accept:
            self.pending_tab = 'chooser'
        return self.accept

    def click_component(self, id):
        self.clicks.append(id)
        if self.accept:
            self.pending_tab = id
        return self.accept

    def advance(self):
        PatchWorld.advance(self)
        if self.pending_tab is not None and self.arrives:
            id = self.pending_tab
            if id == 'chooser':
                self.combat_root = 500
            elif id == 70:
                self.combat_root = 100
                self.values[tabs.ATTACKSTYLE_MAGIC_VARP] = tabs.AUTOCAST_CHOSEN
            elif id == 1:
                self.values[tabs.ATTACKSTYLE_MAGIC_VARP] = (0 if tabs.autocast.armed() else tabs.AUTOCAST_ARMED)
            elif id == 2:
                self.values[tabs.SA_ARMED_VARP] = 1
            elif id == 50:
                self.main = 600
            elif 20 <= id < 35:
                varp = 1000 + id - 20
                self.values[varp] = 1 - self.values.get(varp, 0)
            self.pending_tab = None


def test_prayer_toggle_waits_for_confirmation_and_clear_drops_active_prayers():
    with TabWorld() as world:
        assert tabs.prayer.full() and tabs.prayer.available('Protect from melee')
        assert world.run(tabs.prayer.set('Protect from melee', True))
        assert tabs.prayer.active('Protect from melee') and world.now == 500
        before = len(world.clicks)
        assert world.run(tabs.prayer.set('Protect from melee', True)) and len(world.clicks) == before
        assert tabs.prayer.toggle('Protect from melee', True)
        world.run(tabs.prayer.clear())
        assert not tabs.prayer.active('Protect from melee')


def test_prayer_missing_unavailable_rejected_and_unacknowledged_toggle():
    with TabWorld() as world:
        assert not tabs.prayer.toggle('unknown', True)
        world.points = 0
        assert not world.run(tabs.prayer.set('Protect from melee', True))
        world.points, world.accept = 50, False
        assert not world.run(tabs.prayer.set('Protect from melee', True)) and world.now == 0
        world.accept, world.arrives = True, False
        assert not world.run(tabs.prayer.set('Protect from melee', True)) and world.now == 2000


def test_journal_waits_for_new_modal_and_handles_missing_or_failed_open():
    with TabWorld() as world:
        assert tabs.quests.status("cook's assistant") == 'complete' and tabs.quests.points() == 7
        assert 'complete' in repr(tabs.quests.all()[0])
        assert world.run(tabs.quests.journal('missing')) == []
        world.accept = False
        assert world.run(tabs.quests.journal("Cook's Assistant")) == []
        world.accept = True
        assert world.run(tabs.quests.journal("Cook's Assistant")) == ['Quest complete']


def test_quest_lookups_share_one_scan_and_refresh_after_server_updates():
    with TabWorld() as world:
        journal = tabs._Quests()
        world.components[300][0].colour = 0xFF0000
        for i in range(100):
            assert journal.status(" COOK'S ASSISTANT ") == 'not_started'
            assert journal.status('missing') == 'unknown'
        assert world.interface_reads == 1
        for colour, status in [(0xFFFF00, 'in_progress'), (0x00FF00, 'complete')]:
            world.now += 500
            world.components[300][0].colour = colour
            assert journal.status("Cook's Assistant") == status
        assert world.interface_reads == 3
        assert world.run(journal.journal("Cook's Assistant")) == ['Quest complete']
        assert world.clicks == [50]


def test_quest_lookup_refreshes_when_its_tab_loads_or_changes():
    with TabWorld() as world:
        journal = tabs._Quests()
        world.quest_root = -1
        assert journal.status("Cook's Assistant") == 'unknown'
        world.quest_root = 300
        assert journal.status("Cook's Assistant") == 'complete'
        world.components[301] = [piece(51, type='text', text="Doric's Quest", button='ok', colour=0xFFFF00)]
        world.quest_root = 301
        assert journal.status("Cook's Assistant") == 'unknown'
        assert journal.status("Doric's Quest") == 'in_progress'
        world.now += 500
        world.components[301][0].text = '@gre@Renamed quest'
        assert journal.status("Doric's Quest") == 'unknown'
        assert journal.status('renamed quest') == 'in_progress'


def test_special_arms_once_and_reports_rejected_or_silent_server():
    for outcome in ['success', 'refused', 'silent']:
        with TabWorld() as world:
            world.accept, world.arrives = outcome != 'refused', outcome != 'silent'
            assert tabs.special.wielded() == '' and tabs.special.ready('Dragon dagger')
            assert world.run(tabs.special.arm()) == (outcome == 'success')
            if outcome == 'success':
                assert world.run(tabs.special.arm()) and world.clicks == [2]


def test_autocast_chooser_selects_spell_arms_and_disarms():
    with TabWorld() as world:
        assert world.run(tabs.autocast.arm('Wind strike', world.logs.append))
        assert tabs.autocast.armed() and world.clicks == ['Choose', 70, 1]
        assert world.run(tabs.autocast.disarm()) and not tabs.autocast.armed()
        assert world.run(tabs.autocast.disarm())
        assert 'armed' in world.logs[-1]


def test_autocast_unknown_spell_non_staff_refused_and_missing_chooser():
    with TabWorld() as world:
        assert world.run(tabs.autocast.arm('unknown', world.logs.append)) is False
        world.staff = False
        assert world.run(tabs.autocast.arm('Wind strike', world.logs.append)) is False
        world.staff, world.accept = True, False
        assert world.run(tabs.autocast.arm('Wind strike')) is False
        world.accept, world.arrives = True, False
        assert world.run(tabs.autocast.arm('Wind strike', world.logs.append)) is False
        assert 'did not open' in world.logs[-1]


def test_tab_spell_buttons_select_buttons_and_combat_labels():
    with TabWorld() as world:
        assert tabs.spell_button('Wind strike') == 60
        assert tabs.teleport_button('Cast Varrock teleport') == 61
        assert tabs._select_button(tabs.ATTACKSTYLE_MAGIC_VARP, None).id == 1
        assert tabs._select_button(999, 1) is None
        world.components[100] = [piece(80, button='select', varp=tabs.COM_MODE_VARP, value=0),
            piece(81, type='text', text='(Accurate)', y=0), piece(82, type='text', text='(Defensive)', y=100)]
        assert tabs.combat_styles() == [(0, '(Accurate)')]
        assert 'attack' in repr(tabs.resolve_combat_style('attack', tabs.combat_styles()))
