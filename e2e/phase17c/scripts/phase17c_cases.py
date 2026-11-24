"""Individual targets and explicit, transitive prerequisite-only flags."""

CASES = {'dp': 'death', 'ts': 'troll', 'er': 'eadgar', 'pc': 'elena', 'bh': 'biohazard'}
POINTS = {'death': 1, 'troll': 1, 'eadgar': 1, 'elena': 1, 'biohazard': 3, 'druid': 4}


def prerequisite_flags(quest):
    if quest == 'troll':
        return [('death', 'death_equiproom', 80)]
    if quest == 'eadgar':
        return [('death', 'death_equiproom', 80), ('troll', 'troll_quest', 50),
                ('druid', 'druidquest', 4)]
    return [('elena', 'elenaquest', 29)] if quest == 'biohazard' else []


def initial_points(quest):
    return sum([POINTS[row[0]] for row in prerequisite_flags(quest)])


def preparation_flags(quest):
    flags = [('death_map', 8)] if quest in ['troll', 'eadgar'] else []
    if quest == 'eadgar':
        flags.append(('troll_freed_eadgar', 0))
    return flags


def preparation_items(quest):
    if quest == 'death':
        return [('bread', 'Bread', 10), ('trout', 'Trout', 10)]
    return [('ranarr_weed', 'Ranarr weed', 1)] if quest == 'eadgar' else []
