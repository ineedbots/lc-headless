"""Run each F2P quest on its own fresh account (two opposite gangs for Arrav)."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent / 'scripts'))
import harness
from phase16_cases import CASES, POINTS, initial_points


def account_settings(case, prefix):
    quest = CASES[case]
    partner = prefix + ('ba' if case == 'ph' else 'ph') if case in ['ph', 'ba'] else ''
    return {'quests': [quest], 'food': 'Lobster', 'verbose': True, 'loadout': '',
            'arrav_gang': 'phoenix' if case == 'ph' else 'blackarm', 'arrav_certs': 2,
            'arrav_partner': partner, 'gather_wilderness_planks': True,
            'e2e_expected_qp': initial_points(quest) + POINTS[quest]}


SUITE = {'name': 'phase16-individual', 'prefix': 'f16', 'members': False, 'cases': CASES,
         'groups': [list(CASES)[:10], list(CASES)[10:]], 'partners': [('ph', 'ba')],
         'scripts': Path(__file__).resolve().parent / 'scripts', 'settings': account_settings,
         'seed_settings': lambda case: {'kind': case, 'target': CASES[case]}}

if __name__ == '__main__':
    sys.exit(harness.main(SUITE))
