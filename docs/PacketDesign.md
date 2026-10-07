# Packet I/O Design

Design and test plan for the C++ port of the 289 webclient's packet buffer, ISAAC cipher, and the big-integer support behind RSA. Code style follows [CONVENTIONS.md](../CONVENTIONS.md). None of these classes log: their callers log the failures they handle, through `Logger` from [LoggerDesign.md](LoggerDesign.md).

Reference sources:

- `rs2b0t/289server/webclient/src/io/Packet.ts`
- `rs2b0t/289server/webclient/src/io/Isaac.ts`
- `rs2b0t/289server/webclient/src/util/JsUtil.ts`: only `bytesToBigInt`, `bigIntToBytes`, `bigIntModPow`
- `rs2004-headless - Copy/headless-client/src/big_uint.cpp`: requirements for `BigUInt`

---

## 1. Decisions

| Topic | Decision |
|---|---|
| Method names | Mirror TS in PascalCase (`G1`, `P1Enc`, `GJStr`, ...) so `Client.ts` ports line by line |
| Pooling | `alloc`/`release` and the size-class cache are omitted. The client only used `alloc` for three long-lived buffers and never called `release` |
| Threading | Single-threaded. There is no static mutable state; an instance is not synchronized |
| Modes | A packet is either a reader over bytes it doesn't own or a writer into a vector it grows. The constructor picks the mode; calling a function from the other mode is a bug and asserts |
| Out-of-range access | A read past the end throws `std::out_of_range`, leaving the packet unchanged. Writes never run out of room |
| ISAAC | The packet holds no cipher. `P1Enc` and `G1Enc` take the caller's `Isaac` per call |
| Logging | None. `Packet`, `Isaac` and `BigUInt` don't log, so none of them takes a logger. They are pure and on the hot path, and every failure is an exception that the caller logs where it handles it ([LoggerDesign.md](LoggerDesign.md) §4). `GJStr` running off the end of the buffer returns what TS returns, without a warning (§3) |
| Tests | Hand-written spec tests. The few expected values that can't be worked out by hand were taken once from the TS sources and are listed in this document |

---

## 2. Layout

| TS | C++ |
|---|---|
| `io/Packet.ts` | `src/Io/Packet.hpp` / `.cpp` |
| `io/Isaac.ts` | `src/Io/Isaac.hpp` / `.cpp` |
| `util/JsUtil.ts` RSA helpers | `src/Core/BigUInt.hpp` / `.cpp` |
| (convention) | `src/Core/Endian.hpp`, verbatim from CONVENTIONS §9 |
| (logging) | `src/Core/Logger.hpp` / `.cpp`, specified in [LoggerDesign.md](LoggerDesign.md) |

```
rs2004-headless/
├── CMakeLists.txt
├── CMakePresets.json
├── vcpkg.json
├── docs/
│   ├── LoggerDesign.md
│   └── PacketDesign.md
├── src/
│   ├── pch.hpp
│   ├── main.cpp
│   ├── Application.hpp
│   ├── Application.cpp
│   ├── Core/
│   │   ├── BigUInt.hpp
│   │   ├── BigUInt.cpp
│   │   ├── Endian.hpp
│   │   ├── Logger.hpp
│   │   └── Logger.cpp
│   └── Io/
│       ├── Isaac.hpp
│       ├── Isaac.cpp
│       ├── Packet.hpp
│       └── Packet.cpp
└── tests/
    ├── LogCapture.hpp
    ├── LogCapture.cpp
    ├── Core/
    │   ├── BigUIntTests.cpp
    │   └── LoggerTests.cpp
    └── Io/
        ├── IsaacTests.cpp
        └── PacketTests.cpp
```

`Logger`, `LogCapture` and `LoggerTests.cpp` are specified in [LoggerDesign.md](LoggerDesign.md) and implemented right after the project setup (§8).

Not ported: the `Linkable2` base (it only served the pool) and the rest of `JsUtil.ts` (`sleep`, `downloadUrl`, `arraycopy`, `mulShift16`).

`pch.hpp` gains `<compare>` for `BigUInt::operator<=>`.

---

## 3. Packet

### Interface

```cpp
#pragma once

#include "../Core/BigUInt.hpp"
#include "Isaac.hpp"

class Packet
{
public:
    Packet();
    explicit Packet(std::span<const u8> data);

    [[nodiscard]] static s32 GetCrc(std::span<const u8> source);
    [[nodiscard]] static bool CheckCrc(std::span<const u8> source, s32 expected = 0);

    [[nodiscard]] std::span<const u8> GetData() const;
    [[nodiscard]] std::size_t GetLength() const;
    [[nodiscard]] std::size_t GetAvailable() const;
    [[nodiscard]] std::size_t GetPos() const;
    void SetPos(std::size_t pos);

    u8 G1Enc(Isaac& random);
    u8 G1();
    s8 G1B();
    u16 G2();
    s16 G2B();
    s32 G3();
    s32 G4();
    s64 G8();
    s32 GSmart();
    s32 GSmarts();
    std::string GJStr();
    void GData(std::span<u8> destination);

    void P1Enc(Isaac& random, s32 opcode);
    void P1(s32 value);
    void P2(s32 value);
    void IP2(s32 value);
    void P3(s32 value);
    void P4(s32 value);
    void IP4(s32 value);
    void P8(s64 value);
    void PJStr(std::string_view text);
    void PData(std::span<const u8> source);
    void PSize1(std::size_t size);

    void GBitStart();
    void GBitEnd();
    s32 GBit(u32 bitCount);

    void RsaEnc(const BigUInt& modulus, const BigUInt& exponent);

private:
    enum class Mode_e : u8
    {
        Read,
        Write,
    };

    static constexpr u8 STRING_TERMINATOR = '\n';

    [[nodiscard]] std::span<const u8> NextRead(std::size_t count);
    [[nodiscard]] std::span<u8> NextWrite(std::size_t count);
    void RequireBytes(std::size_t count) const;
    void RequireBits(u32 bitCount) const;

    Mode_e m_mode;
    std::span<const u8> m_readData;
    std::vector<u8> m_writeData;
    std::size_t m_pos = 0;
    std::size_t m_bitPos = 0;
};
```

### Behaviour

- **Modes.** The two modes are exclusive, and the constructor picks one.

    | | Read: `Packet{bytes}` | Write: `Packet{}` |
    |---|---|---|
    | Data | Views the caller's `std::span<const u8>`. Nothing is copied, so the bytes must outlive the packet | Owns a `std::vector<u8>` that grows as it is written |
    | `GetData` | The whole span | `[0, pos)` |
    | `GetLength` | The span's size | `pos`, the number of bytes written |
    | `GetAvailable` | `length - pos` | Doesn't apply (asserts) |
    | `SetPos` | Up to the span's size | Up to the furthest byte ever written, so a length placeholder can be patched and pos moved back to the end |
    | Allowed calls | `G*`, `GBit*` | `P*`, `PSize1`, `RsaEnc` |

    - Calling a function from the other mode is a bug, so it asserts.
    - The socket pattern: receive into a buffer the caller owns, then parse it with `Packet{buffer}`.
    - A writer is reused for the next message with `SetPos(0)`. The vector keeps its capacity, and `GetData` only shows what was written since.
- **Construction.**
    - The read constructor takes one argument, so it is `explicit` (CONVENTIONS §8).
    - Port `Packet.alloc(1)` for output as `Packet{}`. There is nothing to size up front.
    - `Packet{std::vector<u8>{...}}` would view a temporary that dies at the end of the statement. Name the bytes first.
- **Copies.**
    - Rule of zero. Copying a reader copies the view; copying a writer copies its bytes.
- **Includes.**
    - `Packet.hpp` includes `Isaac.hpp`, since `Isaac` appears in `P1Enc`'s and `G1Enc`'s prototypes, and `../Core/BigUInt.hpp`, since `BigUInt` appears in `RsaEnc`'s prototype.
    - `Packet.cpp` uses both, so it includes them again, plus `../Core/Endian.hpp`.
- **Byte order.**
    - Big-endian, except `IP2`/`IP4`, which are little-endian.
    - All multi-byte access goes through `Endian::ToBig`/`FromBig`/`ToLittle`/`FromLittle` plus `std::memcpy`, using template helpers in `Packet.cpp`'s anonymous namespace.
    - `G3`/`P3` combine one byte and two bytes, as TS does.
- **Read return types** carry the wire format's width and signedness, the same as DataView:

    | Method | Type | Range |
    |---|---|---|
    | `G1` | `u8` | 0 to 255 |
    | `G1B` | `s8` | -128 to 127 |
    | `G2` | `u16` | 0 to 65535 |
    | `G2B` | `s16` | -32768 to 32767 |
    | `G3` | `s32` | 0 to 16777215 |
    | `G4` | `s32` | full |
    | `G8` | `s64` | full |
    | `GSmart` | `s32` | 0 to 32767 |
    | `GSmarts` | `s32` | -16384 to 16383 |
    | `GBit` | `s32` | bit pattern of up to 32 bits |

    Reads are not `[[nodiscard]]`, because discarding a read just to skip bytes is legitimate.

- **Write parameters** are `s32` (`s64` for `P8`) and are truncated to the field width, like the DataView setters: `P1(-1)` writes `FF` and `P2(0x12345)` writes `23 45`. Exact-width parameters would force casts at hundreds of call sites under `/W4` with warnings treated as errors.
- **Bounds.**
    - Every read checks its full width before touching any state, and throws `std::out_of_range` with a `std::format` message.
    - Composite reads (`G3`, `GSmart`, `GSmarts`, `G1Enc`, `GBit`) check the whole width up front. A throw therefore leaves `pos` and the cipher unchanged.
    - Writes grow the vector to `pos + width` when they pass its end. A write that starts before the end overwrites the bytes already there and grows only by the rest.
    - Bugs are `assert`s: a call from the wrong mode, `PSize1` with `size + 1 > pos`, a `GBit` width outside 1 to 32, `SetPos` past the end, and `RsaEnc` at `pos == 0`.
- **Strings.**
    - Strings are raw bytes with no encoding conversion, equivalent to `fromCharCode`/`charCodeAt` over 0 to 255.
    - `GJStr` reads up to `\n`, and `PJStr` writes the bytes followed by `\n`.
    - When `GJStr` reaches the end of the buffer without finding `\n`, it returns what TS returns (§6) and logs nothing.
- **Smart values.**
    - Peek at the next byte: below `0x80` the value is one byte, otherwise two.
    - `GSmart` returns `G1()` or `G2() - 0x8000`. `GSmarts` returns `G1() - 0x40` or `G2() - 0xC000`.
    - The thresholds and offsets are named constants in the anonymous namespace.
- **Bit reads.**
    - `GBitStart` sets `bitPos = pos * 8`.
    - `GBit` ports the TS loop with a `constexpr std::array<u32, 33>` of masks.
    - It does all arithmetic in `u32` and returns `static_cast<s32>`, the same bit pattern as TS's int32 shifts, including at width 32.
    - `GBitEnd` sets `pos = (bitPos + 7) / 8`.
- **CRC.**
    - The table is `constexpr`-generated (polynomial `0xEDB88320`), the arithmetic is `u32`, and the result is `static_cast<s32>(~crc)`.
    - The result is signed like TS's, so it compares directly against `G4`.
    - It takes a span. TS's `(offset, length)` actually treats `length` as an end index, and every caller passes `0, data.length`.
- **ISAAC.**
    - The client owns both ciphers (TS `out.random` and `randomIn`) and passes one to each call.
    - `P1Enc(random, opcode)` writes `(opcode + random.NextInt()) & 0xFF`. Unencrypted opcodes use `P1`.
    - `G1Enc(random)` reads a byte and returns `(byte - random.NextInt()) & 0xFF`.
- **`RsaEnc`.**
    1. `m` is the big-endian number in `data[0, pos)`.
    2. `c = BigUInt::ModPow(m, exponent, modulus).ToBytesBigEndian()`.
    3. Throw `std::length_error` if `c.size() > 255`.
    4. Set `pos = 0`, then `P1(c.size())`, then `PData(c)`. When `c` is shorter than the block, `GetData` stops at the new pos, so none of the plaintext shows.
- **Logging.**
    - Nothing in `Packet`, `Isaac` or `BigUInt` logs. A failed bounds check, parse or `ModPow` throws, and the caller logs it where it handles it ([LoggerDesign.md](LoggerDesign.md) §4).
    - Callers never log packet bytes, ISAAC seeds or the RSA block: the login block carries the password.

---

## 4. Isaac

```cpp
#pragma once

class Isaac
{
public:
    explicit Isaac(std::span<const s32> seed);

    [[nodiscard]] s32 NextInt();

private:
    static constexpr std::size_t SIZE = 256;
    static constexpr u32 GOLDEN_RATIO = 0x9E3779B9;

    void Init();
    void Generate();

    std::array<u32, SIZE> m_results{};
    std::array<u32, SIZE> m_memory{};
    u32 m_a = 0;
    u32 m_b = 0;
    u32 m_c = 0;
    u32 m_count = 0;
};
```

- **Seed.** The seed is copied into `m_results[0, n)`, and `assert(n <= 256)` guards the size. The client always passes 4 words.
- **Integer semantics.** All arithmetic is `u32`, so there is no signed-overflow undefined behaviour.
    - TS mixes plain `number` fields with `Int32Array` storage. Every intermediate value is still congruent modulo 2^32, because each one passes through a bitwise operation or an `Int32Array` store before it could pass 2^53.
    - So `u32` arithmetic reproduces TS bit for bit, and the anchor values in §7.3 verify it.
- **Structure.** TS repeats the mixing block three times. It becomes one `Mix(std::array<u32, 8>&)` in the anonymous namespace, and TS's `isaac()` becomes `Generate()`.
- **Count semantics.**
    - `Init()` ends with `Generate(); m_count = 256;`.
    - `NextInt()` does `if (m_count == 0) { Generate(); m_count = 256; }`, then returns `static_cast<s32>(m_results[--m_count])`.
    - This is equivalent to TS's `count-- === 0 ... count = 255`: outputs come from the end of the results array toward the start.

---

## 5. BigUInt

```cpp
#pragma once

class BigUInt
{
public:
    BigUInt() = default;

    [[nodiscard]] static BigUInt Parse(std::string_view text);
    [[nodiscard]] static BigUInt FromBytesBigEndian(std::span<const u8> bytes);
    [[nodiscard]] static BigUInt ModPow(const BigUInt& base, const BigUInt& exponent, const BigUInt& modulus);

    [[nodiscard]] std::vector<u8> ToBytesBigEndian() const;

    [[nodiscard]] std::strong_ordering operator<=>(const BigUInt& other) const;
    [[nodiscard]] bool operator==(const BigUInt& other) const = default;

private:
    static constexpr std::size_t MAX_DIGITS = 1024;

    [[nodiscard]] static BigUInt ParseDigits(std::string_view digits, u32 radix);

    void Normalize();
    [[nodiscard]] bool GetBit(std::size_t bit) const;
    [[nodiscard]] std::size_t GetBitLength() const;
    [[nodiscard]] BigUInt Add(const BigUInt& other) const;
    [[nodiscard]] BigUInt Subtract(const BigUInt& other) const;
    [[nodiscard]] BigUInt AddMod(const BigUInt& other, const BigUInt& modulus) const;
    [[nodiscard]] BigUInt MultiplyMod(const BigUInt& other, const BigUInt& modulus) const;
    void MultiplySmall(u32 factor);
    void AddSmall(u32 value);

    std::vector<u32> m_limbs;
};
```

Limbs are stored least significant first, with no trailing zero limbs, so zero is an empty vector. Mapping from `big_uint.cpp`:

| `big_uint.cpp` | `BigUInt` |
|---|---|
| `parse_hex`, `parse_decimal`, `parse_number` returning `bool` | `Parse`: decimal, or hex after a `0x`/`0X` prefix. Throws `std::invalid_argument` on empty input, a bad digit, a repeated prefix or more than 1024 digits |
| Parsing rejects zero | `Parse` accepts zero; `ModPow` validates its operands |
| `from_bytes_be` | `FromBytesBigEndian`, packing bytes straight into limbs |
| `to_bytes_be(bool signed_padding)` | `ToBytesBigEndian()` always adds the sign-padding byte (the flag was only ever `true`). Zero gives `{}`, matching JS `bigIntToBytes`; the old code returned `{0}` |
| `mod_pow` returning `bool` | `ModPow` returns the result and throws `std::invalid_argument` when `modulus <= 1` or `base >= modulus` |
| `compare`, `is_less_than` | `operator<=>`: limb count first, then limbs from the most significant. It can't be defaulted because the limbs are stored least significant first |

`MultiplyMod` stays shift-and-add, which is fast enough for a public exponent.

---

## 6. Differences from TS

### Kept on purpose

These get a short "why" comment in the code, because they look wrong at first glance:

- `GJStr` without a terminator drops the last byte of the buffer. Calling it at the end throws, just as TS throws a `RangeError`.
- `PSize1` writes at `pos - size - 1`.
- Writes truncate. `G4` and `G8` are signed; `G3` is unsigned 24-bit.
- ISAAC hands out results from the end of the array toward the start.
- `RsaEnc` output layout includes the sign-padding byte.

### Deliberate deviations

| TS | C++ | Why |
|---|---|---|
| `gdata` past the end copies what is left and still advances `pos` | Throws; nothing changes | Network input must not be silently truncated |
| A failed DataView read has already moved `pos` | `pos` and the cipher unchanged | The packet stays in a consistent state after an exception |
| One fixed-size buffer for reading and writing; writing past the end throws a `RangeError` | Exclusive read and write modes; a writer grows | Outgoing packets need no size guess, and incoming bytes are parsed where they were received |
| `out.random` lives on the packet; `p1isaac` uses it | `P1Enc` and `G1Enc` take the cipher as an argument | The client owns both ciphers, and one packet type serves both directions |
| `gdata`, `pdata`, `getcrc` take `(offset, length)` | Take spans | Idiomatic; removes `getcrc`'s end-index quirk |
| `bigIntModPow` accepts `base >= modulus` and `modulus <= 1` | Throws `std::invalid_argument` | The server could not decrypt the result |
| `rsaenc`'s `p1` truncates a length above 255 | Throws `std::length_error` | Only reachable with a modulus over 2040 bits |
| `alloc` / `release` pool | Omitted | Unused by the client |

---

## 7. Test plan

### 7.1 Strategy

All tests are spec tests: hand-written inputs, with expected values written directly into the test source. They are readable and they document the behaviour. The tables below are the test cases, and every case runs in every build configuration.

Most expected values follow directly from the TS semantics. The few that can't be worked out by hand (ISAAC outputs and CRCs) were taken once from the TS sources and are listed here. In the tests they are plain constants; nothing is generated at build or test time.

`PacketTests.cpp` builds readers with `Packet{bytes}` over a named vector that outlives the packet, and writers with `Packet{}`. Round trips read a writer back through `Packet{writer.GetData()}`. None of these classes logs, so no test needs a logger.

Out of scope:

- `assert`-guarded preconditions. They are bugs, not inputs, so there are no death tests.
- Exception message text. Tests check only the exception type.

### 7.2 BigUInt

**Parse, valid input**

| Input | Equals |
|---|---|
| `"0"`, `"000"` | `BigUInt{}` |
| `"255"`, `"0xFF"`, `"0Xff"`, `"0xfF"` | `FromBytesBigEndian({0xFF})` |
| `"000123"` | `Parse("123")` |
| `"4294967296"`, `"0x100000000"` | `FromBytesBigEndian({0x01, 0x00, 0x00, 0x00, 0x00})`, which spans two limbs |
| 1024 x `'9'` | Accepted |
| `"0x"` + 1024 x `'f'` | Accepted |

**Parse, invalid input.** Each of these throws `std::invalid_argument`:

`""`, `"0x"`, `"0x0x1"`, `"12a"`, `"0xg"`, `"-1"`, `"+1"`, `" 1"`, `"1 "`, 1025 x `'9'`, `"0x"` + 1025 x `'f'`

**Ordering**

- `Parse("1") < Parse("2")`
- `Parse("0xFFFFFFFF") < Parse("0x100000000")`: fewer limbs.
- `Parse("0x100000001") < Parse("0x200000000")`: same limb count, top limb differs.
- `Parse("0x100000001") < Parse("0x100000002")`: top limb equal, low limb differs.
- `FromBytesBigEndian({0x00, 0x00, 0x01}) == Parse("1")`: leading zeros are normalised away.

**Byte round trip:** `ToBytesBigEndian(FromBytesBigEndian(input))`

| Input | Output |
|---|---|
| `{}` | `{}` |
| `{00}` | `{}` |
| `{7F}` | `{7F}` |
| `{80}` | `{00 80}` |
| `{00 00 01}` | `{01}` |
| `{01 00 00 00 00}` | `{01 00 00 00 00}` |
| `{FF FF FF FF}` | `{00 FF FF FF FF}` |

**ModPow**

| Base | Exponent | Modulus | Result | Note |
|---|---|---|---|---|
| 4 | 13 | 497 | 445 | |
| 5 | 0 | 7 | 1 | Zero exponent |
| 0 | 5 | 7 | 0 | Zero base |
| 3 | 1 | 7 | 3 | |
| 3 | 5 | 16 | 3 | Even modulus |
| 65 | 17 | 3233 | 2790 | Textbook RSA encryption |
| 2790 | 2753 | 3233 | 65 | Textbook RSA decryption |
| 3 | `0x7FFF...FFE` (2^127 - 2) | `0x7FFF...FFF` (2^127 - 1) | 1 | Fermat's little theorem; 2^127 - 1 is prime; 4 limbs |

Each of these throws `std::invalid_argument`: modulus 0, modulus 1, `base == modulus`, `base > modulus`.

### 7.3 Isaac

**Anchor values**, taken from TS `Isaac`. Output #n is the value returned by the n-th `NextInt()` call. Outputs #256 and #257 fall on either side of the first refill; #512 and #1024 come after later refills.

| Seed | Outputs | Values |
|---|---|---|
| `{1, 2, 3, 4}` | #1, #2, #3 | -621246914, 1957022519, -1345000077 |
| `{1, 2, 3, 4}` | #256, #257 | 681500538, 1010642953 |
| `{1, 2, 3, 4}` | #512, #1024 | -962902924, 392795429 |
| `{0, 0, 0, 0}` | #1, #256, #257 | 405143795, -412232903, 2053665039 |
| `{INT32_MIN, -1, INT32_MAX, 0x12345678}` | #1, #257 | -528844012, -343157757 |

- **Empty seed:** an empty seed gives the same first 1024 outputs as `{0, 0, 0, 0}`.
- **Independence:**
    - Two instances with the same seed produce identical streams.
    - Interleaving draws from two differently seeded instances gives each one's solo stream, which shows there is no shared state.

### 7.4 Packet

**Read mode**

- A reader over 5000 bytes: length 5000, pos 0, available 5000, and `GetData().data()` equals the vector's `data()`, so nothing was copied.
- A reader over an empty span has length 0, and `G1` throws.
- On a length-10 reader, `SetPos(3)` gives available 7 with length and data size still 10, and `SetPos(10)` gives available 0.

**Write mode**

- `Packet{}` has empty data, length 0 and pos 0.
- 2000 `P4` calls give length and pos 8000, and read back unchanged.
- After `P4(0x11223344)`, `SetPos(1)` gives length 1 and data `11`; `SetPos(4)` gives length 4 and data `11 22 33 44`.
- After `P4(0x11223344)`, `SetPos(1)`, `P1(0xAB)`, `SetPos(4)`: data `11 AB 33 44`.
- After `P2(0x1122)`, `SetPos(1)`, `P4(0x33445566)`: data `11 33 44 55 66`, so a write across the end overwrites and then grows.
- After `P4(0x11223344)`, `SetPos(0)`, `P1(0x55)`: data `55`, the reuse pattern for the next message.

**Fixed-width reads**

| Bytes | Call | Value | Pos after |
|---|---|---|---|
| `FF` | `G1` | 255 | 1 |
| `FF` | `G1B` | -1 | 1 |
| `80` | `G1B` | -128 | 1 |
| `7F` | `G1B` | 127 | 1 |
| `12 34` | `G2` | `0x1234` | 2 |
| `FF FF` | `G2` | 65535 | 2 |
| `FF FE` | `G2B` | -2 | 2 |
| `80 00` | `G2B` | -32768 | 2 |
| `12 34 56` | `G3` | `0x123456` | 3 |
| `FF FF FF` | `G3` | 16777215 | 3 |
| `12 34 56 78` | `G4` | `0x12345678` | 4 |
| `FF FF FF FF` | `G4` | -1 | 4 |
| `80 00 00 00` | `G4` | `INT32_MIN` | 4 |
| `01 02 03 04 05 06 07 08` | `G8` | `0x0102030405060708` | 8 |
| `80 00 00 00 00 00 00 00` | `G8` | `INT64_MIN` | 8 |
| `FF` x 8 | `G8` | -1 | 8 |

**Smart reads**

| Bytes | `GSmart` | `GSmarts` | Pos after |
|---|---|---|---|
| `00` | 0 | -64 | 1 |
| `40` | 64 | 0 | 1 |
| `7F` | 127 | 63 | 1 |
| `80 00` | 0 | -16384 | 2 |
| `80 80` | 128 | -16256 | 2 |
| `C0 00` | 16384 | 0 | 2 |
| `FF FF` | 32767 | 16383 | 2 |

**Strings**

| Bytes | Call | Result | Pos after |
|---|---|---|---|
| `61 62 63 0A` | `GJStr` | `"abc"` | 4 |
| `0A` | `GJStr` | `""` | 1 |
| `61 0A 62 0A` | `GJStr` twice | `"a"`, `"b"` | 4 |
| `61 62 63` | `GJStr` | `"ab"` (TS quirk: last byte dropped) | 3 |
| `61` | `GJStr` | `""` (same quirk) | 1 |
| `E9 FF 0A` | `GJStr` | the raw bytes `E9 FF` | 3 |
| pos == length | `GJStr` | throws `std::out_of_range` | unchanged |

**GData**

- Bytes `01 02 03 04 05`, then `SetPos(1)` and `GData` into a 3-byte destination: the destination holds `02 03 04` and pos is 4.
- An empty destination is a no-op, even at the end of the buffer.
- A 3-byte destination with 2 bytes available throws. Pos and the destination are both unchanged (a deviation from TS).

**Writes** (each on a fresh `Packet{}`; `GetData` is exactly the bytes written)

| Call | Bytes written | Pos after |
|---|---|---|
| `P1(0x12)` | `12` | 1 |
| `P1(-1)` | `FF` | 1 |
| `P1(256)` | `00` | 1 |
| `P1(0x1FF)` | `FF` | 1 |
| `P2(0x1234)` | `12 34` | 2 |
| `P2(0x12345)` | `23 45` | 2 |
| `P2(-1)` | `FF FF` | 2 |
| `IP2(0x1234)` | `34 12` | 2 |
| `IP2(-2)` | `FE FF` | 2 |
| `P3(0x123456)` | `12 34 56` | 3 |
| `P3(0x1234567)` | `23 45 67` | 3 |
| `P3(-1)` | `FF FF FF` | 3 |
| `P4(0x12345678)` | `12 34 56 78` | 4 |
| `P4(INT32_MIN)` | `80 00 00 00` | 4 |
| `IP4(0x12345678)` | `78 56 34 12` | 4 |
| `IP4(-1)` | `FF FF FF FF` | 4 |
| `P8(0x0102030405060708)` | `01 02 03 04 05 06 07 08` | 8 |
| `P8(INT64_MIN)` | `80 00 00 00 00 00 00 00` | 8 |
| `P8(-2)` | `FF FF FF FF FF FF FF FE` | 8 |
| `PJStr("abc")` | `61 62 63 0A` | 4 |
| `PJStr("")` | `0A` | 1 |
| `PJStr("\xE9")` | `E9 0A` | 2 |
| `PData({09, 08, 07})` | `09 08 07` | 3 |
| `PData({})` | nothing | 0 |

**Round trips.** These read/write pairs are checked:

`P1`/`G1`, `P1`/`G1B`, `P2`/`G2`, `P2`/`G2B`, `P3`/`G3`, `P4`/`G4`, `P8`/`G8`, `PJStr`/`GJStr`, `PData`/`GData`

For each pair:

1. Write the read type's minimum, maximum, 0 and 1, plus -1 for signed types, in sequence, into a writer.
2. Read every value back unchanged through a reader over the writer's data.
3. Check that the reader has nothing left available.

**PSize1**

- Call `P1(42)`, `P1(0)`, record `start = GetPos()`, then `PJStr("hello")`, `P1(7)`, `PSize1(GetPos() - start)`.
- The data is `2A 07 68 65 6C 6C 6F 0A 07`, and pos is unchanged.
- `PSize1(0)` right after the placeholder writes 0.

**Bounds.** Each read runs with exactly one byte fewer than it needs. It must throw `std::out_of_range` and leave pos unchanged. Writes can't run out, so they have no bounds cases.

| Operation | Bytes needed |
|---|---|
| `G1`, `G1B` | 1 |
| `G2`, `G2B` | 2 |
| `G3` | 3 |
| `G4` | 4 |
| `G8` | 8 |
| `GData` with n bytes | n |
| `GSmart`, `GSmarts` | 1, or 2 when the first byte is `>= 0x80` |
| `GJStr` | 1 (throws only when pos == length) |
| `GBit` | on a 2-byte buffer, `GBit(16)` succeeds and `GBit(17)` throws |

**Bit reads**

| Bytes | Setup | Calls | Results | Pos after `GBitEnd` |
|---|---|---|---|---|
| `B0` | `GBitStart` | `GBit(1)` x 4 | 1, 0, 1, 1 | 1 |
| `AB CD` | `GBitStart` | `GBit(4)`, `GBit(8)`, `GBit(4)` | `0xA`, `0xBC`, `0xD` | 2 |
| `AB CD` | `GBitStart` | `GBit(3)`, `GBit(13)` | 5, `0xBCD` | 2 |
| `FF FF FF FF` | `GBitStart` | `GBit(32)` | -1 | 4 |
| `80 00 00 00` | `GBitStart` | `GBit(32)` | `INT32_MIN` | 4 |
| `12 34 56 78 9A` | `GBitStart` | `GBit(4)`, `GBit(32)` | 1, `0x23456789` | 5 |
| `00 FF` | `G1`, `GBitStart` | `GBit(8)` | 255 | 2 |
| any | `GBitStart` | none | none | 0 |
| any | `GBitStart` | `GBit(9)` | | 2 |

**Width sweep:** test every width from 1 to 32 at every starting bit offset from 0 to 7. Offsets 1 to 7 are reached with a leading `GBit(offset)`.

- On all-`FF` bytes, `GBit(width)` returns the width's mask as `s32`: `(1 << width) - 1`, which is -1 at width 32.
- On all-`00` bytes, it returns 0.

**CRC**

| Input | `GetCrc` |
|---|---|
| `"123456789"` | -873187034 (`0xCBF43926`) |
| `"a"` | -390611389 (`0xE8B7BE43`) |
| `"The quick brown fox jumps over the lazy dog"` | 1095738169 (`0x414FA339`) |
| empty | 0 |

- `CheckCrc("123456789", -873187034)` is true.
- `CheckCrc("123456789", -873187033)` is false.
- `CheckCrc(empty)` is true, because the default expected value is 0.

**ISAAC opcode coding.** A writer runs 600 `P1Enc` calls with a cipher seeded `{1, 2, 3, 4}`, crossing two refills.

- Each byte equals `(opcode + twin.NextInt()) & 0xFF`, where `twin` is a separate `Isaac` with the same seed.
- A reader over those bytes, calling `G1Enc` with another same-seed cipher, gets back every opcode.
- `G1Enc` at the end of the reader throws without moving pos or advancing the cipher. After `SetPos(0)`, the next `G1Enc` still decodes the first opcode.

**RsaEnc** (each on a fresh `Packet{}`)

| Case | Expected |
|---|---|
| Textbook key `n = 3233`, `e = 17`; block `{41}` | data `02 0A E6` |
| Modulus 251, exponent 1; block `{41}` | data `01 41` (no sign padding) |
| Modulus 251, exponent 1; block `{80}` | data `02 00 80` (sign padding, because the top bit is set) |
| Modulus 251, exponent 1; block `{00 00 41}` | data `01 41`: the output is shorter than the block, and none of the block is left in `GetData` |
| A fixed 512-bit test key pair (`n`, `e = 65537`, `d`), stored as hex constants in `PacketTests.cpp`; blocks of 1 to 40 bytes starting with `0A` | `length == 1 + data[0]`; `data[1, length)` equals `ModPow(block, e, n).ToBytesBigEndian()`; `ModPow(ciphertext, d, n)` gives back the block |
| The login block with the 512-bit key: `P1(10)`, the seed `{1, 2, 3, 4}` as four `P4`s, `P4(1337)`, `PJStr("user")`, `PJStr("pass")` | Decrypting gives exactly `0A 00 00 00 01 00 00 00 02 00 00 00 03 00 00 00 04 00 00 05 39 75 73 65 72 0A 70 61 73 73 0A` |
| Block `{0C A1}`, equal to modulus 3233 | Throws `std::invalid_argument` |
| Modulus `2^2047 + 1`, exponent 2046, block `{02}` | Throws `std::length_error`: `2^2046` needs 256 bytes |

### 7.5 Tooling

- **Catch2** comes from vcpkg (added to `vcpkg.json`).
- **CMake:**
    - Every `src/` source except `main.cpp` builds a static library. The app executable (`main.cpp`) and the test executable both link it.
    - This departs from the single-executable template on purpose, so the tests link exactly the shipped code.
    - The test executable globs `tests/**/*.cpp` and uses the same `pch.hpp` and `src/` include directory.
    - Test presets are added to `CMakePresets.json`. Run the tests with `ctest --preset windows-debug`.
- **Test files:**
    - A test `.cpp` holds test cases rather than a class. This is an exception to "every `.cpp` has a class", like `main.cpp`.
    - The tables above become data-driven cases. Tags are `[BigUInt]`, `[Isaac]` and `[Packet]`.

### 7.6 Done when

- All tests pass on `windows-debug` and `windows-release` (and on the `linux-*` presets once available), with zero warnings.

---

## 8. Implementation order

1. **Project setup:**
    - Create `CMakeLists.txt` (library, app and test targets), `CMakePresets.json` (including test presets), `vcpkg.json` (with Catch2), `.clang-format`, `.editorconfig` and `.gitattributes`.
    - Create `pch.hpp` (with `<compare>`), `main.cpp`, `Application`, and `Core/Endian.hpp`.
2. **`Logger`:** implement it and `LogCapture` per [LoggerDesign.md](LoggerDesign.md) §7, plus their tests.
3. **`BigUInt`:** implement it, plus its tests.
4. **`Isaac`:** implement it, plus its tests.
5. **`Packet`:** implement it, plus its tests.
