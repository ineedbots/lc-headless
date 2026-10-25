"""The loadout AIOQuester resolved for the quests: rs2b0t's api/ai/quests/gear.ts (MIT, see thirdparty/rs2b0t)."""

__all__ = ['quest_loadout']


class _QuestLoadout:
    def __init__(self):
        self.current = None


quest_loadout = _QuestLoadout()
