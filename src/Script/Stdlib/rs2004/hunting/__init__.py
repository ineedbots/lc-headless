"""rs2b0t's boss and dragon framework (api/combat/hunting, MIT, see thirdparty/rs2b0t), in snake_case:

    from rs2004.hunting import Fight, Retreat, HoldSafespot, WalkToSpot, site_for, bank_routine, BankOpts

Its parts are modules of their own too: logic (the pure decisions), sites (the dragon sites), supply (doses,
escape runes, lairs, the bank run and keys), combat (the tasks) and guarded (loot under guard).
"""

from rs2004.hunting.logic import *
from rs2004.hunting.sites import *
from rs2004.hunting.guarded import *
from rs2004.hunting.supply import *
from rs2004.hunting.combat import *
