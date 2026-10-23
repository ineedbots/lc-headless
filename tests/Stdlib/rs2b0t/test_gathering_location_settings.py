"""rs2b0t's test/scripts/GatheringBot/LocationSettings.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect.
Its two banking tests spy on banking.open, which this harness can't."""

from rs2004.settings import apply_schema

from bots.fisher import BOT as FISHER
from bots.miner import BOT as MINER
from bots.woodcutter import BOT as WOODCUTTER


def preserves(manifest):
    def body():
        schema = manifest.settings_schema
        expect(schema['location'].default).to_be('Auto')
        for mode in ['Auto', 'None', 'Use Closest', 'Use Start Position', 'Use Custom Position']:
            bag = SettingsBag({'location': mode, 'bank': False})
            expect(apply_schema(bag, schema)).to_equal([])
            expect(bag.str('location')).to_be(mode)
            expect(bag.bool('bank', True)).to_be(False)
            expect(bag.tile('custom_location', Tile(1, 1, 0))).to_equal(Tile(3200, 3200, 0))
    return body


for _manifest in [MINER, FISHER, WOODCUTTER]:
    test(f'{_manifest.name} preserves saved gathering modes and exposes bank/custom settings', preserves(_manifest))
