# Revision 274 Design

Plan for connecting to revision-274 servers. It follows [RevisionDesign.md](RevisionDesign.md) §14, "Adding a revision later", and keeps that plan's rules (§2.3 there): 225 is the base, a later revision's difference is a `>=` branch on the first supported revision that has it, and whether a packet exists is asked of the opcode table. Code style follows [CONVENTIONS.md](../CONVENTIONS.md).

One finding shapes the whole plan: 274 is 289's protocol with its own opcode numbers. Diffing the two engines and the two webclients finds only:

- every opcode renumbered, with the same packets at the same sizes;
- `UPDATE_INV_FULL` and `UPDATE_INV_PARTIAL` with 225's field widths;
- four definition opcodes that only 289 has: loc `77`, obj `115`, varp `12` and `13`;
- public chat effects numbered as in 225.

So most of the work is moving existing thresholds from `Rev289` down to `Rev274` (§3). Three things don't move that way. The two inventory packets stay at `Rev289`. The definition opcodes, whose "removed in 289" and "added in 289" lists can't describe a revision in between, become a table (§6). Chat effects get a branch that 225 already needs (§7). The work ships in six phases (§11).

Reference sources, beside this repository:

- `274server/engine/src/network/game/server/ServerGameProt.ts`, `ServerGameZoneProt.ts`, `client/ClientGameProt.ts`: the 274 opcode tables (Appendix A). The webclient's `io/ServerProt.ts` and `io/ClientProt.ts` agree on every opcode. They name five packets differently (`IF_SETICON`, `IF_SHOWICON`, `P_LOCMERGE`, `VARP_SYNC`, `SEND_SNAPSHOT`); this client keeps the engine's names
- `274server/engine/src/network/`: every payload. Diffed against `289server`'s, it differs only in the opcode tables, the two inventory encoders, and two handlers' server-side checks (§5)
- `274server/engine/src/network/rsbuf/`: entity info, byte-identical to 289's
- `274server/engine/src/engine/entity/Player.ts` (`generateAppearance`): the appearance block
- `274server/webclient/src/client/Client.ts`: the login and `tcpIn`. It differs from 289's only in `CLIENT_VERSION`, the two inventory reads, chat effects, multilocs and teams
- `274server/webclient/src/config/*.ts`: the definition decoders (§6)
- `274server/engine/tools/pack/`: the cache packers. The interface packer is 289's apart from its verify CRC
- `274server/engine/data/pack/`: a packed 274 store. `274server/engine/data/config/public.pem`: the server's RSA key

The comparison is reproducible with `diff -r --strip-trailing-cr` between `274server` and `289server` on `engine/src`, `webclient/src` and `engine/tools/pack`.

---

## 1. Decisions

| Topic | Decision |
|---|---|
| Revisions | 225, 274 and 289. `Rev274 = 274` goes between the other two in `Revision_e`, which stays in release order |
| Nearest revision | 289. A branch that names `Rev289` today moves to `Rev274`, unless §3 says it stays |
| Opcodes | New `SERVER_PROTS_274` and `CLIENT_PROTS_274` tables: the same 69 server and 82 client packets as 289, at different opcodes (Appendix A). No logical packet is added |
| Inventories | 274 sends `UPDATE_INV_FULL`'s size and `UPDATE_INV_PARTIAL`'s slots in a byte, as 225 does. Those two branches stay at `Rev289` |
| Definitions | `TypeDecoder::HasOpcode`'s two lists become one table per type of `RevisionedOpcode_s`, each entry naming the revision that added or removed its opcode (§6) |
| Chat effects | 225 and 274 servers drop a public message whose effect is over 2, and number scroll `2`; 289 numbers it `4` and adds three more. `MessagePublic` maps `Scroll` and rejects the other three before 289. This fixes 225 too (§7) |
| Cache | 289's store layout. `client.cacheDirectory` points at the 274 engine's `data/pack` folder (§8) |
| Replies | None. 274 has no `REBUILD_GETMAPS` or input tracking, and `GameClient::Reply` already asks the table, so it sends neither without a change |
| Where it's set | `login.revision: 274`, as for the other two. The default stays `289` |
| Script API | `game.revision()` returns `274`. Nothing else changes: 274 has `members`, player ops 1 to 5 and drag-insert, as 289 does |
| Content | 274's obj, NPC, loc and inv ids are a prefix of 289's, and its interface and varp ids are the same numbers. The catalogs and nav data load; what 274 lacks is the audit in §12 |

---

## 2. How 274 compares

| Area | 225 | 274 | 289 |
|---|---|---|---|
| Opcode table | its own | its own; 289's packets and sizes | its own |
| Login | server seed first; `u8` revision; status `2` or `18`, nothing after | 289's | seed request; `0xFF` then `u16` revision; status `2` then staff level and mouse tracking; `21` hop timer |
| `UPDATE_PID`, `LAST_LOGIN_INFO`, `REBUILD_NORMAL`, `MIDI_SONG`, `MIDI_JINGLE`, `MESSAGE_PRIVATE` | 225's | 289's | 289's |
| `UPDATE_INV_FULL` size, `UPDATE_INV_PARTIAL` slot | `u8`, `u8` | `u8`, `u8` | `u16`, smart |
| Entity info | 13-bit NPC index, no jump bit, no `DAMAGE2`, no transform, no total level | 289's | 14-bit index, jump bit, `DAMAGE2`, transform, total level |
| `INV_BUTTOND`, `EVENT_CAMERA_POSITION` | 6 bytes, 6 bytes | 289's | 7 bytes, 4 bytes |
| 225-only packets: `DATA_*`, `ENABLE_TRACKING`, `FINISH_TRACKING`, `IF_SETRECOL`, `REBUILD_GETMAPS`, `EVENT_TRACKING` | present | absent | absent |
| 289-only packets of RevisionDesign §4: `SET_PLAYER_OP`, `OPPLAYER5`, `MAP_BUILD_COMPLETE` and the rest | absent | present | present |
| Cache layout | loose files and `maps/` | store | store |
| Interfaces | 225's format | 289's | 289's |
| Bank component | found by content | client code 206 | client code 206 |
| Player menu | fixed | from `SET_PLAYER_OP` | from `SET_PLAYER_OP` |
| Chat effects | 0 to 2; scroll is `2` | 0 to 2; scroll is `2` | 0 to 5; scroll is `4` |
| Definition opcodes | §6 | §6 | §6 |

---

## 3. Every branch, and where 274 lands

`grep -rn "Revision_e::" src` lists these. Line numbers are as of commit `2244c0f`.

| Site | Guards | 274 takes | Change |
|---|---|---|---|
| `ServerProt::GetTable`, `ClientProt::GetTable` | the opcode table | its own | `case Revision_e::Rev274: return TABLE_274;` |
| `LoginHandshake.cpp:40` | the first stage: seed request or server seed | 289's | `>= Rev274` |
| `LoginHandshake.cpp:182` | the revision field | 289's | `>= Rev274` |
| `LoginHandshake.cpp:241` | status `2` or `18` ends the login | 289's | `< Rev274` |
| `LoginHandshake.cpp:254` | status `21`, the hop timer | 289's | `>= Rev274` |
| `PlayerStateDecoder.cpp:131` | `LAST_LOGIN_INFO`'s `warnMembers` | 289's | `>= Rev274` |
| `PlayerStateDecoder.cpp:170` | `UPDATE_PID`'s `members` | 289's | `>= Rev274` |
| `SceneDecoder.cpp:46` | `REBUILD_NORMAL`'s map squares | 289's | `< Rev274` |
| `SceneDecoder.cpp:103`, `:112` | `MIDI_SONG` and `MIDI_JINGLE` consumed | 289's | `< Rev274` |
| `SocialDecoder.cpp:119` | `MESSAGE_PRIVATE`'s staff level sent one higher | 289's | `< Rev274` |
| `InventoryDecoder.cpp:37` | `UPDATE_INV_FULL`'s size | **225's** | stays `>= Rev289`; comment (§5) |
| `InventoryDecoder.cpp:58` | `UPDATE_INV_PARTIAL`'s slot | **225's** | stays `>= Rev289`; comment (§5) |
| `PlayerInfoDecoder.cpp:158` | the appearance transform | 289's | `>= Rev274` |
| `PlayerInfoDecoder.cpp:183` | the appearance total level | 289's | `>= Rev274` |
| `PlayerInfoDecoder.cpp:291` | a `DAMAGE2` bit is an error | 289's | `< Rev274` |
| `NpcInfoDecoder.cpp:36` | index bits and end of list | 289's | `>= Rev274` |
| `NpcInfoDecoder.cpp:115` | the jump bit | 289's | `>= Rev274` |
| `NpcInfoDecoder.cpp:151` | a `DAMAGE2` bit is an error | 289's | `< Rev274` |
| `ClientPackets.cpp:127` | `EVENT_CAMERA_POSITION`'s minimap bytes | 289's | `< Rev274` |
| `ClientPackets.cpp:324` | `INV_BUTTOND`'s mode | 289's | `>= Rev274` |
| `Menus.cpp:154` | the fixed player menu | 289's | `< Rev274` |
| `CacheLoader.cpp:248` | the bank by client code | 289's | `>= Rev274` |
| `CacheLoader.cpp:502` | the missing-map warning's wording | 289's | `>= Rev274` |
| `CacheLoader.cpp:531` | store or folder | 289's | `>= Rev274` |
| `InterfaceDecoder.cpp:106`, `:147`, `:166`, `:260` | `objReplace`, the child count, `colour2Over`, `trans` | 289's | `>= Rev274` |
| `TypeDecoder.cpp:19`, `HasOpcode` | definition opcodes | mixed | replaced by a table (§6) |
| `ClientPackets::MessagePublic` | chat effects | 225's | a new branch (§7) |
| `Config_s.hpp:10`, `SUPPORTED_REVISIONS` | which revisions the config accepts | | `Rev274` added in phase 5 |
| `Config_s.hpp:15`, `GameCache_s.hpp:25` | defaults | | unchanged |

`FakeGameServer`'s login branches (`FakeGameServer.cpp:227`, `:278`, `:362`, `:388`, `:398`) move with `LoginHandshake`'s.

A comment beside a moved branch names the supported revisions on each side, not the revision a change landed in, because nothing between 225 and 274 is known: `// 225 only swaps; later revisions add the mode.` Error messages that name revision 225, such as `Revision 225 can't insert a dragged item, only swap it`, stay as they are, since only 225 still reaches them.

---

## 4. Opcode tables

`Revision_e` gains the new revision in release order:

```cpp
enum class Revision_e : u16
{
    Rev225 = 225,
    Rev274 = 274,
    Rev289 = 289,
};
```

`ServerProt.cpp` gains `SERVER_PROTS_274` with 69 rows, `static_assert(SERVER_PROTS_274.size() == 69, "Revision 274 has 69 server packets")`, the `HasUniqueRows` check, `TABLE_274` and a case in `GetTable`. `ClientProt.cpp` gains the same for its 82 client packets.

`ServerProt_e`, `ClientProt_e` and their name tables don't change, because 274 has exactly 289's packets. The zone sub-packets are the same ten. The packets 274 lacks are the 225-only ones: server `DATA_LAND`, `DATA_LAND_DONE`, `DATA_LOC`, `DATA_LOC_DONE`, `ENABLE_TRACKING`, `FINISH_TRACKING` and `IF_SETRECOL`; client `EVENT_TRACKING` and `REBUILD_GETMAPS`. An opcode outside the 274 table is a `ProtocolError` naming revision 274, as for the others.

Generate the rows instead of copying them. Appendix A came from:

```sh
sed -n 's/.*static readonly \([A-Z0-9_]*\) = new ServerGame[A-Za-z]*Prot(\([0-9]*\), \(-\?[0-9]*\)).*/\1 \2 \3/p' \
    ServerGameProt.ts ServerGameZoneProt.ts
```

and the same pattern with `ClientGameProt` for the client table.

---

## 5. The wire

### Login

289's, byte for byte. The client sends `14` and the login-server byte, reads 8 zero bytes, status `0` and the seed, then sends `0xFF` and `u16 274`, and reads status `2` followed by the staff level and the mouse-tracking flag. Status `21` is the hop timer. The server answers `6` for a revision other than its `ENGINE_REVISION`, which is `274` by default. `LoginHandshake`'s four branches move (§3), and nothing else changes.

### Server packets

Every payload is 289's except these two, which take 225's field widths:

| Packet | 274 | Decoder |
|---|---|---|
| `UPDATE_INV_FULL` | `u16 com`, `u8 size`, then the items. The size runs to the last used slot, as 289's does, not over the whole capacity, as 225's does | Reads the size in a byte, as for 225. It replaces the inventory with `size` slots either way, so what the size covers doesn't matter to it |
| `UPDATE_INV_PARTIAL` | `u16 com`, then per entry a `u8 slot` and an item | Reads the slot in a byte, as for 225 |

The branches stay at `Rev289`, and their comments change to name both older revisions:

```cpp
// 225 and 274 send the size in a byte; 289 widened it to two.
const auto size = protocol.GetRevision() >= Revision_e::Rev289 ? packet.G2() : packet.G1();
```

```cpp
// 225 and 274 send each slot in a byte; 289 widened it to a smart.
const auto slot = static_cast<std::size_t>(protocol.GetRevision() >= Revision_e::Rev289 ? packet.GSmart() : packet.G1());
```

A byte is enough on 274: its bank holds 240 slots and its largest other inventory 216. 289's bank holds 288, which is why 289 widened both fields.

The two handlers that differ between the 274 and 289 engines only check things on the server. 289's `OpLocHandler` resolves a multiloc through its varbit before checking the op, and 289's `MessagePublicHandler` allows effects up to 5 (§7). Neither changes a payload.

### Entity info

289's. `rsbuf/` is byte-identical between the two engines. The 274 engine's `generateAppearance` writes the `u16` total level after the combat level. The 274 webclient reads 14-bit NPC indexes with a jump bit, `DAMAGE2` and the `0xFFFF` transform marker. The six entity branches move (§3).

### Client packets

289's, for every packet. `INV_BUTTOND` is 7 bytes with its mode, so drag-insert works, and `EVENT_CAMERA_POSITION` is 4 bytes. `OPPLAYER5`, `MAP_BUILD_COMPLETE`, `EVENT_APPLET_FOCUS`, `EVENT_MOUSE_CLICK`, `EVENT_MOUSE_MOVE` and `ANTICHEAT_CYCLELOGIC7` all exist. The two builder branches move (§3). Chat effects are §7.

### Replies

None. `GameClient::Reply` sends `REBUILD_GETMAPS` and `EVENT_TRACKING` only when `m_protocol.Has(...)` says the revision has them, which 274's table doesn't, and a 274 server never sends `ENABLE_TRACKING`. `GameClient` doesn't change.

---

## 6. Definition opcodes

The opcodes each revision's webclient decodes, where they differ:

| Type | 225 only | 274 and 289 | 289 only |
|---|---|---|---|
| loc | `25` | `5`, `74`, `75` | `77` (multiloc) |
| npc | `16` | `99` to `103` | |
| obj | `9` | `110` to `114` | `115` (team) |
| varp | | `11` | `12`, `13` |

The seq and varbit decoders differ too (289 adds seq `12` and varbit `2` to `4`), but this client decodes neither.

Today each decoder hands two lists to `TypeDecoder::HasOpcode(revision, opcode, removedIn289, addedIn289)`, which can only put a revision on one side of 289. With three revisions, each opcode has to say where it starts and where it stops. `src/Cache/RevisionedOpcode_s.hpp`, beside `DroppedOpcodes_s.hpp`:

```cpp
#pragma once

#include "../Config/Revision_e.hpp"

// An opcode only some revisions have: every revision from addedIn on, until removedIn if a later one dropped it.
struct RevisionedOpcode_s
{
    u8 opcode = 0;
    Revision_e addedIn = Revision_e::Rev225;
    std::optional<Revision_e> removedIn;

    [[nodiscard]] static constexpr RevisionedOpcode_s AddedIn(u8 opcode, Revision_e revision)
    {
        return {.opcode = opcode, .addedIn = revision};
    }

    [[nodiscard]] static constexpr RevisionedOpcode_s RemovedIn(u8 opcode, Revision_e revision)
    {
        return {.opcode = opcode, .removedIn = revision};
    }
};
```

`TypeDecoder::HasOpcode` takes one table:

```cpp
// Whether the revision has the opcode; one the table doesn't list is in every revision. A cache decoded as
// the wrong revision then fails on an unknown opcode rather than reading garbage.
[[nodiscard]] static bool HasOpcode(Revision_e revision, u8 opcode, std::span<const RevisionedOpcode_s> table);
```

```cpp
bool TypeDecoder::HasOpcode(Revision_e revision, u8 opcode, std::span<const RevisionedOpcode_s> table)
{
    const auto found = std::ranges::find(table, opcode, &RevisionedOpcode_s::opcode);
    if (found == table.end())
    {
        return true;
    }

    return revision >= found->addedIn && (!found->removedIn || revision < *found->removedIn);
}
```

Each decoder's `REMOVED_IN_289` and `ADDED_IN_289` become one `REVISIONED` table. The loc decoder's, once 274 exists:

```cpp
using Revisioned = RevisionedOpcode_s;

constexpr auto REVISIONED = std::to_array({
    Revisioned::RemovedIn(ANIMATE_TRANSPARENCIES, Revision_e::Rev274),
    Revisioned::AddedIn(MODELS, Revision_e::Rev274),
    Revisioned::AddedIn(BREAK_ROUTE_FINDING, Revision_e::Rev274),
    Revisioned::AddedIn(RAISE_OBJECT, Revision_e::Rev274),
    Revisioned::AddedIn(MULTILOC, Revision_e::Rev289),
});
```

| Decoder | `RemovedIn(…, Rev274)` | `AddedIn(…, Rev274)` | `AddedIn(…, Rev289)` |
|---|---|---|---|
| `LocTypeDecoder` | `ANIMATE_TRANSPARENCIES` | `MODELS`, `BREAK_ROUTE_FINDING`, `RAISE_OBJECT` | `MULTILOC` |
| `NpcTypeDecoder` | `ANIMATE_TRANSPARENCIES` | `ALWAYS_ON_TOP`, `AMBIENT`, `CONTRAST`, `HEAD_ICON`, `TURN_SPEED` | |
| `ObjTypeDecoder` | `CODE9` | `RESIZE_X`, `RESIZE_Y`, `RESIZE_Z`, `AMBIENT`, `CONTRAST` | `TEAM` |
| `VarpTypeDecoder` | | `CODE11` | `CODE12`, `CODE13` |

The `DROPPED` tables don't change: an opcode a revision lacks is rejected before `SkipDropped` sees it.

Phase 2 writes these tables with `Rev289` wherever the lists say 289 today, so 225 and 289 decode exactly as before. Phase 4 lowers the thresholds in the middle column to `Rev274`.

---

## 7. Chat effects

The 225 and 274 servers drop a public message whose effect is over 2, and their webclients send `1` for `wave:` and `2` for `scroll:`. 289 allows effects up to 5 and renumbers them: `1` wave, `2` wave2, `3` shake, `4` scroll, `5` slide. `ChatEffect_e` follows 289, and `ClientPackets::MessagePublic` writes it unmapped. So on a 225 server today, a `Scroll` message is dropped and a `Wave2` one scrolls.

`MessagePublic` keeps its range check and then maps the effect through a helper in its anonymous namespace:

```cpp
constexpr auto SCROLL_BEFORE_289 = u8{2};

// 225 and 274 have three effects, with scroll third; 289 added three more and moved scroll to 4.
u8 GetWireEffect(ChatEffect_e effect, Revision_e revision)
{
    if (revision >= Revision_e::Rev289)
    {
        return static_cast<u8>(effect);
    }

    switch (effect)
    {
    case ChatEffect_e::None:
    case ChatEffect_e::Wave:
        return static_cast<u8>(effect);
    case ChatEffect_e::Scroll:
        return SCROLL_BEFORE_289;
    case ChatEffect_e::Wave2:
    case ChatEffect_e::Shake:
    case ChatEffect_e::Slide:
        break;
    }

    throw std::invalid_argument{std::format("Revision {} has only the wave and scroll chat effects", static_cast<u16>(revision))};
}
```

Scripts can't choose an effect yet (`say(text)` sends `None`), so nothing a script sees changes. The fix keeps the builder from writing a packet the server drops, and it is the one place 274 needs a branch that 225 was missing.

`PlayerInfoDecoder` keeps the CHAT block's effect in `Player_s::chat.effect` as the server sent it, and nothing reads it. It stays the wire byte. A binding that exposes it later maps it back the way `MESSAGE_PRIVATE`'s staff level is mapped (RevisionDesign §6).

---

## 8. The cache

| | 274 |
|---|---|
| Folder | The 274 engine's `data/pack`: `main_file_cache.dat` and `.idx0` to `.idx4`, as for 289 |
| CRCs | Files 0 to 8 of store 0 |
| Maps | `map_index` in `versionlist`; gzip with a 2-byte version |
| Interfaces | 289's format: `trans`, a `u16` child count, `objReplace` and four colours |
| Bank | Client code 206 |
| Definitions | §6 |

`CacheLoader`'s three branches and `InterfaceDecoder`'s four move to `Rev274` (§3).

`STORE_HINT` names revision 289 today. It becomes a format string over the revision, so a 274 config pointed at a folder without a store reads `main_file_cache.dat not found; for revision 274, set client.cacheDirectory to the folder that holds the server's cache`.

The other likely mistake is a store from the wrong one of the two store revisions, and the files alone can't show it:

- A 289 cache read as 274 fails, because two 289 objs use opcode `115`. `CacheLoader::Load`'s catch adds the revision it read as, so the error explains itself: `../289server/engine/data/pack: read as revision 274: obj N: unknown opcode 115`.
- A 274 cache read as 289 decodes, since 274's opcodes are a subset of 289's. The login then fails with status `6`, whose message already asks whether `login.revision` and `client.cacheDirectory` match the server.

`CacheDesign.md`'s notes on revisions gain 274: the store layout, the opcode table of §6, and `RS2004_CACHE_DIR_274`.

---

## 9. Script API and configuration

| Piece | Change |
|---|---|
| `LoginSettings_s::SUPPORTED_REVISIONS` | `{Rev225, Rev274, Rev289}`, in phase 5. `ConfigValidator` builds `must be 225, 274 or 289` from the list without a code change |
| `rs2004/game.py` | `revision()`'s docstring: `The server revision this client speaks: 225, 274 or 289.` |
| Typings | None: `revision() -> int` already covers it |
| `client.jsonc.sample` | `// 289, 274 or 225. client.cacheDirectory must hold the same revision's cache.` |
| `README.md` | The intro, the requirements, the `login.revision` and `client.cacheDirectory` rows, and `tcp-protocol-274.md` in the document table |
| `ConfigDesign.md` | The `login.revision` rows and the validation table's cases |
| `ScriptingApi.md` | `revision()` lists 274. A "Revision 274" note beside the 225 one: the catalogs and nav data are 289's, and anything added after 274 doesn't exist there |

---

## 10. Tests

| File | Tests |
|---|---|
| `Game/ProtocolTests.cpp` | `SERVER_ROWS_274`, `CLIENT_ROWS_274` and 274's missing client packets. Every `GENERATE` over revisions gains `Rev274`, and the zone test covers 274's ten zone opcodes |
| `Game/NetTests.cpp` | The 289 login tests also run for 274: the seed request, `0xFF` and `u16 274`, the staff-level and mouse-tracking bytes, and the hop timer |
| `Game/ServerPacketDecoderTests.cpp` | 274's `UPDATE_INV_FULL` with a byte size and `UPDATE_INV_PARTIAL` with byte slots. `UPDATE_PID`, `LAST_LOGIN_INFO`, `REBUILD_NORMAL`, `MIDI_SONG`, `MIDI_JINGLE` and `MESSAGE_PRIVATE` read as 289's. A 225-only opcode such as `DATA_LAND`'s is a `ProtocolError` on 274 |
| `Game/EntityInfoTests.cpp` | The 289 cases also run for 274: the 14-bit NPC index and jump bit, `DAMAGE2`, the transform and the total level |
| `Game/ClientPacketsTests.cpp` | 274's `INV_BUTTOND` is 7 bytes and inserts; `EVENT_CAMERA_POSITION` is 4 bytes; `REBUILD_GETMAPS` and `EVENT_TRACKING` throw. Chat effects: `Scroll` writes `2` on 225 and 274 and `4` on 289; `Wave2`, `Shake` and `Slide` throw on 225 and 274 |
| `Game/MenusTests.cpp` | 274's player menu comes from `playerOps` |
| `Game/GameClientTests.cpp` | Against `FakeGameServer{..., Revision_e::Rev274}`: a login, and a `REBUILD_NORMAL` that gets no reply |
| `Cache/TypeDecoderTests.cpp` | `HasOpcode` for an unlisted opcode, and for `AddedIn` and `RemovedIn` on each side of their revision. Each opcode in §6's first table is read in the revisions that have it and rejected in those that don't |
| `Cache/InterfaceDecoderTests.cpp` | The `GENERATE`s gain 274 with 289's fields. The "read as the other revision" pairs become 225 against each of 274 and 289, and 274's bytes read as 289 give the same components |
| `Cache/CacheLoaderTests.cpp` | A 274 store loads and finds the bank by client code. A 274 config pointed at a folder gets the hint naming 274. An unknown opcode's error names the revision it read as |
| `Support/Cache/RealCache.cpp`, `Cache/RealCacheTests.cpp` | `RS2004_CACHE_DIR_274`, such as `../274server/engine/data/pack`, skipped when unset. Its CRCs, its components and a few map squares match the 274 content, and every loc, NPC and obj decodes |
| `Config/ConfigFileTests.cpp` | 274 loads; 273 and 275 fail with `must be 225, 274 or 289` |
| `Script/ScriptBindingsTests.cpp` | `game.revision()` returns 274 |

---

## 11. Phases

Each phase builds on both presets and passes every test before the next starts, as in RevisionDesign §13. On this machine that means Windows Debug and Release, where warnings are errors. linux-clang can't be built here, so keep every `Revision_e` switch exhaustive for clang's `-Wswitch`.

### Phase 1: chat effects

§7 and its `ClientPacketsTests`. This doesn't depend on 274 and fixes 225 on its own.

### Phase 2: definition opcodes as a table, with 225 and 289 unchanged

`RevisionedOpcode_s`, the new `HasOpcode`, and the four decoders' `REVISIONED` tables with `Rev289` wherever the lists say 289 today. The `HasOpcode` tests. Every existing decoder test passes untouched.

### Phase 3: `Rev274` and its opcode tables

`Revision_e::Rev274`, `SERVER_PROTS_274` and `CLIENT_PROTS_274`, the `GetTable` cases, and the `ProtocolTests`. `Rev274` isn't in `SUPPORTED_REVISIONS` yet, so nothing can select it while every other branch still treats it as 225.

### Phase 4: the 274 cache

The `Rev274` thresholds in §6, `CacheLoader`'s and `InterfaceDecoder`'s branches, the bank, the revision-aware hint and error context, and their tests, including the optional real 274 cache test.

### Phase 5: logging in to 274, decoding and acting

- Every wire branch in §3, and `FakeGameServer`'s.
- The login, decoder, entity, client-packet, menu, game-client and binding tests.
- `Rev274` joins `SUPPORTED_REVISIONS`, and §9's documents are updated.
- A live run against a local 274 server. Use a scratch `client.jsonc` with `login.revision: 274`, `cacheDirectory` at `274server/engine/data/pack` and the RSA key from `274server/engine/data/config/public.pem`. Log in, walk, bank, drop and pick up an item, trade, go through a dialogue, drag an inventory item both as a swap and as an insert, attack another player where that's allowed, and stay logged in for ten minutes. The 274 and 289 servers default to the same ports (`WEB_PORT`, `NODE_PORT`), so run one at a time or move one.

### Phase 6: the 274 reference

`docs/tcp-protocol-274.md`, written as differences from [tcp-protocol-289.md](../tcp-protocol-289.md): Appendix A's tables, the two inventory payloads, chat effects, and the cache's definition opcodes. The README's document table links it.

---

## 12. Out of scope and risks

- **Content.** 274's obj, NPC, loc and inv ids are a prefix of 289's: 3894 of 4089 objs, 1359 of 1596 NPCs, 4671 of 5116 locs and 217 of 228 invs, each with the same id. Its interface and varp ids are 289's numbers, and only some names differ. So anything the catalogs and `random_solvers.py` use that 274 has means the same thing; what was added after 274 is missing. Its maps differ in 85 squares, and 51 squares exist only in 289, so some of `data/nav`'s edges and teleports from rs2b0t, which moved to 289, cross scenery that 274 doesn't have. The cache gives the right collision either way. The audit belongs with RevisionDesign §15's: run the catalog-name test against the real 274 cache and key what's missing on `game.revision()`.
- **Server options.** The 274 server honours `NODE_DEBUG`, which defaults to true, while the 289 server here forces it off. It changes only debug messages and whether staff accounts get random events, not the wire.
- **Live-only checks.** The CHAT block's `rights` numbering and `MESSAGE_PRIVATE`'s staff level are 289's code in the 274 engine, but the live run in phase 5 still confirms them.

---

## Appendix A. Opcode tables

Generated from the 274 engine's `ServerGameProt.ts`, `ServerGameZoneProt.ts` and `ClientGameProt.ts`, with 289's opcode beside each for comparison. Every size equals 289's, so one column serves both. A size of `-1` is a byte length and `-2` a 2-byte length.

### Server to client

| Name | 274 op | Size | 289 op |
|---|---:|---:|---:|
| `CAM_LOOKAT` | 233 | 6 | 82 |
| `CAM_MOVETO` | 200 | 6 | 73 |
| `CAM_RESET` | 101 | 0 | 133 |
| `CAM_SHAKE` | 64 | 4 | 208 |
| `CHAT_FILTER_SETTINGS` | 114 | 3 | 13 |
| `FRIENDLIST_LOADED` | 185 | 1 | 235 |
| `HINT_ARROW` | 156 | 6 | 115 |
| `IF_CLOSE` | 171 | 0 | 23 |
| `IF_OPENCHAT` | 166 | 2 | 81 |
| `IF_OPENMAIN` | 211 | 2 | 119 |
| `IF_OPENMAIN_SIDE` | 158 | 4 | 55 |
| `IF_OPENOVERLAY` | 240 | 2 | 127 |
| `IF_OPENSIDE` | 16 | 2 | 252 |
| `IF_SETANIM` | 134 | 4 | 211 |
| `IF_SETCOLOUR` | 183 | 4 | 160 |
| `IF_SETHIDE` | 10 | 3 | 138 |
| `IF_SETMODEL` | 129 | 4 | 222 |
| `IF_SETNPCHEAD` | 142 | 4 | 244 |
| `IF_SETOBJECT` | 28 | 6 | 18 |
| `IF_SETPLAYERHEAD` | 192 | 2 | 30 |
| `IF_SETPOSITION` | 77 | 6 | 79 |
| `IF_SETSCROLLPOS` | 54 | 4 | 184 |
| `IF_SETTAB` | 215 | 3 | 63 |
| `IF_SETTAB_ACTIVE` | 241 | 1 | 189 |
| `IF_SETTEXT` | 44 | -2 | 59 |
| `LAST_LOGIN_INFO` | 91 | 10 | 253 |
| `LOC_ADD_CHANGE` | 138 | 4 | 90 |
| `LOC_ANIM` | 48 | 4 | 106 |
| `LOC_DEL` | 173 | 2 | 194 |
| `LOC_MERGE` | 176 | 14 | 83 |
| `LOGOUT` | 88 | 0 | 121 |
| `MAP_ANIM` | 85 | 6 | 233 |
| `MAP_PROJANIM` | 107 | 15 | 87 |
| `MESSAGE_GAME` | 161 | -1 | 196 |
| `MESSAGE_PRIVATE` | 235 | -1 | 243 |
| `MIDI_JINGLE` | 15 | 4 | 29 |
| `MIDI_SONG` | 23 | 2 | 187 |
| `MINIMAP_TOGGLE` | 194 | 1 | 136 |
| `NPC_INFO` | 197 | -2 | 65 |
| `OBJ_ADD` | 81 | 5 | 60 |
| `OBJ_COUNT` | 95 | 7 | 117 |
| `OBJ_DEL` | 52 | 3 | 71 |
| `OBJ_REVEAL` | 219 | 7 | 176 |
| `PLAYER_INFO` | 167 | -2 | 188 |
| `P_COUNTDIALOG` | 210 | 0 | 35 |
| `REBUILD_NORMAL` | 231 | 4 | 219 |
| `RESET_ANIMS` | 47 | 0 | 201 |
| `RESET_CLIENT_VARCACHE` | 190 | 0 | 172 |
| `SET_MULTIWAY` | 207 | 1 | 247 |
| `SET_PLAYER_OP` | 17 | -1 | 21 |
| `SYNTH_SOUND` | 34 | 5 | 177 |
| `TUT_FLASH` | 90 | 1 | 181 |
| `TUT_OPEN` | 130 | 2 | 12 |
| `UNSET_MAP_FLAG` | 115 | 0 | 164 |
| `UPDATE_FRIENDLIST` | 247 | 9 | 168 |
| `UPDATE_IGNORELIST` | 3 | -2 | 47 |
| `UPDATE_INV_FULL` | 106 | -2 | 107 |
| `UPDATE_INV_PARTIAL` | 172 | -2 | 76 |
| `UPDATE_INV_STOP_TRANSMIT` | 227 | 2 | 28 |
| `UPDATE_PID` | 133 | 3 | 120 |
| `UPDATE_REBOOT_TIMER` | 89 | 2 | 204 |
| `UPDATE_RUNENERGY` | 83 | 1 | 195 |
| `UPDATE_RUNWEIGHT` | 67 | 2 | 46 |
| `UPDATE_STAT` | 105 | 6 | 154 |
| `UPDATE_ZONE_FULL_FOLLOWS` | 153 | 2 | 144 |
| `UPDATE_ZONE_PARTIAL_ENCLOSED` | 195 | -2 | 112 |
| `UPDATE_ZONE_PARTIAL_FOLLOWS` | 32 | 2 | 155 |
| `VARP_LARGE` | 245 | 6 | 97 |
| `VARP_SMALL` | 203 | 3 | 75 |

274 has 69 server packets, as 289 does, and none keeps its 289 opcode. The zone sub-packets are `LOC_ANIM` 48, `OBJ_DEL` 52, `OBJ_ADD` 81, `MAP_ANIM` 85, `OBJ_COUNT` 95, `MAP_PROJANIM` 107, `LOC_ADD_CHANGE` 138, `LOC_DEL` 173, `LOC_MERGE` 176 and `OBJ_REVEAL` 219.

### Client to server

| Name | 274 op | Size | 289 op |
|---|---:|---:|---:|
| `ANTICHEAT_CYCLELOGIC1` | 12 | -1 | 130 |
| `ANTICHEAT_CYCLELOGIC2` | 149 | -1 | 154 |
| `ANTICHEAT_CYCLELOGIC3` | 52 | 1 | 125 |
| `ANTICHEAT_CYCLELOGIC4` | 230 | 1 | 137 |
| `ANTICHEAT_CYCLELOGIC5` | 100 | 0 | 85 |
| `ANTICHEAT_CYCLELOGIC6` | 188 | 1 | 255 |
| `ANTICHEAT_CYCLELOGIC7` | 89 | 0 | 232 |
| `ANTICHEAT_OPLOGIC1` | 219 | 4 | 195 |
| `ANTICHEAT_OPLOGIC2` | 201 | 2 | 81 |
| `ANTICHEAT_OPLOGIC3` | 41 | 4 | 122 |
| `ANTICHEAT_OPLOGIC4` | 80 | 1 | 49 |
| `ANTICHEAT_OPLOGIC5` | 235 | 1 | 46 |
| `ANTICHEAT_OPLOGIC6` | 250 | 2 | 73 |
| `ANTICHEAT_OPLOGIC7` | 25 | 4 | 133 |
| `ANTICHEAT_OPLOGIC8` | 0 | 1 | 168 |
| `ANTICHEAT_OPLOGIC9` | 24 | 3 | 88 |
| `CHAT_SETMODE` | 154 | 3 | 161 |
| `CLIENT_CHEAT` | 224 | -1 | 34 |
| `CLOSE_MODAL` | 51 | 0 | 93 |
| `EVENT_APPLET_FOCUS` | 73 | 1 | 149 |
| `EVENT_CAMERA_POSITION` | 53 | 4 | 193 |
| `EVENT_MOUSE_CLICK` | 20 | 4 | 224 |
| `EVENT_MOUSE_MOVE` | 222 | -1 | 229 |
| `FRIENDLIST_ADD` | 13 | 8 | 235 |
| `FRIENDLIST_DEL` | 106 | 8 | 203 |
| `IDK_SAVEDESIGN` | 125 | 13 | 27 |
| `IDLE_TIMER` | 209 | 0 | 145 |
| `IF_BUTTON` | 9 | 2 | 86 |
| `IGNORELIST_ADD` | 255 | 8 | 192 |
| `IGNORELIST_DEL` | 101 | 8 | 251 |
| `INV_BUTTON1` | 74 | 6 | 44 |
| `INV_BUTTON2` | 82 | 6 | 111 |
| `INV_BUTTON3` | 239 | 6 | 124 |
| `INV_BUTTON4` | 179 | 6 | 248 |
| `INV_BUTTON5` | 46 | 6 | 227 |
| `INV_BUTTOND` | 93 | 7 | 253 |
| `MAP_BUILD_COMPLETE` | 214 | 0 | 214 |
| `MESSAGE_PRIVATE` | 139 | -1 | 107 |
| `MESSAGE_PUBLIC` | 253 | -1 | 156 |
| `MOVE_GAMECLICK` | 207 | -1 | 234 |
| `MOVE_MINIMAPCLICK` | 86 | -1 | 236 |
| `MOVE_OPCLICK` | 138 | -1 | 67 |
| `NO_TIMEOUT` | 120 | 0 | 181 |
| `OPHELD1` | 185 | 6 | 76 |
| `OPHELD2` | 2 | 6 | 177 |
| `OPHELD3` | 123 | 6 | 40 |
| `OPHELD4` | 216 | 6 | 191 |
| `OPHELD5` | 42 | 6 | 79 |
| `OPHELDT` | 135 | 8 | 112 |
| `OPHELDU` | 136 | 12 | 200 |
| `OPLOC1` | 215 | 6 | 10 |
| `OPLOC2` | 103 | 6 | 45 |
| `OPLOC3` | 187 | 6 | 196 |
| `OPLOC4` | 157 | 6 | 53 |
| `OPLOC5` | 127 | 6 | 126 |
| `OPLOCT` | 213 | 8 | 218 |
| `OPLOCU` | 60 | 12 | 184 |
| `OPNPC1` | 236 | 2 | 252 |
| `OPNPC2` | 233 | 2 | 21 |
| `OPNPC3` | 223 | 2 | 178 |
| `OPNPC4` | 147 | 2 | 30 |
| `OPNPC5` | 189 | 2 | 247 |
| `OPNPCT` | 181 | 4 | 108 |
| `OPNPCU` | 150 | 8 | 160 |
| `OPOBJ1` | 247 | 6 | 97 |
| `OPOBJ2` | 169 | 6 | 4 |
| `OPOBJ3` | 108 | 6 | 110 |
| `OPOBJ4` | 62 | 6 | 147 |
| `OPOBJ5` | 117 | 6 | 22 |
| `OPOBJT` | 91 | 8 | 241 |
| `OPOBJU` | 39 | 12 | 55 |
| `OPPLAYER1` | 109 | 2 | 220 |
| `OPPLAYER2` | 166 | 2 | 51 |
| `OPPLAYER3` | 196 | 2 | 13 |
| `OPPLAYER4` | 98 | 2 | 189 |
| `OPPLAYER5` | 174 | 2 | 69 |
| `OPPLAYERT` | 240 | 4 | 138 |
| `OPPLAYERU` | 36 | 8 | 16 |
| `REPORT_ABUSE` | 137 | 10 | 94 |
| `RESUME_PAUSEBUTTON` | 72 | 2 | 166 |
| `RESUME_P_COUNTDIALOG` | 102 | 4 | 180 |
| `TUT_CLICKSIDE` | 94 | 1 | 146 |

274 has 82 client packets, as 289 does. Only `MAP_BUILD_COMPLETE` keeps its 289 opcode, 214.
