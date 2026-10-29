"""The crawl reads rendered card text and verifies drinks and the final guard hand-in."""

import rs2004.quests.barcrawl.run_barcrawl as crawl
from rs2004.catalogs.record import Record
from helpers import FakeModule
from quest_world import QuestWorld, QuestObject


class Card(QuestObject):
    def use_on(self, npc):
        if self.accept:
            bar = [b for b in crawl.BARS if b.id == npc.id][0]
            world = self.world
            self.world.effects.append(lambda: world.serve(bar))
        return self.accept


class CrawlWorld(QuestWorld):
    def __init__(self):
        QuestWorld.__init__(self)
        self.remaining = list(crawl.BARS)
        self.reads = 0
        self.read_mode = 'card'
        self.read_after = 1
        self.drinks = True
        self.card = Card(self, crawl.BARCRAWL_CARD, effect=self.read)

    def __enter__(self):
        QuestWorld.__enter__(self)
        self.install(crawl)
        self.patch(crawl, 'reader', FakeModule(modals=lambda: FakeModule(main=self.get_main_modal()),
                                               main_modal_texts=self.texts))
        return self

    def read(self):
        self.reads += 1
        if self.read_mode == 'drunk':
            self.messages.append(crawl.TOO_DRUNK)
        elif self.read_mode == 'lost':
            self.pack = []
        elif self.read_mode != 'silent' and self.reads >= self.read_after:
            self.pages = [('main', [])]

    def texts(self):
        if self.read_mode == 'bad_text':
            return ['Loading...']
        left = [b.line for b in self.remaining]
        return ['The Official Barcrawl!'] + [b.line + (' - Not Completed...' if b.line in left else ' - Completed!') for b in crawl.BARS]

    def serve(self, bar):
        self.actions.append(('serve', bar.line))
        if self.drinks:
            self.remaining = [b for b in self.remaining if b.line != bar.line]
            coin = self.first('Coins')
            coin.count -= bar.gp
        return True


def test_card_read_retries_late_modal_and_parses_fresh_text():
    with CrawlWorld() as w:
        w.pack = [w.card]
        w.read_after = 2
        state = w.run(crawl.read_card(w.logs.append))
        assert len(state.remaining) == 10 and not state.done and w.reads == 2
        w.remaining = []
        state = w.run(crawl.read_card(w.logs.append))
        assert state.done and not state.remaining and w.get_main_modal() == -1


def test_card_read_distinguishes_drunk_missing_refused_and_unreadable_cards():
    for mode in ['missing', 'refused', 'silent', 'lost', 'bad_text', 'drunk']:
        with CrawlWorld() as w:
            w.pack = [] if mode == 'missing' else [w.card]
            w.card.accept = mode != 'refused'
            w.read_mode = mode
            result = w.run(crawl.read_card(w.logs.append))
            assert (result is not None) == (mode == 'drunk')
            if result is not None:
                assert result.done


def test_bartender_drink_checks_arrival_card_and_signature():
    for mode in ['walk_failed', 'missing', 'no_card', 'refused', 'unsigned', 'signed']:
        with CrawlWorld() as w:
            bar = crawl.BARS[0]
            w.can_walk = mode != 'walk_failed'
            w.scene = [] if mode == 'missing' else [QuestObject(w, bar.npc, bar.id, at=bar.tile)]
            coins = QuestObject(w, 'Coins')
            coins.count = 1000
            w.pack = [coins] if mode == 'no_card' else [w.card, coins]
            w.card.accept = mode != 'refused'
            w.drinks = mode != 'unsigned'
            result = w.run(crawl.drink_at(bar, w.logs.append))
            assert result == (mode == 'signed'), (mode, w.logs, w.actions, w.texts())


def test_crawl_tours_all_bars_and_stops_after_three_consecutive_refusals():
    with CrawlWorld() as w:
        coins = QuestObject(w, 'Coins')
        coins.count = 2000
        w.pack = [w.card, coins]
        w.scene = [QuestObject(w, b.npc, b.id, at=b.tile) for b in crawl.BARS]
        progress = []
        result = w.run(crawl.run_barcrawl(w.logs.append, lambda done, total: progress.append((done, total))))
        assert result, (w.logs, w.actions, w.texts())
        assert len([a for a in w.actions if a[0] == 'serve']) == 10
        assert progress[-1] == (10, 10)
        w.remaining = list(crawl.BARS)
        w.drinks = False
        assert not w.run(crawl.run_barcrawl(w.logs.append))
        assert '3 bars in a row' in w.logs[-1]
        w.pack = []
        assert not w.run(crawl.run_barcrawl(w.logs.append))


def test_guard_greeting_issues_card_or_proves_already_complete():
    for mode in ['unreachable', 'missing_guard', 'failed', 'complete', 'issued', 'interrupted']:
        with CrawlWorld() as w:
            w.can_walk = mode != 'unreachable'
            w.scene = [] if mode == 'missing_guard' else [QuestObject(w, 'Barbarian guard', crawl.BARBARIAN_GUARD_ID, at=crawl.GUARD_TILE)]
            def talk(find, op, expect, **kw):
                assert find() is not None and op == 'Talk-to'
                w.pages = [('continue', ["'Ello friend." if mode == 'complete' else 'How is the Barcrawl?'])]
                yield from w.reply()
                if mode == 'issued':
                    w.pack = [w.card]
                return 'failed' if mode == 'failed' else 'done'
            w.patch(crawl, 'reach', FakeModule(entity_op=talk))
            verdict = w.run(crawl.ask_guard(w.logs.append))
            assert verdict == ('complete' if mode == 'complete' else ('issued' if mode == 'issued' else 'retry'))


def test_ensure_crawl_and_handin_propagate_each_leg_result():
    for mode in ['complete', 'retry', 'tour_failed', 'handin_failed', 'done']:
        with CrawlWorld() as w:
            w.patch(crawl, 'ask_guard', lambda *a: w.reply(mode if mode in ['complete', 'retry'] else 'issued'))
            w.patch(crawl, 'run_barcrawl', lambda *a: w.reply(mode != 'tour_failed'))
            w.patch(crawl, 'talk_to_guard', lambda *a: w.reply(mode != 'handin_failed'))
            assert w.run(crawl.ensure_barcrawl(w.logs.append)) == (mode in ['complete', 'done'])
