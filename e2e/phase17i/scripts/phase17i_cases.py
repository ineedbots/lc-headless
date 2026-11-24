"""Independent targets and explicit preparation-only prerequisites."""

CASES = {'lq': 'legends'}
POINTS = {'legends': 4, 'runemysteries': 1, 'doric': 1, 'squire': 1, 'sheep': 1, 'priest': 1, 'cook': 1, 'imp': 1, 'haunted': 4, 'hetty': 1, 'romeojuliet': 5, 'prince': 3, 'hunt': 2, 'blackarmgang': 1, 'gobdip': 5, 'demon': 3, 'blackknight': 3, 'vampire': 3, 'dragon': 2, 'zanaris': 3, 'arthur': 6, 'druid': 4, 'elena': 1, 'biohazard': 3, 'upass': 5, 'hero': 1, 'crest': 1, 'junglepotion': 1, 'zombiequeen': 2, 'waterfall': 1, 'grandtree': 5, 'itwatchtower': 4, 'tree': 2, 'ball': 4, 'murder': 3, 'sheepherder': 4, 'arena': 2, 'itgronigen': 2, 'desertrescue': 2, 'grail': 2, 'chompybird': 2, 'viking': 3, 'itexam': 2, 'drunkmonk': 1, 'totem': 1, 'seaslug': 1}


# Includes completed ancestors and QP-gate preparation; totals 107 real quest points.
FLAGS = [
    ('runemysteries', 'runemysteries', 6),
    ('doric', 'doricquest', 100),
    ('squire', 'squire', 7),
    ('sheep', 'sheep', 22),
    ('priest', 'prieststart', 5),
    ('cook', 'cookquest', 2),
    ('imp', 'imp', 2),
    ('haunted', 'haunted', 3),
    ('hetty', 'hetty', 3),
    ('romeojuliet', 'rjquest', 100),
    ('prince', 'princequest', 110),
    ('hunt', 'hunt', 4),
    ('blackarmgang', 'blackarmgang', 4),
    ('gobdip', 'goblinquest', 6),
    ('demon', 'demonstart', 30),
    ('blackknight', 'spy', 4),
    ('vampire', 'vampire', 3),
    ('dragon', 'dragonquest', 10),
    ('zanaris', 'zanaris', 6),
    ('arthur', 'arthur', 7),
    ('druid', 'druidquest', 4),
    ('elena', 'elenaquest', 29),
    ('biohazard', 'biohazard', 16),
    ('upass', 'upass', 10),
    ('hero', 'heroquest', 15),
    ('crest', 'crestquest', 11),
    ('junglepotion', 'junglepotion', 12),
    ('zombiequeen', 'zombiequeen', 15),
    ('waterfall', 'waterfall_quest', 10),
    ('grandtree', 'grandtree', 160),
    ('itwatchtower', 'itwatchtower', 13),
    ('tree', 'treequest', 9),
    ('ball', 'ballquest', 7),
    ('murder', 'murderquest', 2),
    ('sheepherder', 'sheepherderquest', 3),
    ('arena', 'arenaquest', 14),
    ('itgronigen', 'itgronigen', 7),
    ('desertrescue', 'desertrescue', 30),
    ('grail', 'grail', 10),
    ('chompybird', 'chompybird', 65),
    ('viking', 'viking', 10),
    ('itexam', 'itexamlevel', 9),
    ('drunkmonk', 'drunkmonkquest', 80),
    ('totem', 'totemquest', 5),
    ('seaslug', 'seaslugquest', 12),
]


def prerequisite_flags(quest):
    return list(FLAGS)


def initial_points(quest):
    return sum([POINTS[row[0]] for row in prerequisite_flags(quest)])


def preparation_flags(quest):
    return []


def preparation_items(quest):
    return [('rune_axe', 'Rune axe', 1), ('lockpick', 'Lockpick', 5),
            ('stafforb', 'Unpowered orb', 5), ('cosmicrune', 'Cosmic rune', 100),
            ('opal', 'Opal', 1), ('jade', 'Jade', 1), ('red_topaz', 'Red topaz', 1),
            ('sapphire', 'Sapphire', 1), ('emerald', 'Emerald', 1),
            ('ruby', 'Ruby', 1), ('diamond', 'Diamond', 1)]
