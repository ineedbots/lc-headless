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

    std::vector<u8> ToVector(std::span<const u8> bytes)
    {
        return {bytes.begin(), bytes.end()};
    }

    std::span<const u8> AsBytes(std::string_view text)
    {
        return {reinterpret_cast<const u8*>(text.data()), text.size()};
    }

    void CheckRoundTrip(std::initializer_list<s64> values, void (*write)(Packet&, s64), s64 (*read)(Packet&))
    {
        auto writer = Packet{};
        for (const auto value : values)
        {
            write(writer, value);
        }

        auto reader = Packet{writer.GetData()};
        for (const auto value : values)
        {
            CHECK(read(reader) == value);
        }

        CHECK(reader.GetAvailable() == 0);
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

TEST_CASE("Packet read mode", "[Packet]")
{
    SECTION("views the bytes without copying them, at pos 0")
    {
        const auto bytes = std::vector<u8>(5000);
        const auto packet = Packet{bytes};
        CHECK(packet.GetData().data() == bytes.data());
        CHECK(packet.GetData().size() == 5000);
        CHECK(packet.GetLength() == 5000);
        CHECK(packet.GetPos() == 0);
        CHECK(packet.GetAvailable() == 5000);
    }

    SECTION("an empty packet has nothing to read")
    {
        auto packet = Packet{std::span<const u8>{}};
        CHECK(packet.GetLength() == 0);
        CHECK_THROWS_AS(packet.G1(), std::out_of_range);
    }

    SECTION("SetPos changes what is available, not the data or the length")
    {
        const auto bytes = std::vector<u8>(10);
        auto packet = Packet{bytes};
        packet.SetPos(3);
        CHECK(packet.GetAvailable() == 7);
        CHECK(packet.GetLength() == 10);
        CHECK(packet.GetData().size() == 10);
        packet.SetPos(10);
        CHECK(packet.GetAvailable() == 0);
    }
}

TEST_CASE("Packet write mode", "[Packet]")
{
    SECTION("a new packet is empty, at pos 0")
    {
        const auto packet = Packet{};
        CHECK(packet.GetData().empty());
        CHECK(packet.GetLength() == 0);
        CHECK(packet.GetPos() == 0);
    }

    SECTION("the packet grows as it is written")
    {
        constexpr auto COUNT = 2000;
        auto packet = Packet{};
        for (auto i = 0; i < COUNT; ++i)
        {
            packet.P4(i);
        }

        CHECK(packet.GetLength() == COUNT * sizeof(s32));
        CHECK(packet.GetPos() == COUNT * sizeof(s32));

        auto reader = Packet{packet.GetData()};
        for (auto i = 0; i < COUNT; ++i)
        {
            CHECK(reader.G4() == i);
        }
    }

    SECTION("GetData and GetLength cover the bytes before pos")
    {
        auto packet = Packet{};
        packet.P4(0x11223344);
        packet.SetPos(1);
        CHECK(packet.GetLength() == 1);
        CHECK(ToVector(packet.GetData()) == std::vector<u8>{0x11});

        packet.SetPos(4);
        CHECK(packet.GetLength() == 4);
        CHECK(ToVector(packet.GetData()) == std::vector<u8>{0x11, 0x22, 0x33, 0x44});
    }

    SECTION("writing after SetPos overwrites in place")
    {
        auto packet = Packet{};
        packet.P4(0x11223344);
        packet.SetPos(1);
        packet.P1(0xAB);
        packet.SetPos(4);
        CHECK(ToVector(packet.GetData()) == std::vector<u8>{0x11, 0xAB, 0x33, 0x44});
    }

    SECTION("a write across the end overwrites, then grows")
    {
        auto packet = Packet{};
        packet.P2(0x1122);
        packet.SetPos(1);
        packet.P4(0x33445566);
        CHECK(ToVector(packet.GetData()) == std::vector<u8>{0x11, 0x33, 0x44, 0x55, 0x66});
    }

    SECTION("SetPos(0) starts the next message in the same packet")
    {
        auto packet = Packet{};
        packet.P4(0x11223344);
        packet.SetPos(0);
        packet.P1(0x55);
        CHECK(ToVector(packet.GetData()) == std::vector<u8>{0x55});
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
    auto packet = Packet{testCase.bytes};
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
    auto smartPacket = Packet{testCase.bytes};
    CHECK(smartPacket.GSmart() == testCase.smart);
    CHECK(smartPacket.GetPos() == testCase.posAfter);

    auto smartsPacket = Packet{testCase.bytes};
    CHECK(smartsPacket.GSmarts() == testCase.smarts);
    CHECK(smartsPacket.GetPos() == testCase.posAfter);
}

TEST_CASE("Packet string reads", "[Packet]")
{
    SECTION("a terminated string")
    {
        const auto bytes = std::vector<u8>{0x61, 0x62, 0x63, 0x0A};
        auto packet = Packet{bytes};
        CHECK(packet.GJStr() == "abc");
        CHECK(packet.GetPos() == 4);
    }

    SECTION("an empty string")
    {
        const auto bytes = std::vector<u8>{0x0A};
        auto packet = Packet{bytes};
        CHECK(packet.GJStr().empty());
        CHECK(packet.GetPos() == 1);
    }

    SECTION("two strings in a row")
    {
        const auto bytes = std::vector<u8>{0x61, 0x0A, 0x62, 0x0A};
        auto packet = Packet{bytes};
        CHECK(packet.GJStr() == "a");
        CHECK(packet.GJStr() == "b");
        CHECK(packet.GetPos() == 4);
    }

    SECTION("a missing terminator drops the last byte, as TS does")
    {
        const auto bytes = std::vector<u8>{0x61, 0x62, 0x63};
        auto packet = Packet{bytes};
        CHECK(packet.GJStr() == "ab");
        CHECK(packet.GetPos() == 3);

        const auto singleBytes = std::vector<u8>{0x61};
        auto single = Packet{singleBytes};
        CHECK(single.GJStr().empty());
        CHECK(single.GetPos() == 1);
    }

    SECTION("bytes are kept raw")
    {
        const auto bytes = std::vector<u8>{0xE9, 0xFF, 0x0A};
        auto packet = Packet{bytes};
        CHECK(packet.GJStr() == "\xE9\xFF");
        CHECK(packet.GetPos() == 3);
    }

    SECTION("reading at the end throws")
    {
        const auto bytes = std::vector<u8>{0x61, 0x0A};
        auto packet = Packet{bytes};
        packet.SetPos(2);
        CHECK_THROWS_AS(packet.GJStr(), std::out_of_range);
        CHECK(packet.GetPos() == 2);
    }
}

TEST_CASE("Packet GData", "[Packet]")
{
    const auto bytes = std::vector<u8>{0x01, 0x02, 0x03, 0x04, 0x05};
    auto packet = Packet{bytes};

    SECTION("copies bytes from pos")
    {
        packet.SetPos(1);
        auto destination = std::array<u8, 3>{};
        packet.GData(destination);
        CHECK(destination == std::array<u8, 3>{0x02, 0x03, 0x04});
        CHECK(packet.GetPos() == 4);
    }

    SECTION("an empty destination is a no-op, even at the end")
    {
        packet.SetPos(5);
        CHECK_NOTHROW(packet.GData(std::span<u8>{}));
        CHECK(packet.GetPos() == 5);
    }

    SECTION("too few bytes throws and changes nothing")
    {
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
    auto packet = Packet{};
    testCase.write(packet);
    CHECK(ToVector(packet.GetData()) == testCase.expected);
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
        auto writer = Packet{};
        for (const auto* const text : texts)
        {
            writer.PJStr(text);
        }

        auto reader = Packet{writer.GetData()};
        for (const auto* const text : texts)
        {
            CHECK(reader.GJStr() == text);
        }

        CHECK(reader.GetAvailable() == 0);
    }

    SECTION("PData and GData")
    {
        const auto first = std::vector<u8>{0x00, 0xFF, 0x7F, 0x80};
        const auto second = std::vector<u8>{0x01};
        auto writer = Packet{};
        writer.PData(first);
        writer.PData(second);

        auto reader = Packet{writer.GetData()};
        auto readFirst = std::vector<u8>(first.size());
        auto readSecond = std::vector<u8>(second.size());
        reader.GData(readFirst);
        reader.GData(readSecond);
        CHECK(readFirst == first);
        CHECK(readSecond == second);
        CHECK(reader.GetAvailable() == 0);
    }
}

TEST_CASE("Packet PSize1 fills in a length placeholder", "[Packet]")
{
    SECTION("the placeholder before the sized bytes")
    {
        auto packet = Packet{};
        packet.P1(42);
        packet.P1(0);
        const auto start = packet.GetPos();
        packet.PJStr("hello");
        packet.P1(7);
        const auto end = packet.GetPos();
        packet.PSize1(end - start);

        CHECK(packet.GetPos() == end);
        CHECK(ToVector(packet.GetData()) == std::vector<u8>{42, 7, 'h', 'e', 'l', 'l', 'o', '\n', 7});
    }

    SECTION("a size of 0 right after the placeholder")
    {
        auto packet = Packet{};
        packet.P1(99);
        packet.PSize1(0);
        CHECK(ToVector(packet.GetData()) == std::vector<u8>{0});
    }
}

TEST_CASE("Packet reads past the end throw and leave pos unchanged", "[Packet]")
{
    const auto testCase = GENERATE(
        BoundsCase_s{"G1", 1, [](Packet& packet) { packet.G1(); }},
        BoundsCase_s{"G1B", 1, [](Packet& packet) { packet.G1B(); }},
        BoundsCase_s{"G2", 2, [](Packet& packet) { packet.G2(); }},
        BoundsCase_s{"G2B", 2, [](Packet& packet) { packet.G2B(); }},
        BoundsCase_s{"G3", 3, [](Packet& packet) { packet.G3(); }},
        BoundsCase_s{"G4", 4, [](Packet& packet) { packet.G4(); }},
        BoundsCase_s{"G8", 8, [](Packet& packet) { packet.G8(); }},
        BoundsCase_s{"GData(5)", 5, [](Packet& packet) { auto destination = std::array<u8, 5>{}; packet.GData(destination); }},
        BoundsCase_s{"GSmart", 1, [](Packet& packet) { packet.GSmart(); }},
        BoundsCase_s{"GSmart, two-byte form", 2, [](Packet& packet) { packet.GSmart(); }},
        BoundsCase_s{"GSmarts", 1, [](Packet& packet) { packet.GSmarts(); }},
        BoundsCase_s{"GSmarts, two-byte form", 2, [](Packet& packet) { packet.GSmarts(); }},
        BoundsCase_s{"GJStr", 1, [](Packet& packet) { packet.GJStr(); }});

    CAPTURE(testCase.call);
    const auto bytes = std::vector<u8>(BOUNDS_START + testCase.bytesNeeded - 1, BOUNDS_FILL);
    auto packet = Packet{bytes};
    packet.SetPos(BOUNDS_START);

    CHECK_THROWS_AS(testCase.operation(packet), std::out_of_range);
    CHECK(packet.GetPos() == BOUNDS_START);
}

TEST_CASE("Packet GBit stops at the end of the buffer", "[Packet]")
{
    const auto bytes = std::vector<u8>{0xFF, 0xFF};
    auto packet = Packet{bytes};

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
    auto packet = Packet{testCase.bytes};
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
    const auto allOnes = std::vector<u8>(5, 0xFF);
    const auto allZeros = std::vector<u8>(5, 0x00);

    for (auto offset = u32{0}; offset < 8; ++offset)
    {
        for (auto width = u32{1}; width <= 32; ++width)
        {
            CAPTURE(offset, width);

            auto ones = Packet{allOnes};
            ones.GBitStart();
            if (offset > 0)
            {
                ones.GBit(offset);
            }

            CHECK(ones.GBit(width) == GetMask(width));

            auto zeros = Packet{allZeros};
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

TEST_CASE("Packet P1Enc and G1Enc code opcodes with the ISAAC cipher", "[Packet]")
{
    constexpr auto COUNT = std::size_t{600};

    auto encoder = Isaac{ISAAC_SEED};
    auto packet = Packet{};
    for (std::size_t i = 0; i < COUNT; ++i)
    {
        packet.P1Enc(encoder, static_cast<s32>(i));
    }

    SECTION("P1Enc offsets each opcode by the next ISAAC value")
    {
        auto twin = Isaac{ISAAC_SEED};
        const auto data = packet.GetData();
        REQUIRE(data.size() == COUNT);
        for (std::size_t i = 0; i < COUNT; ++i)
        {
            CAPTURE(i);
            CHECK(data[i] == static_cast<u8>(static_cast<u32>(i) + static_cast<u32>(twin.NextInt())));
        }
    }

    SECTION("G1Enc takes the offset back off with a cipher seeded the same way")
    {
        auto decoder = Isaac{ISAAC_SEED};
        auto reader = Packet{packet.GetData()};
        for (std::size_t i = 0; i < COUNT; ++i)
        {
            CAPTURE(i);
            CHECK(reader.G1Enc(decoder) == static_cast<u8>(i));
        }
    }

    SECTION("a failed G1Enc doesn't advance the cipher")
    {
        auto decoder = Isaac{ISAAC_SEED};
        auto reader = Packet{packet.GetData()};
        reader.SetPos(COUNT);
        CHECK_THROWS_AS(reader.G1Enc(decoder), std::out_of_range);
        CHECK(reader.GetPos() == COUNT);

        reader.SetPos(0);
        CHECK(reader.G1Enc(decoder) == 0);
    }
}

TEST_CASE("Packet RsaEnc with small keys", "[Packet]")
{
    auto packet = Packet{};

    SECTION("textbook key")
    {
        packet.P1(0x41);
        packet.RsaEnc(BigUInt::Parse("3233"), BigUInt::Parse("17"));
        CHECK(ToVector(packet.GetData()) == std::vector<u8>{0x02, 0x0A, 0xE6});
    }

    SECTION("no sign padding when the top bit is clear")
    {
        packet.P1(0x41);
        packet.RsaEnc(BigUInt::Parse("251"), BigUInt::Parse("1"));
        CHECK(ToVector(packet.GetData()) == std::vector<u8>{0x01, 0x41});
    }

    SECTION("sign padding when the top bit is set")
    {
        packet.P1(0x80);
        packet.RsaEnc(BigUInt::Parse("251"), BigUInt::Parse("1"));
        CHECK(ToVector(packet.GetData()) == std::vector<u8>{0x02, 0x00, 0x80});
    }

    SECTION("a result shorter than the block leaves none of the block behind")
    {
        packet.PData(std::array<u8, 3>{0x00, 0x00, 0x41});
        packet.RsaEnc(BigUInt::Parse("251"), BigUInt::Parse("1"));
        CHECK(ToVector(packet.GetData()) == std::vector<u8>{0x01, 0x41});
    }

    SECTION("a block equal to the modulus throws")
    {
        packet.PData(std::array<u8, 2>{0x0C, 0xA1});
        CHECK_THROWS_AS(packet.RsaEnc(BigUInt::Parse("3233"), BigUInt::Parse("17")), std::invalid_argument);
    }

    SECTION("a result over 255 bytes throws")
    {
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
        auto packet = Packet{};
        packet.PData(block);
        packet.RsaEnc(modulus, exponent);

        const auto data = packet.GetData();
        REQUIRE(data.size() == std::size_t{1} + data[0]);
        const auto ciphertext = data.subspan(1);
        CHECK(ToVector(ciphertext) == BigUInt::ModPow(BigUInt::FromBytesBigEndian(block), exponent, modulus).ToBytesBigEndian());
        CHECK(Decrypt(ciphertext) == block);
    }

    SECTION("the login block decrypts back exactly")
    {
        auto packet = Packet{};
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
        CHECK(Decrypt(packet.GetData().subspan(1)) == expected);
    }
}
