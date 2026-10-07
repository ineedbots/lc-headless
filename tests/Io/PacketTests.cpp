#include "pch.hpp"

#include "Core/BigUInt.hpp"
#include "Io/Isaac.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/generators/catch_generators_range.hpp>

namespace
{
    constexpr auto TEST_MODULUS = "0xb254c4d18952bce1f6be151a7d507fc40e031ab0a6fa4871dde898bc8fb9d6771eeb67c6efc7ae8a105e7a23c6c6e0127ea0654a63293deb06e8a668dade947d";
    constexpr auto TEST_PUBLIC_EXPONENT = "65537";
    constexpr auto TEST_PRIVATE_EXPONENT = "0x1ba13aa5646b674c73585c18b095ca55ebfddb22c79c3ba138ca92ef942d2ce72196e1e969797cbf146e68ac2147dd1565edc89b0e6bc74e7ab0e1a4285c5659";
    constexpr auto ISAAC_SEED = std::array<s32, 4>{1, 2, 3, 4};
    constexpr auto BOUNDS_FILL = u8{0xA5};
    constexpr auto BOUNDS_START = std::size_t{2};

    struct ReadCase_s
    {
        std::vector<u8> bytes;
        std::string_view call;
        s64 (*read)(Packet& packet);
        s64 expected;
        std::size_t posAfter;
    };

    struct SmartCase_s
    {
        std::vector<u8> bytes;
        s32 smart;
        s32 smarts;
        std::size_t posAfter;
    };

    struct WriteCase_s
    {
        std::string_view call;
        void (*write)(Packet& packet);
        std::vector<u8> expected;
    };

    struct BoundsCase_s
    {
        std::string_view call;
        std::size_t bytesNeeded;
        void (*operation)(Packet& packet);
    };

    struct BitCase_s
    {
        std::vector<u8> bytes;
        std::size_t bytesBeforeStart;
        std::vector<u32> widths;
        std::vector<s32> results;
        std::size_t posAfterEnd;
    };

    struct CrcCase_s
    {
        std::string_view text;
        s32 crc;
    };

    Packet MakePacket(std::vector<u8> bytes)
    {
        return Packet{std::move(bytes)};
    }

    std::vector<u8> ToVector(std::span<const u8> bytes)
    {
        return {bytes.begin(), bytes.end()};
    }

    std::span<const u8> AsBytes(std::string_view text)
    {
        return {reinterpret_cast<const u8*>(text.data()), text.size()};
    }

    std::vector<u8> PadTo(std::vector<u8> bytes, std::size_t size)
    {
        bytes.resize(size);
        return bytes;
    }

    void CheckRoundTrip(std::initializer_list<s64> values, void (*write)(Packet&, s64), s64 (*read)(Packet&))
    {
        auto packet = MakePacket(std::vector<u8>(values.size() * sizeof(s64)));
        for (const auto value : values)
        {
            write(packet, value);
        }

        const auto end = packet.GetPos();
        packet.SetPos(0);
        for (const auto value : values)
        {
            CHECK(read(packet) == value);
        }

        CHECK(packet.GetPos() == end);
    }

    std::vector<u8> Decrypt(std::span<const u8> ciphertext)
    {
        return BigUInt::ModPow(BigUInt::FromBytesBigEndian(ciphertext), BigUInt::Parse(TEST_PRIVATE_EXPONENT), BigUInt::Parse(TEST_MODULUS)).ToBytesBigEndian();
    }

    std::vector<u8> MakeBlock(std::size_t length)
    {
        auto block = std::vector<u8>(length);
        block[0] = 0x0A;
        for (std::size_t i = 1; i < length; ++i)
        {
            block[i] = static_cast<u8>(i * 37 + 11);
        }

        return block;
    }

    s32 GetMask(u32 width)
    {
        return width == 32 ? -1 : static_cast<s32>((u32{1} << width) - 1);
    }
}

TEST_CASE("Packet construction and accessors", "[Packet]")
{
    SECTION("a new packet is zeroed, at pos 0")
    {
        const auto packet = MakePacket(std::vector<u8>(5000));
        CHECK(packet.GetLength() == 5000);
        CHECK(packet.GetPos() == 0);
        CHECK(packet.GetAvailable() == 5000);
        CHECK(std::ranges::all_of(packet.GetData(), [](u8 byte)
        {
            return byte == 0;
        }));
    }

    SECTION("the constructor moves the buffer instead of copying it")
    {
        auto bytes = std::vector<u8>(5000);
        const auto* const original = bytes.data();
        const auto packet = Packet{std::move(bytes)};
        CHECK(packet.GetData().data() == original);
    }

    SECTION("an empty packet has nothing to read")
    {
        auto packet = MakePacket({});
        CHECK(packet.GetLength() == 0);
        CHECK_THROWS_AS(packet.G1(), std::out_of_range);
    }

    SECTION("SetPos changes what is available")
    {
        auto packet = MakePacket(std::vector<u8>(10));
        packet.SetPos(3);
        CHECK(packet.GetAvailable() == 7);
        packet.SetPos(10);
        CHECK(packet.GetAvailable() == 0);
    }

    SECTION("bytes written through GetData are what reads return")
    {
        auto packet = MakePacket(std::vector<u8>(4));
        const auto data = packet.GetData();
        data[0] = 0xAB;
        data[1] = 0xCD;
        packet.SetPos(0);
        CHECK(packet.G2() == 0xABCD);
    }
}

TEST_CASE("Packet fixed-width reads", "[Packet]")
{
    const auto readG1 = [](Packet& packet) -> s64
    {
        return packet.G1();
    };
    const auto readG1B = [](Packet& packet) -> s64
    {
        return packet.G1B();
    };
    const auto readG2 = [](Packet& packet) -> s64
    {
        return packet.G2();
    };
    const auto readG2B = [](Packet& packet) -> s64
    {
        return packet.G2B();
    };
    const auto readG3 = [](Packet& packet) -> s64
    {
        return packet.G3();
    };
    const auto readG4 = [](Packet& packet) -> s64
    {
        return packet.G4();
    };
    const auto readG8 = [](Packet& packet) -> s64
    {
        return packet.G8();
    };

    const auto testCase = GENERATE_COPY(
        ReadCase_s{{0xFF}, "G1", readG1, 255, 1},
        ReadCase_s{{0xFF}, "G1B", readG1B, -1, 1},
        ReadCase_s{{0x80}, "G1B", readG1B, -128, 1},
        ReadCase_s{{0x7F}, "G1B", readG1B, 127, 1},
        ReadCase_s{{0x12, 0x34}, "G2", readG2, 0x1234, 2},
        ReadCase_s{{0xFF, 0xFF}, "G2", readG2, 65535, 2},
        ReadCase_s{{0xFF, 0xFE}, "G2B", readG2B, -2, 2},
        ReadCase_s{{0x80, 0x00}, "G2B", readG2B, -32768, 2},
        ReadCase_s{{0x12, 0x34, 0x56}, "G3", readG3, 0x123456, 3},
        ReadCase_s{{0xFF, 0xFF, 0xFF}, "G3", readG3, 16777215, 3},
        ReadCase_s{{0x12, 0x34, 0x56, 0x78}, "G4", readG4, 0x12345678, 4},
        ReadCase_s{{0xFF, 0xFF, 0xFF, 0xFF}, "G4", readG4, -1, 4},
        ReadCase_s{{0x80, 0x00, 0x00, 0x00}, "G4", readG4, std::numeric_limits<s32>::min(), 4},
        ReadCase_s{{0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08}, "G8", readG8, 0x0102030405060708, 8},
        ReadCase_s{{0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, "G8", readG8, std::numeric_limits<s64>::min(), 8},
        ReadCase_s{{0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF}, "G8", readG8, -1, 8});

    CAPTURE(testCase.call, testCase.bytes);
    auto packet = MakePacket(testCase.bytes);
    CHECK(testCase.read(packet) == testCase.expected);
    CHECK(packet.GetPos() == testCase.posAfter);
}

TEST_CASE("Packet smart reads", "[Packet]")
{
    const auto testCase = GENERATE(
        SmartCase_s{{0x00}, 0, -64, 1},
        SmartCase_s{{0x40}, 64, 0, 1},
        SmartCase_s{{0x7F}, 127, 63, 1},
        SmartCase_s{{0x80, 0x00}, 0, -16384, 2},
        SmartCase_s{{0x80, 0x80}, 128, -16256, 2},
        SmartCase_s{{0xC0, 0x00}, 16384, 0, 2},
        SmartCase_s{{0xFF, 0xFF}, 32767, 16383, 2});

    CAPTURE(testCase.bytes);
    auto smartPacket = MakePacket(testCase.bytes);
    CHECK(smartPacket.GSmart() == testCase.smart);
    CHECK(smartPacket.GetPos() == testCase.posAfter);

    auto smartsPacket = MakePacket(testCase.bytes);
    CHECK(smartsPacket.GSmarts() == testCase.smarts);
    CHECK(smartsPacket.GetPos() == testCase.posAfter);
}

TEST_CASE("Packet string reads", "[Packet]")
{
    SECTION("a terminated string")
    {
        auto packet = MakePacket({0x61, 0x62, 0x63, 0x0A});
        CHECK(packet.GJStr() == "abc");
        CHECK(packet.GetPos() == 4);
    }

    SECTION("an empty string")
    {
        auto packet = MakePacket({0x0A});
        CHECK(packet.GJStr().empty());
        CHECK(packet.GetPos() == 1);
    }

    SECTION("two strings in a row")
    {
        auto packet = MakePacket({0x61, 0x0A, 0x62, 0x0A});
        CHECK(packet.GJStr() == "a");
        CHECK(packet.GJStr() == "b");
        CHECK(packet.GetPos() == 4);
    }

    SECTION("a missing terminator drops the last byte, as TS does")
    {
        auto packet = MakePacket({0x61, 0x62, 0x63});
        CHECK(packet.GJStr() == "ab");
        CHECK(packet.GetPos() == 3);

        auto single = MakePacket({0x61});
        CHECK(single.GJStr().empty());
        CHECK(single.GetPos() == 1);
    }

    SECTION("bytes are kept raw")
    {
        auto packet = MakePacket({0xE9, 0xFF, 0x0A});
        CHECK(packet.GJStr() == "\xE9\xFF");
        CHECK(packet.GetPos() == 3);
    }

    SECTION("reading at the end throws")
    {
        auto packet = MakePacket({0x61, 0x0A});
        packet.SetPos(2);
        CHECK_THROWS_AS(packet.GJStr(), std::out_of_range);
        CHECK(packet.GetPos() == 2);
    }
}

TEST_CASE("Packet GData", "[Packet]")
{
    SECTION("copies bytes from pos")
    {
        auto packet = MakePacket({0x01, 0x02, 0x03, 0x04, 0x05});
        packet.SetPos(1);
        auto destination = std::array<u8, 3>{};
        packet.GData(destination);
        CHECK(destination == std::array<u8, 3>{0x02, 0x03, 0x04});
        CHECK(packet.GetPos() == 4);
    }

    SECTION("an empty destination is a no-op, even at the end")
    {
        auto packet = MakePacket({0x01, 0x02});
        packet.SetPos(2);
        CHECK_NOTHROW(packet.GData(std::span<u8>{}));
        CHECK(packet.GetPos() == 2);
    }

    SECTION("too few bytes throws and changes nothing")
    {
        auto packet = MakePacket({0x01, 0x02, 0x03, 0x04, 0x05});
        packet.SetPos(3);
        auto destination = std::array<u8, 3>{0x09, 0x09, 0x09};
        CHECK_THROWS_AS(packet.GData(destination), std::out_of_range);
        CHECK(packet.GetPos() == 3);
        CHECK(destination == std::array<u8, 3>{0x09, 0x09, 0x09});
    }
}

TEST_CASE("Packet writes", "[Packet]")
{
    const auto testCase = GENERATE(
        WriteCase_s{"P1(0x12)", [](Packet& packet) { packet.P1(0x12); }, {0x12}},
        WriteCase_s{"P1(-1)", [](Packet& packet) { packet.P1(-1); }, {0xFF}},
        WriteCase_s{"P1(256)", [](Packet& packet) { packet.P1(256); }, {0x00}},
        WriteCase_s{"P1(0x1FF)", [](Packet& packet) { packet.P1(0x1FF); }, {0xFF}},
        WriteCase_s{"P2(0x1234)", [](Packet& packet) { packet.P2(0x1234); }, {0x12, 0x34}},
        WriteCase_s{"P2(0x12345)", [](Packet& packet) { packet.P2(0x12345); }, {0x23, 0x45}},
        WriteCase_s{"P2(-1)", [](Packet& packet) { packet.P2(-1); }, {0xFF, 0xFF}},
        WriteCase_s{"IP2(0x1234)", [](Packet& packet) { packet.IP2(0x1234); }, {0x34, 0x12}},
        WriteCase_s{"IP2(-2)", [](Packet& packet) { packet.IP2(-2); }, {0xFE, 0xFF}},
        WriteCase_s{"P3(0x123456)", [](Packet& packet) { packet.P3(0x123456); }, {0x12, 0x34, 0x56}},
        WriteCase_s{"P3(0x1234567)", [](Packet& packet) { packet.P3(0x1234567); }, {0x23, 0x45, 0x67}},
        WriteCase_s{"P3(-1)", [](Packet& packet) { packet.P3(-1); }, {0xFF, 0xFF, 0xFF}},
        WriteCase_s{"P4(0x12345678)", [](Packet& packet) { packet.P4(0x12345678); }, {0x12, 0x34, 0x56, 0x78}},
        WriteCase_s{"P4(INT32_MIN)", [](Packet& packet) { packet.P4(std::numeric_limits<s32>::min()); }, {0x80, 0x00, 0x00, 0x00}},
        WriteCase_s{"IP4(0x12345678)", [](Packet& packet) { packet.IP4(0x12345678); }, {0x78, 0x56, 0x34, 0x12}},
        WriteCase_s{"IP4(-1)", [](Packet& packet) { packet.IP4(-1); }, {0xFF, 0xFF, 0xFF, 0xFF}},
        WriteCase_s{"P8(0x0102030405060708)", [](Packet& packet) { packet.P8(0x0102030405060708); }, {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08}},
        WriteCase_s{"P8(INT64_MIN)", [](Packet& packet) { packet.P8(std::numeric_limits<s64>::min()); }, {0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},
        WriteCase_s{"P8(-2)", [](Packet& packet) { packet.P8(-2); }, {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE}},
        WriteCase_s{"PJStr(\"abc\")", [](Packet& packet) { packet.PJStr("abc"); }, {0x61, 0x62, 0x63, 0x0A}},
        WriteCase_s{"PJStr(\"\")", [](Packet& packet) { packet.PJStr(""); }, {0x0A}},
        WriteCase_s{"PJStr(\"\\xE9\")", [](Packet& packet) { packet.PJStr("\xE9"); }, {0xE9, 0x0A}},
        WriteCase_s{"PData({09 08 07})", [](Packet& packet) { packet.PData(std::array<u8, 3>{0x09, 0x08, 0x07}); }, {0x09, 0x08, 0x07}},
        WriteCase_s{"PData({})", [](Packet& packet) { packet.PData({}); }, {}});

    CAPTURE(testCase.call);
    auto packet = MakePacket(std::vector<u8>(8));
    testCase.write(packet);
    CHECK(ToVector(packet.GetData()) == PadTo(testCase.expected, 8));
    CHECK(packet.GetPos() == testCase.expected.size());
}

TEST_CASE("Packet writes read back unchanged", "[Packet]")
{
    SECTION("P1 and G1")
    {
        CheckRoundTrip({0, 255, 0, 1}, [](Packet& packet, s64 value) { packet.P1(static_cast<s32>(value)); }, [](Packet& packet) -> s64 { return packet.G1(); });
    }

    SECTION("P1 and G1B")
    {
        CheckRoundTrip({-128, 127, 0, 1, -1}, [](Packet& packet, s64 value) { packet.P1(static_cast<s32>(value)); }, [](Packet& packet) -> s64 { return packet.G1B(); });
    }

    SECTION("P2 and G2")
    {
        CheckRoundTrip({0, 65535, 0, 1}, [](Packet& packet, s64 value) { packet.P2(static_cast<s32>(value)); }, [](Packet& packet) -> s64 { return packet.G2(); });
    }

    SECTION("P2 and G2B")
    {
        CheckRoundTrip({-32768, 32767, 0, 1, -1}, [](Packet& packet, s64 value) { packet.P2(static_cast<s32>(value)); }, [](Packet& packet) -> s64 { return packet.G2B(); });
    }

    SECTION("P3 and G3")
    {
        CheckRoundTrip({0, 16777215, 0, 1}, [](Packet& packet, s64 value) { packet.P3(static_cast<s32>(value)); }, [](Packet& packet) -> s64 { return packet.G3(); });
    }

    SECTION("P4 and G4")
    {
        CheckRoundTrip({std::numeric_limits<s32>::min(), std::numeric_limits<s32>::max(), 0, 1, -1}, [](Packet& packet, s64 value) { packet.P4(static_cast<s32>(value)); }, [](Packet& packet) -> s64 { return packet.G4(); });
    }

    SECTION("P8 and G8")
    {
        CheckRoundTrip({std::numeric_limits<s64>::min(), std::numeric_limits<s64>::max(), 0, 1, -1}, [](Packet& packet, s64 value) { packet.P8(value); }, [](Packet& packet) -> s64 { return packet.G8(); });
    }

    SECTION("PJStr and GJStr")
    {
        const auto texts = std::array{"", "a", "hello world", "\xE9\xFF"};
        auto packet = MakePacket(std::vector<u8>(64));
        for (const auto* const text : texts)
        {
            packet.PJStr(text);
        }

        const auto end = packet.GetPos();
        packet.SetPos(0);
        for (const auto* const text : texts)
        {
            CHECK(packet.GJStr() == text);
        }

        CHECK(packet.GetPos() == end);
    }

    SECTION("PData and GData")
    {
        const auto first = std::vector<u8>{0x00, 0xFF, 0x7F, 0x80};
        const auto second = std::vector<u8>{0x01};
        auto packet = MakePacket(std::vector<u8>(16));
        packet.PData(first);
        packet.PData(second);

        const auto end = packet.GetPos();
        packet.SetPos(0);
        auto readFirst = std::vector<u8>(first.size());
        auto readSecond = std::vector<u8>(second.size());
        packet.GData(readFirst);
        packet.GData(readSecond);
        CHECK(readFirst == first);
        CHECK(readSecond == second);
        CHECK(packet.GetPos() == end);
    }
}

TEST_CASE("Packet PSize1 fills in a length placeholder", "[Packet]")
{
    SECTION("the placeholder before the sized bytes")
    {
        auto packet = MakePacket(std::vector<u8>(16));
        packet.P1Enc(42);
        packet.P1(0);
        const auto start = packet.GetPos();
        packet.PJStr("hello");
        packet.P1(7);
        const auto end = packet.GetPos();
        packet.PSize1(end - start);

        CHECK(packet.GetPos() == end);
        const auto expected = std::vector<u8>{42, 7, 'h', 'e', 'l', 'l', 'o', '\n', 7};
        CHECK(ToVector(packet.GetData().first(end)) == expected);
        CHECK(std::ranges::all_of(packet.GetData().subspan(end), [](u8 byte)
        {
            return byte == 0;
        }));
    }

    SECTION("a size of 0 right after the placeholder")
    {
        auto packet = MakePacket(std::vector<u8>(4));
        packet.P1(99);
        packet.PSize1(0);
        CHECK(packet.GetData()[0] == 0);
        CHECK(packet.GetPos() == 1);
    }
}

TEST_CASE("Packet operations past the end throw and change nothing", "[Packet]")
{
    const auto testCase = GENERATE(
        BoundsCase_s{"G1", 1, [](Packet& packet) { packet.G1(); }},
        BoundsCase_s{"G1B", 1, [](Packet& packet) { packet.G1B(); }},
        BoundsCase_s{"P1", 1, [](Packet& packet) { packet.P1(0x11); }},
        BoundsCase_s{"P1Enc", 1, [](Packet& packet) { packet.P1Enc(0x11); }},
        BoundsCase_s{"G2", 2, [](Packet& packet) { packet.G2(); }},
        BoundsCase_s{"G2B", 2, [](Packet& packet) { packet.G2B(); }},
        BoundsCase_s{"P2", 2, [](Packet& packet) { packet.P2(0x1111); }},
        BoundsCase_s{"IP2", 2, [](Packet& packet) { packet.IP2(0x1111); }},
        BoundsCase_s{"G3", 3, [](Packet& packet) { packet.G3(); }},
        BoundsCase_s{"P3", 3, [](Packet& packet) { packet.P3(0x111111); }},
        BoundsCase_s{"G4", 4, [](Packet& packet) { packet.G4(); }},
        BoundsCase_s{"P4", 4, [](Packet& packet) { packet.P4(0x11111111); }},
        BoundsCase_s{"IP4", 4, [](Packet& packet) { packet.IP4(0x11111111); }},
        BoundsCase_s{"G8", 8, [](Packet& packet) { packet.G8(); }},
        BoundsCase_s{"P8", 8, [](Packet& packet) { packet.P8(0x1111111111111111); }},
        BoundsCase_s{"PJStr(\"ab\")", 3, [](Packet& packet) { packet.PJStr("ab"); }},
        BoundsCase_s{"GData(5)", 5, [](Packet& packet) { auto destination = std::array<u8, 5>{}; packet.GData(destination); }},
        BoundsCase_s{"PData(5)", 5, [](Packet& packet) { packet.PData(std::array<u8, 5>{0x11, 0x11, 0x11, 0x11, 0x11}); }},
        BoundsCase_s{"GSmart", 1, [](Packet& packet) { packet.GSmart(); }},
        BoundsCase_s{"GSmart, two-byte form", 2, [](Packet& packet) { packet.GSmart(); }},
        BoundsCase_s{"GSmarts", 1, [](Packet& packet) { packet.GSmarts(); }},
        BoundsCase_s{"GSmarts, two-byte form", 2, [](Packet& packet) { packet.GSmarts(); }},
        BoundsCase_s{"GJStr", 1, [](Packet& packet) { packet.GJStr(); }});

    CAPTURE(testCase.call);
    auto packet = MakePacket(std::vector<u8>(BOUNDS_START + testCase.bytesNeeded - 1, BOUNDS_FILL));
    packet.SetPos(BOUNDS_START);
    auto cipher = std::make_unique<Isaac>(ISAAC_SEED);
    packet.SetRandom(std::move(cipher));
    const auto before = ToVector(packet.GetData());

    CHECK_THROWS_AS(testCase.operation(packet), std::out_of_range);
    CHECK(packet.GetPos() == BOUNDS_START);
    CHECK(ToVector(packet.GetData()) == before);
}

TEST_CASE("Packet GBit stops at the end of the buffer", "[Packet]")
{
    auto packet = MakePacket({0xFF, 0xFF});

    packet.GBitStart();
    CHECK(packet.GBit(16) == 0xFFFF);

    packet.GBitStart();
    CHECK_THROWS_AS(packet.GBit(17), std::out_of_range);
    CHECK(packet.GBit(16) == 0xFFFF);
}

TEST_CASE("Packet bit reads", "[Packet]")
{
    const auto testCase = GENERATE(
        BitCase_s{{0xB0}, 0, {1, 1, 1, 1}, {1, 0, 1, 1}, 1},
        BitCase_s{{0xAB, 0xCD}, 0, {4, 8, 4}, {0xA, 0xBC, 0xD}, 2},
        BitCase_s{{0xAB, 0xCD}, 0, {3, 13}, {5, 0xBCD}, 2},
        BitCase_s{{0xFF, 0xFF, 0xFF, 0xFF}, 0, {32}, {-1}, 4},
        BitCase_s{{0x80, 0x00, 0x00, 0x00}, 0, {32}, {std::numeric_limits<s32>::min()}, 4},
        BitCase_s{{0x12, 0x34, 0x56, 0x78, 0x9A}, 0, {4, 32}, {1, 0x23456789}, 5},
        BitCase_s{{0x00, 0xFF}, 1, {8}, {255}, 2},
        BitCase_s{{0x12, 0x34}, 0, {}, {}, 0},
        BitCase_s{{0x12, 0x34}, 0, {9}, {0x24}, 2});

    CAPTURE(testCase.bytes, testCase.widths);
    auto packet = MakePacket(testCase.bytes);
    for (std::size_t i = 0; i < testCase.bytesBeforeStart; ++i)
    {
        packet.G1();
    }

    packet.GBitStart();
    for (std::size_t i = 0; i < testCase.widths.size(); ++i)
    {
        CHECK(packet.GBit(testCase.widths[i]) == testCase.results[i]);
    }

    packet.GBitEnd();
    CHECK(packet.GetPos() == testCase.posAfterEnd);
}

TEST_CASE("Packet GBit handles every width at every bit offset", "[Packet]")
{
    for (auto offset = u32{0}; offset < 8; ++offset)
    {
        for (auto width = u32{1}; width <= 32; ++width)
        {
            CAPTURE(offset, width);

            auto ones = MakePacket(std::vector<u8>(5, 0xFF));
            ones.GBitStart();
            if (offset > 0)
            {
                ones.GBit(offset);
            }

            CHECK(ones.GBit(width) == GetMask(width));

            auto zeros = MakePacket(std::vector<u8>(5, 0x00));
            zeros.GBitStart();
            if (offset > 0)
            {
                zeros.GBit(offset);
            }

            CHECK(zeros.GBit(width) == 0);
        }
    }
}

TEST_CASE("Packet CRC", "[Packet]")
{
    const auto testCase = GENERATE(
        CrcCase_s{"123456789", -873187034},
        CrcCase_s{"a", -390611389},
        CrcCase_s{"The quick brown fox jumps over the lazy dog", 1095738169},
        CrcCase_s{"", 0});

    CAPTURE(testCase.text);
    CHECK(Packet::GetCrc(AsBytes(testCase.text)) == testCase.crc);
}

TEST_CASE("Packet CheckCrc", "[Packet]")
{
    CHECK(Packet::CheckCrc(AsBytes("123456789"), -873187034));
    CHECK_FALSE(Packet::CheckCrc(AsBytes("123456789"), -873187033));
    CHECK(Packet::CheckCrc({}));
}

TEST_CASE("Packet P1Enc encodes opcodes with the ISAAC cipher", "[Packet]")
{
    SECTION("without a cipher the opcode is written as is")
    {
        auto packet = MakePacket(std::vector<u8>(1));
        packet.P1Enc(0x41);
        CHECK(packet.GetData()[0] == 0x41);
    }

    SECTION("with a cipher each opcode is offset by the next ISAAC value")
    {
        constexpr auto COUNT = std::size_t{600};
        auto packet = MakePacket(std::vector<u8>(COUNT));
        packet.SetRandom(std::make_unique<Isaac>(ISAAC_SEED));
        for (std::size_t i = 0; i < COUNT; ++i)
        {
            packet.P1Enc(static_cast<s32>(i));
        }

        auto twin = Isaac{ISAAC_SEED};
        auto decoder = Isaac{ISAAC_SEED};
        const auto data = packet.GetData();
        for (std::size_t i = 0; i < COUNT; ++i)
        {
            CAPTURE(i);
            const auto opcode = static_cast<u32>(i);
            CHECK(data[i] == static_cast<u8>(opcode + static_cast<u32>(twin.NextInt())));
            CHECK(static_cast<u8>(data[i] - static_cast<u32>(decoder.NextInt())) == static_cast<u8>(opcode));
        }
    }

    SECTION("SetRandom(nullptr) goes back to plain writes")
    {
        auto packet = MakePacket(std::vector<u8>(1));
        packet.SetRandom(std::make_unique<Isaac>(ISAAC_SEED));
        packet.SetRandom(nullptr);
        packet.P1Enc(0x41);
        CHECK(packet.GetData()[0] == 0x41);
    }

    SECTION("a failed write doesn't advance the cipher")
    {
        auto packet = MakePacket(std::vector<u8>(1));
        packet.SetRandom(std::make_unique<Isaac>(ISAAC_SEED));
        packet.SetPos(1);
        CHECK_THROWS_AS(packet.P1Enc(0x41), std::out_of_range);

        packet.SetPos(0);
        packet.P1Enc(0x41);
        auto twin = Isaac{ISAAC_SEED};
        CHECK(packet.GetData()[0] == static_cast<u8>(0x41 + static_cast<u32>(twin.NextInt())));
    }
}

TEST_CASE("Packet RsaEnc with small keys", "[Packet]")
{
    SECTION("textbook key")
    {
        auto packet = MakePacket(std::vector<u8>(8));
        packet.P1(0x41);
        packet.RsaEnc(BigUInt::Parse("3233"), BigUInt::Parse("17"));
        CHECK(ToVector(packet.GetData().first(3)) == std::vector<u8>{0x02, 0x0A, 0xE6});
        CHECK(packet.GetPos() == 3);
    }

    SECTION("no sign padding when the top bit is clear")
    {
        auto packet = MakePacket(std::vector<u8>(8));
        packet.P1(0x41);
        packet.RsaEnc(BigUInt::Parse("251"), BigUInt::Parse("1"));
        CHECK(ToVector(packet.GetData().first(2)) == std::vector<u8>{0x01, 0x41});
        CHECK(packet.GetPos() == 2);
    }

    SECTION("sign padding when the top bit is set")
    {
        auto packet = MakePacket(std::vector<u8>(8));
        packet.P1(0x80);
        packet.RsaEnc(BigUInt::Parse("251"), BigUInt::Parse("1"));
        CHECK(ToVector(packet.GetData().first(3)) == std::vector<u8>{0x02, 0x00, 0x80});
        CHECK(packet.GetPos() == 3);
    }

    SECTION("a block equal to the modulus throws")
    {
        auto packet = MakePacket(std::vector<u8>(8));
        packet.PData(std::array<u8, 2>{0x0C, 0xA1});
        CHECK_THROWS_AS(packet.RsaEnc(BigUInt::Parse("3233"), BigUInt::Parse("17")), std::invalid_argument);
    }

    SECTION("a result over 255 bytes throws")
    {
        auto packet = MakePacket(std::vector<u8>(5000));
        packet.P1(0x02);
        const auto modulus = BigUInt::Parse("0x8" + std::string(510, '0') + "1");
        CHECK_THROWS_AS(packet.RsaEnc(modulus, BigUInt::Parse("2046")), std::length_error);
    }
}

TEST_CASE("Packet RsaEnc with a 512-bit key", "[Packet]")
{
    const auto modulus = BigUInt::Parse(TEST_MODULUS);
    const auto exponent = BigUInt::Parse(TEST_PUBLIC_EXPONENT);

    SECTION("blocks of 1 to 40 bytes decrypt back")
    {
        const auto length = GENERATE(range(std::size_t{1}, std::size_t{41}));
        CAPTURE(length);

        const auto block = MakeBlock(length);
        auto packet = MakePacket(std::vector<u8>(128));
        packet.PData(block);
        packet.RsaEnc(modulus, exponent);

        const auto data = packet.GetData();
        REQUIRE(packet.GetPos() == std::size_t{1} + data[0]);
        const auto ciphertext = data.subspan(1, packet.GetPos() - 1);
        CHECK(ToVector(ciphertext) == BigUInt::ModPow(BigUInt::FromBytesBigEndian(block), exponent, modulus).ToBytesBigEndian());
        CHECK(Decrypt(ciphertext) == block);
    }

    SECTION("the login block decrypts back exactly")
    {
        auto packet = MakePacket(std::vector<u8>(128));
        packet.P1(10);
        for (const auto seed : ISAAC_SEED)
        {
            packet.P4(seed);
        }

        packet.P4(1337);
        packet.PJStr("user");
        packet.PJStr("pass");
        packet.RsaEnc(modulus, exponent);

        const auto expected = std::vector<u8>{
            0x0A, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x03, 0x00, 0x00, 0x00, 0x04,
            0x00, 0x00, 0x05, 0x39, 0x75, 0x73, 0x65, 0x72, 0x0A, 0x70, 0x61, 0x73, 0x73, 0x0A,
        };
        CHECK(Decrypt(packet.GetData().subspan(1, packet.GetPos() - 1)) == expected);
    }
}
