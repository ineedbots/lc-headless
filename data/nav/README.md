# Walker data

rs2b0t's web walker data, exported by `tools/nav/export_rs2b0t.ts` and used by `NavGraph` and the stdlib's `traversal`. It comes from rs2b0t under the MIT licence; see `thirdparty/rs2b0t/LICENSE`.

| File | Holds |
|---|---|
| `edges.json` | Doors, stairs, ladders, ships, shortcuts and curated travel, compiled to edges as rs2b0t's `PathFinder.addEdges` compiles them, with costs and requirements |
| `teleports.json` | Spell and jewellery teleports |
| `crossings.json` | Special crossings: tolls, fares, keyed doors and their dialogue |
| `danger_zones.json` | Areas a route can be told to avoid |
| `banks.json` | Known banks and how to open the unusual ones |

To refresh it from an rs2b0t checkout, run `bun tools/nav/export_rs2b0t.ts <rs2b0t folder> data/nav` and commit the result.
The current upstream baseline is `27e57fa331656df5a0d9b7b1cd1f4ec0c44519bb`.
Use that revision when regenerating a local engine correction without an upstream refresh.

`NavGraphJson` decodes graph files separately from graph indexing. It preserves
required fields, contextual teleport costs, and the walkability check before
optional edge metadata is decoded. Graph points use objects with an optional
`level` defaulting to zero. Route requests instead require `[x, z, level]` arrays;
`NavPayloadJson.hpp` serializes route results as objects. These formats are
intentionally separate.

rs2b0t derives its stair edges from its own engine's content. Where the 289 engine's differs, the exporter applies `STAIR_FIXES`, `EDGE_ADDITIONS` and `CROSSING_ADDITIONS`. Each was found and checked live.

The Observatory reception ladder pairs an added edge with a dialogue crossing:
the assistant's goblin warning needs continuing before the player lands in the
cavern. See [the revision-289 reproduction and validation](VALIDATION.md) for
the route, engine behavior and test evidence behind issue #56.
