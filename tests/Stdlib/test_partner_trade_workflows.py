"""Partner policy over real trade screens with delayed offers and confirmation updates."""

import rs2004.catalogs.partner as partner
from rs2004.trade import trade
from rs2004 import execution
from helpers import FakeModule
from test_trade_workflows import TradeWorld, Item


class PartnerWorld(TradeWorld):
    def __init__(self):
        TradeWorld.__init__(self)
        self.logs = []
        self.statuses = []
        self.completed = []
        self.declined = []
        self.accept_result = 'confirm'
        self.confirm_closes = True
        self.received = 0
        self.events = []

    def __enter__(self):
        TradeWorld.__enter__(self)
        self.partner_saved = (partner._core, partner.inventory)
        partner._core = self
        partner.inventory = FakeModule(used=self.metric)
        return self

    def __exit__(self, *args):
        partner._core, partner.inventory = self.partner_saved
        TradeWorld.__exit__(self, *args)

    def metric(self):
        return sum([item.count for item in self.pack]) + self.received

    def click_text(self, text, root):
        self.clicks.append(text)
        if text == 'Decline':
            self.pending = ('close', 0)
            return True
        assert text == 'Accept'
        if self.mode == 'offer' and self.accept_result != 'offer':
            self.pending = (self.accept_result, 0)
        elif self.mode == 'confirm' and self.confirm_closes:
            self.pending = ('complete', 0)
        return True

    def advance(self):
        if self.pending is not None and self.pending[0] in ['confirm', 'complete']:
            kind = self.pending[0]
            self.pending = None
            self.mode = 'confirm' if kind == 'confirm' else 'closed'
            if kind == 'complete':
                self.received += sum([item.count for item in self.theirs])
        TradeWorld.advance(self)
        if self.events:
            self.mode = self.events.pop(0)

    def drive(self, role='receiver', **options):
        kwargs = {'on_complete': self.completed.append, 'on_decline': self.declined.append}
        kwargs.update(options)
        return self.run(partner.drive_active_partner_trade(
            role, ['Alice'], lambda name: name == 'Logs', lambda: ['Logs'],
            self.statuses.append, self.logs.append, **kwargs))


def test_receiver_waits_for_missing_header_without_accepting():
    with PartnerWorld() as world:
        world.texts = []
        world.drive()
        assert world.statuses == ['mule: reading partner']
        assert world.clicks == [] and world.completed == []
        assert len(world.waits) == 1


def test_missing_partner_timeout_declines_and_notifies_caller():
    with PartnerWorld() as world:
        world.texts = []
        world.drive(on_missing_partner=lambda: 'decline')
        assert world.mode == 'closed'
        assert world.declined == ['partner header timeout']
        assert world.completed == []


def test_receiver_rejects_stranger_or_nonempty_own_offer():
    for stranger in [True, False]:
        with PartnerWorld() as world:
            world.theirs = [Item(1511, 'Logs', 20, [])]
            if stranger:
                world.texts = ['Trading With: Eve']
            else:
                world.mine = [Item(995, 'Coins', 100, [])]
            world.drive()
            assert world.clicks == ['Decline']
            assert world.mode == 'closed'
            assert len(world.declined) == 1 and world.completed == []


def test_receiver_waits_for_matching_product_instead_of_accepting_other_items():
    with PartnerWorld() as world:
        world.theirs = [Item(995, 'Coins', 100, [])]
        world.drive()
        assert world.clicks == []
        assert world.statuses == ['mule: waiting for product offer']


def test_receiver_capacity_gate_can_decline_with_a_reason_or_boolean():
    for answer in [False, (False,), (False, 'pack is full')]:
        with PartnerWorld() as world:
            world.theirs = [Item(1511, 'Logs', 20, [])]
            seen = []

            def gate(count):
                seen.append(count)
                return answer

            world.drive(receiver_can_accept=gate)
            assert seen == [20]
            assert world.clicks == ['Decline']
            expected = 'pack is full' if answer == (False, 'pack is full') else 'receiver cannot accept offer'
            assert world.declined == [expected]


def test_receiver_accepts_offer_then_confirms_and_reports_received_items():
    with PartnerWorld() as world:
        world.theirs = [Item(1511, 'Logs', 20, [])]
        world.drive(receiver_can_accept=lambda count: (True, 'enough room'))
        assert world.mode == 'confirm' and world.completed == []
        world.drive()
        assert world.mode == 'closed'
        assert world.clicks == ['Accept', 'Accept']
        assert world.completed == [20] and world.declined == []


def test_giver_offers_haul_before_accepting_and_keeps_preoffer_baseline():
    with PartnerWorld() as world:
        before = world.metric()
        world.drive('giver')
        assert world.clicks == [(1511, 'Offer All')]
        assert world.mode == 'offer'
        assert world.metric() == 0
        world.drive('giver')
        assert world.mode == 'confirm' and world.completed == []
        world.drive('giver', baseline=lambda: before)
        assert world.mode == 'closed'
        assert world.completed == [-20]


def test_giver_can_verify_partner_before_offering_anything():
    with PartnerWorld() as world:
        world.texts = ['Trading With: Eve']
        world.drive('giver', verify_giver_partner=True)
        assert world.clicks == ['Decline']
        assert world.pack[0].count == 20


def test_giver_declines_when_no_products_or_all_offer_clicks_fail():
    for empty in [True, False]:
        with PartnerWorld() as world:
            if empty:
                world.pack = []
                # An empty name list and a failed offer are distinct failure paths.
                world.run(partner.drive_active_partner_trade(
                    'giver', ['Alice'], lambda name: True, lambda: [], world.statuses.append,
                    world.logs.append, on_decline=world.declined.append))
            else:
                world.accept_click = False
                world.drive('giver')
            assert world.mode == 'closed'
            assert world.declined == ['nothing to offer' if empty else 'offerAll failed']
            assert 'Accept' not in world.clicks


def test_custom_offer_readiness_can_hold_accept_until_all_products_are_shown():
    with PartnerWorld() as world:
        world.mine = [Item(995, 'Coins', 100, [])]
        world.drive('giver', my_offer_ready=lambda: False)
        assert (1511, 'Offer All') in world.clicks
        assert 'Accept' not in world.clicks
        world.drive('giver', my_offer_ready=lambda: True)
        assert world.mode == 'confirm'


def test_offer_accept_timeout_does_not_report_completion():
    with PartnerWorld() as world:
        world.accept_result = 'offer'
        world.theirs = [Item(1511, 'Logs', 20, [])]
        world.drive()
        assert world.mode == 'offer'
        assert world.completed == []
        assert 'TIMED OUT' in world.logs[-1]


def test_partner_cancellation_after_offer_accept_does_not_report_completion():
    with PartnerWorld() as world:
        world.accept_result = 'close'
        world.theirs = [Item(1511, 'Logs', 20, [])]
        world.drive()
        assert world.mode == 'closed' and world.completed == []
        assert 'without reaching confirm' in world.logs[-1]


def test_confirm_timeout_keeps_trade_open_without_completion_callback():
    with PartnerWorld() as world:
        world.mode = 'confirm'
        world.confirm_closes = False
        world.drive()
        assert world.mode == 'confirm' and world.completed == []
        assert 'partner may not have accepted' in world.logs[-1]


def test_transient_gap_between_screens_is_not_treated_as_completed_trade():
    with PartnerWorld() as world:
        world.mode = 'confirm'
        world.confirm_closes = False
        world.events = ['closed', 'confirm']
        world.drive()
        assert world.mode == 'confirm' and world.completed == []
        assert world.now >= partner.TRADE_CONFIRM_WAIT_MS


def test_closed_poll_requires_continuous_closure_and_resets_on_reopen():
    with PartnerWorld() as world:
        poll = partner.stable_closed_poll(600)
        assert not poll()
        world.mode = 'closed'
        assert not poll()
        world.now = 599
        assert not poll()
        world.mode = 'offer'
        assert not poll()
        world.mode = 'closed'
        assert not poll()
        world.now += 600
        assert poll()


def test_status_labels_can_be_customized_as_dict_or_record():
    for labels in [{'accepting': 'receiving logs'}, FakeModule(accepting='receiving logs')]:
        with PartnerWorld() as world:
            world.theirs = [Item(1511, 'Logs', 20, [])]
            world.drive(labels=labels)
            assert world.statuses == ['receiving logs']


class HandoffWorld(PartnerWorld):
    def __init__(self):
        PartnerWorld.__init__(self)
        self.mode = 'closed'
        self.pack = [Item(995, 'Coins', 1, [])]
        self.land_items = True
        self.arrives = True
        self.walks = []

    def __enter__(self):
        PartnerWorld.__enter__(self)
        self.handoff_saved = (partner.modals, partner.traversal)
        partner.inventory = FakeModule(used=self.metric, count_by_id=self.count_by_id)
        partner.modals = FakeModule(main=lambda: -1)
        partner.traversal = FakeModule(walk_resilient=self.walk)
        return self

    def __exit__(self, *args):
        partner.modals, partner.traversal = self.handoff_saved
        PartnerWorld.__exit__(self, *args)

    def count_by_id(self, id):
        return sum([item.count for item in self.pack if item.id == id])

    def walk(self, dest, **kwargs):
        self.walks.append(dest)
        yield execution.Ticks(1)
        if self.arrives and self.mode == 'closed':
            self.mode = 'offer'
        return self.arrives

    def advance(self):
        completing = self.pending is not None and self.pending[0] == 'complete'
        PartnerWorld.advance(self)
        if completing and self.land_items:
            self.pack.extend(self.theirs)

    def handoff(self, giving):
        return self.run(partner.run_handoff('Alice', (3000, 3000), 989, 'Key', giving,
                                           'key handoff', self.logs.append))


def test_handoff_gives_exact_id_when_two_items_share_the_same_name():
    with HandoffWorld() as world:
        world.pack += [Item(988, 'Key', 1, ['Offer 1']), Item(989, 'Key', 2, ['Offer 1'])]
        assert world.handoff(True)
        assert world.count_by_id(988) == 1
        assert world.count_by_id(989) == 1
        assert world.clicks == [(989, 'Offer 1'), 'Accept', 'Accept']
        assert world.mode == 'closed'


def test_handoff_receives_item_and_checks_pack_after_confirm_closes():
    with HandoffWorld() as world:
        world.theirs = [Item(989, 'Key', 1, [])]
        assert world.handoff(False)
        assert world.count_by_id(989) == 1
        assert world.clicks == ['Accept', 'Accept']
        assert world.logs[-1] == 'key handoff moved a Key'


def test_handoff_does_not_claim_receipt_when_confirm_closes_without_item():
    with HandoffWorld() as world:
        world.theirs = [Item(989, 'Key', 1, [])]
        world.land_items = False
        assert world.handoff(False) is False
        assert world.count_by_id(989) == 0
        assert 'did not move a Key' in world.logs[-1]


def test_handoff_without_item_to_give_does_not_walk_or_request_trade():
    with HandoffWorld() as world:
        assert world.handoff(True) is False
        assert world.walks == [] and world.clicks == []
        assert 'nothing to give' in world.logs[0]


def test_handoff_does_not_trade_when_meeting_point_cannot_be_reached():
    with HandoffWorld() as world:
        world.arrives = False
        assert world.handoff(False) is False
        assert world.clicks == []
        assert world.mode == 'closed'


def test_handoff_declines_wrong_partner_before_offering_key():
    with HandoffWorld() as world:
        world.texts = ['Trading With: Eve']
        world.pack.append(Item(989, 'Key', 1, ['Offer 1']))
        assert world.handoff(True) is False
        assert world.count_by_id(989) == 1
        assert world.clicks == ['Decline'] and world.mode == 'closed'


def test_handoff_declines_when_exact_item_cannot_be_offered():
    with HandoffWorld() as world:
        world.pack.append(Item(989, 'Key', 1, ['Offer 1']))
        world.accept_click = False
        assert world.handoff(True) is False
        assert world.clicks == [(989, 'Offer 1'), 'Decline']
        assert world.count_by_id(989) == 1


def test_handoff_started_on_open_trade_needs_confirmation_to_prove_give():
    with HandoffWorld() as world:
        world.mode = 'offer'
        world.pack.append(Item(989, 'Key', 2, ['Offer 1']))
        assert world.handoff(True)
        assert world.count_by_id(989) == 1
        assert world.clicks == [(989, 'Offer 1'), 'Accept', 'Accept']


def test_cancelled_open_handoff_does_not_mistake_offer_for_completed_give():
    with HandoffWorld() as world:
        world.mode = 'offer'
        world.pack.append(Item(989, 'Key', 1, ['Offer 1']))
        world.accept_result = 'close'
        assert world.handoff(True) is False
        assert world.clicks == [(989, 'Offer 1'), 'Accept']
        assert 'confirmed=False' in world.logs[-1]
