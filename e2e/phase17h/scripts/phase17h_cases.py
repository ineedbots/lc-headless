"""Independent targets and explicit preparation-only prerequisites."""

CASES = {'up': 'upass', 'rg': 'regicide'}
POINTS = {'upass': 5, 'regicide': 3, 'elena': 1, 'biohazard': 3}


def prerequisite_flags(quest):
    flags = [('elena', 'elenaquest', 29), ('biohazard', 'biohazard', 16)]
    if quest == 'regicide':
        flags.append(('upass', 'upass', 10))
    return flags


def initial_points(quest):
    return sum([POINTS[row[0]] for row in prerequisite_flags(quest)])


def preparation_flags(quest):
    # Completing the prerequisite also persists cave entry, four burned orbs,
    # three paladin crests and the unicorn horn. Its journal flag alone does not.
    # These are Underground Pass gates, never Regicide target progress.
    bits = [5, 6, 7, 8, 11, 14, 15, 16, 18]
    return [('ibanmulti', sum([1 << bit for bit in bits]))] if quest == 'regicide' else []


def preparation_items(quest):
    items = [('shortbow', 'Shortbow', 1), ('bronze_arrow', 'Bronze arrow', 500)]
    if quest == 'regicide':
        items.append(('cert_shark', 'Shark', 1000))
    return items
