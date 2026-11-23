# Live end-to-end tests

These scenarios run the real client and bot scripts against a local development
server. They are separate from the fake-server and stdlib tests run by CTest.

| Scenario | Server | Coverage |
|---|---|---|
| [Phase 16](phase16/README.md) | Local revision 289 | 19 individual quest accounts, including both Arrav gangs; optional full queues with earned QP gates |
| [Phase 17a](phase17a/README.md) | Local revision 289 | 12 individual accounts for the introductory members quests |
| [Phase 17b](phase17b/README.md) | Local revision 289 | 9 individual accounts, including Scorpion Catcher's barcrawl |
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
