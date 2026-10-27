"""Ported from rs2b0t's src/bot/../../test/scripts/AIOQuester/arravSettings.test.ts (MIT, see thirdparty/rs2b0t)."""
from rs2004.catalogs.record import Record
from rs2004.quests.engine.types import QuestSnapshot
from rs2004.quests.defs.shieldofarrav.config import arrav_config
from bots.aio_quester import AIO_SETTINGS
from bots.aioquester.logic import ARRAV_GANG_OPTIONS, apply_arrav_settings

def restore_defaults():
    arrav_config.gang = 'random'
    arrav_config.partner = ''
    arrav_config.cert_target = 2
before_each(restore_defaults)
after_each(restore_defaults)

def _fn1():

    def _fn2():
        expect(AIO_SETTINGS.get('arrav_gang').options if AIO_SETTINGS.get('arrav_gang') is not None else None).to_equal(list(ARRAV_GANG_OPTIONS))
        expect(AIO_SETTINGS.get('arrav_gang').default if AIO_SETTINGS.get('arrav_gang') is not None else None).to_be('random')
    test('the schema offers exactly the three documented gangs', _fn2)

    def _fn3():
        expect(AIO_SETTINGS.get('arrav_partner').default if AIO_SETTINGS.get('arrav_partner') is not None else None).to_be('')
        expect(AIO_SETTINGS.get('arrav_certs').default if AIO_SETTINGS.get('arrav_certs') is not None else None).to_be(2)
        expect(AIO_SETTINGS.get('arrav_certs').min if AIO_SETTINGS.get('arrav_certs') is not None else None).to_be(1)
    test('the partner and certificate settings carry the documented defaults', _fn3)

    def _fn4():
        apply_arrav_settings(Fake(**{'gang': 'blackarm', 'partner': 'Zezima', 'certs': 6}))
        expect(arrav_config.gang).to_be('blackarm')
        expect(arrav_config.partner).to_be('Zezima')
        expect(arrav_config.cert_target).to_be(6)
    test('valid settings land on the config', _fn4)

    def _fn5():
        apply_arrav_settings(Fake(**{'gang': 'nonsense', 'partner': '', 'certs': 2}))
        expect(arrav_config.gang).to_be('random')
    test('an unknown gang falls back to random rather than throwing mid-quest', _fn5)

    def _fn6():
        apply_arrav_settings(Fake(**{'gang': 'random', 'partner': '', 'certs': 0}))
        expect(arrav_config.cert_target).to_be(1)
        apply_arrav_settings(Fake(**{'gang': 'random', 'partner': '', 'certs': -5}))
        expect(arrav_config.cert_target).to_be(1)
    test('a certificate target below one is clamped', _fn6)

    def _fn7():
        apply_arrav_settings(Fake(**{'gang': 'random', 'partner': '', 'certs': 7.9}))
        expect(arrav_config.cert_target).to_be(7)
        apply_arrav_settings(Fake(**{'gang': 'random', 'partner': '', 'certs': float('nan')}))
        expect(arrav_config.cert_target).to_be(2)
    test('a fractional target is floored, and a broken one falls back to the default', _fn7)

    def _fn8():
        apply_arrav_settings(Fake(**{'gang': 'random', 'partner': '  Zezima  ', 'certs': 2}))
        expect(arrav_config.partner).to_be('Zezima')
    test('a partner name is trimmed', _fn8)
describe('arrav settings', _fn1)

def snapshot_fields(**fields):
    for name in ['inv', 'inv_ids', 'bank', 'bank_ids']:
        if isinstance(fields.get(name), (Record, Fake)):
            fields[name] = fields[name]._fields
    return QuestSnapshot(**fields)
