# Live end-to-end tests

These scenarios run the real client and bot scripts against a local development
server. They are separate from the fake-server and stdlib tests run by CTest.

| Scenario | Server | Coverage |
|---|---|---|
| [Phase 16](phase16/README.md) | Local revision 289 | 19 individual quest accounts, including both Arrav gangs; optional full queues with earned QP gates |
| [Phase 17a](phase17a/README.md) | Local revision 289 | 12 individual accounts for the introductory members quests |
| [Phase 17b](phase17b/README.md) | Local revision 289 | 9 individual accounts, including Scorpion Catcher's barcrawl |
| [Phase 17c](phase17c/README.md) | Local revision 289 | 5 individual accounts, with explicit prerequisite-only preparation |
| [Phase 17d](phase17d/README.md) | Local revision 289 | 4 individual accounts for Nature Spirit, Shades of Mort'ton, Tai Bwo Wannai Trio and Shilo Village |
| [Phase 17e](phase17e/README.md) | Local revision 289 | 4 individual accounts for Tourist Trap, Watch Tower, Chompy and Grand Tree |
| [Phase 17f](phase17f/README.md) | Local revision 289 | 5 individual accounts for Elemental Workshop, Digsite, Holy Grail, Family Crest and Horror |
| [Phase 17g](phase17g/README.md) | Local revision 289 | Both Hero's Quest gangs, Temple of Ikov (Guardians), The Fremennik Trials |

Generated credentials, configurations, logs and results belong under the ignored
`build/e2e/` directory. Each new acceptance run uses fresh scratch characters.
The setup scripts deliberately seed preparation; consult each scenario's scope
before treating its result as natural account progression or endurance evidence.

All suites use [the shared launcher](harness.py) and runtime helpers in `scripts/`.

[Recorded validation results](VALIDATION.md) include a **Time taken** column for
each quest. Future acceptance tables should include this column too: measure from
the account's first `AIOQuester, queue:` entry to its passing `E2E_RESULT`, including
the final bank return. Exclude seeding and login staggering. Include and disclose
restart gaps in elapsed time; retain the per-session breakdown for resumed cases.
