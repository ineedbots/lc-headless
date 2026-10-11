"""rs2b0t's world catalogs and behaviours (MIT, see thirdparty/rs2b0t): data tables, pure planners, and
tasks built on them. Everything is here as rs2b0t names it, in snake_case:

    from rs2004.catalogs import pickaxe_req, resolve_mining_location, plan_gather_tool_acquire

Each part is a module of its own too: tools, tool_acquire, fishing, mining, gathering, tables, combat,
loadout, partner and tasks.
"""

from rs2004.catalogs.record import *
from rs2004.catalogs.tools import *
from rs2004.catalogs.mining import *
from rs2004.catalogs.fishing import *
from rs2004.catalogs.tool_acquire import *
from rs2004.catalogs.gathering import *
from rs2004.catalogs.tables import *
from rs2004.catalogs.combat import *
from rs2004.catalogs.loadout import *
from rs2004.catalogs.partner import *
from rs2004.catalogs.tasks import *
