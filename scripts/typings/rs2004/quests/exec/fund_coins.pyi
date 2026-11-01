# Coins for a quest from pickpocketing Men: Varrock's for the Al Kharid toll, then Al Kharid's, eating Kebabs bought
# from the seller beside him while Hitpoints are low.
from typing import Callable, Optional
from __builtins__ import Tile, Wait
from rs2004.catalogs.record import Record

VARROCK_FUNDING_MAN: Tile
AL_KHARID_FUNDING_MAN: Tile
KEBAB_SELLER: Tile
AL_KHARID_TOLL: int
AL_KHARID_ENTRY_CASH: int
SAFE_PICKPOCKET_HP: int

def in_al_kharid_funding_area(tile: Optional[Tile]) -> bool: ...
def east_of_al_kharid_gate(tile: Optional[Tile]) -> bool: ...
def fund_quest_coins(target: int, log: Callable[[str], None], label: Optional[str] = None) -> Wait[bool]: ...
def earn_quest_coins_step(target: int, label: str = 'quest') -> Record: ...
