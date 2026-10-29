"""Both handoff APIs prove delivery after confirmation and retry mutual requests."""

import rs2004.partner_handoff as handoff
import rs2004.catalogs.partner as partner
from rs2004 import execution
from rs2004.entities import EntityQuery
from helpers import FakeModule
from test_partner_trade_workflows import HandoffWorld, Item


class MeetingWorld(HandoffWorld):
    def __init__(self):
        HandoffWorld.__init__(self)
        self.scene = [FakeModule(name='Alice', distance=lambda: 1)]
        self.requests = []
        self.request_accepts = True
        self.open_after = 2
        self.pending_request = False
        self.near_at = None
        self.cancel_at = None
        self.patches = []

    def patch(self, module, name, value):
        self.patches.append((module, name, getattr(module, name)))
        setattr(module, name, value)

    def __enter__(self):
        HandoffWorld.__enter__(self)
        for name in ['_core', 'inventory', 'traversal']:
            self.patch(handoff, name, getattr(partner, name))
        self.patch(handoff, 'reader', FakeModule(modals=lambda: FakeModule(main=-1)))
        query = FakeModule(query=lambda: EntityQuery(self.players, lambda obj: True))
        self.patch(handoff, 'players', query)
        self.patch(partner, 'players', query)
        # Requests are the external handshake boundary; offers and acceptance use real trade readers.
        self.saved_request = type(partner.trade).request
        self.install_request()
        return self

    def __exit__(self, *args):
        type(partner.trade).request = self.saved_request
        for module, name, value in reversed(self.patches):
            setattr(module, name, value)
        HandoffWorld.__exit__(self, *args)

    def players(self, ids, names, radius, layer):
        return self.scene

    def advance(self):
        HandoffWorld.advance(self)
        if self.near_at is not None and self.now >= self.near_at:
            self.scene = [FakeModule(name='Alice', distance=lambda: 1)]
        if self.cancel_at is not None and self.now >= self.cancel_at:
            self.mode = 'closed'

    def install_request(self):
        world = self
        def request(trade, name):
            world.requests.append((name, world.now))
            if world.request_accepts and len(world.requests) >= world.open_after:
                world.mode = 'offer'
            return world.request_accepts
        type(partner.trade).request = request

    def standalone(self, giving):
        return self.run(handoff.run_handoff(FakeModule(partner='Alice', rendezvous=(3000, 3000), id=989,
            name='Key', giving=giving, label='key handoff', log=self.logs.append)))


def test_handoff_request_retries_until_mutual_window_opens():
    for standalone in [True, False]:
        with MeetingWorld() as world:
            world.install_request()
            task = handoff.open_trade('Alice', world.logs.append) if standalone else partner._open_trade('Alice', world.logs.append)
            assert world.run(task)
            assert len(world.requests) == 2 and world.requests[1][1] >= handoff.OPEN_REQUEST_EVERY_MS


def test_handoff_waits_for_partner_to_return_before_requesting():
    with MeetingWorld() as world:
        world.install_request()
        world.scene, world.near_at, world.open_after = [], 1500, 1
        assert world.run(handoff.open_trade('Alice', world.logs.append))
        assert world.requests[0][1] >= 1500 and 'come back' in world.logs[0]
        assert not handoff.partner_near('   ')


def test_handoff_refused_request_is_failure_for_both_apis():
    for standalone in [True, False]:
        with MeetingWorld() as world:
            world.install_request()
            world.request_accepts = False
            task = handoff.open_trade('Alice', world.logs.append) if standalone else partner._open_trade('Alice', world.logs.append)
            assert world.run(task) is False and len(world.requests) == 1


def test_handoff_open_deadline_does_not_send_more_requests():
    with MeetingWorld() as world:
        world.install_request()
        world.scene = []
        world.now = 0
        task = handoff.open_trade('Alice', world.logs.append)
        next(task)
        world.now = handoff.MEET_MS
        try:
            next(task)
        except StopIteration as stopped:
            assert stopped.value is False
        assert world.requests == [] and 'never opened' in world.logs[-1]


def test_standalone_handoff_gives_exact_id_and_confirms_pack_delta():
    with MeetingWorld() as world:
        world.pack += [Item(988, 'Key', 1, ['Offer 1']), Item(989, 'Key', 2, ['Offer 1'])]
        assert world.standalone(True)
        assert world.count_by_id(988) == 1 and world.count_by_id(989) == 1
        assert world.clicks == [(989, 'Offer 1'), 'Accept', 'Accept']


def test_standalone_handoff_receives_and_detects_missing_delivery():
    for lands in [True, False]:
        with MeetingWorld() as world:
            world.theirs = [Item(989, 'Key', 1, [])]
            world.land_items = lands
            assert world.standalone(False) == lands
            assert world.mode == 'closed'


def test_standalone_handoff_missing_item_or_failed_walk_stops():
    with MeetingWorld() as world:
        assert world.standalone(True) is False and world.walks == []
        world.arrives = False
        assert world.standalone(False) is False and world.clicks == []


def test_standalone_handoff_cancellation_is_not_delivery():
    with MeetingWorld() as world:
        world.mode = 'offer'
        world.pack.append(Item(989, 'Key', 1, ['Offer 1']))
        world.accept_result = 'close'
        assert world.standalone(True) is False
        assert 'did not move' in world.logs[-1]


def test_standalone_handoff_already_open_trade_requires_confirmation():
    with MeetingWorld() as world:
        world.mode = 'offer'
        world.pack.append(Item(989, 'Key', 2, ['Offer 1']))
        assert world.standalone(True)
        assert world.count_by_id(989) == 1 and world.mode == 'closed'


def test_handoff_receiver_waits_for_item_in_offer_before_accepting():
    for standalone in [True, False]:
        with MeetingWorld() as world:
            world.cancel_at = 1500
            result = world.standalone(False) if standalone else world.handoff(False)
            assert result is False and 'Accept' not in world.clicks


def test_standalone_handoff_declines_wrong_partner_and_failed_offer():
    for stranger in [True, False]:
        with MeetingWorld() as world:
            world.pack.append(Item(989, 'Key', 1, ['Offer 1']))
            if stranger:
                world.texts = ['Trading With: Eve']
            else:
                world.accept_click = False
            assert world.standalone(True) is False
            assert world.mode == 'closed' and world.clicks[-1] == 'Decline'
