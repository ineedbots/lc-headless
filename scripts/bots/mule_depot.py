"""Shared-bank dump and supply bot, ported from rs2b0t #878 (MIT, see thirdparty/rs2b0t)."""

import _core

from rs2004.catalogs import Record, ContinueDialog
from rs2004.market.catalog import live_catalog, noted_id
from bots.depot.logic import BANK_OPTIONS, DEFAULT_BANK, MODE_OPTIONS, ROLE_OPTIONS, bank_tile, parse_accounts, parse_item_names
from bots.depot.logic import parse_loadout, plan_deliveries, normalize_account, is_giver_role, pick_request_target, line_key
from bots.depot.tasks import DepotBank, DepotTrade, DepotMove, DepotWait

DEFAULT_ITEMS = [
    'Air rune',
    'water rune',
    'earth rune',
    'fire rune',
    'cosmic rune',
    'law rune',
    'mind rune',
    'body rune',
    'nature rune',
    'chaos rune',
    'death rune',
    'soul rune',
    'blood rune',
    'Bronze arrow',
    'iron arrow',
    'steel arrow',
    'mithril arrow',
    'adamant arrow',
    'rune arrow',
    'rune dart',
    'rune knife',
    'Feather',
    'cowhide',
    'dragonhide',
    'dragon bones',
    'big bones',
    'Snape grass',
    'unicorn horn',
    'limpwurt root',
    'herb',
    'Nature talisman',
    'half of a key',
    'uncut sapphire',
    'uncut emerald',
    'uncut ruby',
    'uncut diamond',
    'chaos talisman',
    'rune javelin',
    'dragon spear',
    'rune spear',
    'shield left half',
    'rune longsword',
    'adamant platebody',
    'rune dagger',
    'adamant full helm',
    'rune sq shield',
    'rune battleaxe',
    'runite bar',
    'runite ore',
    'rune kiteshield',
    'rune scimitar',
    'rune sword',
    'rune full helm',
    'dragon platelegs',
    'dragon plateskirt',
    'dragon chainbody',
    'adamant platelegs',
    'Air talisman',
    'earth talisman',
    'water talisman',
    'fire talisman',
    'mind talisman',
    'body talisman',
    'cosmic talisman',
    'Ashes',
    'eye of newt',
    'vial',
    'vial of water',
    'rune essence',
    'coal',
    'iron ore',
    'gold ore',
    'mithril ore',
    'adamantite ore',
    'runite ore',
    'yew logs',
    'magic logs',
    'hard leather',
    'leather',
    'seaweed',
]
DEFAULT_LOADOUT = ['10000 Air rune', '10000 Mind rune']


SETTINGS = {
    'mode': SettingDef('string', 'Dump', 'Mode', options=MODE_OPTIONS),
    'designation': SettingDef('string', 'Mule', 'Designation', options=ROLE_OPTIONS),
    'bank': SettingDef('string', DEFAULT_BANK, 'Bank', options=BANK_OPTIONS),
    'accounts': SettingDef('string', '', 'Partner accounts', help='Comma-separated names. Supplier serves clients in this order; receivers accept only these accounts.'),
    'items': SettingDef('string[]', DEFAULT_ITEMS, 'Dump item names'),
    'loadout': SettingDef('string[]', DEFAULT_LOADOUT, 'Supply loadout', help='Each entry is quantity followed by exact name or item id; quantity defaults to 1.'),
    'trade_slots': SettingDef('number', 28, 'Slots per batch', 1, 28),
}


class MuleDepot(TaskBot):
    def __init__(self):
        self.role = 'Mule'
        self.partners = []
        self.items = []
        self.lines = []
        self.batches = []
        self.batch_index = 0
        self.client_index = 0
        self.delivered = {}
        self.unavailable = set()
        self.pending = []
        self.asker = None
        self.asker_at = 0
        self.cursor = 0
        self.last_request = -3000
        self.transfers = 0
        self.units = 0
        self.status = 'starting'

    def on_start(self):
        from bots.depot.logic import resolve_role
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        self.role = resolve_role(self.settings.str('mode', 'Dump'), self.settings.str('designation', 'Mule'))
        if self.role is None:
            raise RuntimeError('MuleDepot: use Dump/Mule, Dump/Supermule, Supply/Supplier or Supply/Client')
        self.partners = parse_accounts(self.settings.str('accounts', ''))
        if not self.partners:
            raise RuntimeError('MuleDepot: no partner accounts configured')
        self.items = parse_item_names(self.settings.list('items', DEFAULT_ITEMS))
        parsed = parse_loadout(self.settings.list('loadout', DEFAULT_LOADOUT))
        if self.role in ['Supplier', 'Client'] and parsed.problems:
            raise RuntimeError(f'MuleDepot: invalid loadout: {parsed.problems[0].raw}: {parsed.problems[0].reason}')
        if self.role in ['Supplier', 'Client']:
            self.lines = self.resolve_loadout(parsed.lines)
            self.batches = plan_deliveries(self.lines, self.slots_for, max(1, min(28, int(self.settings.num('trade_slots', 28)))))
        if self.role == 'Mule' and not self.items:
            raise RuntimeError('MuleDepot: dump item list is empty')
        if self.role in ['Supplier', 'Client'] and not self.batches:
            raise RuntimeError('MuleDepot: supply loadout is empty')
        self.bank_tile = bank_tile(self.settings.str('bank', DEFAULT_BANK))
        self.on('chat_message', self.heard)
        reached = yield from traversal.walk_resilient(self.bank_tile, radius=3, attempts=6, timeout_ms=240000)
        if not reached:
            self.request_finish('MuleDepot: could not reach the depot bank')
            return
        banker = DepotBank(self)
        opened = yield from banker.open()
        if not opened:
            self.request_finish('MuleDepot: could not open the depot bank')
            return
        yield from bank.deposit_all_matching(lambda name, id: True)
        if inventory.used() > 0:
            self.request_finish('MuleDepot: could not bank the starting inventory')
            return
        yield from bank.close()
        self.add(DepotTrade(self), ContinueDialog(), banker, DepotMove(self), DepotWait(self))
        self.log(f'MuleDepot {self.role}: {len(self.partners)} partner(s) at {self.bank_tile}')

    def resolve_loadout(self, lines):
        catalog = live_catalog()
        resolved = {}
        for line in lines:
            record = catalog.by_id.get(line.id) if line.id >= 0 else next_record(catalog, line.name)
            if record is None:
                raise RuntimeError(f'MuleDepot: unknown loadout item {line.name or str(line.id)}')
            id = catalog.unnoted_of.get(record.id, record.id)
            if id in resolved:
                resolved[id].quantity += line.quantity
            else:
                resolved[id] = Record({'id': id, 'name': catalog.by_id[id].name, 'quantity': line.quantity})
        return list(resolved.values())

    def slots_for(self, line):
        catalog = live_catalog()
        record = catalog.by_id.get(line.id) if line.id >= 0 else next_record(catalog, line.name)
        if record is None:
            raise RuntimeError(f'MuleDepot: unknown loadout item {line.name or str(line.id)}')
        return 1 if record.stackable or noted_id(catalog, record.id) is not None else line.quantity

    def heard(self, event):
        if event.type != 'trade_request' or 'wishes to trade with you' not in (event.text or '').lower():
            return
        name = normalize_account(event.username or '')
        if name in self.partners:
            self.asker = name
            self.asker_at = _core.step_time()

    def current_client(self):
        return self.partners[self.client_index] if self.client_index < len(self.partners) else None

    def current_batch(self):
        return self.batches[self.batch_index] if self.batches and self.current_client() is not None else None

    def held(self, line):
        catalog = live_catalog()
        note = noted_id(catalog, line.id)
        return sum([i.count for i in inventory.items() if i.id == line.id or (note is not None and i.id == note)]) if line.id >= 0 else sum([i.count for i in inventory.items() if (i.name or '').lower() == line.name.lower()])

    def shortfall(self):
        batch = self.current_batch()
        if batch is None:
            return []
        out = []
        for line in batch.lines:
            if line_key(line) in self.unavailable:
                continue
            needed = line.quantity - self.held(line)
            if needed > 0:
                out.append(Record({'id': line.id, 'name': line.name, 'quantity': needed}))
        return out

    def accepts(self, name):
        if name is None or normalize_account(name) not in self.partners:
            return False
        return self.role != 'Supplier' or normalize_account(name) == self.current_client()

    def target(self):
        visible = lambda name: players.query().name(name).nearest() is not None
        asker = self.asker if _core.step_time() - self.asker_at < 15000 else None
        name = pick_request_target(asker, self.partners, self.cursor, self.accepts, visible)
        return players.query().name(name).nearest() if name else None

    def pack_units(self):
        return sum([i.count for i in inventory.items()])

    def advance_batch(self):
        client = self.current_client()
        ledger = self.delivered.get(client, {})
        for line in self.pending:
            key = line_key(line)
            ledger[key] = ledger.get(key, 0) + line.quantity
        self.delivered[client] = ledger
        self.pending = []
        self.batch_index += 1
        if self.batch_index < len(self.batches):
            return
        self.batch_index = 0
        self.client_index += 1
        self.unavailable.clear()
        if self.current_client() is None:
            short = []
            for name in self.partners:
                given = self.delivered.get(name, {})
                for line in self.lines:
                    missing = line.quantity - given.get(line_key(line), 0)
                    if missing > 0:
                        short.append(f'{name}: {missing} {line.name or str(line.id)}')
            reason = f'MuleDepot: supplied {len(self.partners)} account(s), {self.units} units moved'
            if short:
                reason += ' — short: ' + '; '.join(short)
            self.request_finish(reason)

    def on_progress_report(self):
        return {'Role': self.role, 'Status': self.status, 'Trades': self.transfers, 'Units': self.units,
                'Clients served': self.client_index}


def next_record(catalog, name):
    found = [r for r in catalog.by_id.values() if (r.name or '').lower() == name.lower() and getattr(r, 'note_of', None) is None]
    return found[0] if found else None


BOT = define_bot(name='MuleDepot', create=MuleDepot, category='Utility', tags=['trade', 'mule', 'banking'], settings_schema=SETTINGS,
                 description='Dump listed bank goods to a supermule, or supply a loadout to each client in batches. All partners use the same depot bank. Reports delivered items and shortages for each client.')
