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
