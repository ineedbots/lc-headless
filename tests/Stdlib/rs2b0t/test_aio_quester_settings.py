"""rs2b0t's test/scripts/AIOQuester/AIOQuesterSettings.test.ts (MIT, see thirdparty/rs2b0t), on spec.py's describe, test and expect.
rs2b0t's picker starts at Big Chompy Bird Hunting; here it starts at the first of the quests ported so far."""

from rs2004.catalogs import FOOD_OPTIONS
from rs2004.quests.defs import QUEST_DEFS
from rs2004.settings import settings_store
from bots.aio_quester import AIO_SETTINGS, QUEST_OPTION_LABELS


def _reset():
    settings_store.load({})


before_each(_reset)


def _fn2():
    ids = [d.record.id for d in QUEST_DEFS]
    expect(sorted(list(AIO_SETTINGS['quests'].options or []))).to_equal(sorted(ids))
    labels = {}
    for d in QUEST_DEFS:
        labels[d.record.id] = d.record.name
    expect(QUEST_OPTION_LABELS).to_equal(labels)
    expect(AIO_SETTINGS['quests'].option_labels).to_be(QUEST_OPTION_LABELS)


test('AIO quest options keep stable IDs but display canonical quest names', _fn2)


def _fn4():
    names = [QUEST_OPTION_LABELS.get(id) for id in AIO_SETTINGS['quests'].options or []]
    expect(names).to_equal(sorted(list(names)))
    expect(names[0]).to_be("Black Knight's Fortress")
    expect(QUEST_DEFS[0].record.name).not_.to_be(names[0])


test('the quest picker lists every quest alphabetically by name, not in run order', _fn4)


def _fn6():
    settings_store.save('AIOQuester', 'quests', 'cook, sheep')
    expect(settings_store.resolve('AIOQuester', AIO_SETTINGS).get('quests')).to_equal(['cook', 'sheep'])


test('canonical labels do not migrate or invalidate existing stored quest IDs', _fn6)


def _fn7():
    expect(AIO_SETTINGS['food'].default).to_be('Lobster')
    expect(AIO_SETTINGS['food'].options).to_equal(FOOD_OPTIONS)


test('the food the engine provisions is a setting, and defaults to Lobster', _fn7)


def _fn8():
    settings_store.save('AIOQuester', 'food', 'Shark')
    expect(settings_store.resolve('AIOQuester', AIO_SETTINGS).get('food')).to_be('Shark')


test('a configured food is what gets withdrawn', _fn8)
