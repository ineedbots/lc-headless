"""Run phase 16's eighteen F2P quests on two fresh opposite-gang accounts."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness

QUESTS = ['runemysteries', 'doric', 'squire', 'sheep', 'priest', 'cook', 'imp', 'haunted', 'hetty', 'romeojuliet', 'prince', 'hunt', 'blackarmgang', 'gobdip', 'demon', 'blackknight', 'vampire', 'dragon']
CASES = {'ph': QUESTS, 'ba': QUESTS}


def account_settings(case, prefix):
    return {'quests': list(QUESTS), 'food': 'Lobster', 'verbose': True, 'loadout': '',
            'arrav_gang': 'phoenix' if case == 'ph' else 'blackarm', 'arrav_certs': 2,
            'arrav_partner': prefix + ('ba' if case == 'ph' else 'ph'),
            'gather_wilderness_planks': True, 'e2e_expected_qp': 39}


SUITE = {'name': 'phase16', 'prefix': 'g16', 'members': False, 'cases': CASES,
         'scripts': Path(__file__).resolve().parent / 'scripts', 'settings': account_settings}

if __name__ == '__main__':
    sys.exit(harness.main(SUITE))
