"""Ported from rs2b0t's src/bot/scripts/ArravSupplier/ArravSupplier.ts (MIT, see thirdparty/rs2b0t)."""

import math
from rs2004.catalogs.record import Record
from rs2004.quests.exec.steps import open_bank_leg, execute_step
from rs2004.quests.exec.primitives import goto_npc, talk_strict
from rs2004.quests.exec.legs import talk_until
from rs2004.quests.exec.prompts import clear_boxes, drive_boxes
from rs2004.quests.defs.shieldofarrav.certs import mint_certificates
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.shieldofarrav.journal import SOA_STAGE, read_shield_of_arrav_progress
from rs2004.quests.defs.shieldofarrav.phoenix import phoenix_step
from rs2004.quests.defs.shieldofarrav.areas import KATRINE_HANDIN, KATRINE_JOIN, SOA_ID, SOA_TILE, TRAMP
from rs2004.quests.defs.shieldofarrav.blackarm import raid_weapon_store, take_black_arm_half
from rs2004.quests.defs.shieldofarrav.config import arrav_config
from rs2004.quests.defs.shieldofarrav.hideout import enter_hideout
from rs2004.quests.defs.shieldofarrav.phoenix import kill_jonny, take_phoenix_half
from rs2004.quests.defs.shieldofarrav.partner import run_handoff
from bots.arravsupplier.logic import supplier_phase
from rs2004.settings import settings_store

__all__ = ['ARRAV_SUPPLIER_SETTINGS', 'ArravSupplier']

# Why: redeeming completes Phoenix Gang and permanently stops certificate supply, so this is not a QuestModule.
# Using the report on Straven bypasses the Black Arm guard and creates the dual-gang state.
STRAVEN_NPC = 644
BANK = SOA_TILE.RENDEZVOUS
ARRAV_SUPPLIER_SETTINGS = {
    'cert_target': SettingDef('number', 10, min=2, max=200, label='Certificates to bank', help='stop once the bank holds this many; each pair costs one trip to each hideout'),
    'partner': SettingDef('string', '', label='Bootstrap key partner', help='character name of a Phoenix Gang bot that can trade over a weapon-store key; only needed once'),
}


class ArravSupplier(LoopingBot):
    """Mints Shield of Arrav certificates forever from one dual-gang account."""
    loop_delay = 600
    _status = 'starting'
    _phase = 'await-key'
    _banked = 0
    _minted = 0
    _failures = 0
    # Why: membership is a server varp the client cannot read, so the proof is having been through the door.
    _black_arm_proven = False
    _phoenix_proven = False

    def on_start(self):
        yield from execution.delay_until(lambda: game.ingame() and game.tile() is not None, 0)
        arrav_config.partner = self.settings.str('partner', '').strip()
        self._black_arm_proven = bool(settings_store.saved('ArravSupplierState', 'blackarm'))
        self._phoenix_proven = bool(settings_store.saved('ArravSupplierState', 'phoenix'))
        self.log(f'ArravSupplier — banking {self._cert_target()} certificates, never redeeming')
        prepared = yield from self._prepare_phoenix()
        if not prepared:
            self.request_finish('could not prepare the Phoenix mission before joining Black Arm')

    def _prepare_phoenix(self):
        # Straven's report use-on bypasses the Black Arm refusal only once his mission is assigned.
        # Prepare that mission before Katrine's join makes his ordinary talk refuse us.
        if settings_store.saved('ArravSupplierState', 'mission'):
            return True
        for attempt in range(24):
            progress = yield from read_shield_of_arrav_progress()
            if progress is None:
                yield from execution.delay_ticks(2)
                continue
            if progress.stage == SOA_STAGE.KILL_JONNY:
                settings_store.save('ArravSupplierState', 'mission', True)
                return True
            if progress.stage >= SOA_STAGE.PHOENIX_JOINED:
                self.log('start the supplier on an unjoined character; the Phoenix mission must precede Black Arm membership')
                return False
            counts = {}
            for item in inventory.items():
                counts[item.id] = counts.get(item.id, 0) + item.count
            snap = QuestSnapshot(journal='in_progress', progress=progress, inv_ids=counts, bank_known=True)
            step = phoenix_step(snap)
            self.log(f'preparing Phoenix mission: {step.name or step.kind}')
            yield from execute_step(step, [], self.log)
        return False

    def _cert_target(self):
        return max(2, math.floor(self.settings.num('cert_target', 10)))

    def _read_state(self):
        """The journal is blank for a dual-gang character, so every field is an item or a door's own refusal."""
        _w1 = yield from self._can_open_black_arm_door()
        _w2 = yield from self._can_open_phoenix_door()
        return Record({
            'in_black_arm': _w1,
            'in_phoenix': _w2,
            'has_key': inventory.count_by_id(SOA_ID.STORE_KEY) > 0,
            'has_report': inventory.count_by_id(SOA_ID.REPORT) > 0,
            'crossbows': inventory.count_by_id(SOA_ID.CROSSBOW),
            'phoenix_half': inventory.count_by_id(SOA_ID.SHIELD_PHOENIX),
            'blackarm_half': inventory.count_by_id(SOA_ID.SHIELD_BLACKARM),
            'certs_banked': self._banked,
            'cert_target': self._cert_target(),
        })

    def _can_open_black_arm_door(self):
        return self._black_arm_proven
        if False:
            yield


    def _can_open_phoenix_door(self):
        return self._phoenix_proven
        if False:
            yield


    def loop(self):
        if not game.ingame():
            return 1200
        yield from self._refresh_banked()
        state = yield from self._read_state()
        self._phase = supplier_phase(state)
        self._status = self._phase
        if self._phase == 'done':
            self.request_finish(f'banked {self._banked} certificates — stock is ready for other bots')
            return
        ok = yield from self._run_phase(self._phase)
        self._failures = (0 if ok else self._failures + 1)
        if self._failures >= 8:
            self.request_finish(f'\'{self._phase}\' failed 8 times in a row — stopping rather than looping')
            return
        return (600 if ok else 2400)

    def _run_phase(self, phase):
        def log(m):
            return self.log(f'  {m}')

        if phase == 'await-key':
            if len(arrav_config.partner) == 0:
                self.log('no bootstrap partner set — a weapon-store key can only come from a Phoenix Gang member')
                return False
            _result3 = yield from run_handoff('take-key', 'blackarm', log)
            return _result3
        elif phase == 'raid-store':
            _w4 = yield from self._ensure_katrine_task(log)
            if not (_w4):
                return False
            _result5 = yield from raid_weapon_store(log)
            return _result5
        elif phase == 'join-blackarm':
            ready = yield from self._ensure_katrine_task(log)
            if not ready:
                return False
            _w6 = yield from talk_until(KATRINE_HANDIN, [], lambda: inventory.count_by_id(SOA_ID.CROSSBOW) == 0, log)
            if not (_w6):
                return False
            self._black_arm_proven = inventory.count_by_id(SOA_ID.CROSSBOW) == 0
            if self._black_arm_proven:
                settings_store.save('ArravSupplierState', 'blackarm', True)
            return self._black_arm_proven
        elif phase == 'kill-jonny':
            _result7 = yield from kill_jonny(log)
            return _result7
        elif phase == 'join-phoenix':
            _result8 = yield from self._join_phoenix_with_report(log)
            return _result8
        elif phase == 'take-phoenix-half':
            _result9 = yield from take_phoenix_half(log)
            return _result9
        elif phase == 'take-blackarm-half':
            _result10 = yield from take_black_arm_half(log)
            return _result10
        elif phase == 'mint':
            _result11 = yield from self._mint(log)
            return _result11
        else:
            return False

    def _ensure_katrine_task(self, log):
        """Tramp then Katrine, so the crossbow task is set before the store is raided."""
        if self._black_arm_proven:
            return True
        # Unlike the engine, this bot cannot rely on a later decide pass to finish a dialogue's last pages.
        for stop in [TRAMP, KATRINE_JOIN]:
            yield from clear_boxes()
            arrived = yield from goto_npc(stop, [], log)
            if not arrived:
                return False
            talked = yield from talk_strict(stop.npc, stop.prefer, log)
            if not talked:
                return False
        progress = yield from read_shield_of_arrav_progress()
        return progress is not None and progress.stage in [SOA_STAGE.KATRINE_TASK, SOA_STAGE.BLACKARM_JOINED]

    # Why: [opnpc1,straven] sends a Black Arm member to the brush-off branch; only [opnpcu,straven] reaches the join.
    def _join_phoenix_with_report(self, log):
        """Use the intelligence report on Straven rather than talking to him."""
        _w12 = yield from enter_hideout(log)
        if not (_w12):
            return False
        _w13 = yield from traversal.walk_resilient(SOA_TILE.PHOENIX_DOOR, radius=3, attempts=3, timeout_ms=90000, log=log)
        if not (_w13):
            return False
        straven = npcs.query().where(lambda n: n.id == STRAVEN_NPC).nearest()
        report = ([i for i in inventory.items() if i.id == SOA_ID.REPORT] or [None])[0]
        if not straven or not report:
            log('no Straven in the scene, or no report in the pack')
            return False
        if not (report.use_on(straven)):
            return False
        yield from drive_boxes(lambda: inventory.count_by_id(SOA_ID.REPORT) == 0, 20000, [], log)
        yield from clear_boxes()
        self._phoenix_proven = inventory.count_by_id(SOA_ID.REPORT) == 0 and inventory.count_by_id(SOA_ID.STORE_KEY) > 0
        if self._phoenix_proven:
            settings_store.save('ArravSupplierState', 'phoenix', True)
        if not self._phoenix_proven:
            log('Straven did not take the report — the dual-gang join did not land')
        return self._phoenix_proven

    def _mint(self, log):
        before = inventory.count_by_id(SOA_ID.CERTIFICATE)
        _w14 = yield from mint_certificates(log)
        if not (_w14):
            return False
        yield from modals.close()
        gained = inventory.count_by_id(SOA_ID.CERTIFICATE) - before
        if gained <= 0:
            log('the curator minted nothing — check that neither gang varp has gone complete')
            return False
        self._minted += gained
        _result15 = yield from self._bank_certificates(log)
        return _result15

    def _bank_certificates(self, log):
        _w16 = yield from open_bank_leg('supplier: no known bank', BANK, log)
        if not (_w16):
            return False
        yield from bank.deposit_all_matching(lambda _name, id: id == SOA_ID.CERTIFICATE)
        yield from self._refresh_banked(True)
        yield from modals.close()
        self.log(f'banked certificates: {self._banked}/{self._cert_target()}')
        return True

    def _refresh_banked(self, force=False):
        if not bank.is_open():
            return
        if force:
            yield from execution.delay_until(lambda: bank.loaded(), 3000)
        if bank.loaded():
            self._banked = bank.count_by_id(SOA_ID.CERTIFICATE)

    def on_progress_report(self):
        return {'Status': self._status, 'Certificates banked': self._banked,
                'Target': self._cert_target(), 'Minted': self._minted, 'Failures': self._failures}



BOT = define_bot(
    name='ArravSupplier',
    description='Shield of Arrav certificate faucet — joins both gangs from one account, farms both shield halves and banks certificates for other bots; never redeems, so the chest and the curator keep working',
    category='Quest',
    tags=['quest', 'shield of arrav', 'certificate', 'supplier'],
    settings_schema=ARRAV_SUPPLIER_SETTINGS,
    create=ArravSupplier,
)
