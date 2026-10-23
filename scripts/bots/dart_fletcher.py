# Uses feathers on stackable dart tips, five times a tick, the most the server reads, until either stack runs
# out: rs2b0t's DartFletcher (MIT, see thirdparty/rs2b0t). It runs anywhere.

DARTS_PER_ACTION = 10
# The engine decodes at most five USER_EVENT packets per player each tick. One item-on-item packet makes up to
# ten darts, so five is the useful ceiling.
DART_ACTIONS_PER_TICK = 5
NO_PROGRESS_LIMIT = 3


class DartPlan:
    def __init__(self, tier, tips, product, level, xp_per_dart):
        self.tier = tier
        self.tips = tips
        self.product = product
        self.level = level
        self.xp_per_dart = xp_per_dart


DART_PLANS = [
    DartPlan('Bronze', 'Bronze dart tip', 'Bronze dart', 1, 1.8),
    DartPlan('Iron', 'Iron dart tip', 'Iron dart', 22, 3.8),
    DartPlan('Steel', 'Steel dart tip', 'Steel dart', 37, 7.5),
    DartPlan('Mithril', 'Mithril dart tip', 'Mithril dart', 52, 11.2),
    DartPlan('Adamant', 'Adamant dart tip', 'Adamant dart', 67, 15),
    DartPlan('Rune', 'Rune dart tip', 'Rune dart', 81, 18.8),
]
DART_TIER_OPTIONS = [plan.tier for plan in DART_PLANS]


def dart_plan_for(tier):
    wanted = tier.strip().lower()
    for plan in DART_PLANS:
        if plan.tier.lower() == wanted:
            return plan
    return None


def dart_actions_for(tips, feathers):
    """How many item-on-item packets to send this tick: enough for the darts the stacks make, at most 5."""
    available = max(0, min(int(tips), int(feathers)))
    return min(DART_ACTIONS_PER_TICK, (available + DARTS_PER_ACTION - 1) // DARTS_PER_ACTION)


def dart_xp_ceiling_per_hour(plan, tick_ms=600):
    if tick_ms <= 0:
        return 0
    return plan.xp_per_dart * DARTS_PER_ACTION * DART_ACTIONS_PER_TICK * 3600000 / tick_ms


SETTINGS = {
    'tier': SettingDef('string', 'Bronze', 'Dart tier', options=DART_TIER_OPTIONS,
                       help='Feathers are spam-used on this tier of stackable dart tips; runs anywhere and stops when either stack is empty'),
}


class DartFletcher(LoopingBot):
    # Every loop waits a tick itself after its burst of packets.
    loop_delay = 0

    def on_start(self):
        selected = self.settings.str('tier', 'Bronze')
        plan = dart_plan_for(selected)
        if plan is None:
            raise ValueError(f"DartFletcher: unknown dart tier '{selected}'")
        level = skills.level('fletching')
        if level < plan.level:
            raise ValueError(f'DartFletcher: Fletching {plan.level} required for {plan.tier} darts (have {level})')
        self.plan = plan
        self.xp_at_start = skills.xp('fletching')
        self.product_at_start = inventory.count(plan.product)
        self.actions_sent = 0
        self.no_progress = 0
        self.finished = False
        self.status = f'spamming {plan.tier.lower()} darts'
        ceiling = round(dart_xp_ceiling_per_hour(plan))
        self.log(f'DartFletcher: Feather + {plan.tips} -> {plan.product}; up to 5 actions/tick (10 darts each, theoretical {ceiling} XP/hr at 600ms ticks)')

    def loop(self):
        if chat_dialog.can_continue():
            self.status = 'clearing a dialog'
            yield from chat_dialog.continue_()
            yield from execution.delay_ticks(1)
            return
        if chat_dialog.is_open():
            self.status = 'waiting for a dialog'
            yield from execution.delay_ticks(1)
            return

        plan = self.plan
        tips_before = inventory.count(plan.tips)
        feathers_before = inventory.count('Feather')
        if tips_before <= 0 or feathers_before <= 0:
            self.finish(f'out of {plan.tips}' if tips_before <= 0 else 'out of Feather')
            return
        if inventory.count(plan.product) == 0 and inventory.free() == 0:
            self.finish(f'needs one free inventory slot for {plan.product}')
            return

        feather = inventory.first('Feather')
        tips = inventory.first(plan.tips)
        if feather is None or tips is None:
            self.finish('the input stacks disappeared')
            return

        sent = 0
        for _ in range(dart_actions_for(tips_before, feathers_before)):
            if feather.use_on(tips):
                sent += 1
        self.actions_sent += sent
        yield from execution.delay_ticks(1)

        def used():
            return inventory.count(plan.tips) < tips_before or inventory.count('Feather') < feathers_before

        progressed = yield from execution.delay_until(lambda: used() or chat_dialog.is_open(), 1200)
        if progressed and used():
            self.no_progress = 0
            self.status = f'spamming {plan.tier.lower()} darts'
            return

        self.no_progress += 1
        self.status = f'no progress ({self.no_progress}/{NO_PROGRESS_LIMIT})'
        if sent == 0 or self.no_progress >= NO_PROGRESS_LIMIT:
            self.finish('item-on-item actions made no progress')

    def made(self):
        return max(0, inventory.count(self.plan.product) - self.product_at_start)

    def on_progress_report(self):
        return {
            'Status': self.status,
            'Fletching': skills.level('fletching'),
            'XP': skills.xp('fletching') - self.xp_at_start,
            'Made': self.made(),
            self.plan.tips: inventory.count(self.plan.tips),
            'Feathers': inventory.count('Feather'),
            'Actions sent': self.actions_sent,
        }

    def finish(self, reason):
        if self.finished:
            return
        self.finished = True
        self.status = reason
        self.request_finish(f'DartFletcher: {reason}; made {self.made()} darts')


BOT = define_bot(
    name='DartFletcher',
    create=DartFletcher,
    description='Spam-attaches feathers to stackable dart tips at the five-action-per-tick server ceiling; runs anywhere until either input stack is empty',
    category='Fletching',
    tags=['fletching', 'darts', 'members', 'fast'],
    settings_schema=SETTINGS,
)
