# Open work

GitHub issues are the source of truth for remaining work. The reviewed 2026-11-05 backlog has been
migrated below, including optional work and observations awaiting a recurrence. Those observations
are not confirmed failures or release blockers. Follow issue state rather than treating this index
as a second checklist.

All original parity phases (10–18) are implemented. Historical plans, acceptance evidence and limits
remain in [BotApiParityDesign.md](BotApiParityDesign.md), [BotApiParityQuestPhases.md](BotApiParityQuestPhases.md),
[BotApiParityStatus.md](BotApiParityStatus.md) and [Rs2b0tUpstreamReview.md](Rs2b0tUpstreamReview.md).
Issue bodies retain the original context through commit-pinned links.

## Implementation and tooling

- [#28: Implement the playable Tutorial Island sequence](https://github.com/ineedbots/lc-headless/issues/28)
- [#29: Review upstream rs2b0t changes after 8b7db422](https://github.com/ineedbots/lc-headless/issues/29)
- [#30: Finish the JiveDragons and JiveKQ upstream scenario audit](https://github.com/ineedbots/lc-headless/issues/30)
- [#31: Resolve the cache-backed Debug navigation test timeout](https://github.com/ineedbots/lc-headless/issues/31)

## Live validation

- [#32: Record live acceptance for Cosmic, MuleDepot, MuleCrafter and three-tick fishing](https://github.com/ineedbots/lc-headless/issues/32)
- [#33: Validate multiloc transitions against real revision-289 content](https://github.com/ineedbots/lc-headless/issues/33)
- [#34: Repeat phases 17h and 17i acceptance at 600 ms ticks](https://github.com/ineedbots/lc-headless/issues/34)
- [#35: Extend AccountLeveler live validation beyond low-level accelerated methods](https://github.com/ineedbots/lc-headless/issues/35)
- [#36: Complete the phase-11 fifteen-minute live acceptance runs](https://github.com/ineedbots/lc-headless/issues/36)
- [#37: Demonstrate live rerouting after a refused crossing with an alternative](https://github.com/ineedbots/lc-headless/issues/37)
- [#38: Complete revision-225 and revision-274 live protocol evidence](https://github.com/ineedbots/lc-headless/issues/38)

## Bugs and limitations awaiting a trigger

- [#39: Investigate recurring JiveKQ Shantay-pass restock failure](https://github.com/ineedbots/lc-headless/issues/39)
- [#40: Detect quest watchdog loops caused by tile oscillation](https://github.com/ineedbots/lc-headless/issues/40)
- [#41: Detect quest watchdog loops hidden by repeated wield swaps](https://github.com/ineedbots/lc-headless/issues/41)
- [#42: Bound repeated offers of a failing teleport during repaths](https://github.com/ineedbots/lc-headless/issues/42)
- [#43: Investigate Radimus dialogue closure if retry recovery fails](https://github.com/ineedbots/lc-headless/issues/43)
- [#44: Investigate delayed gilded-totem hand-in if it recurs](https://github.com/ineedbots/lc-headless/issues/44)
- [#45: Source a replacement spade after Regicide death when needed](https://github.com/ineedbots/lc-headless/issues/45)
- [#46: Support paired Heros Quest rune-kit provisioning without a harness](https://github.com/ineedbots/lc-headless/issues/46)
- [#47: Handle hard-clue Kharazi pack pressure and Saradomin Wizard loadout](https://github.com/ineedbots/lc-headless/issues/47)
- [#48: Investigate a recurring unexplained clue bank stall](https://github.com/ineedbots/lc-headless/issues/48)

## Revisions and deferred maintenance

- [#49: Audit revision-specific content IDs and navigation on 225 and 274](https://github.com/ineedbots/lc-headless/issues/49)
- [#50: Implement optional revision-225 map downloads over the wire](https://github.com/ineedbots/lc-headless/issues/50)
- [#51: Allow accounts to use different revisions and caches](https://github.com/ineedbots/lc-headless/issues/51)
- [#52: Replace custom byte swapping when adopting C++23](https://github.com/ineedbots/lc-headless/issues/52)
- [#53: Support literal IPv6 server hosts when required](https://github.com/ineedbots/lc-headless/issues/53)
- [#54: Bound the transport send queue under stalled-server backpressure](https://github.com/ineedbots/lc-headless/issues/54)
- [#55: Add a configuration JSON Schema when configuration growth warrants it](https://github.com/ineedbots/lc-headless/issues/55)
- [#56: Correct engine-specific walker data when new routes expose mismatches](https://github.com/ineedbots/lc-headless/issues/56)
- [#57: Refresh obsolete revision-289 protocol implementation notes](https://github.com/ineedbots/lc-headless/issues/57)

## Cosmetic and optional coverage

- [#58: Remove duplicate trail-complete logging](https://github.com/ineedbots/lc-headless/issues/58)
- [#59: Correct GnomeMagicChopper chopped-count reporting](https://github.com/ineedbots/lc-headless/issues/59)
- [#60: Evaluate useful JiveKBD default combat settings](https://github.com/ineedbots/lc-headless/issues/60)
- [#61: Avoid redundant Black Knights Fortress grill listening after restart](https://github.com/ineedbots/lc-headless/issues/61)
- [#62: Add optional behavioral coverage beyond the stdlib 95-percent floor](https://github.com/ineedbots/lc-headless/issues/62)

[All open repository issues](https://github.com/ineedbots/lc-headless/issues?q=is%3Aissue%20state%3Aopen).
