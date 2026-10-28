# Revision 225 TCP Protocol

This page is the wire reference for this repository's revision-225 engine
([`225server/engine`](../../../225server/engine/src)) and its webclient
([`225server/webclient`](../../../225server/webclient/src)), written as the differences from
[tcp-protocol-289.md](tcp-protocol-289.md). Anything this page doesn't mention is the same in both
revisions: the conventions, the encodings, ISAAC, the framing, the zone sub-packets, and every payload
not listed below. Almost every opcode is different, so both opcode tables are given whole.

Every layout here was read from the 225 engine's encoders and decoders and checked against its
webclient's decoders. Entity info comes from a prebuilt `@2004scape/rsbuf` package whose source isn't
in `225server`, so its layout rests on the webclient's `getPlayerPos*`, `getNpcPos*` and
`ClientPlayer.setAppearance`. [RevisionDesign.md](RevisionDesign.md) is how this client supports both
revisions.

## Contents

1. [Endpoints and Transport](#endpoints-and-transport)
2. [Login Negotiation](#login-negotiation)
3. [In-Game Packet Framing](#in-game-packet-framing)
4. [Session Lifecycle](#session-lifecycle)
5. [Server-to-Client Opcodes](#server-to-client-opcodes)
6. [Server-to-Client Payloads](#server-to-client-payloads)
7. [PLAYER_INFO](#player_info-184)
8. [NPC_INFO](#npc_info-1)
9. [Client-to-Server Opcodes](#client-to-server-opcodes)
10. [Client-to-Server Payloads](#client-to-server-payloads)
11. [Input Tracking](#input-tracking)
12. [Maps over the Wire](#maps-over-the-wire)
13. [The Cache](#the-cache)
14. [Source Map](#source-map)

## Endpoints and Transport

The ports, the WebSocket route `GET /` and the TCP listener's options are as in 289. The WebSocket
server's largest message is 2000 bytes, not 1600.

The server speaks first. As soon as a WebSocket opens, or a TCP connection is accepted, it sends the
8-byte login seed, so there is no seed request.

## Login Negotiation

| Login opcode | Body | Meaning |
|---:|---|---|
| `16` | `u8` length, then body | Normal login. |
| `18` | `u8` length, then body | Reconnect login; same body as `16`. |
| anything else | - | The server terminates the socket. There's no `14` (seed request) and no `15` (on-demand). |

### Server Seed

Before anything from the client, the server sends 8 bytes: a random `u32` below `0x00FFFFFF`, then
a random `u32`. The client reads them as one `s64` and seeds ISAAC from it as in 289.

### Login Request

The body is 289's with the revision in a byte:

| Field | Type | 289 |
|---|---|---|
| revision | `u8`, `225` | `u8 0xFF`, then `u16 289` |
| info | `u8`, bit 0 low memory | same |
| CRCs | 9 `s32` | same; for 225 they're `0` and the CRC32 of the eight archive files (§13) |
| RSA block | `u8` length, then the block | same |

The server checks the revision byte, then the CRC32 of the nine CRCs against its own, and answers `6`
for either mismatch.

### Login Responses

| Status | Meaning | After it |
|---:|---|---|
| `2` | Logged in, staff level 0 | nothing |
| `18` | Logged in with a staff level of 1 or more | nothing |
| `15` | Reconnected to the session | nothing |
| `3` to `17` | As in 289 | - |

289's `2` is followed by the staff level and the mouse-tracking flag; 225 sends neither. `21`, the hop
timer, is never sent.

## In-Game Packet Framing

As in 289, with one addition: a client packet can have a `u16` length too. `EVENT_TRACKING` is the only
one.

## Session Lifecycle

After a login the server sends the same kinds of packets as 289, except that its `REBUILD_NORMAL` lists
the area's map squares. A 225 client also does two things a 289 client never does:

- **Rebuilds.** The webclient answers each `REBUILD_NORMAL` with `REBUILD_GETMAPS`, asking for each map
  file it doesn't have stored (§12). The server also recomputes the player's active zones when it gets
  one, though it does that on every zone change too. An empty request is valid.
- **Input tracking.** The server turns input tracking on for every player at intervals and logs out as
  idle a player that sends no report for a window (§11), so a client that stays logged in has to send
  one. This is on top of `IDLE_TIMER`, which works as in 289.

Keepalives, reconnects and the clean logout are as in 289.

## Server-to-Client Opcodes

Where 289's length differs, it follows in brackets. The zone sub-packets are the same ten, with 225's
opcodes: `23`, `42`, `49`, `50`, `59`, `69`, `76`, `151`, `191` and `223`.

| Opcode | Name | Length | 289 opcode |
|---:|---|---|---:|
| `1` | `NPC_INFO` | var short | 65 |
| `2` | `IF_SETCOLOUR` | 4 | 160 |
| `3` | `CAM_MOVETO` | 6 | 73 |
| `4` | `MESSAGE_GAME` | var byte | 196 |
| `7` | `UPDATE_ZONE_PARTIAL_FOLLOWS` | 2 | 155 |
| `12` | `SYNTH_SOUND` | 5 | 177 |
| `13` | `CAM_SHAKE` | 4 | 208 |
| `14` | `IF_OPENCHAT` | 2 | 81 |
| `15` | `UPDATE_INV_STOP_TRANSMIT` | 2 | 28 |
| `19` | `UNSET_MAP_FLAG` | 0 | 164 |
| `20` | `DATA_LOC_DONE` | 2 | - |
| `21` | `UPDATE_IGNORELIST` | var short | 47 |
| `22` | `UPDATE_RUNWEIGHT` | 2 | 46 |
| `23` | `LOC_MERGE` | 14 | 83 |
| `25` | `HINT_ARROW` | 6 | 115 |
| `26` | `IF_SETHIDE` | 3 | 138 |
| `28` | `IF_OPENMAIN_SIDE` | 4 | 55 |
| `32` | `CHAT_FILTER_SETTINGS` | 3 | 13 |
| `41` | `MESSAGE_PRIVATE` | var byte | 243 |
| `42` | `LOC_ANIM` | 4 | 106 |
| `43` | `UPDATE_REBOOT_TIMER` | 2 | 204 |
| `44` | `UPDATE_STAT` | 6 | 154 |
| `46` | `IF_SETOBJECT` | 6 | 18 |
| `49` | `OBJ_DEL` | 3 | 71 |
| `50` | `OBJ_REVEAL` | 7 | 176 |
| `54` | `MIDI_SONG` | var byte (289: 2) | 187 |
| `59` | `LOC_ADD_CHANGE` | 4 | 90 |
| `68` | `UPDATE_RUNENERGY` | 1 | 195 |
| `69` | `MAP_PROJANIM` | 15 | 87 |
| `74` | `CAM_LOOKAT` | 6 | 82 |
| `76` | `LOC_DEL` | 2 | 194 |
| `80` | `DATA_LAND_DONE` | 2 | - |
| `84` | `IF_SETTAB_ACTIVE` | 1 | 189 |
| `87` | `IF_SETMODEL` | 4 | 222 |
| `98` | `UPDATE_INV_FULL` | var short | 107 |
| `103` | `IF_SETRECOL` | 6 | - |
| `126` | `TUT_FLASH` | 1 | 181 |
| `129` | `IF_CLOSE` | 0 | 23 |
| `132` | `DATA_LAND` | var short | - |
| `133` | `FINISH_TRACKING` | 0 | - |
| `135` | `UPDATE_ZONE_FULL_FOLLOWS` | 2 | 144 |
| `136` | `RESET_ANIMS` | 0 | 201 |
| `139` | `UPDATE_PID` | 2 (289: 3) | 120 |
| `140` | `LAST_LOGIN_INFO` | 9 (289: 10) | 253 |
| `142` | `LOGOUT` | 0 | 121 |
| `146` | `IF_SETANIM` | 4 | 211 |
| `150` | `VARP_SMALL` | 3 | 75 |
| `151` | `OBJ_COUNT` | 7 | 117 |
| `152` | `UPDATE_FRIENDLIST` | 9 | 168 |
| `162` | `UPDATE_ZONE_PARTIAL_ENCLOSED` | var short | 112 |
| `167` | `IF_SETTAB` | 3 | 63 |
| `168` | `IF_OPENMAIN` | 2 | 119 |
| `175` | `VARP_LARGE` | 6 | 97 |
| `184` | `PLAYER_INFO` | var short | 188 |
| `185` | `TUT_OPEN` | 2 | 12 |
| `191` | `MAP_ANIM` | 6 | 233 |
| `193` | `RESET_CLIENT_VARCACHE` | 0 | 172 |
| `195` | `IF_OPENSIDE` | 2 | 252 |
| `197` | `IF_SETPLAYERHEAD` | 2 | 30 |
| `201` | `IF_SETTEXT` | var short | 59 |
| `204` | `IF_SETNPCHEAD` | 4 | 244 |
| `209` | `IF_SETPOSITION` | 6 | 79 |
| `212` | `MIDI_JINGLE` | var short (289: 4) | 29 |
| `213` | `UPDATE_INV_PARTIAL` | var short | 76 |
| `220` | `DATA_LOC` | var short | - |
| `223` | `OBJ_ADD` | 5 | 60 |
| `226` | `ENABLE_TRACKING` | 0 | - |
| `237` | `REBUILD_NORMAL` | var short (289: 4) | 219 |
| `239` | `CAM_RESET` | 0 | 133 |
| `243` | `P_COUNTDIALOG` | 0 | 35 |
| `254` | `SET_MULTIWAY` | 1 | 247 |

289 has five packets 225 doesn't: `FRIENDLIST_LOADED`, `IF_OPENOVERLAY`, `IF_SETSCROLLPOS`, `MINIMAP_TOGGLE`, `SET_PLAYER_OP`.

## Server-to-Client Payloads

Only the payloads that differ from 289's are listed.

| Packet | 225 | 289 |
|---|---|---|
| `UPDATE_PID` | `u16 pid` | adds `u8 members` |
| `LAST_LOGIN_INFO` | `s32 lastIp`, `u16 daysSinceLogin`, `u8 daysSinceRecoveryChange`, `u16 unreadMessages` | adds `u8 warnMembers` |
| `UPDATE_INV_FULL` | `u16 com`, `u8 size`, then `size` items; the size is the whole capacity | `u16 size`, up to the last used slot |
| `UPDATE_INV_PARTIAL` | `u16 com`, then per entry `u8 slot` and an item | `smart slot` |
| `REBUILD_NORMAL` | `u16 zoneX`, `u16 zoneZ`, then to the end, per map square: `u8 x`, `u8 z`, `s32 landCrc`, `s32 locCrc` | 4 bytes |
| `MIDI_SONG` | `jstr name`, `s32 crc`, `s32 length` | `u16 song` |
| `MIDI_JINGLE` | `u16 delay`, then the jingle's bzip2 MIDI bytes to the end | `u16 jingle`, `u16 delay` |
| `MESSAGE_PRIVATE` | Same bytes, but a staff level of 1 or more is sent as one higher | as it is |

An item is `u16 id + 1` (0 for an empty slot), then `u8 count`, or `255` and `s32 count`, as in 289.

A `REBUILD_NORMAL` CRC is the CRC32 of the server's map file, or `0` when it has none. The squares are
the ones the area's 13 x 13 zones touch.

### Packets 289 doesn't have

| Packet | Payload |
|---|---|
| `DATA_LAND`, `DATA_LOC` | `u8 x`, `u8 z`, `u16 offset`, `u16 totalLength`, then a chunk of the map file to the end |
| `DATA_LAND_DONE`, `DATA_LOC_DONE` | `u8 x`, `u8 z` |
| `ENABLE_TRACKING`, `FINISH_TRACKING` | none |
| `IF_SETRECOL` | `u16 com`, `u16 from`, `u16 to`: recolours a component's model |

## PLAYER_INFO (184)

The bit section is as in 289, and so are the loop guards.

The extended masks are `0x001` to `0x200`, read in 289's order, with no `DAMAGE2` (`0x400`). The `CHAT`
block is the same bytes: `u8 colour`, `u8 effect`, `u8 rights`, `u8 length`, then the packed text.

### Appearance Block

As 289's, except:

- No NPC transform. Slot 0's `0xFFFF` is an ordinary wear slot.
- It ends after `u8 combatLevel`; 289 adds `u16 totalLevel`.

## NPC_INFO (1)

A new NPC is `13 index` (`8191` ends the list), `11 type`, `5 dx`, `5 dz` and `1 hasExtended`. There's no
`jump` bit, so every new NPC is placed as a walk. 289 has a 14-bit index (`16383` ends) and the jump
bit before `hasExtended`. The list is read while `bitPos + 21` is less than the payload's bits, as in
289, so the end marker is only read when an extended block follows the bit section.

The extended masks are `0x02` to `0x80`, in 289's order, with no `DAMAGE2` (`0x01`).

## Client-to-Server Opcodes

Where 289's length differs, it follows in brackets.

| Opcode | Name | Length | 289 opcode |
|---:|---|---|---:|
| `2` | `ANTICHEAT_OPLOGIC8` | 2 (289: 1) | 168 |
| `4` | `CLIENT_CHEAT` | var byte | 34 |
| `6` | `INV_BUTTON5` | 6 | 227 |
| `7` | `ANTICHEAT_OPLOGIC1` | 4 | 195 |
| `8` | `OPNPC2` | 2 | 21 |
| `9` | `OPLOCT` | 8 | 218 |
| `11` | `FRIENDLIST_DEL` | 8 | 203 |
| `17` | `ANTICHEAT_OPLOGIC7` | 4 | 133 |
| `27` | `OPNPC3` | 2 | 178 |
| `30` | `ANTICHEAT_OPLOGIC3` | 3 (289: 4) | 122 |
| `31` | `INV_BUTTON1` | 6 | 44 |
| `38` | `INV_BUTTON4` | 6 | 248 |
| `40` | `OPOBJ2` | 6 | 4 |
| `48` | `OPHELDT` | 8 | 112 |
| `52` | `IDK_SAVEDESIGN` | 13 | 27 |
| `53` | `OPPLAYER2` | 2 | 51 |
| `59` | `INV_BUTTON2` | 6 | 111 |
| `66` | `ANTICHEAT_OPLOGIC6` | 4 (289: 2) | 73 |
| `70` | `IDLE_TIMER` | 0 | 145 |
| `71` | `OPHELD2` | 6 | 177 |
| `75` | `OPLOCU` | 12 | 184 |
| `79` | `IGNORELIST_ADD` | 8 | 192 |
| `81` | `EVENT_TRACKING` | var short | - |
| `85` | `ANTICHEAT_CYCLELOGIC5` | 0 | 85 |
| `88` | `ANTICHEAT_OPLOGIC2` | 4 (289: 2) | 81 |
| `93` | `MOVE_OPCLICK` | var byte | 67 |
| `96` | `OPLOC3` | 6 | 196 |
| `97` | `OPLOC4` | 6 | 53 |
| `100` | `OPNPC5` | 2 | 247 |
| `108` | `NO_TIMEOUT` | 0 | 181 |
| `113` | `OPNPC4` | 2 | 30 |
| `116` | `OPLOC5` | 6 | 126 |
| `118` | `FRIENDLIST_ADD` | 8 | 235 |
| `130` | `OPHELDU` | 12 | 200 |
| `133` | `OPHELD3` | 6 | 40 |
| `134` | `OPNPCT` | 4 | 108 |
| `138` | `OPOBJT` | 8 | 241 |
| `140` | `OPOBJ1` | 6 | 97 |
| `146` | `ANTICHEAT_CYCLELOGIC2` | var byte | 154 |
| `148` | `MESSAGE_PRIVATE` | var byte | 107 |
| `150` | `REBUILD_GETMAPS` | var byte | - |
| `155` | `IF_BUTTON` | 2 | 86 |
| `157` | `OPHELD4` | 6 | 191 |
| `158` | `MESSAGE_PUBLIC` | var byte | 156 |
| `159` | `INV_BUTTOND` | 6 (289: 7) | 253 |
| `164` | `OPPLAYER1` | 2 | 220 |
| `165` | `MOVE_MINIMAPCLICK` | var byte | 236 |
| `171` | `IGNORELIST_DEL` | 8 | 251 |
| `172` | `OPLOC2` | 6 | 45 |
| `175` | `TUT_CLICKSIDE` | 1 | 146 |
| `176` | `ANTICHEAT_OPLOGIC4` | 2 (289: 1) | 49 |
| `177` | `OPPLAYERT` | 4 | 138 |
| `178` | `OPOBJ4` | 6 | 147 |
| `181` | `MOVE_GAMECLICK` | var byte | 234 |
| `185` | `OPPLAYER3` | 2 | 13 |
| `189` | `EVENT_CAMERA_POSITION` | 6 (289: 4) | 193 |
| `190` | `REPORT_ABUSE` | 10 | 94 |
| `194` | `OPNPC1` | 2 | 252 |
| `195` | `OPHELD1` | 6 | 76 |
| `200` | `OPOBJ3` | 6 | 110 |
| `202` | `OPNPCU` | 8 | 160 |
| `206` | `OPPLAYER4` | 2 | 189 |
| `211` | `OPHELD5` | 6 | 79 |
| `212` | `INV_BUTTON3` | 6 | 124 |
| `215` | `ANTICHEAT_CYCLELOGIC3` | 3 (289: 1) | 125 |
| `219` | `ANTICHEAT_CYCLELOGIC6` | var byte (289: 1) | 255 |
| `220` | `ANTICHEAT_OPLOGIC5` | 0 (289: 1) | 46 |
| `231` | `CLOSE_MODAL` | 0 | 93 |
| `233` | `ANTICHEAT_CYCLELOGIC1` | 1 (289: var byte) | 130 |
| `235` | `RESUME_PAUSEBUTTON` | 2 | 166 |
| `236` | `ANTICHEAT_CYCLELOGIC4` | 4 (289: 1) | 137 |
| `237` | `RESUME_P_COUNTDIALOG` | 4 | 180 |
| `238` | `ANTICHEAT_OPLOGIC9` | 1 (289: 3) | 88 |
| `239` | `OPOBJU` | 12 | 55 |
| `244` | `CHAT_SETMODE` | 3 | 161 |
| `245` | `OPLOC1` | 6 | 10 |
| `247` | `OPOBJ5` | 6 | 22 |
| `248` | `OPPLAYERU` | 8 | 16 |

289 has six packets 225 doesn't: `ANTICHEAT_CYCLELOGIC7`, `EVENT_APPLET_FOCUS`, `EVENT_MOUSE_CLICK`, `EVENT_MOUSE_MOVE`, `MAP_BUILD_COMPLETE`, `OPPLAYER5`.

## Client-to-Server Payloads

Every payload the client sends is 289's, except:

| Packet | 225 | 289 |
|---|---|---|
| `INV_BUTTOND` | `u16 com`, `u16 fromSlot`, `u16 toSlot`; a drag always swaps | adds `u8 mode`, 1 to insert |
| `EVENT_CAMERA_POSITION` | `u16 pitch`, `u16 yaw`, `u8 minimapAngle`, `u8 minimapZoom` | the first two. The engine never reads it |
| `REBUILD_GETMAPS` | var byte; per request `u8 type` (0 land, 1 locs), `u8 x`, `u8 z` | - |
| `EVENT_TRACKING` | var short; 1 to 500 bytes of input events (§11) | - |

The anticheat packets differ in length too, but a client has no need to send them.

## Input Tracking

The server enables tracking for each player with `ENABLE_TRACKING` 200 ticks, give or take 15, after login
or after the last window ended, and turns it off 150 ticks (90 seconds) later with `FINISH_TRACKING`. It accepts
`EVENT_TRACKING` while tracking is on, and for 16 ticks after `FINISH_TRACKING`. A report must be 1 to
500 bytes. When those 16 ticks are up, a player that sent no report for the window is logged out as
idle, unless the server runs with `NODE_DEBUG`.

The webclient records events into a buffer from `ENABLE_TRACKING`. An event that would bring the buffer
to 500 bytes first sets it aside, and the set-aside buffer is sent at the end of the client's next
cycle. `FINISH_TRACKING` sends what's left. A window with no input sends nothing, which is how the
server spots an idle player.

Each event is a code, a delta and its fields. The delta is the time since the previous event in tens of
milliseconds, capped at 250.

| Code | Event | Fields |
|---:|---|---|
| `1`, `2` | Right, left mouse press | `u24 x + (y << 10)` |
| `3`, `4` | Right, left mouse release | none |
| `5` | Mouse move within 8 pixels | `u8 (x - lastX + 8) + ((y - lastY + 8) << 4)` |
| `6` | Mouse move within 128 pixels | `u8 x - lastX + 128`, `u8 y - lastY + 128` |
| `7` | Mouse move, absolute | `u24 x + (y << 10)` |
| `8`, `9` | Key press, release | `u8` key |
| `10`, `11`, `12` | Focus gained, focus lost, mouse entered | none |

Positions are in the client's 789 x 532 frame; the game view is the 512 x 334 rectangle at `(8, 11)`.
This client records an absolute move, a left press and a release for each action it sends while
tracking is on, and one absolute move for a window with no actions.

## Maps over the Wire

The webclient's `REBUILD_GETMAPS` lists each file whose stored copy is missing, or whose CRC differs from
the one `REBUILD_NORMAL` sent. The server answers within 10 ticks of the rebuild, and only for up to 18
files of squares in the area. Each file comes as `DATA_LAND` or `DATA_LOC` chunks of up to 991 bytes,
each saying where it goes in the file and how long the file is, then `DATA_LAND_DONE` or
`DATA_LOC_DONE`. The assembled file is the same as the one in the cache's `maps/` folder.

## The Cache

225's cache is the engine's `data/pack/client/` folder: loose archive files and a `maps/` folder of
`m{x}_{z}` and `l{x}_{z}` files, each a `u32` unpacked size and headerless bzip2. The login CRCs are `0`
and the CRC32 of `title`, `config`, `interface`, `media`, `models`, `textures`, `wordenc` and `sounds`, a
missing file skipped and the rest moved up. Some definition opcodes and interface fields differ from
289's. [CacheDesign.md](CacheDesign.md) §18 has the details.

## Source Map

| Topic | Engine | Webclient |
|---|---|---|
| Server opcode table | [`ServerGameProt.ts`](../../../225server/engine/src/network/game/server/ServerGameProt.ts), [`ServerGameZoneProt.ts`](../../../225server/engine/src/network/game/server/ServerGameZoneProt.ts) | [`ServerProt.ts`](../../../225server/webclient/src/io/ServerProt.ts) |
| Client opcode table | [`ClientGameProt.ts`](../../../225server/engine/src/network/game/client/ClientGameProt.ts) | [`ClientProt.ts`](../../../225server/webclient/src/io/ClientProt.ts) |
| Payloads | [`server/codec/`](../../../225server/engine/src/network/game/server/codec), [`client/codec/`](../../../225server/engine/src/network/game/client/codec) | [`Client.ts`](../../../225server/webclient/src/client/Client.ts) `tcpIn` |
| Login | [`World.ts`](../../../225server/engine/src/engine/World.ts) `onClientData`, `processLogins`; [`web.ts`](../../../225server/engine/src/web.ts) | [`Client.ts`](../../../225server/webclient/src/client/Client.ts) `login` |
| Entity info | `@2004scape/rsbuf` | [`Client.ts`](../../../225server/webclient/src/client/Client.ts) `getPlayerPos*`, `getNpcPos*`; [`ClientPlayer.ts`](../../../225server/webclient/src/dash3d/ClientPlayer.ts) `setAppearance` |
| Input tracking | [`InputTracking.ts`](../../../225server/engine/src/engine/entity/tracking/InputTracking.ts), [`EventTrackingHandler.ts`](../../../225server/engine/src/network/game/client/handler/EventTrackingHandler.ts) | [`InputTracking.ts`](../../../225server/webclient/src/client/InputTracking.ts) |
| Maps | [`RebuildGetMapsHandler.ts`](../../../225server/engine/src/network/game/client/handler/RebuildGetMapsHandler.ts), [`PreloadedPacks.ts`](../../../225server/engine/src/cache/PreloadedPacks.ts) | [`Client.ts`](../../../225server/webclient/src/client/Client.ts) `REBUILD_NORMAL`, `DATA_*` |
| Cache CRCs | [`CrcTable.ts`](../../../225server/engine/src/cache/CrcTable.ts) | |
