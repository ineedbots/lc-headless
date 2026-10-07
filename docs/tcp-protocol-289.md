# Revision 289 TCP Protocol

This page is the wire reference for this repository's revision-289 engine
([`289server/engine`](../../289server/engine/src)) and its webclient
([`289server/webclient`](../../289server/webclient/src)). It covers the login handshake, packet
framing, and the payload layout of every in-game opcode in both directions, so that a headless
client can decode everything the server sends and build every request the webclient can send.
It is not a general RuneScape protocol specification. The cache CRCs, RSA public key, and
interface component IDs belong to a specific deployment and cache.

Every layout here was read from the engine encoders and decoders and checked against the
webclient's decoders. Where they disagree in naming or signedness, both are given; the bytes on
the wire are the same.

## Contents

1. [Conventions](#conventions)
2. [Endpoints and Transport](#endpoints-and-transport)
3. [Login Negotiation](#login-negotiation)
4. [In-Game Packet Framing](#in-game-packet-framing)
5. [Session Lifecycle](#session-lifecycle)
6. [Server-to-Client Opcodes](#server-to-client-opcodes)
7. [Server-to-Client Payloads](#server-to-client-payloads)
8. [PLAYER_INFO](#player_info-188)
9. [NPC_INFO](#npc_info-65)
10. [Zone Updates](#zone-updates)
11. [Client-to-Server Opcodes](#client-to-server-opcodes)
12. [Client-to-Server Payloads](#client-to-server-payloads)
13. [Server-Side Acceptance Rules](#server-side-acceptance-rules)
14. [Encodings](#encodings)
15. [Headless Client Implementation Notes](#headless-client-implementation-notes)
16. [Source Map](#source-map)

## Conventions

### Primitive Types

All multi-byte integers are big-endian unless a field says otherwise.

| Notation | Bytes | Encoding |
|---|---:|---|
| `u8`, `s8` | 1 | Unsigned, or two's-complement signed. |
| `u16`, `s16` | 2 | Big-endian. |
| `u24` | 3 | Big-endian. Only used by an ignored anticheat packet. |
| `s32` | 4 | Big-endian two's complement. The webclient reads every 4-byte integer as signed. |
| `u64` | 8 | Big-endian. Used only for base-37 names (`name37`). |
| `jstr` | n + 1 | One byte per character (code unit `& 0xff`, effectively Latin-1), terminated by LF (`0x0a`). There is no length prefix and no NUL. |
| `smart` | 1 or 2 | Values 0-127 are one byte. Values 128-32767 are a `u16` holding `value + 0x8000`. To decode, peek the first byte: below `0x80` it is a `u8`, otherwise read a `u16` and subtract `0x8000`. |
| `bits(n)` | - | An `n`-bit field in an MSB-first bit stream. See [Bit Access](#bit-access). |
| `name37` | 8 | A `u64` base-37 username. See [Base-37 Names](#base-37-names). |
| `wordpack` | n | Packed chat text. See [WordPack Text](#wordpack-text). |

Sentinels used by many packets:

- An ID field written as `u16` `65535` (`0xffff`) means "none" (`-1`). This applies to animation
  (`seq`) IDs, spot animations, face-entity, MIDI songs, and `IF_SETTAB` components.
- Fields marked `s8` or `s16` are read signed by the webclient (`g1b` or `g2b`). The engine
  writes them with an unsigned writer, so negative values arrive as two's complement.

### Coordinates

| Space | Definition | Used by |
|---|---|---|
| Absolute tile | `x` grows east, `z` grows north, `level` is 0-3. | Client action packets, `HINT_ARROW`, `REBUILD_NORMAL` (as zone indices). |
| Zone | An 8x8-tile block. Zone index = `coord >> 3`. | `REBUILD_NORMAL`. |
| Build area | 13x13 zones (104x104 tiles) centred on the zone sent in `REBUILD_NORMAL`. Its base is `baseX = (zoneX - 6) * 8`, `baseZ = (zoneZ - 6) * 8`. Local = absolute - base, so 0-103. | `PLAYER_INFO` local-player teleport, zone base bytes, `CAM_LOOKAT`, `CAM_MOVETO`, `EXACT_MOVE`. |
| Zone-relative | A tile within the current zone, packed into one byte as `(dx << 4) + dz` with `dx` and `dz` in 0-7. | First byte of every [zone sub-packet](#zone-sub-packets). |
| Entity-relative | Signed 5-bit tile offsets from the local player's tile. | New-entity entries in `PLAYER_INFO` and `NPC_INFO`. |
| Fine | Half-tiles: `absolute * 2 + entitySize`. A size-1 entity's tile centre is `x * 2 + 1`. | `FACE_COORD` blocks. |

A headless client should store entities, ground items, and loc changes in absolute coordinates
and convert using the current build-area base. The webclient instead stores local coordinates
and shifts everything on each `REBUILD_NORMAL`.

### Server Tick

The world runs one tick about every 600 ms. Each tick sends each connected player exactly one
`PLAYER_INFO` and one `NPC_INFO`, so a healthy session never goes more than about a second
without receiving a packet.

## Endpoints and Transport

The engine's `TcpServer` listens on `Environment.node.port` (43594 by default) for
raw TCP connections. The webclient instead opens a WebSocket to the web server's
root route; that route passes binary message bytes into the same world protocol
parser. A direct TCP client connects to the node port and must not send a WebSocket
upgrade or WebSocket frames.

TCP is a byte stream: reads may split or combine protocol fields and packets. Buffer
bytes and consume a frame only after its complete length is available. In the login
state, send each negotiation request only after receiving the preceding response;
the server processes one negotiation request per socket data callback.

The WebSocket route is `GET /` on the web port (80 on Windows/macOS, 8888 on Linux by
default). The webclient connects to `ws[s]://<page host>/` and requests the `binary`
subprotocol. Every client message must be a binary message carrying protocol bytes, and
each message is one socket data callback, so send each login negotiation request as its
own message. Server messages are binary; treat them as a byte stream and do not assume
one packet per message. The server sets `maxPayload` to 1600 bytes and disables per-message deflate. If
`WEB_ALLOWED_ORIGIN` is configured, the server rejects handshakes whose `Origin` header
does not match it.

The TCP listener enables `TCP_NODELAY` and has a 30-second socket inactivity timeout.
See [`TcpServer.ts`](../../289server/engine/src/server/tcp/TcpServer.ts),
[`web.ts`](../../289server/engine/src/web.ts), and
[`ClientStream.ts`](../../289server/webclient/src/io/ClientStream.ts).

## Login Negotiation

Before admission the server reads a one-byte login opcode:

| Login opcode | Body | Meaning |
|---:|---|---|
| `14` | 1 byte | Request login seed. |
| `16` | `u8` length, then body | Normal login. |
| `18` | `u8` length, then body | Reconnect login; same body layout as `16`. |
| `15` | none | On-demand (cache update) handshake. The server replies with eight zero bytes and switches the socket to the update protocol. A game client does not use it. |
| anything else | - | The server terminates the socket. |

### Seed Request

Client sends two bytes:

| Offset | Type | Meaning |
|---|---|---|
| 0 | u8 | `14` (`0x0e`), request login seed |
| 1 | u8 | Login-server selector; the webclient sends `(name37 >> 16) & 0x1f`, but this engine reads and ignores it |

If accepted, the server sends eight zero bytes, status `0`, then an eight-byte
big-endian server seed. These are byte-stream fields and can arrive in any number of
TCP reads. If address rate limiting rejects the connection, the server sends the
eight zero bytes followed by status `16` and closes, without sending a seed.

### Login Request

After reading the eight zero bytes, status, and seed, send one of:

| Opcode | Meaning |
|---|---|
| `16` | Normal login |
| `18` | Reconnect login; same body layout |

Both opcodes are followed by a one-byte body length, then the body:

| Field | Encoding | Size |
|---|---|---:|
| Revision marker | `0xff` | 1 byte |
| Revision | unsigned big-endian; `289` is `0x0121` | 2 bytes |
| Client info | bit 0 is low-memory; webclient sends `0` or `1` | 1 byte |
| Cache checksums | nine unsigned big-endian 32-bit values, in webclient order | 36 bytes |
| RSA block | one-byte ciphertext length followed by ciphertext | variable |

The outer body length equals 40 plus the RSA block's total size (including its
one-byte ciphertext-length prefix). The engine rejects a revision mismatch or a
mismatch in the CRC32 of the 36 checksum bytes with status `6`. The nine checksum
values must come from the cache used by the running engine; the webclient calculates
them as `jagChecksum` values. (The engine also accepts a one-byte revision with no `0xff`
marker, but 289 does not fit in one byte.)

The RSA plaintext, before encryption, is:

| Field | Encoding | Size |
|---|---|---:|
| Marker | `10` | 1 byte |
| ISAAC seed | four signed 32-bit big-endian words | 16 bytes |
| UID/device value | signed 32-bit big-endian; webclient sends `1337` | 4 bytes |
| Username | one-byte character values followed by LF (`0x0a`) | variable |
| Password | one-byte character values followed by LF (`0x0a`) | variable |

The webclient forms the four seed words from two random words followed by the high
and low 32-bit words of the server seed. Username and password are not NUL-terminated
or UTF-8 encoded by this client. The engine accepts usernames of 1-12 characters and
passwords of 1-20 characters. In production, the engine also rate-limits login attempts
per `UID@address` and replies `16` when the limit is hit.

The webclient converts the plaintext bytes to a big-endian integer and applies raw
RSA modular exponentiation with the configured public exponent and modulus. It
prefixes the resulting big-endian ciphertext bytes with their one-byte length. Match
this implementation exactly; the source does not use an OAEP or PKCS#1 v1.5 padding
block. The key must correspond to the engine's configured private key. In the
webclient build, its public values are `LOGIN_RSAN` and `LOGIN_RSAE`.

See [`Client.ts`](../../289server/webclient/src/client/Client.ts),
[`Packet.ts` in the webclient](../../289server/webclient/src/io/Packet.ts),
[`JsUtil.ts`](../../289server/webclient/src/util/JsUtil.ts), and the engine's
[`World.onClientData`](../../289server/engine/src/engine/World.ts) and
[`Packet.rsadec`](../../289server/engine/src/io/Packet.ts) implementations.

### Login Responses

| Status | Meaning |
|---:|---|
| `2` | Login succeeded; followed by staff level (0-2) and mouse-tracking flag (`1` in this engine) |
| `3` | Invalid credentials or invalid username/password length |
| `4` | Account disabled |
| `5` | Existing session or previous logout still pending |
| `6` | Revision, cache CRC, or RSA marker/key mismatch |
| `7` | World full or connection limit reached |
| `8` | Login service unavailable |
| `9` | Login limit exceeded |
| `11` | Login rejected (for example, no save and not reconnecting) |
| `12` | Members-world login attempted with a free-to-play account |
| `13` | Player save failed to load |
| `14` | Server shutting down |
| `15` | Reconnect accepted (opcode `18` matched a player still in the world); no further bytes |
| `16` | Rate limited |
| `17` | Members account in an area unavailable on this world |
| `21` | Hop timer; followed by one byte of remaining seconds |

Responses other than `2` and `15` are followed by connection closure. The webclient also
handles `1` (retry after 2 seconds), `10` (bad session ID), and `20` (invalid login server),
but the reviewed engine login paths do not emit them. Status `2` and its two following bytes,
and status `15`, are unencrypted login responses; the game-packet ISAAC streams start right
after them, seeded from this attempt's four seed words. The server may immediately send
world-update packets, so a client must continue reading after status `2` or `15`.

## In-Game Packet Framing

Each game packet is:

```text
encoded-opcode [length-prefix] payload
```

Only the one-byte opcode is ISAAC-transformed. For client-to-server packets, encode
it as `(opcode + ISAAC.nextInt()) & 0xff`; the server subtracts the next ISAAC value.
The client seeds this ISAAC stream with the four login seed words. For server-to-
client packets, use the four words with `50` added to each; the server encodes the
opcode and the client subtracts the next value. Length prefixes and payload bytes are
not ISAAC-transformed. Multi-byte integers and lengths are big-endian unless a packet
definition explicitly says otherwise.

Each direction consumes exactly one ISAAC output per packet, in stream order. A client must
never discard an outgoing packet after encrypting its opcode, because the server would then
decode every later opcode with the wrong ISAAC value. On the receive side, decrypt each opcode
exactly once. If a frame is still incomplete, keep the decrypted opcode (or a copy of the
pre-decrypt cipher state) until the rest arrives.

Packet payload length is defined by the opcode table:

| Definition length | Bytes after opcode |
|---:|---|
| `0` or positive `n` | Exactly `n` payload bytes; `0` has no length prefix |
| `-1` | One-byte payload length, then that many bytes |
| `-2` | Two-byte big-endian payload length, then that many bytes |

The server closes on unknown client opcodes and rejects client `-2` payloads above
1600 bytes (no client opcode uses `-2`). A headless client can ignore the contents of server
packets it does not use, but it must decrypt each opcode, read the length from the
[server opcode table](#server-to-client-opcodes), and consume the complete payload to remain
synchronized. An unknown server opcode cannot be skipped, because its length is unknown; treat
it as fatal. The first login response is not an in-game packet and is not ISAAC-transformed.

Opcode IDs and declared sizes live in the engine's
[`ClientGameProt.ts`](../../289server/engine/src/network/game/client/ClientGameProt.ts),
[`ServerGameProt.ts`](../../289server/engine/src/network/game/server/ServerGameProt.ts), and
[`ServerGameZoneProt.ts`](../../289server/engine/src/network/game/server/ServerGameZoneProt.ts),
and in the webclient's [`ServerProt.ts`](../../289server/webclient/src/io/ServerProt.ts) and
[`ClientProt.ts`](../../289server/webclient/src/io/ClientProt.ts).

## Session Lifecycle

### Tick Phases

Each world tick runs these phases in order
([`World.ts`](../../289server/engine/src/engine/World.ts)):

1. World queues and scripts.
2. Client input: each player's buffered client packets are decoded, subject to the per-tick
   limits in [Server-Side Acceptance Rules](#server-side-acceptance-rules).
3. NPCs, then players (interactions, movement, scripts).
4. Logouts, then logins.
5. Zones (loc and obj respawn timers, shared zone buffers).
6. Info computation. `REBUILD_NORMAL` is written here, when the player leaves the central area
   of the current build area.
7. Client output, per player, in this order: camera packets queued for after a rebuild and
   `SET_MULTIWAY`; `PLAYER_INFO`; `NPC_INFO`; zone updates; inventory updates and
   `UPDATE_RUNWEIGHT`; `UPDATE_STAT` and `UPDATE_RUNENERGY`; then modal interface changes
   (`IF_CLOSE`, `IF_OPENMAIN_SIDE`, `IF_OPENMAIN`, `IF_OPENCHAT`, `IF_OPENSIDE`,
   `IF_OPENOVERLAY`).
8. Cleanup.

Packets written by scripts during earlier phases (messages, varps, interface text, sounds, and
so on) are sent immediately, so they arrive before that tick's `PLAYER_INFO`.

### After Login

After status `2`, the same tick sends the following, in this order (`Player.onLogin`):

1. `REBUILD_NORMAL`
2. `CHAT_FILTER_SETTINGS`
3. `FRIENDLIST_LOADED` (`1` with the friend server enabled; otherwise `2`, followed by an empty
   `UPDATE_IGNORELIST`)
4. `IF_CLOSE`
5. `UPDATE_PID` (the local player's index and members flag)
6. `RESET_CLIENT_VARCACHE`, then one `VARP_SMALL` or `VARP_LARGE` per transmitted varp
7. `RESET_ANIMS`
8. Whatever the content login script sends (typically `IF_SETTAB` for every tab, messages, and
   more varps)
9. `UPDATE_REBOOT_TIMER`, if a shutdown is pending
10. The normal tick output: `PLAYER_INFO` (local-player teleport plus appearance), `NPC_INFO`,
    zone resets for every zone in view, `UPDATE_INV_FULL` for each listened inventory,
    `UPDATE_RUNWEIGHT`, an `UPDATE_STAT` per stat, and `UPDATE_RUNENERGY`

`REBUILD_NORMAL` always precedes the `PLAYER_INFO` that places the local player, so the client
knows the build-area base before it decodes the 7-bit local coordinates.

### Reconnect

The webclient treats 15 seconds without any server packet as a lost connection and logs in
again with opcode `18`. If the player is still in the world, the server replies `15` and
replays state (`Player.onReconnect`): `RESET_CLIENT_VARCACHE` and all transmitted varps,
`REBUILD_NORMAL`, `UPDATE_REBOOT_TIMER` if pending, a modal close, `IF_SETTAB` for every tab,
an `UPDATE_STAT` per stat, `UPDATE_RUNENERGY`, and `RESET_ANIMS`. The output phase then adds
`UPDATE_INV_FULL` for each listened inventory, `UPDATE_RUNWEIGHT`, and a `PLAYER_INFO` that
re-places the local player with a teleport and appearance. The server clears its per-viewer
player list, NPC list, and appearance cache, so the first `PLAYER_INFO` and `NPC_INFO` after
reconnect start with a tracked `count` of 0, which removes every tracked entry, and then re-add
everything in view. The webclient keeps its other state across a reconnect; the ISAAC streams
restart from the new attempt's seeds. Any other reply to opcode `18` follows the normal login
rules.

### Keepalive and Idle Logout

| Client packet | ID | Length | Behavior |
|---|---:|---:|---|
| `NO_TIMEOUT` | `181` | 0 | Webclient sends it when no outgoing bytes have been flushed for about 1 second. It is an ordinary ISAAC-encoded game packet; the server sends no pong. Receiving any game-packet bytes refreshes the server's response timer. |
| `IDLE_TIMER` | `145` | 0 | Webclient sends it after about 90 seconds without local input, then backs off by 10 seconds between further idle notices. In non-debug mode the server requests idle logout. This is not a keepalive. |

The engine has separate liveness checks: 50 world ticks (about 30 seconds) after a
connection is lost, and 100 ticks (about 60 seconds) without any client response.
The TCP socket also has its own 30-second inactivity timeout. Sending `NO_TIMEOUT`
keeps the response timer fresh, but does not prevent the idle-logout behavior caused
by `IDLE_TIMER`. A headless client that intends to remain logged in should send
`NO_TIMEOUT` when otherwise idle and should not send `IDLE_TIMER` unless it intends
to request idle logout.

See [`NetworkPlayer.ts`](../../289server/engine/src/engine/entity/NetworkPlayer.ts),
[`World.ts`](../../289server/engine/src/engine/World.ts), and
[`IdleTimerHandler.ts`](../../289server/engine/src/network/game/client/handler/IdleTimerHandler.ts).

### Clean Logout

There is no dedicated client-to-server logout opcode. The webclient's logout button
sends `IF_BUTTON` (client opcode `86`) with a two-byte big-endian interface component
ID. The current project helper uses component `2458`; this value belongs to the
active interface/cache and is not a universal protocol constant. The engine handles
the button through the component's configured trigger.

When the world removes the player, it sends server packet `LOGOUT` (server opcode
`121`, zero payload), then closes the client socket, removes the player, and flushes
the save. The server opcode is ISAAC-encoded like other in-game server packets. The
webclient also starts a 250-frame local logout timer when the button is selected; it
is client UI behavior, not a wire timeout. A direct client should wait for the
server's `LOGOUT` packet or a socket close rather than treating that frame counter
as protocol state.

Abrupt TCP close is not equivalent to clean logout: the engine detects the lost
connection and applies its disconnect grace/timeout handling. See
[`IfButtonHandler.ts`](../../289server/engine/src/network/game/client/handler/IfButtonHandler.ts),
[`Logout.ts`](../../289server/engine/src/network/game/server/model/Logout.ts),
[`World.removePlayer`](../../289server/engine/src/engine/World.ts), and the current
project's [`cleanLogout.ts`](../../e2e/lib/cleanLogout.ts).

## Server-to-Client Opcodes

There are 69 server opcodes, and this table is complete. Any opcode not listed is never sent;
treat it as a fatal desync. "Size" uses the [framing](#in-game-packet-framing) convention. Names
are the engine's; the webclient name is given only where it differs. Opcodes marked "zone" are
[zone sub-packets](#zone-sub-packets). They can arrive as standalone packets or embedded in
`UPDATE_ZONE_PARTIAL_ENCLOSED`.

| Op | Name | Webclient name | Size | Group |
|---:|---|---|---:|---|
| 12 | `TUT_OPEN` | | 2 | [Tutorial](#tutorial) |
| 13 | `CHAT_FILTER_SETTINGS` | | 3 | [Social](#social-and-chat) |
| 18 | `IF_SETOBJECT` | | 6 | [Interface updates](#interface-component-updates) |
| 21 | `SET_PLAYER_OP` | | -1 | [Player state](#player-state-and-miscellaneous) |
| 23 | `IF_CLOSE` | | 0 | [Interfaces](#interfaces-and-modals) |
| 28 | `UPDATE_INV_STOP_TRANSMIT` | | 2 | [Inventory](#inventories) |
| 29 | `MIDI_JINGLE` | | 4 | [Audio](#audio) |
| 30 | `IF_SETPLAYERHEAD` | | 2 | [Interface updates](#interface-component-updates) |
| 35 | `P_COUNTDIALOG` | | 0 | [Interfaces](#interfaces-and-modals) |
| 46 | `UPDATE_RUNWEIGHT` | | 2 | [Player state](#player-state-and-miscellaneous) |
| 47 | `UPDATE_IGNORELIST` | | -2 | [Social](#social-and-chat) |
| 55 | `IF_OPENMAIN_SIDE` | | 4 | [Interfaces](#interfaces-and-modals) |
| 59 | `IF_SETTEXT` | | -2 | [Interface updates](#interface-component-updates) |
| 60 | `OBJ_ADD` | | 5 | [Zone](#zone-sub-packets) |
| 63 | `IF_SETTAB` | `IF_SETICON` | 3 | [Interfaces](#interfaces-and-modals) |
| 65 | `NPC_INFO` | | -2 | [NPC_INFO](#npc_info-65) |
| 71 | `OBJ_DEL` | | 3 | [Zone](#zone-sub-packets) |
| 73 | `CAM_MOVETO` | | 6 | [Camera](#camera) |
| 75 | `VARP_SMALL` | | 3 | [Variables](#variables) |
| 76 | `UPDATE_INV_PARTIAL` | | -2 | [Inventory](#inventories) |
| 79 | `IF_SETPOSITION` | | 6 | [Interface updates](#interface-component-updates) |
| 81 | `IF_OPENCHAT` | | 2 | [Interfaces](#interfaces-and-modals) |
| 82 | `CAM_LOOKAT` | | 6 | [Camera](#camera) |
| 83 | `LOC_MERGE` | `P_LOCMERGE` | 14 | [Zone](#zone-sub-packets) |
| 87 | `MAP_PROJANIM` | | 15 | [Zone](#zone-sub-packets) |
| 90 | `LOC_ADD_CHANGE` | | 4 | [Zone](#zone-sub-packets) |
| 97 | `VARP_LARGE` | | 6 | [Variables](#variables) |
| 106 | `LOC_ANIM` | | 4 | [Zone](#zone-sub-packets) |
| 107 | `UPDATE_INV_FULL` | | -2 | [Inventory](#inventories) |
| 112 | `UPDATE_ZONE_PARTIAL_ENCLOSED` | | -2 | [Zone updates](#zone-framing-packets) |
| 115 | `HINT_ARROW` | | 6 | [Player state](#player-state-and-miscellaneous) |
| 117 | `OBJ_COUNT` | | 7 | [Zone](#zone-sub-packets) |
| 119 | `IF_OPENMAIN` | | 2 | [Interfaces](#interfaces-and-modals) |
| 120 | `UPDATE_PID` | | 3 | [Player state](#player-state-and-miscellaneous) |
| 121 | `LOGOUT` | | 0 | [Player state](#player-state-and-miscellaneous) |
| 127 | `IF_OPENOVERLAY` | | 2 | [Interfaces](#interfaces-and-modals) |
| 133 | `CAM_RESET` | | 0 | [Camera](#camera) |
| 136 | `MINIMAP_TOGGLE` | | 1 | [Player state](#player-state-and-miscellaneous) |
| 138 | `IF_SETHIDE` | | 3 | [Interface updates](#interface-component-updates) |
| 144 | `UPDATE_ZONE_FULL_FOLLOWS` | | 2 | [Zone updates](#zone-framing-packets) |
| 154 | `UPDATE_STAT` | | 6 | [Player state](#player-state-and-miscellaneous) |
| 155 | `UPDATE_ZONE_PARTIAL_FOLLOWS` | | 2 | [Zone updates](#zone-framing-packets) |
| 160 | `IF_SETCOLOUR` | | 4 | [Interface updates](#interface-component-updates) |
| 164 | `UNSET_MAP_FLAG` | | 0 | [Player state](#player-state-and-miscellaneous) |
| 168 | `UPDATE_FRIENDLIST` | | 9 | [Social](#social-and-chat) |
| 172 | `RESET_CLIENT_VARCACHE` | `VARP_SYNC` | 0 | [Variables](#variables) |
| 176 | `OBJ_REVEAL` | | 7 | [Zone](#zone-sub-packets) |
| 177 | `SYNTH_SOUND` | | 5 | [Audio](#audio) |
| 181 | `TUT_FLASH` | | 1 | [Tutorial](#tutorial) |
| 184 | `IF_SETSCROLLPOS` | | 4 | [Interface updates](#interface-component-updates) |
| 187 | `MIDI_SONG` | | 2 | [Audio](#audio) |
| 188 | `PLAYER_INFO` | | -2 | [PLAYER_INFO](#player_info-188) |
| 189 | `IF_SETTAB_ACTIVE` | `IF_SHOWICON` | 1 | [Interfaces](#interfaces-and-modals) |
| 194 | `LOC_DEL` | | 2 | [Zone](#zone-sub-packets) |
| 195 | `UPDATE_RUNENERGY` | | 1 | [Player state](#player-state-and-miscellaneous) |
| 196 | `MESSAGE_GAME` | | -1 | [Social](#social-and-chat) |
| 201 | `RESET_ANIMS` | | 0 | [Player state](#player-state-and-miscellaneous) |
| 204 | `UPDATE_REBOOT_TIMER` | | 2 | [Player state](#player-state-and-miscellaneous) |
| 208 | `CAM_SHAKE` | | 4 | [Camera](#camera) |
| 211 | `IF_SETANIM` | | 4 | [Interface updates](#interface-component-updates) |
| 219 | `REBUILD_NORMAL` | | 4 | [Map](#map-rebuild) |
| 222 | `IF_SETMODEL` | | 4 | [Interface updates](#interface-component-updates) |
| 233 | `MAP_ANIM` | | 6 | [Zone](#zone-sub-packets) |
| 235 | `FRIENDLIST_LOADED` | | 1 | [Social](#social-and-chat) |
| 243 | `MESSAGE_PRIVATE` | | -1 | [Social](#social-and-chat) |
| 244 | `IF_SETNPCHEAD` | | 4 | [Interface updates](#interface-component-updates) |
| 247 | `SET_MULTIWAY` | | 1 | [Player state](#player-state-and-miscellaneous) |
| 252 | `IF_OPENSIDE` | | 2 | [Interfaces](#interfaces-and-modals) |
| 253 | `LAST_LOGIN_INFO` | | 10 | [Player state](#player-state-and-miscellaneous) |

## Server-to-Client Payloads

Fields are listed in wire order. "Com" means an interface component ID from the cache's
interface definitions. A headless client without the interface cache can still track these
IDs as opaque numbers.

### Interfaces and Modals

The client has three modal slots (main, side, chat), one overlay slot, and a component for
each side tab. Opening a modal closes conflicting ones, as described below. When scripts open
or close modals or change the overlay, the server batches the result into the tick's final
output step. `IF_SETTAB`, `IF_SETTAB_ACTIVE`, and `P_COUNTDIALOG` are sent as soon as the
script runs, and login sends an `IF_CLOSE` directly.

| Op | Name | Payload | Client action |
|---:|---|---|---|
| 119 | `IF_OPENMAIN` | `u16 com` | Main modal = com. Closes the side modal, chat modal, and count dialog. |
| 252 | `IF_OPENSIDE` | `u16 com` | Side modal = com (replaces the tab area). Closes the main modal, chat modal, and count dialog. |
| 81 | `IF_OPENCHAT` | `u16 com` | Chat modal = com (dialogue box). Closes the main and side modals. Clears the "pause button already resumed" latch. |
| 55 | `IF_OPENMAIN_SIDE` | `u16 mainCom`, `u16 sideCom` | Main and side modals together. Closes the chat modal and count dialog. |
| 23 | `IF_CLOSE` | - | Closes the main, side, and chat modals and the count dialog. |
| 127 | `IF_OPENOVERLAY` | `s16 com` | Overlay = com; `-1` removes it. Independent of the modals. |
| 63 | `IF_SETTAB` | `u16 com`, `u8 tab` | Side tab `tab` shows com; `65535` empties the tab. |
| 189 | `IF_SETTAB_ACTIVE` | `u8 tab` | Selects side tab `tab`. |
| 35 | `P_COUNTDIALOG` | - | Opens the numeric input prompt. Answer with `RESUME_P_COUNTDIALOG`. |

Tab indices are 0-based client slots. The webclient selects tab 3 (inventory) by default and
treats tab 12 as the tab that shows run energy and weight; the content login script decides
what each tab contains.

### Interface Component Updates

These change properties of an interface component in the client's interface table.

| Op | Name | Payload | Notes |
|---:|---|---|---|
| 59 | `IF_SETTEXT` | `u16 com`, `jstr text` | Replaces the component's text. |
| 138 | `IF_SETHIDE` | `u16 com`, `u8 hidden` | `1` hides, `0` shows. |
| 160 | `IF_SETCOLOUR` | `u16 com`, `u16 rgb555` | 5 bits each of red (bits 10-14), green (5-9), and blue (0-4). The webclient expands each channel with `<< 3`. |
| 18 | `IF_SETOBJECT` | `u16 com`, `u16 obj`, `u16 zoom` | Shows an object model. The webclient's model zoom is `obj.zoom2d * 100 / zoom`. |
| 222 | `IF_SETMODEL` | `u16 com`, `u16 model` | Shows a raw model ID. |
| 211 | `IF_SETANIM` | `u16 com`, `s16 seq` | Animates the component's model; `-1` stops it. |
| 30 | `IF_SETPLAYERHEAD` | `u16 com` | Shows the local player's chathead (built from the local appearance). |
| 244 | `IF_SETNPCHEAD` | `u16 com`, `u16 npc` | Shows an NPC type's chathead. |
| 79 | `IF_SETPOSITION` | `u16 com`, `s16 x`, `s16 y` | Moves the component (pixels). |
| 184 | `IF_SETSCROLLPOS` | `u16 com`, `u16 y` | Scroll position of a layer component, clamped by the client to its scroll height. |

### Tutorial

| Op | Name | Payload | Notes |
|---:|---|---|---|
| 12 | `TUT_OPEN` | `s16 com` | Persistent tutorial chatbox component; `-1` removes it. |
| 181 | `TUT_FLASH` | `u8 tab` | Flashes side tab `tab`. When the player opens that tab, the client sends `TUT_CLICKSIDE`. |

### Inventories

Inventories are addressed by the interface component that displays them, not by inventory
type. The component IDs for the backpack, equipment, bank, and so on come from the cache and
content, like the logout component.

Each slot is encoded as an item entry:

| Field | Type | Meaning |
|---|---|---|
| `id` | `u16` | Object ID **plus one**; `0` means the slot is empty. |
| `n` | `u8` | Count if below 255. |
| `count` | `s32` | Present only when `n` is `255`; the real count. |

An empty slot is encoded as `id = 0, n = 0`.

| Op | Name | Payload | Client action |
|---:|---|---|---|
| 107 | `UPDATE_INV_FULL` | `u16 com`, `u16 size`, then `size` item entries for slots `0..size-1` | Replace the inventory. Every slot at or above `size` becomes empty. The engine sends `size` = last occupied slot + 1, capped at the component's width x height. |
| 76 | `UPDATE_INV_PARTIAL` | `u16 com`, then until the payload ends: `smart slot` plus an item entry | Update only the listed slots. Ignore slots outside the component's capacity. |
| 28 | `UPDATE_INV_STOP_TRANSMIT` | `u16 com` | Clear every slot of that component. |

### Camera

Camera packets matter only for rendering, but they must still be consumed.

| Op | Name | Payload | Notes |
|---:|---|---|---|
| 73 | `CAM_MOVETO` | `u8 localX`, `u8 localZ`, `u16 height`, `u8 rate`, `u8 rate2` | Cinematic camera position in build-area tiles. `rate2 >= 100` jumps instantly. |
| 82 | `CAM_LOOKAT` | `u8 localX`, `u8 localZ`, `u16 height`, `u8 rate`, `u8 rate2` | Cinematic look-at target, same units. |
| 208 | `CAM_SHAKE` | `u8 axis`, `u8 random`, `u8 amplitude`, `u8 rate` | `axis` is 0-4. Engine field names are given here; the webclient stores them under shifted names. |
| 133 | `CAM_RESET` | - | Leaves cinematic mode and stops all shakes. |

### Social and Chat

| Op | Name | Payload | Notes |
|---:|---|---|---|
| 196 | `MESSAGE_GAME` | `jstr text` | Game message. Text ending in `:tradereq:` is a trade request from the name before the first `:`; `:duelreq:` is a duel request in the same format. |
| 243 | `MESSAGE_PRIVATE` | `name37 from`, `s32 messageId`, `u8 staffLevel`, then `wordpack` for the rest of the payload (payload length - 13) | Incoming private message. The webclient drops duplicate `messageId` values (it remembers the last 100). `staffLevel` 0 is a player, 1 a player moderator, and 2-3 staff. |
| 168 | `UPDATE_FRIENDLIST` | `name37 name`, `u8 world` | Friend status. `world` 0 means offline; otherwise it is the world (node) ID. Adds the friend if unknown. |
| 47 | `UPDATE_IGNORELIST` | `name37` repeated (payload length / 8 entries) | Replaces the whole ignore list. |
| 235 | `FRIENDLIST_LOADED` | `u8 status` | `0` loading, `1` connecting to the friend server, `2` online. |
| 13 | `CHAT_FILTER_SETTINGS` | `u8 public`, `u8 private`, `u8 trade` | Current chat modes; the same values `CHAT_SETMODE` sends. |

Public chat and overhead text from other players arrive inside `PLAYER_INFO`, not as separate
packets.

### Player State and Miscellaneous

| Op | Name | Payload | Notes |
|---:|---|---|---|
| 120 | `UPDATE_PID` | `u16 index`, `u8 members` | The local player's index in the player table. This is the value other packets use to refer to "you" (`OBJ_REVEAL`, `LOC_MERGE`, face-entity). `members` is `1` for a members account. |
| 154 | `UPDATE_STAT` | `u8 stat`, `s32 xp`, `u8 level` | Whole XP (the engine stores tenths and divides by 10). `level` is the current, possibly boosted or drained, level. The webclient derives the base level from XP (see below). |
| 195 | `UPDATE_RUNENERGY` | `u8 percent` | 0-100. |
| 46 | `UPDATE_RUNWEIGHT` | `s16 kg` | Carried weight in kilograms; can be negative. |
| 204 | `UPDATE_REBOOT_TIMER` | `u16 ticks` | Server shutdown countdown in 600 ms ticks. |
| 253 | `LAST_LOGIN_INFO` | `s32 lastIp`, `u16 daysSinceLogin`, `u8 daysSinceRecoveryChange`, `u16 unreadMessages`, `u8 warnMembers` | Welcome-screen data. `lastIp` is an IPv4 address, most significant octet first. |
| 115 | `HINT_ARROW` | `u8 type`, then 5 bytes that depend on `type` | See the table below. |
| 21 | `SET_PLAYER_OP` | `u8 op`, `u8 priority`, `jstr text` | Right-click option `op` (1-5) shown on other players. `priority` 0 deprioritises the option: the webclient sorts it below "Walk here", so it is never the left-click default. Any other value leaves it in normal order. The text `null` (case-insensitive) removes the option. |
| 247 | `SET_MULTIWAY` | `u8 multi` | `1` inside a multi-combat area. |
| 136 | `MINIMAP_TOGGLE` | `u8 state` | `0` normal, `1` minimap clicks disabled, `2` blacked out. |
| 164 | `UNSET_MAP_FLAG` | - | Clears the minimap destination flag. The server sends it when a move is rejected or the walk queue empties. |
| 201 | `RESET_ANIMS` | - | Stops the primary animation of every known player and NPC. |
| 121 | `LOGOUT` | - | The server is about to close the socket. See [Clean Logout](#clean-logout). |

`HINT_ARROW` payloads:

| `type` | Following 5 bytes | Meaning |
|---:|---|---|
| `1` | `u16 npcIndex`, 3 zero bytes | Arrow over an NPC. |
| `2`-`6` | `u16 x`, `u16 z`, `u8 height` | Arrow over absolute tile (`x`, `z`). The type picks the position within the tile: `2` centre, `3` west edge, `4` east edge, `5` south edge, `6` north edge. |
| `10` | `u16 playerIndex`, 3 zero bytes | Arrow over a player. |
| `255` | 5 zero bytes | Clears the arrow (engine type `-1`). |

Stat IDs: 0 attack, 1 defence, 2 strength, 3 hitpoints, 4 ranged, 5 prayer, 6 magic, 7 cooking,
8 woodcutting, 9 fletching, 10 fishing, 11 firemaking, 12 crafting, 13 smithing, 14 mining,
15 herblore, 16 agility, 17 thieving, 18 and 19 unused, 20 runecraft
([`PlayerStat.ts`](../../289server/engine/src/engine/entity/PlayerStat.ts)). The base level is
the highest `L` such that `xp >= table[L - 2]`, where for `i` in 0-98 the table accumulates
`floor(L + 300 * 2^(L / 7))` over `L = 1..i+1` and divides the running sum by 4 (see
`levelExperience` in the webclient).

### Variables

| Op | Name | Payload | Notes |
|---:|---|---|---|
| 75 | `VARP_SMALL` | `u16 varp`, `s8 value` | Sent when the value is in -128 to 127. |
| 97 | `VARP_LARGE` | `u16 varp`, `s32 value` | Any other value. |
| 172 | `RESET_CLIENT_VARCACHE` | - | The webclient copies its last server-sent value over every locally predicted varp value (toggle and select buttons change varps locally). A client that stores only server values can treat it as a no-op. |

Varps drive quest progress, settings, and many interface states. Their meaning comes from the
cache and content scripts.

### Audio

| Op | Name | Payload | Notes |
|---:|---|---|---|
| 187 | `MIDI_SONG` | `u16 song` | Background music; `65535` stops it. |
| 29 | `MIDI_JINGLE` | `u16 jingle`, `u16 delay` | Short jingle; music resumes after `delay`. |
| 177 | `SYNTH_SOUND` | `u16 sound`, `u8 loops`, `u16 delay` | Sound effect. |

### Map Rebuild

| Op | Name | Payload | Notes |
|---:|---|---|---|
| 219 | `REBUILD_NORMAL` | `u16 zoneX`, `u16 zoneZ` | Centre zone of the new build area. Set `baseX = (zoneX - 6) * 8` and `baseZ = (zoneZ - 6) * 8`. The map squares to load are every `(x, z)` with `x` from `(zoneX - 6) / 8` to `(zoneX + 6) / 8` and `z` likewise (integer division). They are not sent. |

The server sends `REBUILD_NORMAL` at login, on reconnect, and whenever the player's tile leaves
the central area of the current build area. Afterwards the server re-sends every zone in view
with `UPDATE_ZONE_FULL_FOLLOWS`, so a client may discard ground items and loc changes on
rebuild. The webclient ignores a rebuild that repeats the current centre while its scene is
loaded. Entity positions from `PLAYER_INFO` and `NPC_INFO` continue across a rebuild.

## PLAYER_INFO (188)

`PLAYER_INFO` arrives every tick. It moves the local player, updates the tracked player list,
adds new players, and carries "extended info" blocks (appearance, animation, chat, damage, and
so on). The payload is a bit stream followed by a byte section. The engine builds it in
[`rsbuf/info.ts`](../../289server/engine/src/network/rsbuf/info.ts); the webclient decodes it in
`Client.getPlayerPos`.

### Client State Required

- The local player's absolute tile and level.
- An ordered list of tracked player indices (at most 255; the server caps it at 250). The order
  must match the server's: surviving entries keep their relative order, and new entries are
  appended in the order received.
- Per player index: position, and the most recent appearance block. The webclient caches
  appearance by index (`playerAppearanceBuffer`), so a re-added player whose appearance did not
  change can be rendered without a new block.

### Bit Section

Start reading bits at byte 0.

**1. Local player.**

| Bits | Field | Notes |
|---:|---|---|
| 1 | `update` | `0`: nothing more for the local player. |
| 2 | `type` | Only if `update` is 1. |

| `type` | Further bits | Meaning |
|---:|---|---|
| 0 | none | No movement; the local player has an extended block. |
| 1 | `3 dir`, `1 hasExtended` | Walked one step. |
| 2 | `3 walkDir`, `3 runDir`, `1 hasExtended` | Ran two steps (walk step, then run step). |
| 3 | `2 level`, `7 localX`, `7 localZ`, `1 jump`, `1 hasExtended` | Placed at build-area tile (`localX`, `localZ`) on `level`. `jump` 1 is a teleport; `jump` 0 lets the client animate a short move (8 tiles or fewer). Sent on login and after teleports. |

**2. Tracked players.**

| Bits | Field | Notes |
|---:|---|---|
| 8 | `count` | Number of entries from the client's tracked list that follow. If `count` is less than the list length, every entry at position `count` or later is removed. A `count` greater than the list length is a desync. |

Then, for each of the first `count` entries of the tracked list, in list order:

| Bits | Field | Meaning |
|---:|---|---|
| 1 | `update` | `0`: unchanged; keep the entry. |
| 2 | `type` | `0` keep, with an extended block; `1` walk: `3 dir`, `1 hasExtended`; `2` run: `3 walkDir`, `3 runDir`, `1 hasExtended`; `3` remove from the list. |

**3. New players.** Loop while at least 11 bits remain (`bitPos + 10 < payloadLength * 8`,
exactly as the webclient checks):

| Bits | Field | Notes |
|---:|---|---|
| 11 | `index` | Player index 0-2046. `2047` ends the list. |
| 5 | `dx` | Signed: values above 15 mean `dx - 32`. |
| 5 | `dz` | Signed, same rule. |
| 1 | `jump` | `1` places the player without a walk animation. |
| 1 | `hasExtended` | The engine always sends `1` for new players. |

The new player's absolute tile is the local player's tile (after step 1) plus (`dx`, `dz`).
Append the index to the tracked list. The engine writes the `2047` terminator only when at least
one extended block follows; otherwise the loop ends because fewer than 11 bits remain.

Then advance to the next byte boundary (`bytePos = (bitPos + 7) >> 3`).

Direction codes (3 bits), from
[`ClientEntity.moveCode`](../../289server/webclient/src/dash3d/ClientEntity.ts):

| Code | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| Step (`dx`, `dz`) | NW (-1, +1) | N (0, +1) | NE (+1, +1) | W (-1, 0) | E (+1, 0) | SW (-1, -1) | S (0, -1) | SE (+1, -1) |

### Extended Info Section

One block for each entity flagged above, in flag order: the local player first (if flagged),
then tracked players in list order, then new players in the order received. Each block starts
with a mask:

```text
mask = u8
if (mask & 0x80) mask |= u8 << 8
```

The engine writes masks above `0xff` as a little-endian `u16` with `0x80` set, which is the same
bytes. Fields follow in this fixed order, each present only if its bit is set:

| Order | Bit | Engine / webclient name | Payload |
|---:|---|---|---|
| 1 | `0x001` | `APPEARANCE` | `u8 length`, then `length` bytes of [appearance block](#appearance-block). |
| 2 | `0x002` | `ANIM` | `u16 seq` (`65535` stops the animation), `u8 delay` (client cycles). |
| 3 | `0x004` | `FACE_ENTITY` / `FACEENTITY` | `u16 target`: `65535` none; `>= 32768` is player index `target - 32768`; otherwise an NPC index. |
| 4 | `0x008` | `SAY` | `jstr text`: overhead text forced by a script. Unlike `CHAT` it is not WordPack-encoded; the webclient also prints it in the chatbox as public chat. |
| 5 | `0x010` | `DAMAGE` / `HITMARK` | `u8 damage`, `u8 type`, `u8 currentHp`, `u8 maxHp`. |
| 6 | `0x020` | `FACE_COORD` / `FACESQUARE` | `u16 fineX`, `u16 fineZ` in [fine coordinates](#coordinates). |
| 7 | `0x040` | `CHAT` | `u8 colour`, `u8 effect`, `u8 rights`, `u8 length`, then `length` bytes of `wordpack`. The webclient reads the first two bytes as one `u16`. `rights` is the sender's staff level (0-2); messages with `rights` 0 or 1 from ignored names are hidden. The server never sends the local player its own `CHAT`. |
| - | `0x080` | `BIG` / `BIG_UPDATE` | Mask-extension flag only; no payload. |
| 8 | `0x100` | `SPOT_ANIM` | `u16 spotanim` (`65535` none), `s32 info`: height is `info >> 16`, delay is `info & 0xffff` (client cycles). |
| 9 | `0x200` | `EXACT_MOVE` | `u8 startX`, `u8 startZ`, `u8 endX`, `u8 endZ` (build-area tiles), `u16 begin`, `u16 finish` (client cycles from now), `u8 direction`. Forced movement such as agility shortcuts. |
| 10 | `0x400` | `DAMAGE2` / `HITMARK2` | Same layout as `DAMAGE`; a second hitsplat in the same tick. |

For a newly added player, the server always includes `FACE_COORD`. It also includes
`FACE_ENTITY` if one is set, and `APPEARANCE` unless this viewer already holds the player's
current appearance.

After the last block, the read position must equal the payload length. The webclient throws
(and logs out) on a mismatch. Treat a mismatch as a decoder bug, not as data to skip.

### Appearance Block

From `Player.generateAppearance` and `ClientPlayer.setAppearance`:

| Field | Encoding | Notes |
|---|---|---|
| `gender` | `u8` | 0 male, 1 female. |
| `headicons` | `u8` | Bitmask: bit `i` draws headicon sprite `i` above the player (prayer and skull icons). |
| 12 wear slots | per slot, see below | Slot order is wear position 0-11. |
| `colours` | 5 x `u8` | Hair, torso, legs, feet, and skin colour indices. |
| animations | 7 x `u16` | `readyanim`, `turnanim`, `walkanim`, `walkanim_b`, `walkanim_l`, `walkanim_r`, `runanim`; `65535` = none. |
| `name` | `name37` | Display with `_` replaced by a space and word capitalisation. |
| `combatLevel` | `u8` | |
| `skillLevel` | `u16` | Total level. |

Each wear slot starts with one byte. If it is `0`, the slot is empty and is only that byte.
Otherwise read one more byte to form a `u16` value:

| Value | Meaning |
|---|---|
| `0x100 + n` | Body kit `n` (an identity-kit ID: hair, jaw, torso, arms, hands, legs, or feet). |
| `0x200 + n` | Worn object `n`. |
| `0xffff` (slot 0 only) | The player is transformed into an NPC: a `u16` NPC type follows, and the remaining slots are **not** sent. Continue with `colours`. |

The engine fills body-kit fallbacks for slots 4 (torso), 6 (arms), 7 (legs), 8 (hair),
9 (hands), 10 (feet), and 11 (jaw). Slots 0-3 and 5 hold only equipment. A slot hidden by
another item's secondary wear position is sent empty.

## NPC_INFO (65)

`NPC_INFO` has the same structure as `PLAYER_INFO`, without the local-player section. The client
keeps an ordered list of tracked NPC indices (at most 255).

### Bit Section

Start reading bits at byte 0.

1. `8 count` and then per tracked NPC exactly as in
   [tracked players](#bit-section): `1 update`, `2 type` (0 extended only, 1 walk, 2 run,
   3 remove), with the same direction and `hasExtended` bits. There is no teleport type; an NPC
   that teleports is removed and re-added.
2. New NPCs. Loop while `bitPos + 21 < payloadLength * 8`:

| Bits | Field | Notes |
|---:|---|---|
| 14 | `index` | NPC index 0-16382. `16383` ends the list. |
| 11 | `type` | NPC type ID. |
| 5 | `dx` | Signed, relative to the local player's current tile. |
| 5 | `dz` | Signed. |
| 1 | `jump` | |
| 1 | `hasExtended` | Always `1` from this engine. |

Then align to the next byte.

### Extended Info Section

NPC masks are a single `u8` with no extension bit. Order and payloads:

| Order | Bit | Engine / webclient name | Payload |
|---:|---|---|---|
| 1 | `0x01` | `DAMAGE2` / `HITMARK2` | `u8 damage`, `u8 type`, `u8 currentHp`, `u8 maxHp`. |
| 2 | `0x02` | `ANIM` | `u16 seq` (`65535` stops), `u8 delay`. |
| 3 | `0x04` | `FACE_ENTITY` | `u16 target`, same encoding as for players. |
| 4 | `0x08` | `SAY` | `jstr text`. |
| 5 | `0x10` | `DAMAGE` / `HITMARK` | Same layout as `DAMAGE2`. |
| 6 | `0x20` | `CHANGE_TYPE` / `CHANGETYPE` | `u16 type`: the NPC becomes this NPC type. |
| 7 | `0x40` | `SPOT_ANIM` | `u16 spotanim`, `s32 info` (height `>> 16`, delay `& 0xffff`). |
| 8 | `0x80` | `FACE_COORD` / `FACESQUARE` | `u16 fineX`, `u16 fineZ`. |

A newly added NPC always gets `FACE_COORD`, plus `FACE_ENTITY` if set. As with players, the
final read position must equal the payload length.

## Zone Updates

Ground items, dynamic locs (scenery), spot animations, and projectiles are sent per zone. A
"current zone" pointer is set by a zone framing packet, and zone sub-packets are applied
relative to it. The webclient applies them to its current level (the level from the last
local-player teleport).

### Zone Framing Packets

| Op | Name | Payload | Client action |
|---:|---|---|---|
| 144 | `UPDATE_ZONE_FULL_FOLLOWS` | `u8 localX`, `u8 localZ` | Set the current zone to build-area tile (`localX`, `localZ`), its south-west corner (a multiple of 8). Delete every ground item in its 8x8 tiles, and expire the client's loc changes there, so the zone returns to its cache state. The server then re-sends the zone's current state as standalone sub-packets. |
| 155 | `UPDATE_ZONE_PARTIAL_FOLLOWS` | `u8 localX`, `u8 localZ` | Set the current zone only. Standalone sub-packets follow. |
| 112 | `UPDATE_ZONE_PARTIAL_ENCLOSED` | `u8 localX`, `u8 localZ`, then until the payload ends: `u8 subOpcode` plus that sub-packet's payload | Set the current zone, then apply each embedded sub-packet. Embedded sub-opcodes are **raw** bytes: they are not ISAAC-encoded and have no length prefix. Their sizes are the fixed sizes below. |

Per zone per tick, the server sends: on the first tick a zone is in view (including every zone
after a rebuild), `FULL_FOLLOWS` plus the current dynamic state; then the shared events of the
tick in one `PARTIAL_ENCLOSED`; then `PARTIAL_FOLLOWS` plus events visible only to this player
(for example, an item drop that only its owner can see yet). A standalone sub-packet always
applies to the zone set by the most recent framing packet.

### Zone Sub-Packets

Every sub-packet starts with the zone-relative position byte `pos`: tile
`(zoneX + ((pos >> 4) & 7), zoneZ + (pos & 7))`. Sizes include `pos`, and are the same whether
standalone or enclosed.

| Op | Name | Size | Payload after `pos` | Client action |
|---:|---|---:|---|---|
| 60 | `OBJ_ADD` | 5 | `u16 obj`, `u16 count` | Add a ground item. Counts above 65535 are sent as 65535. |
| 71 | `OBJ_DEL` | 3 | `u16 obj` | Remove the first ground item on the tile whose ID equals `obj & 0x7fff`. |
| 117 | `OBJ_COUNT` | 7 | `u16 obj`, `u16 oldCount`, `u16 newCount` | Change the count of the first item matching both `obj` and `oldCount`. |
| 176 | `OBJ_REVEAL` | 7 | `u16 obj`, `u16 count`, `u16 receiver` | A private drop becomes public. Add it **unless** `receiver` equals your index from `UPDATE_PID`, since that player already sees it. |
| 90 | `LOC_ADD_CHANGE` | 4 | `u8 info`, `u16 loc` | Place or replace loc `loc` on the tile in the layer given by its shape. |
| 194 | `LOC_DEL` | 2 | `u8 info` | Remove the loc in that shape's layer on the tile. |
| 106 | `LOC_ANIM` | 4 | `u8 info`, `u16 seq` | Play animation `seq` on the existing loc in that layer. |
| 83 | `LOC_MERGE` | 14 | `u8 info`, `u16 loc`, `u16 startCycle`, `u16 endCycle`, `u16 player`, `s8 east`, `s8 south`, `s8 west`, `s8 north` | Temporarily draw loc `loc` as part of player `player`'s model between the two cycle offsets. The four values are tile offsets of the player's bounding area relative to `pos`. |
| 233 | `MAP_ANIM` | 6 | `u16 spotanim`, `u8 height`, `u16 delay` | Spot animation on the tile. |
| 87 | `MAP_PROJANIM` | 15 | `s8 dstDx`, `s8 dstDz`, `s16 target`, `u16 spotanim`, `u8 srcHeight`, `u8 dstHeight`, `u16 startDelay`, `u16 endDelay`, `u8 peak`, `u8 arc` | Projectile from `pos` to `pos + (dstDx, dstDz)`. `target` 0 aims at the tile, `> 0` at NPC index `target - 1`, and `< 0` at player index `-target - 1`. The webclient multiplies both heights by 4. |

`info` packs the loc shape and rotation: `shape = info >> 2` (0-22) and `angle = info & 3`. The
shape selects the layer
([`LocShape.ts`](../../289server/webclient/src/dash3d/LocShape.ts)):

| Shapes | Layer |
|---|---|
| 0-3 | Wall |
| 4-8 | Wall decoration |
| 9-21 | Ground (scenery, including shapes 10 and 11, the centrepieces) |
| 22 | Ground decoration |

## Client-to-Server Opcodes

There are 82 client opcodes, and this table is complete. Sending any other opcode makes the
server close the socket. "Handled" opcodes have a decoder and handler. "Ignored" opcodes are
valid (the server reads their declared bytes and discards them), so a headless client does not
need to send them.

| Op | Name | Size | Engine |
|---:|---|---:|---|
| 4 | `OPOBJ2` | 6 | handled |
| 10 | `OPLOC1` | 6 | handled |
| 13 | `OPPLAYER3` | 2 | handled |
| 16 | `OPPLAYERU` | 8 | handled |
| 21 | `OPNPC2` | 2 | handled |
| 22 | `OPOBJ5` | 6 | handled |
| 27 | `IDK_SAVEDESIGN` | 13 | handled |
| 30 | `OPNPC4` | 2 | handled |
| 34 | `CLIENT_CHEAT` | -1 | handled |
| 40 | `OPHELD3` | 6 | handled |
| 44 | `INV_BUTTON1` | 6 | handled |
| 45 | `OPLOC2` | 6 | handled |
| 46 | `ANTICHEAT_OPLOGIC5` | 1 | ignored |
| 49 | `ANTICHEAT_OPLOGIC4` | 1 | ignored |
| 51 | `OPPLAYER2` | 2 | handled |
| 53 | `OPLOC4` | 6 | handled |
| 55 | `OPOBJU` | 12 | handled |
| 67 | `MOVE_OPCLICK` | -1 | handled |
| 69 | `OPPLAYER5` | 2 | handled |
| 73 | `ANTICHEAT_OPLOGIC6` | 2 | ignored |
| 76 | `OPHELD1` | 6 | handled |
| 79 | `OPHELD5` | 6 | handled |
| 81 | `ANTICHEAT_OPLOGIC2` | 2 | ignored |
| 85 | `ANTICHEAT_CYCLELOGIC5` | 0 | ignored |
| 86 | `IF_BUTTON` | 2 | handled |
| 88 | `ANTICHEAT_OPLOGIC9` | 3 | ignored |
| 93 | `CLOSE_MODAL` | 0 | handled |
| 94 | `REPORT_ABUSE` (webclient `SEND_SNAPSHOT`) | 10 | handled |
| 97 | `OPOBJ1` | 6 | handled |
| 107 | `MESSAGE_PRIVATE` | -1 | handled |
| 108 | `OPNPCT` | 4 | handled |
| 110 | `OPOBJ3` | 6 | handled |
| 111 | `INV_BUTTON2` | 6 | handled |
| 112 | `OPHELDT` | 8 | handled |
| 122 | `ANTICHEAT_OPLOGIC3` | 4 | ignored |
| 124 | `INV_BUTTON3` | 6 | handled |
| 125 | `ANTICHEAT_CYCLELOGIC3` | 1 | ignored |
| 126 | `OPLOC5` | 6 | handled |
| 130 | `ANTICHEAT_CYCLELOGIC1` | -1 | ignored |
| 133 | `ANTICHEAT_OPLOGIC7` | 4 | ignored |
| 137 | `ANTICHEAT_CYCLELOGIC4` | 1 | ignored |
| 138 | `OPPLAYERT` | 4 | handled |
| 145 | `IDLE_TIMER` | 0 | handled |
| 146 | `TUT_CLICKSIDE` | 1 | handled |
| 147 | `OPOBJ4` | 6 | handled |
| 149 | `EVENT_APPLET_FOCUS` | 1 | handled |
| 154 | `ANTICHEAT_CYCLELOGIC2` | -1 | ignored |
| 156 | `MESSAGE_PUBLIC` | -1 | handled |
| 160 | `OPNPCU` | 8 | handled |
| 161 | `CHAT_SETMODE` | 3 | handled |
| 166 | `RESUME_PAUSEBUTTON` | 2 | handled |
| 168 | `ANTICHEAT_OPLOGIC8` | 1 | ignored |
| 177 | `OPHELD2` | 6 | handled |
| 178 | `OPNPC3` | 2 | handled |
| 180 | `RESUME_P_COUNTDIALOG` | 4 | handled |
| 181 | `NO_TIMEOUT` | 0 | ignored (still refreshes liveness) |
| 184 | `OPLOCU` | 12 | handled |
| 189 | `OPPLAYER4` | 2 | handled |
| 191 | `OPHELD4` | 6 | handled |
| 192 | `IGNORELIST_ADD` | 8 | handled |
| 193 | `EVENT_CAMERA_POSITION` | 4 | handled |
| 195 | `ANTICHEAT_OPLOGIC1` | 4 | ignored |
| 196 | `OPLOC3` | 6 | handled |
| 200 | `OPHELDU` | 12 | handled |
| 203 | `FRIENDLIST_DEL` | 8 | handled |
| 214 | `MAP_BUILD_COMPLETE` | 0 | ignored |
| 218 | `OPLOCT` | 8 | handled |
| 220 | `OPPLAYER1` | 2 | handled |
| 224 | `EVENT_MOUSE_CLICK` | 4 | handled |
| 227 | `INV_BUTTON5` | 6 | handled |
| 229 | `EVENT_MOUSE_MOVE` | -1 | handled |
| 232 | `ANTICHEAT_CYCLELOGIC7` | 0 | ignored |
| 234 | `MOVE_GAMECLICK` | -1 | handled |
| 235 | `FRIENDLIST_ADD` | 8 | handled |
| 236 | `MOVE_MINIMAPCLICK` | -1 | handled |
| 241 | `OPOBJT` | 8 | handled |
| 247 | `OPNPC5` | 2 | handled |
| 248 | `INV_BUTTON4` | 6 | handled |
| 251 | `IGNORELIST_DEL` | 8 | handled |
| 252 | `OPNPC1` | 2 | handled |
| 253 | `INV_BUTTOND` | 7 | handled |
| 255 | `ANTICHEAT_CYCLELOGIC6` | 1 | ignored |

## Client-to-Server Payloads

Layouts are given as the webclient writes them and the engine decoders read them
([`codec/`](../../289server/engine/src/network/game/client/codec)). Variable-length (`-1`)
packets carry a `u8` length after the opcode; compute it from the bytes actually written.

### Movement

`MOVE_GAMECLICK` (234), `MOVE_MINIMAPCLICK` (236), and `MOVE_OPCLICK` (67) share one layout:

| Field | Type | Notes |
|---|---|---|
| `run` | `u8` | `1` if Ctrl was held (run this path). Must be 0 or 1. The server ignores it when run energy is below 1%. |
| `startX` | `u16` | Absolute tile of the first waypoint. |
| `startZ` | `u16` | |
| waypoints | `(n - 1)` x (`s8 dx`, `s8 dz`) | Each later waypoint as an offset from (`startX`, `startZ`), not from the previous waypoint. |
| trailer | 14 bytes | `MOVE_MINIMAPCLICK` only; see below. |

The payload length is `2n + 3` (`2n + 17` for the minimap variant), where `n` is the waypoint
count including the start. The engine uses at most 25 waypoints. The webclient's path comes
from a breadth-first search over the cache collision map. Waypoints are the turning points of
the route, starting with the first turn after the player's tile and ending at the destination.
The webclient truncates routes with more than 25 turns, so the last waypoint is then not the
destination.

The `MOVE_MINIMAPCLICK` trailer is ignored by the server. The webclient sends `u8 mouseX`,
`u8 mouseY`, `u16 cameraYaw`, `u8 57`, `u8 minimapAngle`, `u8 minimapZoom`, `u8 89`,
`u16 sceneX`, `u16 sceneZ`, `u8 tryNearest`, and `u8 63`. Any 14 bytes are accepted.

Server behavior ([`MoveClickHandler.ts`](../../289server/engine/src/network/game/client/handler/MoveClickHandler.ts)):

- The start waypoint must be within 104 tiles of the player, or the request is rejected with
  `UNSET_MAP_FLAG`.
- With `NODE_CLIENT_ROUTEFINDER` enabled (the default, `clientRoutefinder: true` in
  [`WorldConfig.ts`](../../289server/engine/src/util/WorldConfig.ts)), the server queues the
  client's waypoints and walks toward each one in a straight line (naive movement). It does not
  route around obstacles, so a client without collision data must send waypoints that avoid
  walls itself. With the option disabled, the server runs its own pathfinder to the last
  waypoint.
- `MOVE_GAMECLICK` and `MOVE_MINIMAPCLICK` cancel the current interaction. `MOVE_OPCLICK` does
  not, because it is always followed by an `OP*` packet that sets the interaction.

For any interaction with a loc, ground object, NPC, or player, the webclient sends
`MOVE_OPCLICK` with a path toward the target first, then the `OP*` packet, in the same flush.
For NPC and player targets the server also re-paths toward the moving target each tick. For locs
and objects the client-supplied path is what the player walks.

### Entity and Item Operations

Op number `N` (1-5) is the right-click option index from the target's definition (`op` for
locs, NPCs, and ground objects; `iop` for held items; `SET_PLAYER_OP` for players). Coordinates
are absolute tiles. NPC and player indices are those from `NPC_INFO` and `PLAYER_INFO`.

| Ops | Names | Payload |
|---|---|---|
| 97, 4, 110, 147, 22 | `OPOBJ1`-`OPOBJ5` | `u16 x`, `u16 z`, `u16 obj` |
| 241 | `OPOBJT` | `u16 x`, `u16 z`, `u16 obj`, `u16 spellCom` |
| 55 | `OPOBJU` | `u16 x`, `u16 z`, `u16 obj`, `u16 useObj`, `u16 useSlot`, `u16 useCom` |
| 252, 21, 178, 30, 247 | `OPNPC1`-`OPNPC5` | `u16 npcIndex` |
| 108 | `OPNPCT` | `u16 npcIndex`, `u16 spellCom` |
| 160 | `OPNPCU` | `u16 npcIndex`, `u16 useObj`, `u16 useSlot`, `u16 useCom` |
| 10, 45, 196, 53, 126 | `OPLOC1`-`OPLOC5` | `u16 x`, `u16 z`, `u16 loc` |
| 218 | `OPLOCT` | `u16 x`, `u16 z`, `u16 loc`, `u16 spellCom` |
| 184 | `OPLOCU` | `u16 x`, `u16 z`, `u16 loc`, `u16 useObj`, `u16 useSlot`, `u16 useCom` |
| 220, 51, 13, 189, 69 | `OPPLAYER1`-`OPPLAYER5` | `u16 playerIndex` |
| 138 | `OPPLAYERT` | `u16 playerIndex`, `u16 spellCom` |
| 16 | `OPPLAYERU` | `u16 playerIndex`, `u16 useObj`, `u16 useSlot`, `u16 useCom` |
| 76, 177, 40, 191, 79 | `OPHELD1`-`OPHELD5` | `u16 obj`, `u16 slot`, `u16 com` |
| 112 | `OPHELDT` | `u16 obj`, `u16 slot`, `u16 com`, `u16 spellCom` |
| 200 | `OPHELDU` | `u16 obj`, `u16 slot`, `u16 com`, `u16 useObj`, `u16 useSlot`, `u16 useCom` |

Field meanings:

- `obj`, `slot`, `com` identify an item by object ID, slot index, and the inventory component
  that displays it.
- `use*` describe the item selected with "Use" (the item being used on the target).
- `spellCom` is the component of the selected spell or targeting button ("Cast X on").
- `loc` is the loc type ID at that tile (the webclient extracts it from the scene typecode).

The webclient's accept-trade and accept-duel chat options send `OPPLAYER4` and `OPPLAYER1` for
the requesting player. `OPPLAYER3` is "follow".

### Interface Buttons and Dialogs

| Op | Name | Payload | Notes |
|---:|---|---|---|
| 86 | `IF_BUTTON` | `u16 com` | Clicks an ordinary button, toggle, or select button. Also continues dialogues registered as resume buttons, and is the logout button. |
| 44, 111, 124, 248, 227 | `INV_BUTTON1`-`INV_BUTTON5` | `u16 obj`, `u16 slot`, `u16 com` | Option `N` on an item shown in an interface inventory (for example, bank or shop actions). |
| 253 | `INV_BUTTOND` | `u16 com`, `u16 fromSlot`, `u16 toSlot`, `u8 mode` | Drag an item between slots. `mode` 0 swaps and 1 inserts (bank insert mode). |
| 166 | `RESUME_PAUSEBUTTON` | `u16 com` | "Click here to continue" in a chat dialogue. The engine ignores the component and resumes the script paused on a pause button. The webclient sends it once per opened dialogue. |
| 180 | `RESUME_P_COUNTDIALOG` | `s32 value` | Answer to `P_COUNTDIALOG`. |
| 93 | `CLOSE_MODAL` | - | Closes open modals (the webclient also clears them locally). |
| 146 | `TUT_CLICKSIDE` | `u8 tab` | The player opened the tab flashed by `TUT_FLASH`. |
| 27 | `IDK_SAVEDESIGN` | `u8 gender`, `7 x u8 kit`, `5 x u8 colour` | Character design. `gender` 0 is male and 1 female. `kit` value 255 means none. |

### Chat and Social

| Op | Name | Payload | Notes |
|---:|---|---|---|
| 156 | `MESSAGE_PUBLIC` | `u8 colour`, `u8 effect`, `wordpack text` | Public chat. `colour` 0-11 and `effect` 0-5, or the message is rejected. At most 100 packed bytes. One message per tick (`socialProtect`). |
| 107 | `MESSAGE_PRIVATE` | `name37 to`, `wordpack text` | Private message. |
| 34 | `CLIENT_CHEAT` | `jstr command` | `::command` text without the `::`, at most 80 characters. What runs depends on staff level and debug mode. |
| 161 | `CHAT_SETMODE` | `u8 public`, `u8 private`, `u8 trade` | Public is 0-3; private and trade are 0-2. |
| 235 | `FRIENDLIST_ADD` | `name37` | |
| 203 | `FRIENDLIST_DEL` | `name37` | |
| 192 | `IGNORELIST_ADD` | `name37` | |
| 251 | `IGNORELIST_DEL` | `name37` | |
| 94 | `REPORT_ABUSE` | `name37 offender`, `u8 rule`, `u8 mute` | `rule` is the report-rule index (0-11); `mute` 1 requests a moderator mute. |

The webclient strips typed prefixes from the text and sends them as the two numbers. Colour:
`yellow:` 0 (default), `red:` 1, `green:` 2, `cyan:` 3, `purple:` 4, `white:` 5, `flash1:`-`flash3:`
6-8, `glow1:`-`glow3:` 9-11. Effect: none 0, `wave:` 1, `wave2:` 2, `shake:` 3, `scroll:` 4,
`slide:` 5. The colour prefix comes first.

### Liveness and Telemetry

| Op | Name | Payload | Notes |
|---:|---|---|---|
| 181 | `NO_TIMEOUT` | - | Keepalive; see [Keepalive and Idle Logout](#keepalive-and-idle-logout). |
| 145 | `IDLE_TIMER` | - | Requests idle logout. A bot should not send it. |
| 214 | `MAP_BUILD_COMPLETE` | - | The webclient sends it after building a scene. The engine ignores it. |
| 224 | `EVENT_MOUSE_CLICK` | `s32 info` | `(delta << 20) + (button << 19) + (y * 765 + x)`. `delta` is ms since the previous click divided by 50 (max 4095); `button` 1 is right-click. |
| 229 | `EVENT_MOUSE_MOVE` | packed samples | Each sample is 2, 3, or 4 bytes: `u16 (delta << 12) + ((dx + 32) << 6) + (dy + 32)`; `u24 0x800000 + (delta << 19) + pos`; or `s32 0xc0000000 + (delta << 19) + pos`, where `pos = y * 765 + x` or `0x7ffff` (outside the window). |
| 193 | `EVENT_CAMERA_POSITION` | `u16 pitch`, `u16 yaw` | |
| 149 | `EVENT_APPLET_FOCUS` | `u8 focused` | |

The engine only records the `EVENT_*` packets when input tracking has been turned on for the
player ([`InputTracking.ts`](../../289server/engine/src/engine/entity/tracking/InputTracking.ts)).
Nothing in the engine requires them. A headless client may omit them all.

### Anticheat Packets

The webclient sends these from counters and timers; the engine has no decoder for them. Sizes
and the webclient's constant payloads, for completeness:

| Op | Name | Payload |
|---:|---|---|
| 195 | `ANTICHEAT_OPLOGIC1` | `s32 0` |
| 81 | `ANTICHEAT_OPLOGIC2` | `u16 37954` |
| 122 | `ANTICHEAT_OPLOGIC3` | `s32 0` |
| 49 | `ANTICHEAT_OPLOGIC4` | `u8 131` |
| 46 | `ANTICHEAT_OPLOGIC5` | `u8 154` |
| 73 | `ANTICHEAT_OPLOGIC6` | `u16 6118` |
| 133 | `ANTICHEAT_OPLOGIC7` | `s32 0` |
| 168 | `ANTICHEAT_OPLOGIC8` | `u8 19` |
| 88 | `ANTICHEAT_OPLOGIC9` | `u24 13018169` |
| 130, 154 | `ANTICHEAT_CYCLELOGIC1`, `2` | `u8` length, then random filler |
| 125, 137, 255 | `ANTICHEAT_CYCLELOGIC3`, `4`, `6` | 1 byte |
| 85, 232 | `ANTICHEAT_CYCLELOGIC5`, `7` | none |

## Server-Side Acceptance Rules

### Per-Tick Decode Limits

[`ClientGameProtCategory.ts`](../../289server/engine/src/network/game/client/ClientGameProtCategory.ts)
caps how many packets the server decodes per player per tick:

| Category | Limit | Packets |
|---|---:|---|
| User events | 5 successful | Every handled opcode except those listed in the next row. A user event whose handler rejects it counts toward the client-event limit instead. |
| Client events | 20 | `EVENT_*`, `IDLE_TIMER`, and rejected user events. |

Decoding stops as soon as either limit is reached, and the remaining bytes wait for the next
tick. Ignored opcodes (no decoder) count toward neither limit. Practically, send at most about
five actions per 600 ms tick; extra actions are delayed, not dropped.

### Common Rejections

Rejected packets are consumed and produce no reply, except where `UNSET_MAP_FLAG` is noted.
Most action handlers reject when:

- The player is delayed (busy with a scripted delay). Movement and NPC ops send
  `UNSET_MAP_FLAG`.
- An `OPLOC*` or `OPOBJ*` tile is more than 52 tiles, on either axis, from the player's origin
  (the player's tile when the last `REBUILD_NORMAL` was sent). The packet is also rejected if no
  loc or object with that ID is at that tile on the player's level and visible to the player,
  or if the option is undefined or `hidden`.
- An `OPNPC*` or `OPPLAYER*` target index does not exist, or is not in this player's tracked
  list. The server checks the same list that `NPC_INFO` and `PLAYER_INFO` maintain.
- An `OPHELD*`, `INV_BUTTON*`, or `INV_BUTTOND` component is not visible, has no transmitted
  inventory, or the slot does not hold that object. `OPHELD*` also requires the component to be
  operable and the item option to be defined.
- An `IF_BUTTON` component has no button type or is not currently visible.
- A `RESUME_PAUSEBUTTON` or `RESUME_P_COUNTDIALOG` arrives when no script is waiting for it.

An unknown opcode closes the socket. So does a client `-2` length above 1600.

## Encodings

### Bit Access

Bit streams are MSB-first. Bit position `p` is bit `7 - (p & 7)` of byte `p >> 3`. A read of
`n` bits returns them as an unsigned integer, the first bit read being the most significant.
After a bit section, the byte position becomes `(bitPos + 7) >> 3`. Equivalent reader:

```text
value = 0
repeat n times:
    bit = (data[bitPos >> 3] >> (7 - (bitPos & 7))) & 1
    value = (value << 1) | bit
    bitPos += 1
```

### Base-37 Names

`name37` packs a name of up to 12 characters into a `u64`
([`JString.toUserhash`](../../289server/webclient/src/datastruct/JString.ts)). Trim the name,
then for each of the first 12 characters: `value = value * 37 + code`, where `a`-`z` and
`A`-`Z` give 1-26, `0`-`9` give 27-36, and anything else (including space and `_`) gives 0.
Finally divide by 37 while the value is a nonzero multiple of 37, which strips trailing
separators. To decode, repeatedly take `value % 37` as the next character from the right, using
the alphabet `_abcdefghijklmnopqrstuvwxyz0123456789`. For display, replace `_` with a space and
capitalise the first letter of each word. Values of `37^12` or more, or multiples of 37, are
invalid.

### WordPack Text

Chat text is packed into 4-bit nibbles, high nibble first
([`WordPack.ts`](../../289server/engine/src/wordenc/WordPack.ts)). The character table has 61
entries:

```text
index  0-12 :  space e t a o i h n s r d l u
index 13-26 :  m w c y f g p b v k x j q z
index 27-36 :  0 1 2 3 4 5 6 7 8 9
index 37-60 :  space ! ? . , : ; ( ) - & * \ ' @ # + = £ $ % " [ ]
```

To pack, lowercase the text, truncate it to 80 characters, and map each character to its first
table index; an unknown character maps to 0 (space). An index below 13 is one nibble. An index
`i` of 13 or more is two nibbles, the high and low halves of `i + 195`; the first of these is
always `0xd`-`0xf`. If the nibble count is odd, pad the final low nibble with 0.

To unpack `length` bytes, read nibbles in order. A nibble below 13 is that table index. A nibble
of 13 or more combines with the next nibble into `((first << 4) + second) - 195`. Stop at 80
characters. A padding nibble decodes as a trailing space. Both sides then apply sentence case
(capitalise the first letter and any letter after `.` or `!`). The server filters text
(`WordEnc.filter`) before repacking it for other players.

### ISAAC

The opcode cipher is standard ISAAC (Bob Jenkins) on 32-bit words
([`Isaac.ts`](../../289server/webclient/src/io/Isaac.ts)). The four seed words fill the first
four of the 256 seed slots, and the rest are zero. Initialisation mixes with the golden ratio
`0x9e3779b9` and runs one generation round. Outputs are taken from the result array from index
255 down to 0, and a new round runs when it is exhausted. The headless client's
[`isaac.cpp`](../../headless-client/src/isaac.cpp) matches this and is pinned by a zero-seed
test vector.

## Headless Client Implementation Notes

These notes are for extending [`headless-client/src/protocol.cpp`](../../headless-client/src/protocol.cpp),
which today frames server packets and discards their payloads.

### Known Gap

`Protocol::server_packet_length` has no entry for opcode **60** (`OBJ_ADD`, size 5). The engine
sends standalone `OBJ_ADD` packets whenever a zone containing a dropped item comes into view, so
the client currently fails with "unknown server opcode 60" in any area with ground items. Add it
first. All other 68 opcodes match the engine and webclient tables. Consider replacing the switch
with a 256-entry size table, with a sentinel for "never sent", mirrored from
[`ServerProtSizes`](../../289server/webclient/src/io/ServerProt.ts) and covered by a test that
checks every opcode in the table above.

### Suggested Structure

1. **Framing** (exists): decrypt the opcode, look up the size, and wait for the whole frame. Hand
   `(opcode, payload span)` to a dispatcher instead of discarding it.
2. **Dispatcher**: one decoder per opcode, grouped as in this document. Every decoder must
   consume exactly the declared payload. For variable packets, check that the read position ends
   at the payload length.
3. **State model**: build-area base, local player index (`UPDATE_PID`), local position and level,
   tracked player and NPC lists, per-index entity state and appearance, inventories keyed by
   component, varps, stats, run energy and weight, ground items and loc changes keyed by absolute
   tile, modal and tab state, friends and ignores, and recent messages.
4. **Entity info**: a bounds-checked MSB-first bit reader. Keep the list-order rules exactly;
   any divergence desynchronises every later `PLAYER_INFO` and `NPC_INFO`.
5. **Zones**: one sub-packet decoder shared by the standalone and enclosed paths, driven by the
   fixed sizes above.
6. **Actions**: builders for the client packets above. Movement needs waypoints that avoid
   obstacles, because the default server configuration does not pathfind for the client.
7. **Reconnect**: opcode `18`, status `15`, and fresh ISAAC streams. Entity lists are emptied
   by the server's first info packets, as described in [Reconnect](#reconnect).

### Decode Priority for a Bot

Every packet must be framed and consumed; this is only the order in which to decode payloads.

| Priority | Packets |
|---|---|
| Essential | `REBUILD_NORMAL`, `UPDATE_PID`, `PLAYER_INFO`, `NPC_INFO`, `UPDATE_INV_FULL`, `UPDATE_INV_PARTIAL`, `UPDATE_INV_STOP_TRANSMIT`, `UPDATE_STAT`, `VARP_SMALL`, `VARP_LARGE`, the zone framing packets and all zone sub-packets, `MESSAGE_GAME`, `LOGOUT` |
| Interaction | `IF_OPENMAIN`, `IF_OPENSIDE`, `IF_OPENCHAT`, `IF_OPENMAIN_SIDE`, `IF_CLOSE`, `IF_SETTAB`, `IF_SETTEXT`, `IF_SETHIDE`, `P_COUNTDIALOG`, `UPDATE_RUNENERGY`, `UPDATE_RUNWEIGHT`, `SET_PLAYER_OP`, `HINT_ARROW`, `UNSET_MAP_FLAG`, `UPDATE_REBOOT_TIMER` |
| Social | `MESSAGE_PRIVATE`, `UPDATE_FRIENDLIST`, `UPDATE_IGNORELIST`, `FRIENDLIST_LOADED`, `CHAT_FILTER_SETTINGS` |
| Render-only (consume and ignore) | Camera, audio, `IF_SETOBJECT`, `IF_SETMODEL`, `IF_SETANIM`, `IF_SETPLAYERHEAD`, `IF_SETNPCHEAD`, `IF_SETCOLOUR`, `IF_SETPOSITION`, `IF_SETSCROLLPOS`, `IF_OPENOVERLAY`, `IF_SETTAB_ACTIVE`, `TUT_OPEN`, `TUT_FLASH`, `MINIMAP_TOGGLE`, `SET_MULTIWAY`, `RESET_ANIMS`, `RESET_CLIENT_VARCACHE`, `LAST_LOGIN_INFO` |

### Testing

- Build fixtures from the engine's encoders: each server packet's bytes are produced by one
  `encode` method in [`server/codec/`](../../289server/engine/src/network/game/server/codec) (or
  [`rsbuf/info.ts`](../../289server/engine/src/network/rsbuf/info.ts) for entity info), so every
  decoder can be tested byte for byte without a running server.
- For entity info, cover: local walk, run, and teleport; tracked-list removal by a short
  `count`; removal by type 3; new entries with negative `dx`/`dz`; a packet with no extended
  blocks (no terminator); a player mask above `0xff`; and an appearance with an NPC transform.
- For zones, cover an `UPDATE_ZONE_PARTIAL_ENCLOSED` holding several sub-opcodes, and a
  standalone `OBJ_ADD` after `UPDATE_ZONE_PARTIAL_FOLLOWS`.
- The existing scripted-server tests (RSA exponent 1, so the test server can read the ISAAC
  seed) can feed encrypted frames of any of these packets through the full state machine.

## Source Map

| Topic | Engine | Webclient |
|---|---|---|
| Login | [`World.onClientData`, `processLogins`](../../289server/engine/src/engine/World.ts) | [`Client.login`](../../289server/webclient/src/client/Client.ts) |
| Server opcode table | [`ServerGameProt.ts`](../../289server/engine/src/network/game/server/ServerGameProt.ts), [`ServerGameZoneProt.ts`](../../289server/engine/src/network/game/server/ServerGameZoneProt.ts) | [`ServerProt.ts`](../../289server/webclient/src/io/ServerProt.ts) |
| Server payloads | [`server/codec/`](../../289server/engine/src/network/game/server/codec) | `Client.tcpIn`, `Client.zonePacket` in [`Client.ts`](../../289server/webclient/src/client/Client.ts) |
| Player and NPC info | [`rsbuf/info.ts`](../../289server/engine/src/network/rsbuf/info.ts), [`rsbuf/messages.ts`](../../289server/engine/src/network/rsbuf/messages.ts), [`rsbuf/prot.ts`](../../289server/engine/src/network/rsbuf/prot.ts) | `Client.getPlayerPos`, `Client.getNpcPos`; [`ClientPlayer.ts`](../../289server/webclient/src/dash3d/ClientPlayer.ts), [`ClientNpc.ts`](../../289server/webclient/src/dash3d/ClientNpc.ts) |
| Appearance | `Player.generateAppearance` in [`Player.ts`](../../289server/engine/src/engine/entity/Player.ts) | `ClientPlayer.setAppearance` |
| Zones | [`Zone.ts`](../../289server/engine/src/engine/zone/Zone.ts), [`BuildArea.ts`](../../289server/engine/src/engine/entity/BuildArea.ts) | `Client.zonePacket`, [`LocShape.ts`](../../289server/webclient/src/dash3d/LocShape.ts) |
| Client opcode table | [`ClientGameProt.ts`](../../289server/engine/src/network/game/client/ClientGameProt.ts), [`ClientGameProtRepository.ts`](../../289server/engine/src/network/game/client/ClientGameProtRepository.ts) | [`ClientProt.ts`](../../289server/webclient/src/io/ClientProt.ts) |
| Client payloads | [`client/codec/`](../../289server/engine/src/network/game/client/codec), [`client/handler/`](../../289server/engine/src/network/game/client/handler) | `Client.doAction`, `Client.tryMove`, `Client.interactWithLoc` |
| Per-tick output | [`NetworkPlayer.ts`](../../289server/engine/src/engine/entity/NetworkPlayer.ts), `World.processClientsOut` | - |
| Primitives | [`io/Packet.ts`](../../289server/engine/src/io/Packet.ts) | [`io/Packet.ts`](../../289server/webclient/src/io/Packet.ts), [`io/Isaac.ts`](../../289server/webclient/src/io/Isaac.ts) |
| Text and names | [`wordenc/WordPack.ts`](../../289server/engine/src/wordenc/WordPack.ts) | [`datastruct/JString.ts`](../../289server/webclient/src/datastruct/JString.ts) |
