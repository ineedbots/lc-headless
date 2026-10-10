# Cache Design

Plan for loading the revision-289 game cache once per process and sharing it, read-only, with every account. The client computes the nine login CRCs from the cache, so `login.crcs` leaves `client.jsonc`. The cache also lifts the packet-only limits in [ScriptingDesign.md](ScriptingDesign.md) §10: scripts get names and options for NPCs, items and scenery, they see scenery the server never changed, and walks route around walls. The work ships in four phases, plus an optional fifth that lets several processes share one copy (§16, §17). Code style follows [CONVENTIONS.md](CONVENTIONS.md). It reads bytes and computes CRCs with `Packet` ([PacketDesign.md](PacketDesign.md) §3), adds a key to `ConfigFile` ([ConfigDesign.md](ConfigDesign.md)), and extends the script API ([ScriptingDesign.md](ScriptingDesign.md) §6).

Reference sources, in `289server/` beside this repository:

- `engine/src/io/FileStream.ts`: the store, `main_file_cache.dat` and `main_file_cache.idx0` to `idx4`
- `engine/src/cache/CrcTable.ts`: how the engine computes the CRCs it checks at login
- `webclient/src/io/JagFile.ts`, `io/BZip2.js`: JAG archives
- `webclient/src/io/OnDemand.ts`: `versionlist`, `map_index`, and the 2-byte trailer on map files
- `webclient/src/config/LocType.ts`, `NpcType.ts`, `ObjType.ts`: definitions
- `webclient/src/client/ClientBuild.ts`: `loadGround`, `loadLocations`, `addLoc` and `finishBuild`, which turn map squares into collision
- `webclient/src/dash3d/CollisionMap.ts`, `CollisionFlag.ts`, `MapFlag.ts`, `LocShape.ts`, `LocAngle.ts`, `DirectionFlag.ts`
- `webclient/src/client/Client.ts`: `tryMove` (the route search), `interactWithLoc`, `locChangeUnchecked`, and the menu code that supplies the default "Take" and "Drop" options
- `engine/data/pack/`: a real 289 cache. Every format and opcode table in this plan was checked against it, and the optional tests read it (§15.8)

---

## 1. Decisions

| Topic | Decision |
|---|---|
| Input | The folder that holds the server's store: `main_file_cache.dat` with `main_file_cache.idx0` to `idx4`, as the engine keeps it in `engine/data/pack/`. It's the only layout with all nine archives and the maps, and it's what the engine computes its CRCs from |
| Config | `client.cacheDirectory`, default `"cache"`, relative to the working directory like `scripting.accountsDirectory`. `login.crcs` is removed; a file that still has it loads, with a warning |
| CRCs | The CRC32 (`Packet::GetCrc`) of each raw file 0 to 8 in store 0, which is what the engine's `makeCrcs` computes. A missing file counts as 0. File 0 is always empty, so the first CRC is always 0 |
| When | Once, at startup, in `Application`, right after the config and before any script loads. A missing or damaged cache stops the process before any login, and the message names the file |
| Sharing | `CacheLoader::Load` returns a `GameCache_s`. `Application` holds it in a `std::shared_ptr<const GameCache_s>` and passes it down to each account's `GameClient`, as it does the config (ConfigDesign §1, Ownership). Nothing modifies it after loading, so every account reads the same copy without locks |
| Shape | `GameCache_s` is plain data with lookups (`FindLoc`, `FindNpc`, `FindObj`, `GetOption`, `FindSquare`), like `GameState_s`. `CacheLoader` is a non-instantiable class, like `ConfigFile`. Tests build a `GameCache_s` in place, without files. It can be moved but not copied, because the types' text points into its own `TextPool` |
| Decoded | The nine CRCs. From the `config` archive, the loc, NPC and obj definitions, with only the fields a headless client uses. From `config`, the run varp, and from `interface`, the components the client uses (§6). From `versionlist`, `map_index`. From store 4, each map square's blocked tiles and scenery. Models, animations, MIDIs, textures, sounds, media, the title screen, the rest of the interfaces and wordenc only count toward the CRCs |
| Decoding | Everything is decoded at load, and nothing is read from disk afterward. The store's files are closed when `Load` returns |
| Maps | Per square: a bitset of the tiles that block walking, and the locs a bot can use, as 6-byte records sorted by tile. A loc is kept when its type has a name or an option, or when it adds collision. The other 39% are decoration, dropped at load (§7.4). Bridges are resolved at load too, so each loc and blocked tile is stored on the level the player sees it on |
| Text | Names and examine text are `std::string_view`s into a `TextPool` that stores each distinct string once. Options are `u16` ids into one table of the distinct option strings (219 in the 289 cache), because most of a type's five option slots are empty. The definitions take under 1 MB |
| Per account | A `WorldMap`, owned by `GameClient`, holds the build area's collision on four levels. It's rebuilt from the shared squares plus the account's `locChanges` whenever the build area or a loc change moves on. It costs about 170 KB per account |
| Paths | A port of the webclient's `tryMove`: a breadth-first search over the build area, with the webclient's rules for reaching walls, wall decor and sized locs (`forceapproach` included), cut to 25 turning points. The server walks those waypoints in straight lines ([tcp-protocol-289.md](tcp-protocol-289.md#movement)), so routing is the client's job |
| Scripts | Names and options on `Npc`, `Item`, `GroundItem` and `Loc`; type lookups; scenery queries; options chosen by their text; `is_reachable`, `find_path` and `reachable=` filters; a `walk_to` that routes. `walk_to` and `get_loc_at` keep their signatures but see more (§12) |
| Compression | JAG archives use bzip2 without its header, and map files are gzip. Both come from vcpkg (`bzip2`, `zlib`) and are called only from `Compression.cpp` |
| Errors | Malformed input throws `CacheError`, a `std::runtime_error`. `CacheLoader::Load` adds the folder and the file it was reading. Messages follow ConfigDesign's form: lowercase, no trailing period. Looking up an unknown id returns `nullptr` |
| Threading | Loading runs on the main thread before the main loop starts. After that the cache is immutable, and each `WorldMap` belongs to one account's `GameClient` on the main thread |
| Memory | Measured on the 289 cache: 534 squares, 567,454 locs kept of 936,653, and 543,497 blocked tiles. The shared data comes to about 5.3 MB: 3.4 MB of loc records, 1 MB of bitsets and 0.9 MB of definitions. Each process holds one copy, so its sixteen accounts share it instead of holding sixteen. A process runs at most 16 accounts, and phase 5 lets several processes share one copy too (§17) |

Rejected:

- **The loose archives** in `engine/data/pack/client/`. That folder has no `wordenc` and no maps, so CRC 7 and every map feature would be missing.
- **Accepting both layouts.** More code and more tests, and nobody needs the second one.
- **Decoding on demand,** as the webclient does with a 10-entry LRU per type and maps fetched for each rebuild. It saves a few MB, but the cache would change after loading. Sharing it would then need locks or a copy per account, and a damaged file would fail during play instead of at startup. Phase 5 gets the same saving, leaving squares nobody visits on disk, without changing the cache after loading. A Python script that unpacked both archives and decoded every map square took 1.7 s; phase 1 measures the C++ load.
- **Keeping every loc.** 369,199 locs have no name, no option and no collision. They would take 2.2 MB, and nothing reads them.
- **`std::string` fields in the types.** Each is 32 bytes even when empty, and the types would hold about 96,000 of them, mostly empty: over 3 MB.
- **A `std::string_view` per option slot.** 16 bytes a slot, five per type and ten per obj, mostly empty: 1 MB more than `u16` ids.
- **Keeping the raw store in memory.** `main_file_cache.dat` is 9.6 MB, mostly models the client never reads.
- **One collision map for the whole world, shared.** Four levels of 32-bit flags for 534 squares is 35 MB, and loc changes are per account (different worlds, different views), so each account would still need an overlay of its own. The webclient keeps one map for the build area, and so does this design.
- **Updating collision one loc change at a time,** as the webclient does. Removing the old loc's collision needs the loc that was there, which the webclient keeps in its scene graph. Rebuilding the area from the squares and `locChanges` takes well under a millisecond and can't drift.
- **`WorldMap` inside `GameState_s`.** `TakeSnapshot` would copy 170 KB of collision with every snapshot, and the decoders would have to call into it.
- **Varbits and `multiloc`.** No loc in the 289 cache uses opcode 77 (measured), so the decoder reads past it and keeps nothing. Nothing else here needs varbits.
- **The webclient's "Members Object" renaming,** which hides members items' names on free worlds. A bot wants the real name.
- **Checking map files against `versionlist`'s `map_crc`.** The store is local, and a damaged file fails to decompress or decode.
- **Downloading the cache from the server** with the on-demand protocol (login opcode 15). The user provides the cache; fetching it is a separate feature.

---

## 2. Layout

```
rs2004-headless/
├── .gitignore                          gains cache/, and cache.bin in phase 5
├── vcpkg.json                          gains "bzip2" and "zlib"
├── CMakeLists.txt                      finds BZip2 and ZLIB
├── docs/
│   └── CacheDesign.md                  this file
├── src/
│   ├── pch.hpp                         gains <unordered_set> and <bitset>
│   ├── Application.hpp/.cpp            loads the cache after the config
│   ├── Core/
│   │   └── MappedFile.hpp/.cpp         phase 5: a whole file, mapped read-only
│   ├── Cache/
│   │   ├── CacheError.hpp
│   │   ├── CacheStore.hpp/.cpp         reads files out of main_file_cache.dat by way of the idx files
│   │   ├── Compression.hpp/.cpp        static: headerless bzip2, gzip
│   │   ├── JagArchive.hpp/.cpp         the named entries of a JAG archive
│   │   ├── TypeDecoder.hpp/.cpp        static: loc, NPC, obj and varp definitions
│   │   ├── MapDecoder.hpp/.cpp         static: map_index, land files, loc files
│   │   ├── InterfaceDecoder.hpp/.cpp   static: the interface archive's components
│   │   ├── ClientCode_e.hpp            the webclient's ClientCode
│   │   ├── CacheLoader.hpp/.cpp        static: Load(directory, logger) -> GameCache_s
│   │   ├── GameCache_s.hpp/.cpp        the loaded cache and its lookups
│   │   ├── TextPool.hpp/.cpp           interned names, examine text and options
│   │   ├── LocType_s.hpp
│   │   ├── NpcType_s.hpp
│   │   ├── ObjType_s.hpp
│   │   ├── VarpType_s.hpp
│   │   ├── MapSquare.hpp/.cpp          one 64x64 square: blocked tiles and MapLoc_s records
│   │   └── CacheFile.hpp/.cpp          phase 5: writes, checks and maps the decoded cache file
│   └── Game/
│       └── Map/
│           ├── LocShape.hpp            shape numbers and the shape-to-layer rule, moved out of ZoneDecoder
│           ├── CollisionFlag.hpp       the flag bits
│           ├── CollisionMap.hpp/.cpp   one level of the build area: adding locs, and the reach tests
│           ├── WorldMap.hpp/.cpp       one account's build area: collision and current scenery
│           └── PathFinder.hpp/.cpp     breadth-first routes to a tile, a wall or an area
└── tests/
    ├── Cache/                          CacheWriter, which builds stores, and a test file per class
    └── Game/                           CollisionMapTests, WorldMapTests, PathFinderTests
```

- `Cache/` depends on `Io/` (`Packet`) and `Core/` (`Logger`), never on `Game/` or `Script/`. `Game/` and `Script/` read it.
- The structs each get their own header, because the decoders, `GameCache_s` and the script API all use them (CONVENTIONS §6).
- `MapSquare` is a class, not a struct. Code outside `Cache/` reads it only through its functions, so phase 5 can change how it's stored without touching its readers (§17).
- `CacheError.hpp` is header-only, like `ConfigError.hpp`.
- CMake:
    - `find_package(BZip2 REQUIRED)` and `find_package(ZLIB REQUIRED)`.
    - The library target links `BZip2::BZip2` and `ZLIB::ZLIB` privately, because no header includes them.
    - The test executable links them too, because `CacheWriter` compresses its fixtures.
- `.gitignore` gains `cache/`, the default folder, so Jagex's files stay out of the repository.

---

## 3. The store

### Format

| File | Layout |
|---|---|
| `main_file_cache.idxN` | 6 bytes per file of store N: `u24 size`, `u24 firstSector`. The file count is the file's length / 6. A size or first sector of 0 means the file isn't there |
| `main_file_cache.dat` | 520-byte sectors: `u16 file`, `u16 part`, `u24 nextSector`, `u8 store + 1`, then up to 512 bytes of the file. Sector 0 is never used |

| Store | Holds | Read |
|---|---|---|
| 0 | Nine JAG archives: 0 unused, 1 `title`, 2 `config`, 3 `interface`, 4 `media`, 5 `versionlist`, 6 `textures`, 7 `wordenc`, 8 `sounds` | All nine, for the CRCs. `config`, `interface` and `versionlist` are decoded |
| 1 | Models | No |
| 2 | Animations | No |
| 3 | MIDI songs and jingles | No |
| 4 | Maps: a land file and a loc file for each square | Every file `map_index` names |

### Interface

```cpp
#pragma once

// Reads files out of a store's main_file_cache.dat, by way of its main_file_cache.idx files. The store
// is only read, and its files close when the CacheStore is destroyed.
class CacheStore
{
public:
    static constexpr u32 STORE_COUNT = 5;
    static constexpr u32 ARCHIVES = 0;
    static constexpr u32 MAPS = 4;
    static constexpr std::size_t SECTOR_SIZE = 520;
    static constexpr std::size_t SECTOR_HEADER_SIZE = 8;
    static constexpr std::size_t MAX_FILE_SIZE = 2'000'000;

    // Throws CacheError when main_file_cache.dat is missing. A missing index file only fails a read
    // from that store.
    explicit CacheStore(const std::filesystem::path& directory);

    [[nodiscard]] u32 GetFileCount(u32 store) const;
    // The file's bytes as stored, or nullopt when the index has no entry for it.
    [[nodiscard]] std::optional<std::vector<u8>> Read(u32 store, u32 file);

private:
    std::ifstream m_dat;
    u64 m_datSize = 0;
    std::array<std::optional<std::vector<u8>>, STORE_COUNT> m_indexes;
};
```

### Behaviour

- **Opening.** The constructor opens `main_file_cache.dat` with `std::ifstream{path, std::ios::binary}` and keeps it open. It reads each of `main_file_cache.idx0` to `idx4` that exists, whole. Index files are small (30 KB for the models) and stay in memory. The `.dat` file doesn't, and each read seeks to its sectors.
- **Reading** follows the engine's `FileStream.read`:
    1. A `store` of `STORE_COUNT` or more is a bug, so it's an `assert`. A store whose index file is missing throws `CacheError{"main_file_cache.idx4 not found"}`.
    2. A `file` at or past `GetFileCount(store)` returns `nullopt`, and so does an entry whose size or first sector is 0.
    3. A size over `MAX_FILE_SIZE`, the engine's limit, throws.
    4. Then each sector in turn, from part 0: seek to `sector * SECTOR_SIZE`, and read the 8-byte header and `min(512, remaining)` bytes. The header must name this file, this part and `store + 1`, and the next sector must lie inside the `.dat` file. A chain that ends (next sector 0) before the file is complete throws too.
- **Errors.** Every failure is a `CacheError` that names the store and file, such as `store 4 file 1234: sector 77 belongs to file 12`. A failed seek or read on the stream is one too (`main_file_cache.dat: read failed at sector 77`). A sector past the end of the file is reported before it's read.
- Each result is sized once and filled sector by sector, so nothing is copied twice.

---

## 4. Archives and compression

### JAG format

| Where | Fields |
|---|---|
| Byte 0 | `u24 unpackedSize`, `u24 packedSize` |
| Byte 6 | When the two sizes differ, the rest of the file is one bzip2 stream, minus its 4-byte `BZh1` header, that unpacks to `unpackedSize` bytes. The entries inside are then stored as they are. When the sizes match, the archive isn't compressed as a whole, and each entry is compressed on its own |
| Start of the unpacked bytes, or byte 6 | `u16 count`, then for each entry `s32 nameHash`, `u24 unpackedSize`, `u24 packedSize`. The entries' bytes follow the table, in order |

- An entry's name hash uppercases the name, then for each character computes `hash = hash * 61 + c - 32`, with 32-bit wraparound. Known values: `loc.dat` is 682978269, `map_index` is 1987120305, and `obj.idx` is -1667598946.
- In the 289 cache, `config` compresses each entry and `versionlist` compresses the whole archive, so loading exercises both paths.

### Compression

```cpp
#pragma once

class Compression
{
public:
    Compression() = delete;

    // A bzip2 stream without its "BZh1" header, as JAG archives store it. Throws CacheError unless it
    // unpacks to exactly expectedSize bytes.
    [[nodiscard]] static std::vector<u8> Bunzip2(std::span<const u8> source, std::size_t expectedSize);
    // One gzip member, as a map file holds once its 2-byte version trailer is dropped. Throws CacheError
    // for damaged data, or for more than CacheStore::MAX_FILE_SIZE bytes of output.
    [[nodiscard]] static std::vector<u8> Gunzip(std::span<const u8> source);
};
```

- `Bunzip2` feeds libbzip2 the 4 bytes `BZh1` and then the source, into an output buffer of `expectedSize` bytes. It must end with `BZ_STREAM_END` having written exactly `expectedSize` bytes.
- `Gunzip` calls zlib's `inflateInit2` with `16 + MAX_WBITS`, which reads the gzip header, and grows its output until `Z_STREAM_END`. The output limit stops a damaged length from using all the memory there is.
- Both release the library's state on every path. A small RAII type in the anonymous namespace ends the stream, as CONVENTIONS §8 wraps C handles.
- Library return codes become `CacheError` where they enter the code (CONVENTIONS §8), such as `bzip2 data is damaged (BZ_DATA_ERROR)`.

### JagArchive

```cpp
#pragma once

// A JAG archive's entries, looked up by name. An entry is unpacked when it's read.
class JagArchive
{
public:
    // Throws CacheError when the header or the entry table doesn't fit the data.
    explicit JagArchive(std::vector<u8> data);

    [[nodiscard]] static s32 HashName(std::string_view name);

    // The entry, unpacked, or nullopt when the archive has no entry by that name. Throws CacheError when
    // the entry doesn't unpack to its listed size.
    [[nodiscard]] std::optional<std::vector<u8>> Read(std::string_view name) const;

private:
    struct Entry_s
    {
        s32 nameHash = 0;
        u32 unpackedSize = 0;
        u32 packedSize = 0;
        std::size_t offset = 0;
    };

    std::vector<u8> m_data;
    bool m_entriesCompressed = false;
    std::vector<Entry_s> m_entries;
};
```

- The constructor takes the archive by value and moves it in, or replaces it with the unpacked bytes, so no archive is copied.
- Every entry's offset and packed size must lie inside the data. When two entries share a hash, the first wins, as the webclient's `indexOf` does.

---

## 5. CRCs

```
crcs[i] = Packet::GetCrc(store 0, file i)    for i from 0 to 8; 0 when the file isn't there
```

- This is the engine's `makeCrcs`. The engine compares the CRC32 of the 36 bytes, so a cache that differs from the server's in any archive gets status 6 ([tcp-protocol-289.md](tcp-protocol-289.md#login-responses)).
- Files past 8 in store 0 are ignored, because the login carries nine CRCs.
- The 289 cache gives `0x00000000`, `0xde5b3345`, `0x6026f8fe`, `0x07550309`, `0x9a13636e`, `0xca2717bd`, `0x368f1792`, `0x1b1fb6b2` and `0xa7129379`, the nine values in ConfigDesign's example.
- They're stored as `std::array<s32, GameCache_s::CRC_COUNT>`, the type `login.crcs` had, so `LoginHandshake` writes them with `P4` as before.

---

## 6. Definitions

### Index and data files

`config` holds `loc.dat` and `loc.idx`, `npc.dat` and `npc.idx`, and `obj.dat` and `obj.idx`:

- `X.idx`: `u16 count`, then a `u16 size` for each definition, in id order.
- `X.dat`: `u16 count`, then the definitions back to back from byte 2. Each is a run of `u8 opcode` and that opcode's values, ending with opcode 0.
- The two counts must match, each definition must end exactly where its size says, and the last must end at the end of the file. Anything else throws, naming the type and id: `loc 1234: ends at byte 88 of its 90`.
- Strings are read with `Packet::GJStr`, as bytes up to `\n`, and kept as they are; the 289 cache uses printable ASCII. Each one is interned into the cache's `TextPool` (Text, below), so a string that appears many times, such as "Attack", is stored once.

### Structs

```cpp
// src/Cache/LocType_s.hpp
#pragma once

struct LocType_s
{
    static constexpr std::size_t OP_COUNT = 5;

    u16 id = 0;
    u8 width = 1;
    u8 length = 1;
    bool blockWalk = true;
    bool blockRange = true;
    // Ground decor only blocks walking when it's active.
    bool active = false;
    // Sides the loc can't be used from, at angle 0: 1 north, 2 east, 4 south, 8 west.
    u8 forceApproach = 0;
    // Views into the cache's TextPool; an empty name means the type has none.
    std::string_view name;
    std::string_view examine;
    // Ids into the cache's option table. TextPool::NO_OPTION is a slot the menu doesn't show.
    std::array<u16, OP_COUNT> ops{};
};
```

```cpp
// src/Cache/NpcType_s.hpp
#pragma once

struct NpcType_s
{
    static constexpr std::size_t OP_COUNT = 5;

    u16 id = 0;
    u8 size = 1;
    // The level the menu shows, if any.
    std::optional<u16> combatLevel;
    std::string_view name;
    std::string_view examine;
    std::array<u16, OP_COUNT> ops{};
};
```

```cpp
// src/Cache/ObjType_s.hpp
#pragma once

struct ObjType_s
{
    static constexpr std::size_t OP_COUNT = 5;

    u16 id = 0;
    bool stackable = false;
    bool members = false;
    s32 cost = 1;
    // For a banknote, the item it's a note of.
    std::optional<u16> noteOf;
    std::string_view name;
    std::string_view examine;
    // On the ground. The menu shows "Take" for op 3 when ops[2] is NO_OPTION.
    std::array<u16, OP_COUNT> ops{};
    // In an inventory. The menu shows "Drop" for op 5 when inventoryOps[4] is NO_OPTION.
    std::array<u16, OP_COUNT> inventoryOps{};
};
```

- The small fields come first so they pack together. A `LocType_s` or an `NpcType_s` is 56 bytes and an `ObjType_s` 72, so the 10,801 types take 0.67 MB.
- An option is read through `GameCache_s::GetOption(id)`, which returns its text.

### Text

```cpp
#pragma once

// The types' text, with each distinct string stored once. The views it hands out stay valid as long as
// the pool lives, after a move too, because the text sits in chunks that never move.
class TextPool
{
public:
    static constexpr u16 NO_OPTION = 0;
    static constexpr std::size_t CHUNK_SIZE = 64 * 1024;

    TextPool();

    [[nodiscard]] std::string_view Intern(std::string_view text);
    // The option's id in the option table. Empty text is NO_OPTION.
    [[nodiscard]] u16 InternOption(std::string_view text);
    [[nodiscard]] std::string_view GetOption(u16 id) const;
    // Counting NO_OPTION.
    [[nodiscard]] std::size_t GetOptionCount() const;
    // Frees the lookup tables that interning needs. Nothing can be interned afterward.
    void FinishInterning();

private:
    std::vector<std::unique_ptr<char[]>> m_chunks;
    std::size_t m_chunkUsed = 0;
    std::vector<std::string_view> m_options;
    std::unordered_set<std::string_view> m_strings;
    std::unordered_map<std::string_view, u16> m_optionIds;
    bool m_finished = false;
};
```

- `Intern` copies new text into the current chunk, starting a new chunk when it doesn't fit; a string longer than a chunk gets a chunk of its own. The same text always returns the same view.
- `InternOption` interns the text and gives each distinct option an id, from 1 in the order first seen. More than 65,535 options throws `CacheError`.
- `CacheLoader` calls `FinishInterning` once everything is decoded, so the lookup tables, a few hundred KB, don't outlive loading. Interning after that is a bug, and it asserts.
- The pool owns its chunks through `std::unique_ptr`, so it can be moved but not copied, and so can the `GameCache_s` that holds it.
- In the 289 cache, the types hold 7,482 distinct strings totalling 162 KB, plus about 50 KB of generated banknote text (below), and 219 distinct options.
- Tests that build types in place set `name` and `examine` to string literals, which never move, and take option ids from `cache.text.InternOption`.

### Opcodes

Opcodes not listed throw `CacheError` (`npc 41: unknown opcode 200`). The webclient's decoders skip an unknown opcode without reading its value, which puts every later field out of step; a throw names the problem instead. Every definition in the 289 cache decodes to exactly its listed size with these tables: 5,116 locs, 1,596 NPCs and 4,089 objs.

**Locs, kept:**

| Opcode | Values | Field |
|---|---|---|
| 1 | `u8 n`, then n × (`u16 model`, `u8 shape`) | Only for `active`'s default (below) |
| 2 | string | `name` |
| 3 | string | `examine` |
| 5 | `u8 n`, then n × `u16 model` | Only for `active`'s default |
| 14 | `u8` | `width` |
| 15 | `u8` | `length` |
| 17 | none | `blockWalk = false` |
| 18 | none | `blockRange = false` |
| 19 | `u8` | `active = value == 1` |
| 30–38 | string | 30–34 are `ops[0]` to `ops[4]`, and "hidden", in any case, is stored as `NO_OPTION`. 35–38 are read and dropped |
| 69 | `u8` | `forceApproach` |
| 74 | none | Breaks route finding: after decoding, `blockWalk` and `blockRange` are false |
| 77 | `u16 varbit`, `u8 n`, then (n + 1) × `u16` | `multiloc`, read and dropped |

Read and dropped: 21, 22, 23, 62, 64 and 73 (no value); 28, 29, 39 and 75 (1 byte); 24, 60, 65, 66, 67, 68, 70, 71 and 72 (2 bytes); 40 (`u8 n`, then n × 4 bytes).

Without opcode 19, `active` follows the webclient's rule. It's true when the last of opcodes 1 and 5 supplied models (n above 0), and either it was opcode 5 or opcode 1's first shape is 10 (`CENTREPIECE_STRAIGHT`). It's also true when any option opcode (30–38) appeared, even one that says "hidden".

**NPCs, kept:** 2 `name`; 3 `examine`; 12 `s8 size`; 30–39 options (30–34 are `ops`, "hidden" is stored as `NO_OPTION`, and 35–39 are dropped); 95 `u16 combatLevel`.

Read and dropped: 93 and 99 (no value); 100 and 101 (1 byte); 13, 14, 90, 91, 92, 97, 98, 102 and 103 (2 bytes); 17 (8 bytes); 1 and 60 (`u8 n`, then n × 2 bytes); 40 (`u8 n`, then n × 4 bytes).

**Objs, kept:** 2 `name`; 3 `examine`; 11 `stackable`; 12 `s32 cost`; 16 `members`; 30–34 `ops` ("hidden" is stored as `NO_OPTION`); 35–39 `inventoryOps` (kept as written, because the webclient doesn't hide these); 97 `u16 certlink`; 98 `u16 certtemplate`.

Read and dropped: 1, 4, 5, 6, 7, 8, 10, 24, 26, 78, 79, 90, 91, 92, 93, 95, 110, 111 and 112 (2 bytes); 23 and 25 (3 bytes); 113, 114 and 115 (1 byte); 100–109 (4 bytes); 40 (`u8 n`, then n × 4 bytes).

### Banknotes

An obj with a `certtemplate` is a banknote. Once every obj is decoded, each note takes the values `ObjType.genCert` gives it:

- `name`, `members` and `cost` come from the `certlink` obj.
- `stackable` is true.
- `examine` is `Swap this note at any bank for a {name}.`, with "an" when the name starts with a vowel, interned like the rest.
- `noteOf` is the `certlink` id.

A `certlink` that isn't an obj throws. The 289 cache has 1,333 notes; 1512 is the note of 1511, "Logs".

### TypeDecoder

```cpp
#pragma once

#include "LocType_s.hpp"
#include "NpcType_s.hpp"
#include "ObjType_s.hpp"
#include "TextPool.hpp"

class TypeDecoder
{
public:
    TypeDecoder() = delete;

    // Each takes a type's .dat and .idx entries from the config archive, interns the text into the
    // pool, and returns the types in id order.
    [[nodiscard]] static std::vector<LocType_s> DecodeLocs(std::span<const u8> dat, std::span<const u8> idx, TextPool& text);
    [[nodiscard]] static std::vector<NpcType_s> DecodeNpcs(std::span<const u8> dat, std::span<const u8> idx, TextPool& text);
    [[nodiscard]] static std::vector<ObjType_s> DecodeObjs(std::span<const u8> dat, std::span<const u8> idx, TextPool& text);
};
```

- Reading goes through `Packet`. Its reads throw `std::out_of_range` at the end of the data, and the decoders turn that into a `CacheError` naming the type and id.
- The opcode loops are functions in the anonymous namespace, one per type, with a shared helper for the option strings.

### Components and the run varp

Some of what a client does goes through ids that the server's content pack numbers when it builds the cache, so they belong to the cache, not the protocol. A player logs out by clicking the logout tab's button, which sends `IF_BUTTON` with the button's component id; scripts read the backpack, the worn equipment and the bank by their inventory components; and running is a varp, set by clicking one of two buttons. In the 289 cache, from `content/pack/interface.pack` and `varp.pack`:

| `GameCache_s` | 289 id | Content name |
|---|---|---|
| `logoutComponent` | 2458 | `logout:try_logout`. It used to be `client.logoutComponent` in the config |
| `inventoryComponent`, `inventorySize` | 3214, 28 | `inventory:inv`, 4 by 7 |
| `equipmentComponent` | 1688 | `wornitems:wear` |
| `bankComponent` | 5382 | `bank_main:inv` |
| `bankInventoryComponent` | 2006 | `bank_side:inv`, the backpack beside the bank |
| `runOffButton`, `runOnButton` | 152, 153 | `controls:com_4` and `controls:com_5` |
| `runVarp` | 173 | `option_run` |

The cache has no names, so `CacheLoader` finds each one by what the cache says about it, and takes the first match:

| Id | Found by |
|---|---|
| The logout button | The component whose client code is `ClientCode_e::Logout`, 205. The webclient starts its logout timer for that code and still sends the click, and the server's `[if_button,logout:try_logout]` script logs the player out |
| The bank | The component whose client code is `ClientCode_e::BankMode`, 206, which the webclient's bank arrange mode applies to |
| The backpack | The inventory whose items can be used on things (`IfType`'s `objUse`). Its width times its height is `inventorySize` |
| The worn equipment | The inventory with slot backgrounds, which draw the empty equipment slots |
| The backpack beside the bank | The inventory whose first option starts with "Deposit" |
| The run varp | The varp whose client code is 7. The webclient does nothing with that code, but the engine's `VarPlayerType` finds its run varp by it too |
| The run buttons | The select buttons whose first script pushes the run varp (opcode 5 and the varp's id) and whose first condition's operand is 0 (off) or 1 (on). That's how the webclient's select buttons find the varp a click sets, and the value it sets it to |

In the 289 content each rule matches only the component it's for. A missing match throws, naming what the rule marks: `store 0 file 3 (interface): no inventory lets its items be used, which marks the backpack`, `store 0 file 2 (config): no varp has client code 7, which marks the run varp`.

`ClientCode_e` (`src/Cache/ClientCode_e.hpp`) is the webclient's `ClientCode` enum, with its values PascalCase (`CC_LOGOUT` is `Logout`) and a `None` for 0.

#### varp.dat

`config` also holds `varp.dat` and `varp.idx`, in the format of the other types (Index and data files, above). `TypeDecoder::DecodeVarps` keeps each varp's client code (opcode 5, a `u16`) in a `VarpType_s`, and reads and drops the webclient's other opcodes: 1 and 2 (a byte), 7 and 12 (4 bytes), 10 (a string) and 3, 4, 6, 8, 11 and 13 (nothing). Any other opcode throws, as for the other types: `varp 1: unknown opcode 9`.

#### The interface archive

`interface` (archive 3) has one entry, `data`: a `u16` count, then every component in turn. Each starts with its id, after `0xFFFF` and its layer's id when it opens a run of that layer's components, then `u8 type`, `u8 buttonType` and `u16 clientCode`. The fields after that depend on the type and button type, and nothing records a component's length, so reading one means reading every component before it, as the webclient's `IfType.init` does.

```cpp
// src/Cache/InterfaceDecoder.hpp
#pragma once

#include "ClientCode_e.hpp"

// The webclient's ComponentType.
enum class ComponentType_e : u8
{
    Layer,
    Unused,
    Inv,
    Rect,
    Text,
    Graphic,
    Model,
    InvText,
};

// The webclient's ButtonType.
enum class ButtonType_e : u8
{
    None,
    Ok,
    Target,
    Close,
    Toggle,
    Select,
    Continue,
};

// The fields of a component that the client finds components by. The inventory fields are only set for
// ComponentType_e::Inv.
struct IfComponent_s
{
    static constexpr std::size_t OPTION_COUNT = 5;

    u16 id = 0;
    ComponentType_e type = ComponentType_e::Layer;
    ButtonType_e buttonType = ButtonType_e::None;
    ClientCode_e clientCode = ClientCode_e::None;
    u16 width = 0;
    u16 height = 0;
    // Each condition's operand, and each script's opcodes, as IfType keeps them.
    std::vector<u16> operands;
    std::vector<std::vector<u16>> scripts;
    // IfType's objUse: whether the items can be used on things.
    bool objUse = false;
    bool hasSlotBackgrounds = false;
    // Empty where the slot has no option.
    std::array<std::string, OPTION_COUNT> options;
};

class InterfaceDecoder
{
public:
    InterfaceDecoder() = delete;

    // Takes the interface archive's data entry and returns its components in the order it lists them.
    // Throws CacheError, naming the component, for data that doesn't decode.
    [[nodiscard]] static std::vector<IfComponent_s> Decode(std::span<const u8> data);
};
```

- It keeps the fields above, and skips every other field by the sizes `IfType.init` reads. A type above 7, which the webclient would read nothing more for, throws, as an unknown opcode does: `component 11: unknown type 8`.
- It reads every component, so damage anywhere in the archive throws. Since [BotApiDesign.md](BotApiDesign.md) §6, `GameCache_s::components` keeps them all, with their children, text, colours and button text, for the interfaces scripts read and click.
- Data that ends inside a component's id names the component before it: `data ends inside the id of the component after 4`.

---

## 7. Maps

### 7.1 `map_index`

`versionlist`'s `map_index` entry has 7 bytes per square: `u16 square`, `u16 landFile`, `u16 locFile`, `u8 free`. `square` is `(squareX << 8) | squareZ`, where a square's coordinates are absolute tile coordinates `>> 6`. Both files are in store 4. `free`, which is 1 for free-to-play squares, isn't kept.

The 289 cache lists 534 squares, and every one has both files.

### 7.2 Map files

Each map file in store 4 is a gzip member followed by a 2-byte version. The loader drops the version, as the webclient's `OnDemand` does, and gunzips the rest. A file shorter than 2 bytes throws.

### 7.3 Land file

For each level from 0 to 3, each x from 0 to 63 and each z from 0 to 63 (z changes fastest), a run of opcodes for that tile:

| Opcode | Values | Meaning |
|---|---|---|
| 0 | none | End of tile |
| 1 | `u8 height` | End of tile |
| 2–49 | `u8 overlay` | Overlay |
| 50–81 | none | Tile flags = opcode − 49 |
| 82 and up | none | Underlay |

Only the flags are kept, and a tile's last flags opcode wins. The bits are the webclient's `MapFlag`: 1 `Block` (blocks walking), 2 `LinkBelow` (a bridge), 4 `RemoveRoof`, 8 `VisBelow` and 16 `ForceHighDetail`. Only `Block` and `LinkBelow` matter here. The file must be used up exactly.

### 7.4 Loc file

```
id = -1
repeat:
    deltaId = smart; stop when it's 0
    id += deltaId
    pos = 0
    repeat:
        deltaPos = smart; go to the next id when it's 0
        pos += deltaPos - 1
        info = u8
        z = pos & 63, x = (pos >> 6) & 63, level = pos >> 12
        shape = info >> 2, angle = info & 3
```

`smart` is `Packet::GSmart`: one byte below 128, and otherwise `u16 − 32768`. The file must be used up exactly.

**Bridges.** A tile whose level-1 flags have `LinkBelow` is a bridge: everything at its x and z is seen one level lower. The loader applies this once, as `finishBuild` and `loadLocations` do on every build:

- A tile with `Block` on level L blocks walking on level L − 1 if it's a bridge, and on level L otherwise.
- A loc on level L is stored on level L − 1 if its tile is a bridge, and on level L otherwise.
- Anything that ends up on level −1 is dropped. That's 3,566 of the 940,219 locs in the 289 cache.

**Decoration.** A loc is kept only when a bot can use it: its type has a name or an option, or the loc adds collision. A loc adds collision when its type blocks walking and it's a wall, a ground-layer loc, or active ground decor (§10, Shapes and layers). The rest are decoration, with no name, no option and nothing to walk into, which the webclient only draws. Of the 936,653 locs left after bridges, 567,454 are kept and 369,199 dropped, which saves 2.2 MB.

### 7.5 MapSquare

```cpp
#pragma once

// One loc, packed as the loc file packs it, in 6 bytes.
struct MapLoc_s
{
    u16 id = 0;
    // level << 12 | x << 6 | z, with x and z within the square, and the level the one it's seen on.
    u16 position = 0;
    // shape << 2 | angle.
    u8 info = 0;

    [[nodiscard]] s32 GetX() const;
    [[nodiscard]] s32 GetZ() const;
    [[nodiscard]] s32 GetLevel() const;
    [[nodiscard]] u8 GetShape() const;
    [[nodiscard]] u8 GetAngle() const;
};

static_assert(sizeof(MapLoc_s) == 6);

// One 64x64 square of the map: the tiles that block walking and the locs a bot can use, both on the
// levels they're seen on. Code outside Cache/ reads it only through these functions (§17).
class MapSquare
{
public:
    static constexpr s32 SIZE = 64;
    static constexpr s32 LEVELS = 4;

    // Sorts the locs by tile.
    MapSquare(u8 x, u8 z, std::bitset<LEVELS * SIZE * SIZE> blocked, std::vector<MapLoc_s> locs);

    [[nodiscard]] static u16 GetId(s32 squareX, s32 squareZ);
    [[nodiscard]] u8 GetX() const;
    [[nodiscard]] u8 GetZ() const;
    [[nodiscard]] bool IsBlocked(s32 level, s32 x, s32 z) const;
    [[nodiscard]] std::span<const MapLoc_s> GetLocsAt(s32 level, s32 x, s32 z) const;
    [[nodiscard]] std::span<const MapLoc_s> GetLocs() const;

private:
    u8 m_x;
    u8 m_z;
    // Bit (level * SIZE + x) * SIZE + z.
    std::bitset<LEVELS * SIZE * SIZE> m_blocked;
    // Sorted by position, which sorts by level, then x, then z.
    std::vector<MapLoc_s> m_locs;
};
```

- `MapLoc_s` keeps the loc file's own packing, with the level replaced by the level the loc is seen on. Its accessors are defined in the header, like `Zone_s::Contains`. The 567,454 kept locs take 3.4 MB, and the bitsets 1 MB across all squares.
- The sort is stable, so the locs on one tile keep the file's order, which is id order. `GetLocsAt` is an `std::ranges::equal_range` over them.
- Readers loop with `for (const auto loc : square.GetLocsAt(...))`, taking each 6-byte record by value. That loop still compiles when phase 5 replaces the span with a range over the mapped file (§17).

### 7.6 MapDecoder

```cpp
#pragma once

#include "LocType_s.hpp"
#include "MapSquare.hpp"

struct MapIndexEntry_s
{
    u16 square = 0;
    u16 landFile = 0;
    u16 locFile = 0;
};

class MapDecoder
{
public:
    MapDecoder() = delete;

    [[nodiscard]] static std::vector<MapIndexEntry_s> DecodeIndex(std::span<const u8> data);
    // Takes the square's land and loc files, already unpacked, and the loc types, which decide what's
    // decoration.
    [[nodiscard]] static MapSquare DecodeSquare(u16 square, std::span<const u8> land, std::span<const u8> locs, std::span<const LocType_s> types);
};
```

- `DecodeIndex` throws when the length isn't a multiple of 7.
- `DecodeSquare` reads the land file first, keeping all four levels of flags for the square, and uses them for the bridges once it has the locs. The flags aren't kept after that.
- A loc id with no type, or a level above 3, throws (`square 50_50 locs: loc 6000 has no type`).

---

## 8. GameCache_s and CacheLoader

### Interface

```cpp
// src/Cache/GameCache_s.hpp
#pragma once

#include "LocType_s.hpp"
#include "MapSquare.hpp"
#include "NpcType_s.hpp"
#include "ObjType_s.hpp"
#include "TextPool.hpp"

// Everything the client uses from the game cache. It's loaded once, and shared read-only by every
// account in the process. It moves but doesn't copy, because the types' text points into its pool.
struct GameCache_s
{
    static constexpr std::size_t CRC_COUNT = 9;

    std::array<s32, CRC_COUNT> crcs{};
    // Components and a varp the client uses. The server's content pack numbers them when it builds the
    // cache, so CacheLoader finds them by what the cache says about them.
    u16 logoutComponent = 0;
    u16 inventoryComponent = 0;
    s32 inventorySize = 0;
    u16 equipmentComponent = 0;
    u16 bankComponent = 0;
    // The backpack beside the bank, which replaces the inventory tab while the bank is open.
    u16 bankInventoryComponent = 0;
    u16 runOffButton = 0;
    u16 runOnButton = 0;
    u16 runVarp = 0;
    TextPool text;
    // Index i holds the type whose id is i.
    std::vector<LocType_s> locs;
    std::vector<NpcType_s> npcs;
    std::vector<ObjType_s> objs;
    // Keyed by MapSquare::GetId.
    std::unordered_map<u16, MapSquare> squares;

    [[nodiscard]] const LocType_s* FindLoc(s32 id) const;
    [[nodiscard]] const NpcType_s* FindNpc(s32 id) const;
    [[nodiscard]] const ObjType_s* FindObj(s32 id) const;
    // Empty for TextPool::NO_OPTION.
    [[nodiscard]] std::string_view GetOption(u16 id) const;
    [[nodiscard]] const MapSquare* FindSquare(s32 squareX, s32 squareZ) const;
};
```

```cpp
// src/Cache/CacheLoader.hpp
#pragma once

#include "../Core/Logger.hpp"
#include "GameCache_s.hpp"

class CacheLoader
{
public:
    static constexpr u32 CONFIG_ARCHIVE = 2;
    static constexpr u32 INTERFACE_ARCHIVE = 3;
    static constexpr u32 VERSIONLIST_ARCHIVE = 5;

    CacheLoader() = delete;

    // Throws CacheError, with the folder in front of the message, when a file is missing or damaged.
    [[nodiscard]] static GameCache_s Load(const std::filesystem::path& directory, Logger& logger = *Logger::GetDefault());
};
```

- The `Find` functions return `nullptr` for an id that's negative or past the end, so callers can handle ids the server sends that the cache doesn't have. `FindSquare` returns `nullptr` for a square that isn't in the cache.
- A default `GameCache_s{}` is a valid, empty cache: nine zero CRCs, every component and varp id 0, no types, no options but `NO_OPTION`, and no squares. Tests of code that needs a cache but not its contents pass `std::make_shared<const GameCache_s>()`. `TestCache::SetComponents` gives a test's cache the 289 ids. Tests that log out through `FakeGameServer` pass `FakeGameServer::MakeCache()`, which is empty but for those ids and the logout button that server answers.
### Behaviour

1. If `directory / "main_file_cache.dat"` doesn't exist, throw `CacheError{"{dir}: main_file_cache.dat not found; set client.cacheDirectory to the folder that holds the server's cache"}`.
2. Open a `CacheStore` and compute the CRCs (§5).
3. Read archive 2 into a `JagArchive`, decode `loc`, `npc` and `obj` from it into the cache's `TextPool`, and find the run varp in `varp` (§6). A missing archive or entry throws, and so does a `varp` without the run varp.
4. Read archive 3, decode its `data` entry, and find the components (§6, Components and the run varp). A missing archive or entry throws, and so does an archive without one of them: `store 0 file 3 (interface): no component has client code 205, which marks the logout button`.
5. Read archive 5, decode `map_index`, and then each square's two files, using the loc types to drop decoration (§7). A square whose files aren't in store 4 is skipped and counted. The webclient builds such a square as open ground, and `WorldMap` does the same for a square that isn't in the cache.
6. Call `text.FinishInterning()`.
7. Log one line at Info, such as `Cache loaded from cache in 240 ms: 5116 locs, 1596 NPCs, 4089 objs, 534 map squares with 567454 locs`. If squares were skipped, log a Warning: `3 map squares in map_index have no files; they load as open ground`.

- **Errors.** Each step catches `CacheError` and throws a new one with its context in front, as `ConfigFile::Load` adds the path (CONVENTIONS §8, adding context). The folder comes first, then the file: `cache: store 4 file 1234 (square 50_50 locs): gzip data is damaged`.
- `Load` returns the `GameCache_s` by value, and `Application` moves it into its `shared_ptr` without a copy.

### Usage

```cpp
Application::Application(CommandLine_s commandLine, std::shared_ptr<Logger> logger)
    : m_logger{std::move(logger)}
    , m_commandLine{std::move(commandLine)}
{
    assert(m_logger && "Application needs a logger");
    m_config = std::make_shared<const Config_s>(ConfigFile::Load(m_commandLine.configPath, *m_logger));
    m_logger->SetLevel(m_config->client.logLevel);
    m_logger->Info("Config loaded from {}", m_commandLine.configPath.string());
    m_cache = std::make_shared<const GameCache_s>(CacheLoader::Load(m_config->client.cacheDirectory, *m_logger));
}
```

- `Application` gains `std::shared_ptr<const GameCache_s> m_cache`. It passes it to `AccountRunner`, which passes it to each `Account`, which passes it to its `GameClient`. Each one takes it by value after the config, moves it into place (the sink-parameter rule, CONVENTIONS §8), and asserts that it isn't null.
- `GameClient::GetCache()` returns `const GameCache_s&`, so `ScriptHost` and `GameActions` reach the cache through the client they already hold.

```
Fatal error: cache: main_file_cache.dat not found; set client.cacheDirectory to the folder that holds the server's cache
Fatal error: cache: store 0 file 2 (config): obj 1512: unknown opcode 200
```

---

## 9. Config

| Change | Detail |
|---|---|
| Removed | `LoginSettings_s::crcs` and `CRC_COUNT`, the CRC array's `adl_serializer`, `FormatCrc`, and `crcs` in `LoginSettings_s`'s macro. Later, `ClientSettings_s::logoutComponent`, when the logout button moved to the cache (§6) |
| Added | `ClientSettings_s::cacheDirectory`, a `std::string` defaulting to `"cache"`, after `idleSeconds`. Its rule is that it's not empty: `client.cacheDirectory: must not be empty` |
| Leftover keys | If the `login` section has `crcs`, or the `client` section has `logoutComponent`, `Parse` logs a Warning, as it does for a leftover `account` section: `Config has login.crcs, which is no longer read; the CRCs come from the cache in client.cacheDirectory`, and `Config has client.logoutComponent, which is no longer read; the logout button comes from the cache in client.cacheDirectory`. The keys are a table, `LEGACY_KEYS`, in `ConfigFile.cpp`'s anonymous namespace |
| Sample header | `// Set server.url and the login RSA key, put the server's cache in client.cacheDirectory, then run again.` |
| Sample | Loses the `crcs` array and `logoutComponent`, and gains `"cacheDirectory": "cache"` in `client` |
| `LoginHandshake` | Takes the CRCs as `std::span<const s32, GameCache_s::CRC_COUNT>`, after the account and login settings. `BuildLoginRequest` takes them the same way. `GameClient` passes its cache's CRCs, and the cache outlives the handshake as the settings do |
| `LoginError` | Status 6 reads `revision, cache CRC or RSA key mismatch; is client.cacheDirectory this server's cache?` |

ConfigDesign.md's key table, sample and tests change to match. README's configuration section drops `login.crcs` and adds `client.cacheDirectory`.

---

## 10. Per account: WorldMap

### Shapes and layers

`LocShape.hpp` holds the webclient's `LocShape` numbers as constants of a non-instantiable `LocShape` class, along with `ZoneDecoder::GetLayer`, which moves there and which `ZoneDecoder` then calls.

| Shapes | Layer | Collision |
|---|---|---|
| 0 `WALL_STRAIGHT`, 1 `WALL_DIAGONAL_CORNER`, 2 `WALL_L`, 3 `WALL_SQUARE_CORNER` | Wall | `AddWall` |
| 4–8, wall decor | Wall decor | None |
| 9 `WALL_DIAGONAL`, 10 `CENTREPIECE_STRAIGHT`, 11 `CENTREPIECE_DIAGONAL`, 12–21 roofs | Ground | `AddLoc` with the type's size |
| 22 `GROUND_DECOR` | Ground decor | `BlockGround`, when the type is active |

Only types with `blockWalk` touch collision, as in `ClientBuild.addLoc`.

### CollisionFlag

The webclient's flag values become `static constexpr u32` members of a non-instantiable `CollisionFlag` class, with names that say what each bit is:

| Webclient | C++ | Value |
|---|---|---|
| `W_N`, `W_E`, `W_S`, `W_W`, `W_NW`, `W_NE`, `W_SE`, `W_SW` | `WALL_NORTH` and so on | 0x2, 0x8, 0x20, 0x80, 0x1, 0x4, 0x10, 0x40 |
| `V_N` and the other seven | `RANGE_WALL_NORTH` and so on | The wall bits shifted left by 9: 0x200 (`V_NW`) to 0x10000 (`V_W`) |
| `WALK_SCENERY` | `LOC` | 0x100 |
| `VIS_SCENERY` | `RANGE_LOC` | 0x20000 |
| `WR_GRND` | `GROUND` | 0x200000 |
| `_BOUNDS` | `BOUNDS` | 0xFFFFFF |
| `PL_WALK_N`, `PL_WALK_NE` and the other six | `BLOCK_ENTER_FROM_NORTH`, `BLOCK_ENTER_FROM_NORTH_EAST` and so on | 0x280102, 0x28010E and so on |

The `BLOCK_ENTER_FROM_*` masks are what the route search tests on the tile it steps into. `PL_WALK_N`, for one, is the north wall plus anything that blocks the whole tile, so it blocks a step south into that tile.

### CollisionMap

```cpp
#pragma once

// One level of the 104x104 build area, indexed by local tile: absolute minus the build area's base.
class CollisionMap
{
public:
    static constexpr s32 SIZE = 104;

    CollisionMap();

    // Open tiles inside, and BOUNDS on the outermost ring.
    void Reset();
    void BlockGround(s32 x, s32 z);
    void AddLoc(s32 x, s32 z, s32 width, s32 length, u8 angle, bool blockRange);
    void AddWall(s32 x, s32 z, u8 shape, u8 angle, bool blockRange);

    [[nodiscard]] u32 GetFlags(s32 x, s32 z) const;
    // Whether a player on (srcX, srcZ) can use the wall or wall decor on (dstX, dstZ).
    [[nodiscard]] bool CanReachWall(s32 srcX, s32 srcZ, s32 dstX, s32 dstZ, u8 shape, u8 angle) const;
    [[nodiscard]] bool CanReachWallDecor(s32 srcX, s32 srcZ, s32 dstX, s32 dstZ, u8 shape, u8 angle) const;
    // Whether a player on (srcX, srcZ) is on the width x length area at (dstX, dstZ), or beside it on a
    // side that forceApproach allows and no wall closes.
    [[nodiscard]] bool CanReachArea(s32 srcX, s32 srcZ, s32 dstX, s32 dstZ, s32 width, s32 length, u8 forceApproach) const;

private:
    void Add(s32 x, s32 z, u32 flags);

    std::vector<u32> m_flags;
};
```

- It ports the build-time half of `CollisionMap.ts` and its three reach tests (`testWall`, `testWDecor`, `testLoc`). `delLoc`, `delWall` and `unblockGround` aren't ported, because the map is rebuilt instead of patched (§1, Rejected).
- `Add` ignores tiles outside the area, as the TS loops do, so a large loc on the edge is cut off instead of written out of bounds.
- `m_flags` holds `SIZE * SIZE` values, indexed `x * SIZE + z` as in the TS.
- The reach tests are ported branch for branch. Their long `if` chains stay as written, because each branch mirrors one case of the webclient's, and tests check them case by case (§15.7).

### WorldMap

```cpp
#pragma once

#include "../../Cache/GameCache_s.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Zone_s.hpp"
#include "../Tile_s.hpp"
#include "CollisionMap.hpp"

// A loc in the build area as it is now: as the server changed it, or else as the cache has it.
struct SceneLoc_s
{
    Tile_s tile;
    LocLayer_e layer = LocLayer_e::Ground;
    // -1 when the server removed it.
    s32 id = -1;
    u8 shape = 0;
    u8 angle = 0;
    bool changed = false;
};

// One account's view of the map: collision for the build area's four levels, and the scenery in it.
// Update rebuilds both from the shared cache and the state whenever the state's build area or loc
// changes have moved on, so they always agree with what the server sent.
class WorldMap
{
public:
    static constexpr s32 LEVELS = 4;

    explicit WorldMap(std::shared_ptr<const GameCache_s> cache);

    void Update(const GameState_s& state);
    // Forgets the area, for a fresh login, which starts the state over.
    void Clear();

    [[nodiscard]] const GameCache_s& GetCache() const;
    [[nodiscard]] bool IsLoaded() const;
    [[nodiscard]] const BuildArea_s& GetBuildArea() const;
    [[nodiscard]] bool Contains(const Tile_s& tile) const;
    [[nodiscard]] const CollisionMap& GetCollision(s32 level) const;
    // nullopt when the tile has nothing in that layer, or is outside the build area.
    [[nodiscard]] std::optional<SceneLoc_s> GetLoc(const Tile_s& tile, LocLayer_e layer) const;
    // Every loc on the level, except ones the server removed.
    [[nodiscard]] std::vector<SceneLoc_s> GetLocs(s32 level) const;

private:
    void Rebuild(const GameState_s& state);
    void AddCollision(s32 level, s32 x, s32 z, s32 id, u8 shape, u8 angle);
    [[nodiscard]] const LocChange_s* FindChange(const Tile_s& tile, LocLayer_e layer) const;

    std::shared_ptr<const GameCache_s> m_cache;
    BuildArea_s m_area;
    std::optional<u64> m_builtAt;
    std::array<CollisionMap, LEVELS> m_collision;
    std::vector<LocChange_s> m_changes;
};
```

- `GameState_s` gains `u64 sceneChangeCount`. The decoders increase it on every change to `buildArea` or `locChanges`: in `DecodeRebuild`, in `ZoneDecoder::SetLoc`, and in `ResetZone` and `PruneInactive` when they erase a loc change. `Update` rebuilds when the area is loaded and the count differs from `m_builtAt`.
- `GameClient` owns a `WorldMap`. It calls `Update(m_state)` at the end of each `Pump`, and `Clear()` where a fresh login resets `m_state`; otherwise the restarted count could come round to the old value and leave the map stale. `GameClient::GetMap()` returns `const WorldMap&`.
- An account that never walks still pays for rebuilds. Each takes under a millisecond, and they only happen on a map rebuild or a loc change, not every tick.
- `m_changes` copies `locChanges` at each rebuild, so `GetLoc` and `GetLocs` don't depend on the state staying in place. It holds tens to a few hundred entries.

### Rebuild

This follows `ClientBuild` and `Client.locChangeUnchecked`:

1. `Reset` each level.
2. Take each square from `(centreZoneX − 6) / 8` to `(centreZoneX + 6) / 8`, and the same for z, that's in the cache:
    - Block each of its blocked tiles that falls inside the area.
    - For each loc whose local tile is strictly inside the area (1 to 102, as `loadLocations` requires), add its collision, unless a loc change covers its tile and layer.
3. For each loc change with an id of 0 or more and a local tile from 1 to 102, add its collision on the change's level.

- A loc change replaces every cached loc in its layer on its tile. There's almost always only one; the webclient replaces the one its scene holds there.
- Squares the cache doesn't have are open ground, apart from the bounds.
- Decoration dropped at load (§7.4) has no collision, so the collision matches the webclient's. `GetLoc` and `GetLocs` never return it.
- `GetLoc` looks for a change first, then for the cache's first loc in that layer on that tile. `GetLocs` goes through the same squares as the rebuild, adds the changed locs, and leaves out the ones a change removed.
- A change's level is the level in its tile, which the zone decoder sets to the local player's. Cached locs are already on the levels they're seen on (§7.4), so changes and cached locs meet on the same level, as they do in the webclient after `finishBuild`.

---

## 11. Paths

### PathFinder

```cpp
#pragma once

#include "../Tile_s.hpp"
#include "WorldMap.hpp"

enum class RouteKind_e : u8
{
    // Stop on the tile.
    Tile,
    // Stop where the wall or wall decor on the tile can be used.
    Wall,
    // Stop on or beside the width x length area whose south-west tile is the target.
    Area,
};

struct RouteTarget_s
{
    RouteKind_e kind = RouteKind_e::Tile;
    Tile_s tile;
    // Tile: when the tile can't be reached, stop on the reachable tile around it that's fewest steps away.
    bool tryNearest = false;
    // Wall: the loc's shape and angle.
    u8 shape = 0;
    u8 angle = 0;
    // Area: already turned for the loc's angle.
    u8 width = 1;
    u8 length = 1;
    u8 forceApproach = 0;
};

class PathFinder
{
public:
    static constexpr std::size_t MAX_WAYPOINTS = 25;

    PathFinder() = delete;

    // The waypoints the webclient would send: the turning points of a shortest route, from the first turn
    // after the start to the stop tile, as absolute tiles on the start's level, cut to MAX_WAYPOINTS. When
    // the start already reaches the target, the start is the one waypoint. nullopt when nothing reaches
    // the target, or when the start or the target is outside the build area.
    [[nodiscard]] static std::optional<std::vector<Tile_s>> FindPath(const WorldMap& map, const Tile_s& start, const RouteTarget_s& target);
};
```

- The search runs on `map.GetCollision(start.level)`, the level the server reports for the player, as `tryMove` uses `collision[minusedlevel]`.
- It's breadth-first over the 104x104 area, with the step and distance arrays local to the call (about 50 KB). Neighbours are tried in the webclient's order: west, east, south, north, south-west, south-east, north-west, north-east. Each step tests the `BLOCK_ENTER_FROM_*` mask of the tile it enters, and a diagonal step also needs both straight steps beside it open. Ties between routes of equal length break the same way as the webclient's, so the server sees the waypoints a real client would send.
- Arrival is checked when a tile is taken off the queue, in `tryMove`'s order. The tile itself always arrives. A Wall target then tries `CanReachWall` for shapes 0–3 and 9, and `CanReachWallDecor` for shapes 0–8, which is what `tryMove`'s `shape + 1` encoding works out to. An Area target tries `CanReachArea`.
- `tryNearest` only applies to Tile targets. When the search ends without arriving, it scans the 3x3 tiles around the target and takes the one with the fewest steps, below 100, scanning x then z as `tryMove` does.
- The route is traced back from the stop tile, keeping each tile where the direction changes, and reversed.

### GameActions

`GameActions` gets its routes from `PathFinder`, with `m_client.GetMap()` and the local player's tile:

| Request | Route | Without a route |
|---|---|---|
| `WalkTo(tile)` | Tile with `tryNearest`, sent as `MOVE_GAMECLICK`. Returns `true` when it sent a walk | For a tile in the build area, returns `false` and sends nothing. For one outside it, or before the first rebuild, it sends today's single straight-line waypoint and returns `true` |
| NPC and player interactions | Area 1x1 on the entity's tile, as the webclient uses for an NPC of any size. `MOVE_OPCLICK`, then the op | The op alone, as the webclient sends it when `tryMove` fails |
| Loc interactions (options, items, spells) | The loc with that id on the tile, from `WorldMap::GetLoc` in each layer. Shapes 10, 11 and 22 route to an Area of the type's width and length, swapped for angles 1 and 3, with `forceApproach` turned by the angle as `interactWithLoc` does it: `((f << angle) & 0xF) + (f >> (4 - angle))`. Other shapes route to a Wall with the loc's shape and angle | The op alone. When the map has no loc with that id on the tile, today's single waypoint on the tile |
| Ground item interactions | Tile on the item's tile, and when that fails, Area 1x1 on it, as the webclient does | The op alone |
| `WalkPath` and the `*Via` overloads | The caller's waypoints, unchanged | Not applicable |

- The server already follows a moving NPC or player each tick ([tcp-protocol-289.md](tcp-protocol-289.md#movement)), so the route only has to get the walk started.
- `WalkTo` returning `bool` is the one signature change in `GameActions`. `ScriptApi::WalkTo` passes the result on.
- A walk without a route is logged at Verbose, with its start and destination.

---

## 12. Script API

Phase 2 adds names and types, phase 3 scenery, and phase 4 reachability and routes. ScriptingApi.md, the stubs in `scripts/typings/__builtins__.pyi` and the prelude's classes change with each phase.

### Objects

| Class | Gains |
|---|---|
| `Npc` | `name` (`None` when the type has none, or isn't in the cache), `combat_level` (`None` when the menu shows none) and `size` |
| `GroundItem`, `Item` | `name` |
| `Loc` | `name`, and `changed`, which is `False` for scenery as the cache has it |
| `NpcType` (new) | `id`, `name`, `examine`, `ops` (five strings or `None`), `size` and `combat_level` |
| `ItemType` (new) | `id`, `name`, `examine`, `ops` (on the ground), `inventory_ops`, `stackable`, `members`, `value`, and `note_of`: `None`, or the id of the item it's a note of |
| `LocType` (new) | `id`, `name`, `examine`, `ops`, `width`, `length`, `blocks_walk` and `blocks_projectiles` |

Names are exactly as the cache has them, case included.

### Functions

| Function | Phase | Returns or does |
|---|---|---|
| `get_npc_type(id)`, `get_item_type(id)`, `get_loc_type(id)` | 2 | The type, or `None` for an id the cache doesn't have |
| `get_nearest_npc_by_name(names, radius=None, in_combat=None)` | 2 | Like `get_nearest_npc_by_id`, matching names instead of ids |
| `get_nearest_ground_item_by_name(names, radius=None)` | 2 | Likewise for ground items |
| `get_inventory_item_by_name(names, com=INVENTORY)`, `get_inventory_count_by_name(names, com=INVENTORY)` | 2 | Likewise for inventories |
| `op` as text | 2 | Every action that takes `op` also takes the option's text, matched without regard to case, as in `interact_npc(npc, 'Pickpocket')`. Ground items also offer "Take" for op 3 and inventory items "Drop" for op 5, as the menu does. Text that matches no option raises `ValueError`, listing the options there are. `inv_button` keeps taking numbers, because its options come from the interface, whose options aren't kept |
| `get_loc_at(x, z, layer=None)` | 3 | The scenery on the tile now: the server's change, or else the cache's, apart from decoration with no name, no option and no collision (§7.4). Before this, only changes |
| `get_locs(ids=None, radius=None, layer=None)` | 3 | Every `Loc` on your level in the build area, nearest first |
| `get_nearest_loc_by_id(ids=None, radius=None, layer=None)`, `get_nearest_loc_by_name(names, radius=None, layer=None)` | 3 | The nearest matching `Loc`, or `None` |
| `interact_loc(loc, op)` | 3 | `interact_loc(id, x, z, op)` still works, and a `Loc` can stand in for the first three arguments |
| `walk_to(x, z, run=False)` | 4 | Routes around obstacles (§11). Returns `True` when it sent a walk, and `False` when the tile is in view but can't be reached |
| `is_reachable(x, z)` | 4 | Whether a walk can end on the tile |
| `find_path(x, z)` | 4 | The `(x, z)` waypoints `walk_to` would send, or `None` |
| `reachable=False` | 4 | A new keyword on every `get_nearest_*` function. `True` skips targets the path finder can't reach, by the same rule as the matching interaction. "Nearest" still counts tiles, not steps |

- `names` takes one name or a list. A type without a name never matches.
- The `ids` arguments are unchanged.
- `walk_path(points)` keeps sending straight lines, so a script can still choose its own waypoints.

### C++ side

- Phase 2 gives `ScriptApi` a `const GameCache_s&`. Phase 3 replaces it with a `const WorldMap&`, and types come from `WorldMap::GetCache()`. `ScriptHost` passes `client.GetCache()`, then `client.GetMap()`.
- `SearchFilter_s` gains `std::vector<std::string> names`, and one matching function handles both ids and names.
- `PyConvert` converts the three type structs and the new attributes, turning option ids into text with `GameCache_s::GetOption`. The prelude defines `NpcType`, `ItemType` and `LocType` as plain classes, like the existing ones.
- Matching an option's text compares it with the type's option strings. It doesn't use the ids, so a script never sees them.
- Each new binding parses its arguments as the existing ones do, and `op` accepts `int` or `str`.

### Porting from plutonium

The porting lists in ScriptingDesign §6 and ScriptingApi.md change:

- `walk_path_to(x, z)` becomes `walk_to(x, z)`, `calculate_path_to(x, z)` becomes `find_path(x, z)`, and `is_reachable(x, z)` exists.
- `get_item_name(id)` becomes `get_item_type(id).name`.
- `get_nearest_object_by_id` becomes `get_nearest_loc_by_id`, and `at_object(obj)` becomes `interact_loc(loc, 1)`.

ScriptingDesign §10's "Packet-only world" item, ScriptingApi's Limits section, and README's list of limits are replaced with what's still missing: interface definitions, beyond finding the components the client uses (§6), and that `get_nearest_*` measures in tiles, not steps.

---

## 13. Changes to existing code

| Code | Change | Phase |
|---|---|---|
| `vcpkg.json`, `CMakeLists.txt` | `bzip2` and `zlib` (§2) | 1 |
| `.gitignore` | `cache/` | 1 |
| `ConfigFile` | §9 | 1 |
| `Application` | Loads the cache and passes it on (§8) | 1 |
| `AccountRunner`, `Account` | Take the cache after the config, and pass it to `GameClient` | 1 |
| `GameClient` | Takes the cache, adds `GetCache()`, and gives `LoginHandshake` the CRCs. In phase 3 it owns a `WorldMap`, updates it in `Pump`, clears it on a fresh login, and adds `GetMap()`. Its logout clicks use the cache's `logoutComponent`. `ScriptApi` and the script constants `INVENTORY`, `EQUIPMENT`, `BANK`, `BANK_INVENTORY` and `INVENTORY_SIZE` read the cache's ids, as do `is_running()` and `set_run(run)` | 1, 3 |
| `LoginHandshake`, `LoginError` | §9 | 1 |
| `ScriptApi`, `ScriptBindings`, `PyConvert`, the prelude, `__builtins__.pyi`, `ScriptHost` | §12 | 2–4 |
| `pch.hpp` | `<unordered_set>` (2) and `<bitset>` (3) | 2, 3 |
| `GameState_s` | `sceneChangeCount` | 3 |
| `ServerPacketDecoder`, `ZoneDecoder` | Increase `sceneChangeCount`. `GetLayer` moves to `LocShape` | 3 |
| `GameActions` | Routes (§11), and `WalkTo` returns `bool` | 4 |
| README | Requirements (the cache instead of the CRCs), configuration, the limits under "Writing scripts", the project layout and the documentation table | 1–4 |
| ConfigDesign.md, ScriptingDesign.md, ScriptingApi.md | §9 and §12 | 1–4 |
| Tests | Every `GameClient`, `Account` and `AccountRunner` a test builds gets `std::make_shared<const GameCache_s>()`. `NetTests` passes CRCs 1 to 9 directly instead of through `login.crcs`. `ConfigFileTests` loses the CRC cases and gains `cacheDirectory` and the leftover-key warning | 1 |
| `CacheLoader`, `MapSquare`, `GameCache_s`, `ConfigFile` (`client.decodedCacheFile`), `.gitignore` (`cache.bin`) | §17 | 5 |

---

## 14. Differences from the webclient

### Kept on purpose

- The outer ring of the build area is `BOUNDS`, and cached locs on it are skipped, as in `loadLocations`.
- Routes run on the collision of the level the server reports for the player.
- NPCs and players are reached as 1x1 targets on their tile, whatever the NPC's size.
- The search's neighbour order, the 25-waypoint cut and `tryNearest`'s 3x3 scan, so the waypoints match what a webclient would send.
- An interaction sends its op even without a route.
- A Wall route tests walls for shapes 0–3 and 9, and wall decor for shapes 0–8.
- Bridges move blocked tiles and locs one level down, and anything that lands below level 0 is dropped.

### Deliberate deviations

- Everything is decoded at load, instead of through small per-type caches and maps fetched for each rebuild (§1).
- An unknown opcode throws instead of putting the rest of the definition out of step.
- Members items keep their names on free worlds.
- Locs with no name, no option and no collision are dropped at load (§7.4). The webclient keeps them to draw.
- Collision is rebuilt instead of patched (§1).
- `lowMemory` changes nothing here. The webclient's low-memory build skips some decor and levels for rendering; this builds all four levels.
- A square missing from the cache is open ground. The webclient also blends the terrain around it, which means nothing without graphics.

---

## 15. Test plan

### 15.1 Strategy

- Unit tests build their inputs in memory. `CacheWriter` writes stores into a `TempFolder` for the store, archive, decoder and loader tests. Tests of `WorldMap`, `PathFinder`, `GameActions` and the script API build a `GameCache_s` in place.
- `CacheWriter` writes the formats on its own, following `FileStream.write` and §3 to §7, and compresses with the same libraries. Values taken from the real cache (§15.8) check the reader and the writer against the engine, so a mistake shared by both doesn't go unnoticed.
- As in PacketDesign §7.1, values that can't be worked out by hand (name hashes, CRCs, counts and names) were taken once from the TS sources and the real cache, and are plain constants in the tests.

### 15.2 CacheWriter

`tests/Cache/CacheWriter.hpp/.cpp`, a test helper:

- `Put(store, file, bytes)` collects files, and `Write(directory)` writes `main_file_cache.dat` and the five index files. Each file's sectors follow one another from sector 1. It also returns the bytes it wrote, so error tests can damage one field and write them back.
- `Bzip2Headerless(data)` calls `BZ2_bzBuffToBuffCompress` with block size 1 and drops the first 4 bytes. `Gzip(data, version)` calls `deflateInit2` with `16 + MAX_WBITS` and appends the 2-byte version.
- `MakeArchive(entries, compressWhole)` builds a JAG archive either way.
- `MakeTypeFiles(definitions)` builds a `.dat` and `.idx` pair from each definition's bytes. Tests write definitions opcode by opcode with `Packet`.
- `MakeLand(flags)` and `MakeLocFile(locs)` build map files, with `smart` values on both sides of 128.
- `MakeInterfaces(components)` builds the `interface` archive's `data` entry. Each component's type and button type fields get sample values, in `IfType.init`'s order, with both forms of every variable-size field: a model and an animation with and without their second byte, and an inventory slot with and without a background.
- `MakeStore(contents)` builds a whole store: archives 1 to 8 (filler bytes where nothing is decoded), a `config` with the given types, an `interface` with the given components, a `versionlist` with a `map_index`, and the squares' files.

### 15.3 Store, compression and archives

- **Store:** a file of one sector, of 1,300 bytes (three sectors), and of exactly 512 bytes; a file in store 4; entries that are absent (size 0, sector 0, past the count). Each damage throws, naming the store and file: a sector header with the wrong file, part or store; a next sector past the end; a chain that ends early; a size over the limit. A missing `.dat`, and a read from a store whose index is missing, throw too.
- **Compression:** round trips of small data and of 300 KB, which spans several bzip2 blocks. An `expectedSize` one too small or too large throws, and so do truncated and garbage input. `Gunzip` round-trips, and throws for truncated data and for output over the limit.
- **JagArchive:** the same entries packed both ways read the same. The three known name hashes, and `HashName("")` is 0. A missing name gives `nullopt`. An entry past the end of the data, or a header whose sizes don't fit, throws.

### 15.4 Definitions

- For each type, one definition that uses every opcode in its tables, kept and dropped, followed by a minimal one. The second must decode correctly, which checks every value size.
- "hidden" in any case is stored as `NO_OPTION` for locs, NPCs and ground options; inventory options keep it.
- **TextPool:** the same text interns to the same view. Views stay valid after the pool is moved. Option ids start at 1 in the order first seen, empty text is `NO_OPTION`, and `GetOption` gives the text back. A string longer than `CHUNK_SIZE` gets its own chunk.
- `active`: models from opcode 5; from opcode 1 with first shape 10; from opcode 1 with first shape 22 (inactive); options only; opcode 19 with 0 overriding options.
- Opcode 74 clears `blockWalk` and `blockRange`.
- Notes: name, members and cost from the link; the examine text with "a" and with "an"; `noteOf`; a missing link throws.
- Errors: an unknown opcode (the message has the type, id and opcode), a definition shorter or longer than its size, a count mismatch, and a string without its `\n`.
- **InterfaceDecoder:** every type and button type, with layers, a hover layer, conditions and scripts, decodes in order, with its type, button type, client code, operands and scripts. An inventory's size, use flag, slot backgrounds and options are kept, and an inventory without them has none. A file with no components gives none. Errors name the component: an unknown type, fields that run past the end, a string without its `\n`, and an id cut short.

### 15.5 Maps

- **Land:** each opcode range; the last flags win; a file one byte short or one byte long throws.
- **Locs:** `smart` values of 127 and 128 for both deltas; a position with level 3, x 63 and z 63; shape and angle unpacked; sorted by tile, keeping id order within a tile.
- **Bridges:** `LinkBelow` on level 1 moves level-1 and level-2 locs and blocked tiles down one level; a level-0 loc on a bridge is dropped; a tile without the flag is unchanged.
- **Decoration:** a loc whose type has no name, no option and no collision is dropped. Each of these is kept: a type with only a name, one with only an option, a nameless wall that blocks walking, and nameless active ground decor that blocks. Nameless ground decor that blocks but isn't active is dropped. A loc id with no type throws.
- **Index:** three entries decode; a length that isn't a multiple of 7 throws.

### 15.6 CacheLoader and config

- A whole synthetic store loads. The CRCs equal `Packet::GetCrc` of each archive's bytes, a missing archive gives 0, and the types and squares are there.
- A missing folder or `.dat` gives the message in §8. A missing `config` archive, a missing entry and a damaged map file each throw with the folder, store, file and square in the message. So do a varp that doesn't decode, a `config` without the run varp, a missing `interface` archive, one without `data`, one whose components don't decode, and one without each of the components, each naming what its rule marks.
- The loaded cache has each component's id, the inventory's size and the run varp, with a decoy varp button before the run buttons.
- A square without files is skipped with the warning, and the Info line is logged (`LogCapture`).
- Config: `cacheDirectory` defaults to `cache`, an empty one fails `Validate`, and the serialized sample has it and no `crcs`. A leftover `login.crcs` or `client.logoutComponent` logs its warning, and the file still loads.
- `NetTests`: the login request carries the CRCs it was given, in order.

### 15.7 Collision, WorldMap and paths

- **CollisionMap:** `Reset` makes the ring `BOUNDS` and leaves the inside open. `AddWall` for each shape and angle sets the flags on both sides, in a table taken from `CollisionMap.ts`. `AddLoc` with angle 1 swaps width and length, `blockRange` adds the range flags, and parts outside the area are ignored. The reach tests are checked against a table of shape, angle and source tile, with each row's expected result taken from the TS branches.
- **WorldMap:** it rebuilds only when `sceneChangeCount` moves. A door (a wall) in the cache blocks. A change with id -1 on the door's tile and layer opens it, and a change to another id applies that type instead. `ResetZone` brings the cache's door back. `Clear` forgets the area. Squares at the area's corners are included, and locs on the outer ring are ignored.
- **PathFinder:** a straight line in the open is one waypoint. A route around a wall has only its turning points. A diagonal step past a corner is refused. A tie between equal routes produces fixed waypoints. Unreachable gives `nullopt`. `tryNearest` stops beside an unreachable tile. A door is reached from either side as a Wall target, and a 2x2 tree from any side as an Area target, except a side `forceApproach` forbids. A route with more than 25 turns is cut to 25. A start or target outside the area gives `nullopt`, and a start on the target gives the start.
- **GameActions,** with `FakeGameServer` and a cache built in place: `WalkTo` sends a routed `MOVE_GAMECLICK`; an unreachable `WalkTo` sends nothing and returns `false`; a loc interaction sends `MOVE_OPCLICK` with the route and then `OPLOC`; an interaction without a route sends only the op.

### 15.8 The real cache

Tagged `[RealCache]`. Each test reads the folder from the `RS2004_CACHE_DIR` environment variable and calls Catch2's `SKIP` when it isn't set, so the suite passes without the cache. To run them: set `RS2004_CACHE_DIR` to `../289server/engine/data/pack`, then run `ctest` as usual.

- The CRCs equal the nine values in §5.
- The components and the run varp are the ids in §6's table: logout 2458, inventory 3214 with 28 slots, equipment 1688, bank 5382, the backpack beside the bank 2006, run off 152, run on 153, and varp 173.
- 5,116 locs, 1,596 NPCs and 4,089 objs, with 219 distinct options. 534 squares, keeping 567,454 locs and holding 543,497 blocked tiles.
- NPC 41 is "Chicken", with op 2 "Attack", size 1 and combat level 1. NPC 1 is "Man", with "Talk-to", "Attack" and "Pickpocket".
- Obj 995 is "Coins", stackable. Obj 526 is "Bones", with inventory op 1 "Bury". Obj 1511 is "Logs", with ground op 4 "Light". Obj 1512 is a note of 1511, named "Logs", and stackable.
- Loc 1276 is "Tree", 2x2, with op 1 "Chop down". Loc 1530 is "Door", with op 1 "Open". Loc 2213 is "Bank booth", with ops "Use" and "Use-quickly", and blocks walking but not projectiles.
- Square (38, 53) has loc 2213 at absolute tile (2444, 3424), on level 1, with shape 10 and angle 1.
- The load time is logged, not asserted.

### 15.9 Scripts

For each phase's API: the names on objects; type lookups, with `None` for an unknown id; options by text, including "Take", "Drop" and the `ValueError`; the `_by_name` functions; `get_loc_at` for cached and changed scenery; `get_locs` order and filters; `interact_loc(loc, op)`; `walk_to`'s routes and result; `is_reachable`; `find_path`; and the `reachable=` filters. The example scripts still load.

### 15.10 Done when

Each phase ends with the tests passing on both presets (`windows-msvc` and `linux-clang`) with no warnings, plus a manual check against a local 289 engine with `client.cacheDirectory` pointing at its `engine/data/pack`:

1. An account logs in with no `login.crcs` in the config.
2. A script logs the names of the NPCs and ground items around it.
3. A script finds a bank booth with `get_nearest_loc_by_name` and uses it.
4. A script walks between two tiles that a straight line can't join, such as from inside a building to outside it.

Phase 5 has its own check (§17).

---

## 16. Implementation order

**Phase 1: store and CRCs.** The client logs in with CRCs from the cache.

1. vcpkg and CMake dependencies, `CacheError`, `Compression` and its tests, and the store, compression and archive parts of `CacheWriter`.
2. `CacheStore` and its tests.
3. `JagArchive` and its tests.
4. `GameCache_s` with only `crcs`, and a `CacheLoader` that computes the CRCs. Its tests, and the real-cache CRC test.
5. The config change (§9), `LoginHandshake` and `LoginError`, and the wiring from `Application` down to `GameClient`. Update the tests that build clients, and the README and ConfigDesign.

**Phase 2: definitions.** Scripts see names and options.

1. `<unordered_set>` in the PCH, `TextPool`, the type structs and `TypeDecoder`, with their tests. The loader decodes `config`, and the real-cache type checks are added.
2. Names, types, options by text and the `_by_name` functions in the script API, with ScriptingApi.md and the stubs.

**Phase 3: maps and scenery.** Scripts see scenery the server never changed.

1. `<bitset>` in the PCH, `MapSquare`, and `MapDecoder` with the decoration filter, with their tests. The loader decodes the maps, and the real-cache map checks are added.
2. `LocShape` (taking `GetLayer` from `ZoneDecoder`), `CollisionFlag`, and `CollisionMap`'s build half, with tests.
3. `sceneChangeCount`, `WorldMap` and its tests, and `GameClient` owning it.
4. `get_loc_at` over cached scenery, `get_locs`, the nearest-loc functions and `interact_loc(loc, op)`, with their docs.

**Phase 4: paths.** Walks and interactions route around walls.

1. `CollisionMap`'s reach tests, then `PathFinder`, with tests.
2. Routes in `GameActions`, with tests.
3. `walk_to`'s routes, `is_reachable`, `find_path` and `reachable=`. ScriptingDesign §10, ScriptingApi's Limits and porting sections, and README's limits change to match.

**Phase 5, optional: one file for several processes.** Processes on one machine share one copy of the cache (§17).

1. `MappedFile` and its tests.
2. `CacheFile`, which writes the format and reads it back, with its tests.
3. `client.decodedCacheFile`, the new startup in `CacheLoader`, and `MapSquare` and `GameCache_s` reading from the mapping, with their tests and the real-cache checks.

---

## 17. Phase 5: one mapped file for several processes

pocketpy's 16 interpreter slots cap a process at 16 accounts, so more accounts take more processes, and phases 1 to 4 give each process its own 5.3 MB copy. Phase 5 is optional, and it pays off when several processes run on one machine. The first process writes the decoded cache to a file, and every process maps that file read-only. The operating system then keeps one physical copy for all of them, and never reads the pages of map squares that no account visits. With 64 accounts in four processes, the cache takes about 7.5 MB in all instead of 21 MB.

### Decisions

| Topic | Decision |
|---|---|
| File | `client.decodedCacheFile`, default `"cache.bin"`, relative to the working directory and git-ignored. It's derived data, so deleting it only costs the next start a full decode |
| Key | The header holds a magic number, a format version and the nine CRCs. Everything the file is built from is in store 0: `config` holds the types, and `versionlist` holds `map_index` and the CRC of every map file, so a changed map file changes `versionlist` and its CRC. The nine CRCs therefore identify the contents, and a file whose header doesn't match the store is rebuilt |
| Startup | Compute the CRCs, which reads only store 0 (about 750 KB). When the file's header matches, map it. Otherwise decode the store as phases 1 to 4 do, write the file under a temporary name in the same folder (`cache.bin.<process id>.tmp`), rename it into place, and map it |
| Mapping | `MappedFile`, in `Core/`: a whole file, mapped read-only and unmapped by its destructor. `CreateFileMappingW` and `MapViewOfFile` on Windows; `mmap` with `PROT_READ` and `MAP_SHARED` on Linux. The platform code stays in `MappedFile.cpp`, behind `#ifdef _WIN32` (CONVENTIONS §9) |
| Format | Little-endian, written field by field through `Endian` (CONVENTIONS §9): a header with a table of sections, then the text, the option table, the three type tables, a sorted index of squares, and for each square its bitset and its 6-byte loc records |
| Mapped | The map squares and the text, almost 90% of the data. The types are decoded from the file into ordinary structs at startup, about 0.7 MB per process, so `FindLoc` and the others still return `const LocType_s*`. Their names point into the mapped text, and `GameCache_s` owns the `MappedFile` that keeps it there |
| Reading | No struct is laid over the mapped bytes, which CONVENTIONS §9 rules out. `MapSquare` keeps its functions; inside, it holds a pointer into the mapping and reads each record through `Endian`. `GetLocsAt` and `GetLocs` return a small range that yields `MapLoc_s` by value, instead of a span |
| Memory | The mapped part counts once in physical memory across all the processes, and only the pages that are touched are loaded. Each process keeps its own types (0.7 MB), the square index, and its accounts' collision maps |

### Ready from phase 1

Two rules in phases 1 to 4 keep phase 5 inside `Cache/`:

- Outside `Cache/`, map squares are read only through `MapSquare`'s functions, and loc records by value through `MapLoc_s`'s accessors.
- Type text is read only through the `std::string_view` fields and `GameCache_s::GetOption`.

Phase 5 then changes `CacheLoader`, `MapSquare`, `GameCache_s` and `ConfigFile`, and adds `CacheFile` and `MappedFile`. `WorldMap`, `PathFinder`, `GameActions` and the script API stay as they are.

### Behaviour

- `CacheLoader::Load` gains the file's path. It logs `Cache mapped from cache.bin` when the file matched, and `Cache loaded from cache; wrote cache.bin` when it had to decode, each with the counts from §8.
- A file shorter than its section table says, or whose sections overlap or run past its end, counts as a mismatch. It's rebuilt, with a Warning.
- The file is never written in place. It only changes by being replaced with a rename, so a process that maps it never sees it change.
- When the rename fails, the process checks the file that's there:
    - If it now matches, another process built it first. The temporary file is deleted, and the existing one mapped.
    - Otherwise, an older process still maps an outdated file, which Windows won't let a rename replace. The process maps its temporary file, deletes it when it exits, and logs a Warning. The next start replaces `cache.bin`.
- A temporary file left behind by a crash is never read. It only takes disk space.

### Rejected

- **Laying structs over the mapped bytes.** It would save decoding, but padding and layout aren't portable, and CONVENTIONS §9 rules it out.
- **A shared memory segment** that the first process creates. Something has to remove it, after a crash too. A mapped file gets the same sharing from the operating system's page cache, and a file nobody uses harms nothing.
- **Mapping the types too.** Every lookup would decode a record. Decoding them once costs 0.7 MB per process, and keeps `FindLoc` and the others returning pointers.
- **One process serving the cache to the others.** Every lookup would be a round trip between processes.
- **Writing the file into `client.cacheDirectory`.** That folder may be the server's own data folder.

### Tests

- A synthetic cache written to the file and mapped back gives the same CRCs, types, options, squares, blocked tiles and loc records as the cache it was written from.
- A header with another version, or with one CRC changed, is rebuilt. So is a truncated file, with a Warning.
- A second load maps the existing file without decoding the store.
- A rename onto a file that already matches keeps the existing file and deletes the temporary one.
- `MappedFile` maps a file's bytes, and throws for a missing or empty file.
- With the real cache, the mapped cache gives the values in §15.8.

### Done when

The tests pass on both presets, and two processes on one machine map the same `cache.bin`. The second starts without decoding the store, and a process monitor shows the mapped pages as shared, not private.
