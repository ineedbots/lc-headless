# Revision 274 TCP Protocol

This page is the wire reference for this repository's revision-274 engine
([`274server/engine`](../../274server/engine/src)) and its webclient
([`274server/webclient`](../../274server/webclient/src)), written as the differences from
[tcp-protocol-289.md](tcp-protocol-289.md). Anything this page doesn't mention is the same in both
revisions: the endpoints, the login, the framing, ISAAC, the session lifecycle, entity info, the zone
sub-packets, and every payload not listed below. 274 has exactly 289's packets at the same lengths, but
almost every opcode is different, so both opcode tables are given whole.

Every layout here was read from the 274 engine's encoders and decoders and checked against its
webclient. The two engines' `network/` folders differ only in the opcode tables, the two inventory
encoders, and two handlers' server-side checks; their `rsbuf/` entity-info encoders are byte-identical.
[Revision274Design.md](Revision274Design.md) is how this client supports 274.

## Contents

1. [Login](#login)
2. [Server-to-Client Opcodes](#server-to-client-opcodes)
3. [Server-to-Client Payloads](#server-to-client-payloads)
4. [Client-to-Server Opcodes](#client-to-server-opcodes)
5. [Client-to-Server Payloads](#client-to-server-payloads)
6. [The Cache](#the-cache)
7. [Source Map](#source-map)

## Login

As in 289, with `274` in the revision field: `u8 0xFF`, then `u16 274`. The server answers `6` when the
revision isn't its `ENGINE_REVISION` (274 by default) or the CRCs aren't its own. Success is `2`, then the
staff level and the mouse-tracking flag, and `21` is the hop timer, as in 289.

## Server-to-Client Opcodes

Every length is 289's. The zone sub-packets are the same ten, with 274's opcodes: `48`, `52`, `81`, `85`,
`95`, `107`, `138`, `173`, `176` and `219`. The webclient names five packets differently: `IF_SETICON` and
`IF_SHOWICON` are `IF_SETTAB` and `IF_SETTAB_ACTIVE`, `P_LOCMERGE` is `LOC_MERGE`, and `VARP_SYNC` is
`RESET_CLIENT_VARCACHE`.

| Opcode | Name | Length | 289 opcode |
|---:|---|---|---:|
| `3` | `UPDATE_IGNORELIST` | var short | 47 |
| `10` | `IF_SETHIDE` | 3 | 138 |
| `15` | `MIDI_JINGLE` | 4 | 29 |
| `16` | `IF_OPENSIDE` | 2 | 252 |
| `17` | `SET_PLAYER_OP` | var byte | 21 |
| `23` | `MIDI_SONG` | 2 | 187 |
| `28` | `IF_SETOBJECT` | 6 | 18 |
| `32` | `UPDATE_ZONE_PARTIAL_FOLLOWS` | 2 | 155 |
| `34` | `SYNTH_SOUND` | 5 | 177 |
| `44` | `IF_SETTEXT` | var short | 59 |
| `47` | `RESET_ANIMS` | 0 | 201 |
| `48` | `LOC_ANIM` | 4 | 106 |
| `52` | `OBJ_DEL` | 3 | 71 |
| `54` | `IF_SETSCROLLPOS` | 4 | 184 |
| `64` | `CAM_SHAKE` | 4 | 208 |
| `67` | `UPDATE_RUNWEIGHT` | 2 | 46 |
| `77` | `IF_SETPOSITION` | 6 | 79 |
| `81` | `OBJ_ADD` | 5 | 60 |
| `83` | `UPDATE_RUNENERGY` | 1 | 195 |
| `85` | `MAP_ANIM` | 6 | 233 |
| `88` | `LOGOUT` | 0 | 121 |
| `89` | `UPDATE_REBOOT_TIMER` | 2 | 204 |
| `90` | `TUT_FLASH` | 1 | 181 |
| `91` | `LAST_LOGIN_INFO` | 10 | 253 |
| `95` | `OBJ_COUNT` | 7 | 117 |
| `101` | `CAM_RESET` | 0 | 133 |
| `105` | `UPDATE_STAT` | 6 | 154 |
| `106` | `UPDATE_INV_FULL` | var short | 107 |
| `107` | `MAP_PROJANIM` | 15 | 87 |
| `114` | `CHAT_FILTER_SETTINGS` | 3 | 13 |
| `115` | `UNSET_MAP_FLAG` | 0 | 164 |
| `129` | `IF_SETMODEL` | 4 | 222 |
| `130` | `TUT_OPEN` | 2 | 12 |
| `133` | `UPDATE_PID` | 3 | 120 |
| `134` | `IF_SETANIM` | 4 | 211 |
| `138` | `LOC_ADD_CHANGE` | 4 | 90 |
| `142` | `IF_SETNPCHEAD` | 4 | 244 |
| `153` | `UPDATE_ZONE_FULL_FOLLOWS` | 2 | 144 |
| `156` | `HINT_ARROW` | 6 | 115 |
| `158` | `IF_OPENMAIN_SIDE` | 4 | 55 |
| `161` | `MESSAGE_GAME` | var byte | 196 |
| `166` | `IF_OPENCHAT` | 2 | 81 |
| `167` | `PLAYER_INFO` | var short | 188 |
| `171` | `IF_CLOSE` | 0 | 23 |
| `172` | `UPDATE_INV_PARTIAL` | var short | 76 |
| `173` | `LOC_DEL` | 2 | 194 |
| `176` | `LOC_MERGE` | 14 | 83 |
| `183` | `IF_SETCOLOUR` | 4 | 160 |
| `185` | `FRIENDLIST_LOADED` | 1 | 235 |
| `190` | `RESET_CLIENT_VARCACHE` | 0 | 172 |
| `192` | `IF_SETPLAYERHEAD` | 2 | 30 |
| `194` | `MINIMAP_TOGGLE` | 1 | 136 |
| `195` | `UPDATE_ZONE_PARTIAL_ENCLOSED` | var short | 112 |
| `197` | `NPC_INFO` | var short | 65 |
| `200` | `CAM_MOVETO` | 6 | 73 |
| `203` | `VARP_SMALL` | 3 | 75 |
| `207` | `SET_MULTIWAY` | 1 | 247 |
| `210` | `P_COUNTDIALOG` | 0 | 35 |
| `211` | `IF_OPENMAIN` | 2 | 119 |
| `215` | `IF_SETTAB` | 3 | 63 |
| `219` | `OBJ_REVEAL` | 7 | 176 |
| `227` | `UPDATE_INV_STOP_TRANSMIT` | 2 | 28 |
| `231` | `REBUILD_NORMAL` | 4 | 219 |
| `233` | `CAM_LOOKAT` | 6 | 82 |
| `235` | `MESSAGE_PRIVATE` | var byte | 243 |
| `240` | `IF_OPENOVERLAY` | 2 | 127 |
| `241` | `IF_SETTAB_ACTIVE` | 1 | 189 |
| `245` | `VARP_LARGE` | 6 | 97 |
| `247` | `UPDATE_FRIENDLIST` | 9 | 168 |

None keeps its 289 opcode.

## Server-to-Client Payloads

Only the payloads that differ from 289's are listed. Both take 225's field widths.

| Packet | 274 | 289 |
|---|---|---|
| `UPDATE_INV_FULL` | `u16 com`, `u8 size`, then `size` items; the size runs to the last used slot | `u16 size` |
| `UPDATE_INV_PARTIAL` | `u16 com`, then per entry `u8 slot` and an item | `smart slot` |

An item is `u16 id + 1` (0 for an empty slot), then `u8 count`, or `255` and `s32 count`, as in 289. A
byte is enough on 274: its bank holds 240 slots, where 289's holds 288. Slots past the size are cleared,
as in 289; 225's size covers the whole capacity instead.

A player's public chat effect, in the CHAT block, is numbered as 274 sends it: `0` none, `1` wave and
`2` scroll. 289 numbers scroll `4`.

## Client-to-Server Opcodes

Every length is 289's. The webclient calls `REPORT_ABUSE` `SEND_SNAPSHOT`.

| Opcode | Name | Length | 289 opcode |
|---:|---|---|---:|
| `0` | `ANTICHEAT_OPLOGIC8` | 1 | 168 |
| `2` | `OPHELD2` | 6 | 177 |
| `9` | `IF_BUTTON` | 2 | 86 |
| `12` | `ANTICHEAT_CYCLELOGIC1` | var byte | 130 |
| `13` | `FRIENDLIST_ADD` | 8 | 235 |
| `20` | `EVENT_MOUSE_CLICK` | 4 | 224 |
| `24` | `ANTICHEAT_OPLOGIC9` | 3 | 88 |
| `25` | `ANTICHEAT_OPLOGIC7` | 4 | 133 |
| `36` | `OPPLAYERU` | 8 | 16 |
| `39` | `OPOBJU` | 12 | 55 |
| `41` | `ANTICHEAT_OPLOGIC3` | 4 | 122 |
| `42` | `OPHELD5` | 6 | 79 |
| `46` | `INV_BUTTON5` | 6 | 227 |
| `51` | `CLOSE_MODAL` | 0 | 93 |
| `52` | `ANTICHEAT_CYCLELOGIC3` | 1 | 125 |
| `53` | `EVENT_CAMERA_POSITION` | 4 | 193 |
| `60` | `OPLOCU` | 12 | 184 |
| `62` | `OPOBJ4` | 6 | 147 |
| `72` | `RESUME_PAUSEBUTTON` | 2 | 166 |
| `73` | `EVENT_APPLET_FOCUS` | 1 | 149 |
| `74` | `INV_BUTTON1` | 6 | 44 |
| `80` | `ANTICHEAT_OPLOGIC4` | 1 | 49 |
| `82` | `INV_BUTTON2` | 6 | 111 |
| `86` | `MOVE_MINIMAPCLICK` | var byte | 236 |
| `89` | `ANTICHEAT_CYCLELOGIC7` | 0 | 232 |
| `91` | `OPOBJT` | 8 | 241 |
| `93` | `INV_BUTTOND` | 7 | 253 |
| `94` | `TUT_CLICKSIDE` | 1 | 146 |
| `98` | `OPPLAYER4` | 2 | 189 |
| `100` | `ANTICHEAT_CYCLELOGIC5` | 0 | 85 |
| `101` | `IGNORELIST_DEL` | 8 | 251 |
| `102` | `RESUME_P_COUNTDIALOG` | 4 | 180 |
| `103` | `OPLOC2` | 6 | 45 |
| `106` | `FRIENDLIST_DEL` | 8 | 203 |
| `108` | `OPOBJ3` | 6 | 110 |
| `109` | `OPPLAYER1` | 2 | 220 |
| `117` | `OPOBJ5` | 6 | 22 |
| `120` | `NO_TIMEOUT` | 0 | 181 |
| `123` | `OPHELD3` | 6 | 40 |
| `125` | `IDK_SAVEDESIGN` | 13 | 27 |
| `127` | `OPLOC5` | 6 | 126 |
| `135` | `OPHELDT` | 8 | 112 |
| `136` | `OPHELDU` | 12 | 200 |
| `137` | `REPORT_ABUSE` | 10 | 94 |
| `138` | `MOVE_OPCLICK` | var byte | 67 |
| `139` | `MESSAGE_PRIVATE` | var byte | 107 |
| `147` | `OPNPC4` | 2 | 30 |
| `149` | `ANTICHEAT_CYCLELOGIC2` | var byte | 154 |
| `150` | `OPNPCU` | 8 | 160 |
| `154` | `CHAT_SETMODE` | 3 | 161 |
| `157` | `OPLOC4` | 6 | 53 |
| `166` | `OPPLAYER2` | 2 | 51 |
| `169` | `OPOBJ2` | 6 | 4 |
| `174` | `OPPLAYER5` | 2 | 69 |
| `179` | `INV_BUTTON4` | 6 | 248 |
| `181` | `OPNPCT` | 4 | 108 |
| `185` | `OPHELD1` | 6 | 76 |
| `187` | `OPLOC3` | 6 | 196 |
| `188` | `ANTICHEAT_CYCLELOGIC6` | 1 | 255 |
| `189` | `OPNPC5` | 2 | 247 |
| `196` | `OPPLAYER3` | 2 | 13 |
| `201` | `ANTICHEAT_OPLOGIC2` | 2 | 81 |
| `207` | `MOVE_GAMECLICK` | var byte | 234 |
| `209` | `IDLE_TIMER` | 0 | 145 |
| `213` | `OPLOCT` | 8 | 218 |
| `214` | `MAP_BUILD_COMPLETE` | 0 | 214 |
| `215` | `OPLOC1` | 6 | 10 |
| `216` | `OPHELD4` | 6 | 191 |
| `219` | `ANTICHEAT_OPLOGIC1` | 4 | 195 |
| `222` | `EVENT_MOUSE_MOVE` | var byte | 229 |
| `223` | `OPNPC3` | 2 | 178 |
| `224` | `CLIENT_CHEAT` | var byte | 34 |
| `230` | `ANTICHEAT_CYCLELOGIC4` | 1 | 137 |
| `233` | `OPNPC2` | 2 | 21 |
| `235` | `ANTICHEAT_OPLOGIC5` | 1 | 46 |
| `236` | `OPNPC1` | 2 | 252 |
| `239` | `INV_BUTTON3` | 6 | 124 |
| `240` | `OPPLAYERT` | 4 | 138 |
| `247` | `OPOBJ1` | 6 | 97 |
| `250` | `ANTICHEAT_OPLOGIC6` | 2 | 73 |
| `253` | `MESSAGE_PUBLIC` | var byte | 156 |
| `255` | `IGNORELIST_ADD` | 8 | 192 |

Only `MAP_BUILD_COMPLETE` keeps its 289 opcode.

## Client-to-Server Payloads

All are 289's, including `INV_BUTTOND` with its mode byte and the 4-byte `EVENT_CAMERA_POSITION`. One
value range differs:

| Packet | 274 | 289 |
|---|---|---|
| `MESSAGE_PUBLIC` | effect `0` to `2`: none, wave, scroll. The server drops a message with an effect over 2 | `0` to `5`: none, wave, wave2, shake, scroll, slide |

## The Cache

274's cache is 289's store: `main_file_cache.dat` and `.idx0` to `.idx4` in the engine's `data/pack`,
with the login CRCs of files 0 to 8 of store 0, `map_index` in `versionlist`, and 289's interface format.
Its definitions lack four opcodes 289 has: loc `77` (multiloc), obj `115` (team), and varp `12` and
`13`. [CacheDesign.md](CacheDesign.md) §19 has the details.

## Source Map

| Topic | Engine | Webclient |
|---|---|---|
| Server opcode table | [`ServerGameProt.ts`](../../274server/engine/src/network/game/server/ServerGameProt.ts), [`ServerGameZoneProt.ts`](../../274server/engine/src/network/game/server/ServerGameZoneProt.ts) | [`ServerProt.ts`](../../274server/webclient/src/io/ServerProt.ts) |
| Client opcode table | [`ClientGameProt.ts`](../../274server/engine/src/network/game/client/ClientGameProt.ts) | [`ClientProt.ts`](../../274server/webclient/src/io/ClientProt.ts) |
| Inventory payloads | [`UpdateInvFullEncoder.ts`](../../274server/engine/src/network/game/server/codec/UpdateInvFullEncoder.ts), [`UpdateInvPartialEncoder.ts`](../../274server/engine/src/network/game/server/codec/UpdateInvPartialEncoder.ts) | [`Client.ts`](../../274server/webclient/src/client/Client.ts) `UPDATE_INV_FULL`, `UPDATE_INV_PARTIAL` |
| Chat effects | [`MessagePublicHandler.ts`](../../274server/engine/src/network/game/client/handler/MessagePublicHandler.ts) | [`Client.ts`](../../274server/webclient/src/client/Client.ts) `wave:`, `scroll:` |
| Login | [`World.ts`](../../274server/engine/src/engine/World.ts), [`web.ts`](../../274server/engine/src/web.ts) | [`Client.ts`](../../274server/webclient/src/client/Client.ts) `login` |
| Entity info | [`rsbuf/`](../../274server/engine/src/network/rsbuf) | [`Client.ts`](../../274server/webclient/src/client/Client.ts) `getPlayerPos*`, `getNpcPos*`; [`ClientPlayer.ts`](../../274server/webclient/src/dash3d/ClientPlayer.ts) |
| Definitions | [`cache/config/`](../../274server/engine/src/cache/config) | [`config/`](../../274server/webclient/src/config) |
| Cache CRCs | [`CrcTable.ts`](../../274server/engine/src/cache/CrcTable.ts) | |
