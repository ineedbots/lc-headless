"""Ported from rs2b0t's src/bot/api/ai/quests/defs/shilo/scene.ts (MIT, see thirdparty/rs2b0t)."""

from rs2004.game import game
from rs2004.quests.defs.shilo.areas import shilo_area
from rs2004.quests.exec.prompts import drive_choice, drive_until, held_id, loc_near, prompt_loc, settle_scene, use_on_loc

__all__ = ['here', 'drive_choice', 'drive_until', 'held_id', 'loc_near', 'prompt_loc', 'settle_scene', 'use_on_loc']


def here():
    return shilo_area(game.tile())
