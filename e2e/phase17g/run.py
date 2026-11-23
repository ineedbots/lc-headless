"""Phase 17g live quest acceptance entry point."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness

CASES = {'ph': 'hero', 'ba': 'hero', 'ik': 'ikov', 'ft': 'viking'}


def account_settings(case, prefix):
    partner = prefix + ('ba' if case == 'ph' else 'ph') if case in ['ph', 'ba'] else ''
    return {'quests': [CASES[case]], 'food': 'Lobster', 'verbose': True, 'loadout': '',
            'arrav_gang': 'phoenix' if case == 'ph' else 'blackarm',
            'hero_partner': partner, 'arrav_partner': partner}


SUITE = {'name': 'phase17g', 'prefix': 'g17', 'members': True, 'cases': CASES,
         'scripts': Path(__file__).resolve().parent / 'scripts', 'settings': account_settings}

if __name__ == '__main__':
    sys.exit(harness.main(SUITE))
