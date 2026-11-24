"""Independent phase 17e targets and preparation-only prerequisites."""

CASES = {'tt': 'desertrescue', 'wt': 'itwatchtower', 'cb': 'chompybird', 'gt': 'grandtree'}
POINTS = {'desertrescue': 2, 'itwatchtower': 4, 'chompybird': 2, 'grandtree': 5, 'druid': 4}


def prerequisite_flags(quest):
    return [('druid', 'druidquest', 4)] if quest == 'itwatchtower' else []


def initial_points(quest):
    return sum([POINTS[row[0]] for row in prerequisite_flags(quest)])


def preparation_flags(quest):
    return []


def preparation_items(quest):
    # These three inputs have no world source in the Watch Tower module.
    if quest == 'itwatchtower':
        return [('guam_leaf', 'Guam leaf', 1), ('bat_bones', 'Bat bones', 1),
                ('gold_bar', 'Gold bar', 1)]
    return []
