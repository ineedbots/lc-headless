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
