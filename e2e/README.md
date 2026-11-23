# Live end-to-end tests

These scenarios run the real client and bot scripts against a local development
server. They are separate from the fake-server and stdlib tests run by CTest.

| Scenario | Server | Coverage |
|---|---|---|
| [Phase 17g](phase17g/README.md) | Local revision 289 | Both Hero's Quest gangs, Temple of Ikov (Guardians), The Fremennik Trials |

Generated credentials, configurations, logs and results belong under the ignored
`build/e2e/` directory. Each new acceptance run uses fresh scratch characters.
The setup scripts deliberately seed preparation; consult each scenario's scope
before treating its result as natural account progression or endurance evidence.
