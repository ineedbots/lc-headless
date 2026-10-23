# Kills cows at one of the cow fields, picks up their hides, and banks each field at its own bank: rs2b0t's
# CowKiller (MIT, see thirdparty/rs2b0t), which is ChickenKiller with a cow field preset. The Lumbridge field banks
# at Al Kharid through the toll gate, so it keeps 20 coins for the toll.

from rs2004.catalogs import AL_KHARID_BANK, COW_LOCATION_OPTIONS, TOLL_COIN_TARGET, cow_bank_destination, is_cow_field_loot_tile
from rs2004.catalogs import nearest_cow_location, needs_toll_coins, resolve_cow_location, should_bootstrap_toll_coins

from bots.chicken_killer import SETTINGS as CHICKEN_SETTINGS
from bots.chicken_killer import ChickenKiller

PRESET = {'leash_radius': 18, 'target_name': 'Cow', 'loot_match': 'Cowhide', 'bury_bones': False}


def chicken_preset(overrides):
    """ChickenKiller's schema with the overrides' defaults."""
    schema = {}
    for key, definition in CHICKEN_SETTINGS.items():
        if key in overrides:
            definition = SettingDef(definition.type, overrides[key], definition.label, definition.min, definition.max, help=definition.help,
                                    options=definition.options, option_labels=definition.option_labels, group=definition.group,
                                    show_if=definition.show_if)
        schema[key] = definition
    return schema


SETTINGS = {
    'location': SettingDef('string', 'Auto', 'Cow field', options=COW_LOCATION_OPTIONS,
                           help='Auto picks the nearer supported field; Start tile keeps custom cow spots'),
    'al_kharid_toll_coins': SettingDef('boolean', True, 'Keep 20 coins for Al Kharid gate?',
                                       help='withdraws/top-ups 20 coins at Al Kharid bank for the Lumbridge round trip',
                                       show_if={'key': 'location', 'any_of': ['Auto', 'Lumbridge cow field']}),
}
SETTINGS.update(chicken_preset(PRESET))


class CowKiller(ChickenKiller):
    def select_anchor(self, here, hinted):
        setting = self.settings.str('location', 'Auto')
        selected = resolve_cow_location(setting, here)
        if setting.strip().lower() == 'auto' and hinted is not None:
            self.location = nearest_cow_location(hinted)
            self.log(f'recovery restart — resuming {self.location.name}')
            return hinted
        if selected is not None:
            self.location = selected
            self.log(f'cow field: {selected.name} at {selected.anchor}')
            return selected.anchor
        self.location = None
        self.log('cow field: custom start tile')
        return hinted if hinted is not None else here

    def prepare_for_travel(self, start):
        """Use with yield from."""
        if not should_bootstrap_toll_coins(self.location, start, inventory.count('Coins'), self.settings.bool('al_kharid_toll_coins', True)):
            return
        self.status = 'preparing Al Kharid toll coins'
        self.log(f'preparing {TOLL_COIN_TARGET} toll coins before leaving Al Kharid')
        arrived = yield from traversal.walk_resilient(AL_KHARID_BANK, radius=4, timeout_ms=90000, log=lambda m: self.log(f'  {m}'))
        opened = False
        if arrived:
            opened = yield from bank.open_nearest('Bank booth', 'Use-quickly')
        if not opened:
            self.log('could not open Al Kharid bank for toll coins — continuing without them')
            return
        yield from self.top_up_toll_coins()

    def keep_list(self):
        keep = ChickenKiller.keep_list(self)
        return keep + ['Coins'] if self.uses_toll_coins() else keep

    def accepts_loot_at(self, tile):
        return is_cow_field_loot_tile(self.anchor, self.leash, tile)

    def after_bank_deposit(self):
        """Ammo or runes, as ChickenKiller restocks them, then the toll float. Use with yield from."""
        yield from ChickenKiller.after_bank_deposit(self)
        if self.uses_toll_coins():
            yield from self.top_up_toll_coins()

    def bank_destination(self):
        """The field's bank, as the bank_locations() entry PeriodicBank walks to."""
        where = cow_bank_destination(self.location, self.settings.bool('al_kharid_toll_coins', True))
        if where is None:
            return None
        for known in bank_locations():
            t = known['tile']
            if t['x'] == where[1].x and t['z'] == where[1].z and t['level'] == where[1].level:
                return known
        return None

    def uses_toll_coins(self):
        return needs_toll_coins(self.location, self.settings.bool('al_kharid_toll_coins', True))

    def top_up_toll_coins(self):
        """Use with yield from."""
        before = inventory.count('Coins')
        need = TOLL_COIN_TARGET - before
        if need <= 0:
            self.log(f'Al Kharid toll float ready: {before} coins')
            return
        available = bank.count('Coins')
        if available < need:
            self.log(f'Al Kharid toll float needs {need} coins, but the bank only has {available}')
            return
        took = yield from bank.withdraw_x('Coins', need)
        if not took:
            self.log(f'could not withdraw {need} toll coins')
            return
        after = inventory.count('Coins')
        if after < TOLL_COIN_TARGET:
            self.log(f'toll coin withdrawal was short: {after}/{TOLL_COIN_TARGET}')
            return
        self.log(f'Al Kharid toll float ready: {after} coins')


BOT = define_bot(
    name='CowKiller',
    create=CowKiller,
    description='Walks to the Lumbridge, north-west Lumbridge, south-Falador, or East Ardougne cow fields, loots cowhide, and banks each field at its pinned bank',
    category='Combat',
    tags=['lumbridge', 'falador', 'ardougne', 'cowhide', 'bones', 'banking', 'afk'],
    settings_schema=SETTINGS,
)
