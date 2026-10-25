"""The quests' food: rs2b0t's api/ai/quests/food.ts (MIT, see thirdparty/rs2b0t). quest_food.name is the food
AIOQuester was set to."""

__all__ = ['quest_food', 'FOOD_FLOAT']


class _QuestFood:
    def __init__(self):
        self.name = 'Trout'


quest_food = _QuestFood()

# Why: 8 unless a quest proves it needs more; the old 12-to-20 packs spent most of the inventory on food that was never
# eaten.
FOOD_FLOAT = 8
