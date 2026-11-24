"""Run each phase 17i members quest on its own fresh scratch account."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent / 'scripts'))
import harness
from phase17i_cases import CASES, POINTS, initial_points


def account_settings(case, prefix):
    quest = CASES[case]
    return {'quests': [quest], 'food': 'Lobster', 'verbose': True, 'loadout': '',
            'e2e_expected_qp': initial_points(quest) + POINTS[quest]}


SUITE = {'name': 'phase17i', 'prefix': 'i17', 'members': True, 'cases': CASES,
         'scripts': Path(__file__).resolve().parent / 'scripts', 'settings': account_settings,
         'seed_settings': lambda case: {'kind': case, 'target': CASES[case]}}

if __name__ == '__main__':
    sys.exit(harness.main(SUITE))
