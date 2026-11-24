"""Focused live reproduction of the three deaths found by the grand concurrent run."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness

CASES = {'hq': 'hero', 'rg': 'regicide', 'lq': 'legends'}


def account_settings(case, prefix):
    return {'quests': [CASES[case]], 'food': 'Shark' if case == 'rg' else 'Lobster',
            'verbose': True, 'loadout': ''}


SUITE = {'name': 'combat_legs', 'prefix': 'cl', 'members': True, 'cases': CASES,
         'scripts': Path(__file__).resolve().parent / 'scripts', 'settings': account_settings}

if __name__ == '__main__':
    sys.exit(harness.main(SUITE))
