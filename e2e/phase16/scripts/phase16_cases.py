"""Independent F2P cases and explicit prerequisite-only development flags."""

CASES = {'ru': 'runemysteries', 'do': 'doric', 'ks': 'squire', 'sh': 'sheep', 'rg': 'priest',
         'co': 'cook', 'im': 'imp', 'er': 'haunted', 'wp': 'hetty', 'rj': 'romeojuliet',
         'pa': 'prince', 'pt': 'hunt', 'ph': 'blackarmgang', 'ba': 'blackarmgang',
         'gd': 'gobdip', 'de': 'demon', 'bk': 'blackknight', 'vs': 'vampire', 'ds': 'dragon'}
POINTS = {'runemysteries': 1, 'doric': 1, 'squire': 1, 'sheep': 1, 'priest': 1, 'cook': 1,
          'imp': 1, 'haunted': 4, 'hetty': 1, 'romeojuliet': 5, 'prince': 3, 'hunt': 2,
          'blackarmgang': 1, 'gobdip': 5, 'demon': 3, 'blackknight': 3, 'vampire': 3, 'dragon': 2}
# Tuples are (quest ID, server varp, completed value). The target itself is never set.
FLAGS = [('runemysteries', 'runemysteries', 6), ('doric', 'doricquest', 100),
         ('squire', 'squire', 7), ('sheep', 'sheep', 22), ('priest', 'prieststart', 5),
         ('cook', 'cookquest', 2), ('imp', 'imp', 2), ('hetty', 'hetty', 3),
         ('romeojuliet', 'rjquest', 100), ('prince', 'princequest', 110), ('hunt', 'hunt', 4),
         ('gobdip', 'goblinquest', 6), ('demon', 'demonstart', 30), ('blackknight', 'spy', 4),
         ('vampire', 'vampire', 3)]


def prerequisite_flags(quest):
    if quest == 'blackknight':
        return [row for row in FLAGS if row[0] in ['romeojuliet', 'gobdip', 'doric', 'cook']]
    return list(FLAGS) if quest == 'dragon' else []


def initial_points(quest):
    return sum([POINTS[row[0]] for row in prerequisite_flags(quest)])
