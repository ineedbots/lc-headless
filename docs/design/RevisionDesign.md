# Revision Design

Plan for connecting to servers of more than one revision. Today the client speaks only revision 289. This plan adds revision 225 and makes every part that touches the wire or the cache revision-aware, so a later revision is added the same way. Revision 225 is the base protocol: code written for 225 runs for every revision, and anything a later revision changes sits in a branch on the protocol's revision. Scripts can ask which revision they're on with `game.revision()`. The work ships in five phases (§13), plus an optional sixth for maps sent over the wire. Code style follows [CONVENTIONS.md](CONVENTIONS.md). It changes the config ([ConfigDesign.md](ConfigDesign.md)), the cache loader ([CacheDesign.md](CacheDesign.md)) and the script API ([ScriptingApi.md](../ScriptingApi.md)). The 289 wire format is in [tcp-protocol-289.md](tcp-protocol-289.md); this plan lists only where 225 differs from it.

Reference sources, beside this repository:

- `225server/engine/src/network/game/server/ServerGameProt.ts`, `ServerGameZoneProt.ts`, `client/ClientGameProt.ts`: the 225 opcode tables (Appendix A)
- `225server/engine/src/network/game/server/codec/`, `client/codec/`: every 225 payload. Diffing these directories against `289server`'s gives §6 and §8 exactly
- `225server/engine/src/engine/World.ts` (`onClientData`, `processLogins`), `src/web.ts`: the 225 login
- `225server/webclient/src/client/Client.ts` (`login`, `tcpIn`, `getPlayerPos*`, `getNpcPos*`, `zonePacket`), `dash3d/ClientPlayer.ts` (`setAppearance`): how the 225 client decodes. Entity info comes from a prebuilt `@2004scape/rsbuf` package in 225, so the webclient is the reference for it
- `225server/engine/src/network/game/client/handler/RebuildGetMapsHandler.ts`, `engine/entity/BuildArea.ts`: maps over the wire
- `225server/engine/src/engine/entity/tracking/InputTracking.ts`, `webclient/src/client/InputTracking.ts`: input tracking (§9.2)
- `225server/engine/src/cache/CrcTable.ts`, `PreloadedPacks.ts`, `engine/data/pack/client/`: the 225 cache layout and a real 225 cache
- `225server/webclient/src/config/*.ts`, `client/ClientBuild.ts`: 225 definitions, interfaces and map decoding

---

## 1. Decisions

| Topic | Decision |
|---|---|
| Revisions | 225 and 289. `Revision_e` lists them in release order |
| Base | 225. Code for 225 runs unconditionally; a later revision's difference is a branch on `GetRevision()` (§2.3). Nothing about 289 is the default any more except the config's default value |
| Where it's set | `login.revision`, as today, beside the RSA key. It stays process-wide, because the cache is loaded once per process (CacheDesign §1) and must be the same revision as the protocol. Two revisions at once means two processes with their own `client.jsonc` |
| Default | `289`, so existing config files keep working |
| Protocol object | `Protocol` (§2.2), owned by each `GameClient`, holds the revision and that revision's opcode tables. The login, the reader, the writer, the decoders and `ClientPackets` all take it |
| Opcodes | `ServerProt_e` and `ClientProt_e` become logical packet names with no wire value. Each revision has a full table mapping them to opcodes and sizes, because every revision reshuffles every opcode (Appendix A) |
| Missing packets | A packet a revision doesn't have isn't in its table. Building one throws `std::invalid_argument` naming the packet and the revision, so an action fails before it walks anywhere; receiving an opcode outside the table is a `ProtocolError`, as today |
| Cache | `CacheLoader::Load` takes the revision and reads that revision's layout. 225 reads loose JAG files and a `maps/` folder; 289 reads the store, as today (§10). The loaded `GameCache_s` records its revision, and `GameClient` asserts it matches the config |
| 225 maps | Read from the cache folder, like 289's. The client still answers every `REBUILD_NORMAL` with a `REBUILD_GETMAPS`, as the webclient does, and warns about squares whose CRC differs from the server's. Downloading those squares is the optional phase 6 |
| 225 input tracking | The 225 server logs out a client that doesn't return an input report when tracking ends. The client keeps a synthetic report and sends it (§9.2) |
| Script API | `_core.get_revision()` returns the number (`225` or `289`); `game.revision()` wraps it. Stdlib code and scripts branch on it where content differs |
| Content | Out of scope: the stdlib's catalogs, the nav data and other content ids were written against 289's content. They load on 225, but ids that differ need their own audit (§15) |

---

## 2. Representing a revision

### 2.1 `Revision_e`

`src/Config/Revision_e.hpp`, in `Config/` because the revision is a setting, read with the rest of `login`. The cache loader and `Protocol` include it from there:

```cpp
#pragma once

// In release order, so a branch can compare against the first revision that changed something.
enum class Revision_e : u16
{
    Rev225 = 225,
    Rev289 = 289,
};
```

The values are the revision numbers, so `static_cast<u16>(revision)` is what the login sends and what scripts see. Scoped enums compare with `<`, `>=` and the rest, so no helper is needed.

### 2.2 `Protocol`

`src/Game/Protocol/Protocol.hpp`:

```cpp
#pragma once

#include "../../Config/Revision_e.hpp"
#include "ClientProt.hpp"
#include "ServerProt.hpp"

// One revision's wire protocol: its opcode tables, and the revision every layout difference branches on.
// The tables are static, so a Protocol is cheap to copy.
class Protocol
{
public:
    explicit Protocol(Revision_e revision);

    [[nodiscard]] Revision_e GetRevision() const;

    // Nullopt for an opcode this revision never sends.
    [[nodiscard]] std::optional<ServerProt_e> FindServerProt(u8 opcode) const;
    [[nodiscard]] s32 GetSize(ServerProt_e prot) const;

    [[nodiscard]] bool Has(ClientProt_e prot) const;
    // These throw std::invalid_argument for a packet this revision doesn't have.
    void Require(ClientProt_e prot) const;
    [[nodiscard]] u8 GetOpcode(ClientProt_e prot) const;
    [[nodiscard]] s32 GetSize(ClientProt_e prot) const;

private:
    Revision_e m_revision;
    const ServerProtTable_s* m_serverProts;
    const ClientProtTable_s* m_clientProts;
};
```

`ServerProtTable_s` and `ClientProtTable_s` are one revision's entries indexed both by opcode and by packet, built at compile time in `ServerProt.cpp` and `ClientProt.cpp` the way today's `INFO_BY_OPCODE` is (§4).

### 2.3 Branching rules

Every difference between revisions is one of three kinds, and each has one way to write it, so `grep -rn "Revision_e::" src` lists every place a revision changes behaviour.

1. **Tables replaced wholesale** (the opcode tables) switch on the exact revision, with a case for each. A new revision has to add a case, and clang's `-Wswitch` flags one that's missing.

    ```cpp
    const ServerProtTable_s& ServerProt::GetTable(Revision_e revision)
    {
        switch (revision)
        {
        case Revision_e::Rev225:
            return TABLE_225;
        case Revision_e::Rev289:
            return TABLE_289;
        }

        assert(false && "Unhandled Revision_e");
        return TABLE_225;
    }
    ```

2. **Layout and behaviour differences** keep 225's code as the base and branch on the first supported revision with the newer behaviour, using `>=`. A change that lands in some revision usually stays in every later one, so a future revision past 289 takes the newer path without anyone touching the branch. A revision added between two supported ones only needs a branch re-pointed where the change landed at or before it (§14).

    ```cpp
    case ServerProt_e::UpdatePid:
        state.pid = packet.G2();
        state.localPlayer.index = state.pid;

        if (m_protocol.GetRevision() >= Revision_e::Rev289)
        {
            state.members = packet.G1() == 1;
        }

        return;
    ```

    When only the older revisions need something, `<` reads better and means the same: `if (m_protocol.GetRevision() < Revision_e::Rev289)`. A change a later revision undoes is a range, `>= Rev244 && < Rev274`, not two nested ifs.

3. **Whether a packet exists** is asked of the table, never of the revision: `m_protocol.Has(ClientProt_e::RebuildGetMaps)`. The table already says which revisions have it, and keeping that in one place means a new revision's table is the only thing to update.

A branch that needs a sentence of why gets one, per CONVENTIONS §7, such as `// 225 sends the size in a byte; 289 widened it.`

### 2.4 Where the revision comes from

```text
client.jsonc login.revision
    -> Application: CacheLoader::Load(cacheDirectory, revision)   -> GameCache_s::revision
    -> GameClient: Protocol{config.login.revision}, asserts it equals cache.revision
        -> LoginHandshake, ServerPacketReader, ClientPacketWriter, ServerPacketDecoder
           (PlayerInfoDecoder, NpcInfoDecoder, ZoneDecoder, and the area decoders: InterfacePacketDecoder,
           InventoryDecoder, PlayerStateDecoder, SocialDecoder, SceneDecoder), ClientPackets, InputTracker
        -> GameActions::GetProtocol() -> ScriptContext::GetRevision() -> _core.get_revision()
```

`GameClient` declares `m_protocol` before every member that's constructed from it, so the members can hold it by value or by reference safely.

---

## 3. Configuration

`LoginSettings_s` changes type and gains the supported list:

```cpp
struct LoginSettings_s
{
    static constexpr auto SUPPORTED_REVISIONS = std::to_array({Revision_e::Rev225, Revision_e::Rev289});

    BigUInt rsaModulus;
    BigUInt rsaExponent;
    bool lowMemory = false;
    Revision_e revision = Revision_e::Rev289;
};
```

nlohmann converts a scoped enum to and from its underlying integer, so `NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT` in `ConfigJson.cpp` keeps working and the file still says `"revision": 289`. `ConfigValidator::Validate` checks the value is in `SUPPORTED_REVISIONS` and otherwise fails with `login.revision: must be 225 or 289`, built from the list. A string, a boolean or a number outside `u16` fails as it does today.

That's the finished list. Until phase 4 it holds only `Rev289`, so a half-built 225 can't be selected.

`client.cacheDirectory` keeps its name. What it points at depends on the revision (§10.1), and the sample config and README say so. `LoginError`'s text for status 6 becomes `revision, cache CRC or RSA key mismatch; do login.revision and client.cacheDirectory match this server?`.

---

## 4. Opcode tables

### Logical packets

`ServerProt_e` and `ClientProt_e` keep their names but lose their values, and gain the packets only some revisions have:

- Server: `DataLand`, `DataLandDone`, `DataLoc`, `DataLocDone`, `EnableTracking`, `FinishTracking`, `IfSetRecol` (225 only). `FriendListLoaded`, `IfOpenOverlay`, `IfSetScrollPos`, `MinimapToggle` and `SetPlayerOp` are already there and become 289 only.
- Client: `EventTracking`, `RebuildGetMaps` (225 only). `AnticheatCycleLogic7`, `EventAppletFocus`, `EventMouseClick`, `EventMouseMove`, `MapBuildComplete` and `OpPlayer5` become 289 only.

A comment on each enum says its values aren't opcodes. `ServerProt::GetName(ServerProt_e)` and `IsZoneProt(ServerProt_e)` take the logical packet, since a name and zone membership don't change between revisions.

### Tables

`ServerProt.cpp` holds `SERVER_PROTS_225` and `SERVER_PROTS_289`, arrays of `{prot, opcode, size}`, and builds each one's both-way index at compile time. `ClientProt.cpp` does the same for the client tables. Each table gets a `static_assert` on its count (225: 71 server, 78 client; 289: 69 and 82) and the existing test that checks every row against the engine (§12).

A client packet can now be `VAR_SHORT`: 225's `EVENT_TRACKING` is. `ClientProt::VAR_SHORT = -2` joins `VAR_BYTE`, and the writer puts a 2-byte length before such a payload.

### Users of the tables

| Code | Change |
|---|---|
| `ServerPacketReader` | Takes a `Protocol`. Decrypts the opcode, looks it up with `FindServerProt`, and reads the size from the table. The error names the revision: `Server sent opcode 60, which revision 225 never sends` |
| `ClientPacketWriter` | Takes a `Protocol`. `Validate` becomes a member and checks the packet exists in this revision before checking its size. `Write` encrypts `GetOpcode(prot)` |
| `ZoneDecoder::DecodeEnclosed` | Enclosed sub-opcodes are raw wire numbers, so it maps each with `FindServerProt` and then checks `IsZoneProt` |
| `GameClient` | Logs names with `ServerProt::GetName(prot)` and `ClientProt::GetName(prot)`. `Send` validates with its writer's rules before the writer exists, through the protocol |
| `FakeGameServer` | Takes a `Revision_e` and encodes with that revision's table |

---

## 5. Login

| Step | 225 (base) | 289 |
|---|---|---|
| Seed | The server sends 8 bytes of seed as soon as the WebSocket opens. The client sends nothing first | The client sends `14` and the login-server byte; the server answers 8 zero bytes, status `0`, then the 8-byte seed |
| Revision field | `u8 revision` | `0xFF`, then `u16 revision` |
| Rest of the body | Same: `u8 info`, nine CRCs, RSA block | Same |
| Success | `2` for a player, `18` for a staff account (staff level 1 or more). Nothing follows | `2`, then `u8 staffLevel` and `u8 mouseTracking` |
| Reconnect | `15`, nothing follows | Same |
| Other statuses | `3` to `17` mean what they mean in 289. `21` (hop timer) is never sent | As today |

`LoginHandshake` takes the `Protocol`. For 225 it starts at `Stage_e::ServerSeed` instead of `SendSeedRequest`, and `GetWaitingFor` says `server seed`. `BuildLoginRequest` branches on the revision field:

```cpp
// 225 fits its revision in a byte; 289 doesn't, so it sends a marker and two bytes.
if (protocol.GetRevision() >= Revision_e::Rev289)
{
    packet.P1(REVISION_MARKER);
    packet.P2(static_cast<u16>(protocol.GetRevision()));
}
else
{
    packet.P1(static_cast<u8>(protocol.GetRevision()));
}
```

The login response: status `18` is a success for 225, with `staffLevel = 1`, and status `2` with `staffLevel = 0`; for 289 the two detail bytes follow as today. `LoginResult_s::mouseTracking` stays false for 225.

The ISAAC seeds, the `+50` for the inbound cipher, the RSA block and the framing are the same in both.

---

## 6. Server packets

Every payload not listed is byte-for-byte the same in both revisions. Diffing the two engines' `server/codec/` directories finds exactly these, and the 225 webclient's `tcpIn` agrees.

| Packet | 225 (base) | 289 | Decoder change |
|---|---|---|---|
| `UPDATE_PID` | `u16 pid` | adds `u8 members` | Read `members` only from 289. 225 leaves it false |
| `LAST_LOGIN_INFO` | 9 bytes, no `warnMembers` | adds `u8 warnMembers` | Read it only from 289 |
| `UPDATE_INV_FULL` | `u16 com`, `u8 size`, items; the size is the whole capacity | `u16 size`, up to the last used slot | Read the size by revision |
| `UPDATE_INV_PARTIAL` | `u8 slot` per entry | `smart slot` | Read the slot by revision |
| `REBUILD_NORMAL` | `u16 zoneX`, `u16 zoneZ`, then per map square `u8 x`, `u8 z`, `s32 landCrc`, `s32 locCrc` to the end | 4 bytes | 225 also reads the squares into a new `BuildArea_s::squares`, a list of square and CRCs (§9.1). A CRC of 0 means the server has no file for it |
| `MIDI_SONG` | `jstr name`, `s32 crc`, `s32 length` | `u16 song` | 225 consumes it; `audio.song` stays -1 |
| `MIDI_JINGLE` | `u16 delay`, then bzip2 MIDI bytes to the end | `u16 jingle`, `u16 delay` | 225 consumes it; `audio.jingle` stays -1 |
| `MESSAGE_PRIVATE` | Same bytes; the engine sends a staff level of 1 or more as one higher | Capped at 3 | 225 subtracts one from a staff level above 0, so `ChatMessage_s::rights` means the same in both |

Each change goes in the decoder for its packet's area: `UPDATE_PID` and `LAST_LOGIN_INFO` in `PlayerStateDecoder`, the two inventory packets in `InventoryDecoder`, `REBUILD_NORMAL`, `MIDI_SONG` and `MIDI_JINGLE` in `SceneDecoder`, and `MESSAGE_PRIVATE` in `SocialDecoder`. `ServerPacketDecoder` holds the `Protocol` and passes it to each area decoder's `Decode`, as it passes the logger to those that warn.

### Packets one revision doesn't have

| Packet | Revision | Payload | Handling |
|---|---|---|---|
| `DATA_LAND`, `DATA_LOC` | 225 | `u8 x`, `u8 z`, `u16 offset`, `u16 totalLength`, then a chunk of the map file | Consumed. Phase 6 assembles them (§9.1) |
| `DATA_LAND_DONE`, `DATA_LOC_DONE` | 225 | `u8 x`, `u8 z` | Consumed |
| `ENABLE_TRACKING`, `FINISH_TRACKING` | 225 | none | Drive the input tracker (§9.2) |
| `IF_SETRECOL` | 225 | `u16 com`, `u16 from`, `u16 to` | Consumed. It recolours a model, which only rendering needs |
| `FRIENDLIST_LOADED`, `IF_OPENOVERLAY`, `IF_SETSCROLLPOS`, `MINIMAP_TOGGLE`, `SET_PLAYER_OP` | 289 | as today | Unchanged. Their state keeps its default on 225 |

`ServerPacketDecoder`'s `switch (prot)` lists every logical packet, as today, and hands each to its area's decoder: `DATA_LAND`, `DATA_LOC` and their `_DONE` packets to `SceneDecoder`, and `IF_SETRECOL` to `InterfacePacketDecoder`. The tracking packets change no state, since `GameClient::Reply` acts on them (§9), so they join `LOGOUT` among the cases that decode nothing. A case for a packet a revision never sends is simply never reached, so no revision check is needed in those cases.

---

## 7. Entity info

`PlayerInfoDecoder` and `NpcInfoDecoder` take the `Protocol`. `NpcInfoDecoder` stops being static so it can hold it.

| Part | 225 (base) | 289 |
|---|---|---|
| Player bit section | Same | Same |
| Player extended masks | `0x001` to `0x200`; no `DAMAGE2` | adds `DAMAGE2` (`0x400`), read after `EXACT_MOVE` |
| Appearance | No NPC transform: slot 0 is a plain wear slot. Ends after `combatLevel` | `0xFFFF` in slot 0 means a transform; a `u16` total level follows `combatLevel` |
| New NPC | `13 index` (`8191` ends the list), `11 type`, `5 dx`, `5 dz`, `1 hasExtended`; no `jump` bit, so every new NPC is placed as a walk | `14 index` (`16383` ends), adds `1 jump` before `hasExtended` |
| NPC extended masks | `0x02` to `0x80`; no `DAMAGE2` | adds `DAMAGE2` (`0x01`), read first |
| Loop guards | Same: `bitPos + 10 <` and `bitPos + 21 <` the payload's bits | Same |

`INDEX_BITS` and `END_OF_LIST` stop being class constants for NPCs and come from a small function that branches on the revision. A 225 mask with `DAMAGE2`'s bit set means the decoder is out of step, so it's a `ProtocolError` rather than four bytes read.

`Appearance_s::totalLevel` stays 0 on 225, and `npcTransform` stays empty. The CHAT block is the same bytes in both, but whether 225 numbers `rights` the way 289 does is checked live in phase 4.

---

## 8. Client packets

`ClientPackets` becomes a class constructed from a `Protocol`, so every builder can branch without its signature changing. Each builder calls `Protocol::Require` on its packet, so one the revision doesn't have throws as it's built. `GameClient::GetPackets()` returns it, and `GameActions` builds with `m_client.GetPackets()`. The builders' signatures stay as they are today.

| Packet | 225 (base) | 289 | Builder change |
|---|---|---|---|
| `INV_BUTTOND` | `u16 com`, `u16 from`, `u16 to` (6 bytes); no insert mode | adds `u8 mode` | Writes `mode` only for 289. `DragMode_e::Insert` on 225 throws `std::invalid_argument` |
| `EVENT_CAMERA_POSITION` | `u16 pitch`, `u16 yaw`, `u8 minimapAngle`, `u8 minimapZoom` | `u16 pitch`, `u16 yaw` | 225 adds the two bytes, as zeros. The engine never decodes it |
| `OPPLAYER5`, `MAP_BUILD_COMPLETE`, `EVENT_APPLET_FOCUS`, `EVENT_MOUSE_*`, `ANTICHEAT_CYCLELOGIC7` | missing | present | The writer rejects them on 225 (§1, Missing packets) |
| `REBUILD_GETMAPS` | `VAR_BYTE`; 3 bytes per request: `u8 type` (0 land, 1 locs), `u8 x`, `u8 z` | missing | New builder, `RebuildGetMaps(std::span<const MapRequest_s>)` |
| `EVENT_TRACKING` | `VAR_SHORT`; 1 to 500 bytes of input events | missing | New builder, `EventTracking(std::span<const u8> report)` |

Every other payload is the same: diffing the engines' `client/codec/` directories finds only `INV_BUTTOND`. The anticheat packets differ in size between revisions too, but the client never sends them.

---

## 9. Replies 225 expects

The decoder only changes state. Packets the client owes in reply are sent by `GameClient` after decoding, from a new `GameClient::Reply(ServerProt_e prot)` called in `ProcessInput`. The replies go through `m_outgoing`, so they're encrypted in order at the next flush like everything else.

### 9.1 `REBUILD_GETMAPS`

The 225 webclient answers every `REBUILD_NORMAL` at once with `REBUILD_GETMAPS`, listing each map file whose CRC doesn't match what it has stored. The server sends the asked-for files as `DATA_LAND` and `DATA_LOC` chunks, but only within 10 ticks of the rebuild and only for up to 18 files. It also recomputes the player's active zones when it gets the request, though it does that on every zone change too, so ground items and scenery changes arrive either way.

Phases 3 to 5 behave as a webclient whose stored maps are all current:

```cpp
case ServerProt_e::RebuildNormal:
    if (m_protocol.Has(ClientProt_e::RebuildGetMaps))
    {
        WarnAboutStaleSquares();
        m_outgoing.push_back(m_packets.RebuildGetMaps({}));
    }

    return;
```

`WarnAboutStaleSquares` compares each square's CRCs in `m_state.buildArea.squares` with the CRCs of the raw map files the cache read (§10.2), and logs one warning per square per client for a mismatch or a file the cache doesn't have: `Map square 50_50's locs differ from the server's; walks there may route through changed scenery`. The client keeps the squares it has warned about, so a warning isn't repeated after a reconnect; keeping them per process would need state shared between accounts for little gain. A server whose CRC is 0 has no file, and the cache's open ground is right.

Phase 6, optional, asks for the stale squares instead, assembles the `DATA_*` chunks by `offset` and `totalLength`, decodes them with the same `MapDecoder`, and lays them over the shared cache in that client's `WorldMap`. The shared `GameCache_s` stays read-only.

### 9.2 Input tracking

A 225 server turns input tracking on for every player at intervals with `ENABLE_TRACKING`, and off with `FINISH_TRACKING`. It then waits up to 15 seconds for at least one `EVENT_TRACKING` report from that window. Unless the server runs with `NODE_DEBUG`, a player that sent none is logged out as idle. The webclient sends a report when its 500-byte buffer fills, and the rest when tracking finishes. A window with no input at all sends nothing, which is how the server spots an idle player.

A new `InputTracker` class in `src/Game/` keeps the report:

- `ENABLE_TRACKING` starts it: an empty buffer, and the clock its event deltas count from.
- Each action `GameClient::Send` accepts while it's running records the events a click would: an absolute mouse move (`7`, delta, `p3(x + (y << 10))`), a left press (`2`, delta, the same position) and a release (`4`, delta). Deltas are tens of milliseconds since the previous event, capped at 250, as the webclient's are. The position is a point in the game view, varied a little each time. Keepalives and replies record nothing.
- A buffer that would pass 500 bytes is set aside and sent as a report at the next flush, as the webclient's `flush()` does.
- `FINISH_TRACKING` stops it and sends what's left. A window in which the script sent nothing still sends one short mouse move, so a bot that waits through a window isn't treated as idle. That matches 289, where the client never sends `IDLE_TIMER` and so is never logged out for idling.

The encodings come from the webclient's `InputTracking.ts`: codes 1 and 2 are right and left presses, 3 and 4 the releases, 5 to 7 small, medium and absolute moves, 8 and 9 keys, and 10 to 12 focus and mouse-enter events.

---

## 10. The cache

`CacheLoader::Load(directory, revision, logger)`. The JAG archive format, both compressions, the definition and map payloads and `TextPool` are shared. What differs is where the files are and a few opcodes.

### 10.1 Layout and CRCs

| | 225 (base) | 289 |
|---|---|---|
| Folder | The 225 engine's `data/pack/client/`: loose files `title`, `config`, `interface`, `media`, `models`, `textures`, `wordenc`, `sounds`, and a `maps/` folder | The store, `main_file_cache.dat` and `.idx0` to `.idx4`, as today |
| CRCs | `0`, then the CRC32 of each of the eight files in that order, as the engine's `makeCrcs` computes. Like `makeCrcs`, a missing file is skipped and the rest move up, with zeros at the end | Files 0 to 8 of store 0, as today |
| Archives | `config` and `interface` are read from their files | From store 0, as today |

A folder of the other layout fails with a message that names what's expected: `config not found; for revision 225, set client.cacheDirectory to the 225 engine's data/pack/client folder`. A 289 store given to a 225 config, or the reverse, is the likely mistake.

### 10.2 Maps

| | 225 (base) | 289 |
|---|---|---|
| Index | None. Every `maps/m{x}_{z}` with a matching `maps/l{x}_{z}` is a square; a square with only one is loaded with the other empty | `map_index` in `versionlist` |
| File | `u32` unpacked size, then bzip2 without its `BZh1` header: `Compression::Bunzip2` as it is | gzip, then a 2-byte version |
| Payload | Same land and loc formats | Same |

For 225 the loader also keeps each square's raw-file CRCs, for §9.1: a `std::unordered_map<u16, MapCrcs_s>` keyed by square, in `GameCache_s`.

### 10.3 Definitions

Each type's decoder takes the revision in its `Decode`: `LocTypeDecoder`, `NpcTypeDecoder`, `ObjTypeDecoder` and `VarpTypeDecoder`. `TypeDecoder`'s shared framing and readers are the same in both. Each opcode one revision lacks is a branch in its type's opcode loop, so a cache decoded as the wrong revision still fails on an unknown opcode rather than reading garbage.

| Type | 225 only | 289 only |
|---|---|---|
| loc | `25` (a flag, no payload) | `5` (models without shapes), `74`, `75`, `77`; opcode `1` may have a count of 0 |
| npc | `16` (a flag) | `99` to `103` |
| obj | `9` (a flag) | `110` to `115` |
| varp | | `11` to `13` |

### 10.4 Interfaces

`InterfaceDecoder::Decode` takes the revision. 289 adds four fields:

| Field | 225 (base) | 289 |
|---|---|---|
| `trans`, after `height` | absent | `u8` |
| Layer child count | `u8` | `u16` |
| Inventory `objReplace` | absent | `u8` |
| Rect and text `colour2Over` | absent; three colours | `s32`; four colours |

### 10.5 Components found by content

| Component | 225 | 289 |
|---|---|---|
| Logout | Client code 205, as today | Same |
| Bank | No client code 206 exists. The inventory whose first option starts with `Withdraw` and that holds the most slots: the bank's 8 x 30 grid, ahead of the party room chest | Client code 206, as today |
| Backpack, equipment, bank backpack, run buttons | The same rules as 289 | As today |

The optional real-cache test (§12) checks each one resolves to the component the 225 content names.

---

## 11. Script API

| Piece | Change |
|---|---|
| `GameActions` | `GetProtocol()`, forwarding `m_client.GetProtocol()` |
| `ScriptContext` | `GetRevision()`, from `GameActions` |
| `ControlBindings` | `{"get_revision()", GetRevision}`, returning `static_cast<u16>(revision)` as an int |
| `rs2004/game.py` | `_Game.revision()`: `"""The server revision this client speaks: 225 or 289."""` |
| Typings | `def revision(self) -> int: ...` in `__builtins__.pyi` and `rs2004/__init__.pyi` |
| `Menus::GetPlayerMenu` | 225 has no `SET_PLAYER_OP`; its webclient's player menu is fixed. For 225 the menu is `Duel-with`, `Attack`, `Follow`, `Trade with` (ops 1 to 4); for 289 it comes from `playerOps`, as today. The server still decides whether an op is allowed where the player is |
| `ScriptingApi.md` | `revision()` in the `game` row; a note that `members` is always false on 225 and that ops 5 and drag-insert raise there |

---

## 12. Tests

| File | Tests |
|---|---|
| `Game/ProtocolTests.cpp` | Each revision's server and client table matches Appendix A row for row, with its count. Every logical packet has a name. `Has` is false for each packet a revision lacks, and `GetOpcode` throws for it. Zone packets are flagged in both |
| `Game/NetTests.cpp` | 225 login: no seed request is sent, the 8-byte seed is read, the body holds a one-byte revision, status 2 gives staff level 0 and 18 gives 1, with nothing read after either. The 289 tests stay as they are |
| `Game/ServerPacketDecoderTests.cpp` | Each row of §6 for 225, with its 289 counterpart: `UPDATE_PID`, `LAST_LOGIN_INFO`, both inventory packets, `REBUILD_NORMAL` with three squares, `MIDI_SONG`, `MIDI_JINGLE`, `MESSAGE_PRIVATE`'s staff level, and each 225-only packet consumed exactly. An opcode from the other revision's table is a `ProtocolError` |
| `Game/EntityInfoTests.cpp` | 225 new NPCs with 13-bit indexes and no jump bit, including the `8191` terminator; an appearance without the trailer; a 225 player or NPC mask with `DAMAGE2`'s bit is a `ProtocolError` |
| `Game/ClientPacketsTests.cpp` | 225 `INV_BUTTOND` is 6 bytes and rejects insert mode; `EVENT_CAMERA_POSITION` is 6 bytes; `REBUILD_GETMAPS` and `EVENT_TRACKING` encode their lengths; 289-only packets throw on 225 |
| `Game/GameClientTests.cpp` | Against `FakeGameServer{Revision_e::Rev225}`: login, a `REBUILD_GETMAPS` after each `REBUILD_NORMAL`, an `EVENT_TRACKING` after `FINISH_TRACKING` both with and without actions in the window, and a report split when it passes 500 bytes |
| `Cache/CacheLoaderTests.cpp`, `CacheWriter` | `CacheWriter` learns the 225 layout. A 225 folder loads with the right CRCs, maps and components; a missing file shifts the CRCs as `makeCrcs` does; each layout given the other revision fails with the message in §10.1 |
| `Cache/TypeDecoderTests.cpp`, `InterfaceDecoderTests.cpp` | Each opcode and field in §10.3 and §10.4, in the revision that has it and as an error in the one that doesn't |
| `Support/Cache/RealCache.cpp` | `RequireShared(Revision_e)`, with `RS2004_CACHE_DIR_225` beside today's variable, skipping when it's unset. `RealCacheTests` checks the 225 components resolve to the ids in the 225 content |
| `Config/ConfigFileTests.cpp` | 225 and 289 load; 224, 226, 288 and 290 fail with the message from §3 |
| Script tests | `game.revision()` returns the configured revision |

---

## 13. Phases

Each phase builds and passes every test on both presets before the next starts.

### Phase 1: plumbing, with 289 unchanged

- `Revision_e`; `LoginSettings_s::revision` as `Revision_e`, with only 289 supported.
- `Protocol`; logical `ServerProt_e` and `ClientProt_e`; the 225 and 289 tables as data; `ClientProt::VAR_SHORT`.
- `ServerPacketReader`, `ClientPacketWriter`, `ServerPacketDecoder` and the area decoders it hands packets to, `ZoneDecoder`, the entity decoders, `ClientPackets` and `FakeGameServer` take the protocol.
- `get_revision()` and `game.revision()`.
- `ProtocolTests` for both tables. Every existing test passes untouched apart from construction.

### Phase 2: the 225 cache

- `CacheLoader::Load` with the revision; the 225 layout, CRCs and maps; the definition and interface branches; the 225 bank rule; `GameCache_s::revision` and the map CRCs.
- `CacheWriter` 225 fixtures, the decoder tests, and the optional real 225 cache test.
- `CacheDesign.md` gains a section on the 225 layout.

### Phase 3: logging in to 225 and decoding

- `LoginHandshake` for 225.
- Every branch in §6 and §7.
- `GameClient::Reply` with the empty `REBUILD_GETMAPS` and the stale-square warning. Tracking packets are consumed but not answered yet.
- `FakeGameServer` 225 mode, and the login, decoder and entity tests.

### Phase 4: acting on 225

- The client packet branches in §8, and `InputTracker` with its replies.
- The fixed player menu.
- `Rev225` joins `SUPPORTED_REVISIONS`.
- A live run against a local 225 server, from a scratch `client.jsonc` pointing at the 225 cache and RSA key: log in, walk, bank, chat, trade, stay logged in across at least two tracking windows, and confirm the CHAT `rights` numbering (§7).
- `README.md`, `client.jsonc.sample`, `ConfigDesign.md` and `ScriptingApi.md` updated.

### Phase 5: the 225 reference

`docs/design/tcp-protocol-225.md`: the 225 wire reference, written as differences from [tcp-protocol-289.md](tcp-protocol-289.md), with Appendix A's tables, §5's login and §6 to §9's payloads. The README's document table links it.

### Phase 6, optional: maps over the wire

The stale-square requests, `DATA_*` assembly and per-client map overlay in §9.1.

---

## 14. Adding a revision later

1. Add `RevNNN` to `Revision_e` in release order.
2. Add `SERVER_PROTS_NNN` and `CLIENT_PROTS_NNN` and a case for each in `GetTable`. Generating them from the engine's `ServerGameProt.ts`, `ServerGameZoneProt.ts` and `ClientGameProt.ts` avoids copying mistakes.
3. Diff the new engine's `server/codec/` and `client/codec/` against the nearest supported revisions, and the webclient's `getPlayerPos*`, `getNpcPos*`, `setAppearance`, `login`, config decoders, `IfType.init` and `ClientBuild` the same way.
4. For each `Revision_e::` in `src` (§2.3), decide which side the new revision takes. A change that landed at or before it, where the branch names a later revision, gets its threshold moved down to `RevNNN`. A new difference gets a new branch on `RevNNN`.
5. Add the cache layout if it differs, and fixtures for every new branch.
6. Add `RevNNN` to `SUPPORTED_REVISIONS` last.

---

## 15. Out of scope and risks

- **Content ids.** The catalogs (`catalogs/_data.py`, `_shops.py` and others), `random_solvers.py`'s loc ids and the walker data in `data/nav` were built from 289's content. Most ids are older than 225 and match, but items, NPCs, scenery and areas added between 225 and 289 don't exist on 225. Auditing them, and keying any that differ on `game.revision()`, is separate work.
- **Per-account revisions.** An account's `server` section can point at another server, but not another revision, because the cache is per process. Supporting that means one cache per revision in `Application`, keyed by revision.
- **Unverified on the wire.** 225's entity info comes from a prebuilt package whose source isn't in `225server`, so §7 rests on the webclient's decoder. The tests pin what the webclient reads; the live run in phase 4 confirms the server sends it.
- **Server options.** A 225 server with `NODE_DEBUG` set never logs out for missing reports, and one without a friend server sends `UPDATE_IGNORELIST` instead of nothing. Neither changes the client.

---

## Appendix A. Opcode tables

Generated from the two engines' `ServerGameProt.ts`, `ServerGameZoneProt.ts` and `ClientGameProt.ts`. A size of `-1` is a byte length, `-2` a 2-byte length, and `-` means the revision doesn't have the packet.

### Server to client

| Name | 225 op | 225 size | 289 op | 289 size |
|---|---:|---:|---:|---:|
| `CAM_LOOKAT` | 74 | 6 | 82 | 6 |
| `CAM_MOVETO` | 3 | 6 | 73 | 6 |
| `CAM_RESET` | 239 | 0 | 133 | 0 |
| `CAM_SHAKE` | 13 | 4 | 208 | 4 |
| `CHAT_FILTER_SETTINGS` | 32 | 3 | 13 | 3 |
| `DATA_LAND` | 132 | -2 | - | - |
| `DATA_LAND_DONE` | 80 | 2 | - | - |
| `DATA_LOC` | 220 | -2 | - | - |
| `DATA_LOC_DONE` | 20 | 2 | - | - |
| `ENABLE_TRACKING` | 226 | 0 | - | - |
| `FINISH_TRACKING` | 133 | 0 | - | - |
| `FRIENDLIST_LOADED` | - | - | 235 | 1 |
| `HINT_ARROW` | 25 | 6 | 115 | 6 |
| `IF_CLOSE` | 129 | 0 | 23 | 0 |
| `IF_OPENCHAT` | 14 | 2 | 81 | 2 |
| `IF_OPENMAIN` | 168 | 2 | 119 | 2 |
| `IF_OPENMAIN_SIDE` | 28 | 4 | 55 | 4 |
| `IF_OPENOVERLAY` | - | - | 127 | 2 |
| `IF_OPENSIDE` | 195 | 2 | 252 | 2 |
| `IF_SETANIM` | 146 | 4 | 211 | 4 |
| `IF_SETCOLOUR` | 2 | 4 | 160 | 4 |
| `IF_SETHIDE` | 26 | 3 | 138 | 3 |
| `IF_SETMODEL` | 87 | 4 | 222 | 4 |
| `IF_SETNPCHEAD` | 204 | 4 | 244 | 4 |
| `IF_SETOBJECT` | 46 | 6 | 18 | 6 |
| `IF_SETPLAYERHEAD` | 197 | 2 | 30 | 2 |
| `IF_SETPOSITION` | 209 | 6 | 79 | 6 |
| `IF_SETRECOL` | 103 | 6 | - | - |
| `IF_SETSCROLLPOS` | - | - | 184 | 4 |
| `IF_SETTAB` | 167 | 3 | 63 | 3 |
| `IF_SETTAB_ACTIVE` | 84 | 1 | 189 | 1 |
| `IF_SETTEXT` | 201 | -2 | 59 | -2 |
| `LAST_LOGIN_INFO` | 140 | 9 | 253 | 10 |
| `LOC_ADD_CHANGE` | 59 | 4 | 90 | 4 |
| `LOC_ANIM` | 42 | 4 | 106 | 4 |
| `LOC_DEL` | 76 | 2 | 194 | 2 |
| `LOC_MERGE` | 23 | 14 | 83 | 14 |
| `LOGOUT` | 142 | 0 | 121 | 0 |
| `MAP_ANIM` | 191 | 6 | 233 | 6 |
| `MAP_PROJANIM` | 69 | 15 | 87 | 15 |
| `MESSAGE_GAME` | 4 | -1 | 196 | -1 |
| `MESSAGE_PRIVATE` | 41 | -1 | 243 | -1 |
| `MIDI_JINGLE` | 212 | -2 | 29 | 4 |
| `MIDI_SONG` | 54 | -1 | 187 | 2 |
| `MINIMAP_TOGGLE` | - | - | 136 | 1 |
| `NPC_INFO` | 1 | -2 | 65 | -2 |
| `OBJ_ADD` | 223 | 5 | 60 | 5 |
| `OBJ_COUNT` | 151 | 7 | 117 | 7 |
| `OBJ_DEL` | 49 | 3 | 71 | 3 |
| `OBJ_REVEAL` | 50 | 7 | 176 | 7 |
| `PLAYER_INFO` | 184 | -2 | 188 | -2 |
| `P_COUNTDIALOG` | 243 | 0 | 35 | 0 |
| `REBUILD_NORMAL` | 237 | -2 | 219 | 4 |
| `RESET_ANIMS` | 136 | 0 | 201 | 0 |
| `RESET_CLIENT_VARCACHE` | 193 | 0 | 172 | 0 |
| `SET_MULTIWAY` | 254 | 1 | 247 | 1 |
| `SET_PLAYER_OP` | - | - | 21 | -1 |
| `SYNTH_SOUND` | 12 | 5 | 177 | 5 |
| `TUT_FLASH` | 126 | 1 | 181 | 1 |
| `TUT_OPEN` | 185 | 2 | 12 | 2 |
| `UNSET_MAP_FLAG` | 19 | 0 | 164 | 0 |
| `UPDATE_FRIENDLIST` | 152 | 9 | 168 | 9 |
| `UPDATE_IGNORELIST` | 21 | -2 | 47 | -2 |
| `UPDATE_INV_FULL` | 98 | -2 | 107 | -2 |
| `UPDATE_INV_PARTIAL` | 213 | -2 | 76 | -2 |
| `UPDATE_INV_STOP_TRANSMIT` | 15 | 2 | 28 | 2 |
| `UPDATE_PID` | 139 | 2 | 120 | 3 |
| `UPDATE_REBOOT_TIMER` | 43 | 2 | 204 | 2 |
| `UPDATE_RUNENERGY` | 68 | 1 | 195 | 1 |
| `UPDATE_RUNWEIGHT` | 22 | 2 | 46 | 2 |
| `UPDATE_STAT` | 44 | 6 | 154 | 6 |
| `UPDATE_ZONE_FULL_FOLLOWS` | 135 | 2 | 144 | 2 |
| `UPDATE_ZONE_PARTIAL_ENCLOSED` | 162 | -2 | 112 | -2 |
| `UPDATE_ZONE_PARTIAL_FOLLOWS` | 7 | 2 | 155 | 2 |
| `VARP_LARGE` | 175 | 6 | 97 | 6 |
| `VARP_SMALL` | 150 | 3 | 75 | 3 |

225 has 71 server packets and 289 has 69. Sizes differ for `LAST_LOGIN_INFO`, `MIDI_JINGLE`, `MIDI_SONG`, `REBUILD_NORMAL` and `UPDATE_PID`.

### Client to server

| Name | 225 op | 225 size | 289 op | 289 size |
|---|---:|---:|---:|---:|
| `ANTICHEAT_CYCLELOGIC1` | 233 | 1 | 130 | -1 |
| `ANTICHEAT_CYCLELOGIC2` | 146 | -1 | 154 | -1 |
| `ANTICHEAT_CYCLELOGIC3` | 215 | 3 | 125 | 1 |
| `ANTICHEAT_CYCLELOGIC4` | 236 | 4 | 137 | 1 |
| `ANTICHEAT_CYCLELOGIC5` | 85 | 0 | 85 | 0 |
| `ANTICHEAT_CYCLELOGIC6` | 219 | -1 | 255 | 1 |
| `ANTICHEAT_CYCLELOGIC7` | - | - | 232 | 0 |
| `ANTICHEAT_OPLOGIC1` | 7 | 4 | 195 | 4 |
| `ANTICHEAT_OPLOGIC2` | 88 | 4 | 81 | 2 |
| `ANTICHEAT_OPLOGIC3` | 30 | 3 | 122 | 4 |
| `ANTICHEAT_OPLOGIC4` | 176 | 2 | 49 | 1 |
| `ANTICHEAT_OPLOGIC5` | 220 | 0 | 46 | 1 |
| `ANTICHEAT_OPLOGIC6` | 66 | 4 | 73 | 2 |
| `ANTICHEAT_OPLOGIC7` | 17 | 4 | 133 | 4 |
| `ANTICHEAT_OPLOGIC8` | 2 | 2 | 168 | 1 |
| `ANTICHEAT_OPLOGIC9` | 238 | 1 | 88 | 3 |
| `CHAT_SETMODE` | 244 | 3 | 161 | 3 |
| `CLIENT_CHEAT` | 4 | -1 | 34 | -1 |
| `CLOSE_MODAL` | 231 | 0 | 93 | 0 |
| `EVENT_APPLET_FOCUS` | - | - | 149 | 1 |
| `EVENT_CAMERA_POSITION` | 189 | 6 | 193 | 4 |
| `EVENT_MOUSE_CLICK` | - | - | 224 | 4 |
| `EVENT_MOUSE_MOVE` | - | - | 229 | -1 |
| `EVENT_TRACKING` | 81 | -2 | - | - |
| `FRIENDLIST_ADD` | 118 | 8 | 235 | 8 |
| `FRIENDLIST_DEL` | 11 | 8 | 203 | 8 |
| `IDK_SAVEDESIGN` | 52 | 13 | 27 | 13 |
| `IDLE_TIMER` | 70 | 0 | 145 | 0 |
| `IF_BUTTON` | 155 | 2 | 86 | 2 |
| `IGNORELIST_ADD` | 79 | 8 | 192 | 8 |
| `IGNORELIST_DEL` | 171 | 8 | 251 | 8 |
| `INV_BUTTON1` | 31 | 6 | 44 | 6 |
| `INV_BUTTON2` | 59 | 6 | 111 | 6 |
| `INV_BUTTON3` | 212 | 6 | 124 | 6 |
| `INV_BUTTON4` | 38 | 6 | 248 | 6 |
| `INV_BUTTON5` | 6 | 6 | 227 | 6 |
| `INV_BUTTOND` | 159 | 6 | 253 | 7 |
| `MAP_BUILD_COMPLETE` | - | - | 214 | 0 |
| `MESSAGE_PRIVATE` | 148 | -1 | 107 | -1 |
| `MESSAGE_PUBLIC` | 158 | -1 | 156 | -1 |
| `MOVE_GAMECLICK` | 181 | -1 | 234 | -1 |
| `MOVE_MINIMAPCLICK` | 165 | -1 | 236 | -1 |
| `MOVE_OPCLICK` | 93 | -1 | 67 | -1 |
| `NO_TIMEOUT` | 108 | 0 | 181 | 0 |
| `OPHELD1` | 195 | 6 | 76 | 6 |
| `OPHELD2` | 71 | 6 | 177 | 6 |
| `OPHELD3` | 133 | 6 | 40 | 6 |
| `OPHELD4` | 157 | 6 | 191 | 6 |
| `OPHELD5` | 211 | 6 | 79 | 6 |
| `OPHELDT` | 48 | 8 | 112 | 8 |
| `OPHELDU` | 130 | 12 | 200 | 12 |
| `OPLOC1` | 245 | 6 | 10 | 6 |
| `OPLOC2` | 172 | 6 | 45 | 6 |
| `OPLOC3` | 96 | 6 | 196 | 6 |
| `OPLOC4` | 97 | 6 | 53 | 6 |
| `OPLOC5` | 116 | 6 | 126 | 6 |
| `OPLOCT` | 9 | 8 | 218 | 8 |
| `OPLOCU` | 75 | 12 | 184 | 12 |
| `OPNPC1` | 194 | 2 | 252 | 2 |
| `OPNPC2` | 8 | 2 | 21 | 2 |
| `OPNPC3` | 27 | 2 | 178 | 2 |
| `OPNPC4` | 113 | 2 | 30 | 2 |
| `OPNPC5` | 100 | 2 | 247 | 2 |
| `OPNPCT` | 134 | 4 | 108 | 4 |
| `OPNPCU` | 202 | 8 | 160 | 8 |
| `OPOBJ1` | 140 | 6 | 97 | 6 |
| `OPOBJ2` | 40 | 6 | 4 | 6 |
| `OPOBJ3` | 200 | 6 | 110 | 6 |
| `OPOBJ4` | 178 | 6 | 147 | 6 |
| `OPOBJ5` | 247 | 6 | 22 | 6 |
| `OPOBJT` | 138 | 8 | 241 | 8 |
| `OPOBJU` | 239 | 12 | 55 | 12 |
| `OPPLAYER1` | 164 | 2 | 220 | 2 |
| `OPPLAYER2` | 53 | 2 | 51 | 2 |
| `OPPLAYER3` | 185 | 2 | 13 | 2 |
| `OPPLAYER4` | 206 | 2 | 189 | 2 |
| `OPPLAYER5` | - | - | 69 | 2 |
| `OPPLAYERT` | 177 | 4 | 138 | 4 |
| `OPPLAYERU` | 248 | 8 | 16 | 8 |
| `REBUILD_GETMAPS` | 150 | -1 | - | - |
| `REPORT_ABUSE` | 190 | 10 | 94 | 10 |
| `RESUME_PAUSEBUTTON` | 235 | 2 | 166 | 2 |
| `RESUME_P_COUNTDIALOG` | 237 | 4 | 180 | 4 |
| `TUT_CLICKSIDE` | 175 | 1 | 146 | 1 |

225 has 78 client packets and 289 has 82. Of the packets the client sends, only `INV_BUTTOND` and `EVENT_CAMERA_POSITION` change size; the rest of the size differences are anticheat packets the client never sends.
