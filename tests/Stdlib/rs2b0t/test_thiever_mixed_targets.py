from bots.thiever import Steal
from bots.account_leveler.record import Record


def mixed_targets():
    scene = Scene(Tile(3221, 3219))
    scene.npc('Man', actions=['Pickpocket'], dist=2)
    scene.npc('Woman', actions=['Pickpocket'], dist=1)
    scene.npc('Farmer', actions=['Pickpocket'], dist=1)
    scene.npc('Man', actions=['Talk-to'], dist=1)
    bot = Record({'target': 'Man / Woman', 'action': 'Pickpocket', 'anchor': Tile(3221, 3219), 'leash_radius': 19})
    spy_on(game, 'tile', returns=Tile(3221, 3219))
    task = Steal(bot)
    assert [npc.name for npc in task.candidates()] == ['Woman', 'Man']
    bot.target = 'Farmer'
    assert [npc.name for npc in task.candidates()] == ['Farmer']


test('combined level-one target selects both men and women and preserves exact farmer selection', mixed_targets)
