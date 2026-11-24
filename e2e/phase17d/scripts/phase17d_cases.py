"""Individual targets and explicit transitive prerequisites for phase 17d."""

CASES = {'ns': 'druidspirit', 'sm': 'mortton', 'tw': 'tbwt', 'sv': 'zombiequeen'}
POINTS = {'druidspirit': 2, 'mortton': 3, 'tbwt': 2, 'zombiequeen': 2,
          'priest': 1, 'priestperil': 1, 'runemysteries': 1,
          'junglepotion': 1, 'druid': 4}


def prerequisite_flags(quest):
    if quest in ['druidspirit', 'mortton']:
        flags = [('runemysteries', 'runemysteries', 6), ('priestperil', 'priestperil', 61)]
        if quest == 'druidspirit':
            flags.append(('priest', 'prieststart', 5))
        return flags
    return [('druid', 'druidquest', 4), ('junglepotion', 'junglepotion', 13)]


def initial_points(quest):
    return sum([POINTS[row[0]] for row in prerequisite_flags(quest)])


def preparation_flags(quest):
    # The swamp gate requires Nature Spirit started, but awards no QP.
    return [('druidspirit', 5)] if quest == 'mortton' else []


def preparation_items(quest):
    if quest == 'tbwt':
        return [('iron_spear', 'Iron spear', 1), ('4dose1agility', 'Agility potion(4)', 1),
                ('magic_shortbow', 'Magic shortbow', 1), ('adamant_arrow', 'Adamant arrow', 500),
                ('rune_med_helm', 'Rune med helm', 1)]
    return []
