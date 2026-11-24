"""Independent phase 17f targets and preparation-only prerequisites."""

CASES = {'ew': 'elemental_workshop', 'ds': 'itexam', 'hg': 'grail', 'fc': 'crest', 'hd': 'horror'}
POINTS = {'elemental_workshop': 1, 'itexam': 2, 'grail': 2, 'crest': 1, 'horror': 2,
          'druid': 4, 'arthur': 6}


def prerequisite_flags(quest):
    if quest == 'itexam':
        return [('druid', 'druidquest', 4)]
    if quest == 'grail':
        return [('arthur', 'arthur', 7)]
    return []


def initial_points(quest):
    return sum([POINTS[row[0]] for row in prerequisite_flags(quest)])


def preparation_flags(quest):
    return []


def preparation_items(quest):
    return []
