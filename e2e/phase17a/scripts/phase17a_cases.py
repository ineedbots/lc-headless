"""Independent members cases and explicit prerequisite-only development flags."""

CASES = {'dr': 'druid', 'mf': 'drunkmonk', 'gc': 'fluffs', 'jp': 'junglepotion',
         'ct': 'cog', 'hc': 'hazeelcult', 'wh': 'ball', 'fc': 'fishingcompo',
         'mm': 'murder', 'ss': 'seaslug', 'pp': 'priestperil', 'tt': 'totem'}
POINTS = {'druid': 4, 'drunkmonk': 1, 'fluffs': 1, 'junglepotion': 1, 'cog': 1,
          'hazeelcult': 1, 'ball': 4, 'fishingcompo': 1, 'murder': 3,
          'seaslug': 1, 'priestperil': 1, 'totem': 1, 'runemysteries': 1}


def prerequisite_flags(quest):
    if quest == 'junglepotion':
        return [('druid', 'druidquest', 4)]
    # Exercise mining the essence rather than seeding the delivery items.
    return [('runemysteries', 'runemysteries', 6)] if quest == 'priestperil' else []


def initial_points(quest):
    return sum([POINTS[row[0]] for row in prerequisite_flags(quest)])
