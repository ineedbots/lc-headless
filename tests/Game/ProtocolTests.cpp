#include "pch.hpp"

#include "Game/Protocol/Base37.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Game/Protocol/WordPack.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>

namespace
{
    struct ProtSize_s
    {
        u8 opcode;
        s32 size;
    };

    // Every server opcode and size from docs/tcp-protocol-289.md, which match the engine's tables.
    constexpr auto SERVER_SIZES = std::to_array<ProtSize_s>({
        {12, 2}, {13, 3}, {18, 6}, {21, -1}, {23, 0}, {28, 2}, {29, 4}, {30, 2}, {35, 0}, {46, 2},
        {47, -2}, {55, 4}, {59, -2}, {60, 5}, {63, 3}, {65, -2}, {71, 3}, {73, 6}, {75, 3}, {76, -2},
        {79, 6}, {81, 2}, {82, 6}, {83, 14}, {87, 15}, {90, 4}, {97, 6}, {106, 4}, {107, -2}, {112, -2},
        {115, 6}, {117, 7}, {119, 2}, {120, 3}, {121, 0}, {127, 2}, {133, 0}, {136, 1}, {138, 3}, {144, 2},
        {154, 6}, {155, 2}, {160, 4}, {164, 0}, {168, 9}, {172, 0}, {176, 7}, {177, 5}, {181, 1}, {184, 4},
        {187, 2}, {188, -2}, {189, 1}, {194, 2}, {195, 1}, {196, -1}, {201, 0}, {204, 2}, {208, 4}, {211, 4},
        {219, 4}, {222, 4}, {233, 6}, {235, 1}, {243, -1}, {244, 4}, {247, 1}, {252, 2}, {253, 10},
    });

    constexpr auto CLIENT_SIZES = std::to_array<ProtSize_s>({
        {4, 6}, {10, 6}, {13, 2}, {16, 8}, {21, 2}, {22, 6}, {27, 13}, {30, 2}, {34, -1}, {40, 6},
        {44, 6}, {45, 6}, {46, 1}, {49, 1}, {51, 2}, {53, 6}, {55, 12}, {67, -1}, {69, 2}, {73, 2},
        {76, 6}, {79, 6}, {81, 2}, {85, 0}, {86, 2}, {88, 3}, {93, 0}, {94, 10}, {97, 6}, {107, -1},
        {108, 4}, {110, 6}, {111, 6}, {112, 8}, {122, 4}, {124, 6}, {125, 1}, {126, 6}, {130, -1}, {133, 4},
        {137, 1}, {138, 4}, {145, 0}, {146, 1}, {147, 6}, {149, 1}, {154, -1}, {156, -1}, {160, 8}, {161, 3},
        {166, 2}, {168, 1}, {177, 6}, {178, 2}, {180, 4}, {181, 0}, {184, 12}, {189, 2}, {191, 6}, {192, 8},
        {193, 4}, {195, 4}, {196, 6}, {200, 12}, {203, 8}, {214, 0}, {218, 8}, {220, 2}, {224, 4}, {227, 6},
        {229, -1}, {232, 0}, {234, -1}, {235, 8}, {236, -1}, {241, 8}, {247, 2}, {248, 6}, {251, 8}, {252, 2},
        {253, 7}, {255, 1},
    });

    constexpr auto ZONE_OPCODES = std::to_array<u8>({60, 71, 83, 87, 90, 106, 117, 176, 194, 233});

    constexpr auto BASE37_LIMIT = u64{6582952005840035281};

    template <std::size_t N>
    std::optional<s32> FindSize(const std::array<ProtSize_s, N>& table, u8 opcode)
    {
        const auto found = std::ranges::find(table, opcode, &ProtSize_s::opcode);
        if (found == table.end())
        {
            return std::nullopt;
        }

        return found->size;
    }

    std::vector<u8> Bytes(std::initializer_list<u8> bytes)
    {
        return bytes;
    }
}

TEST_CASE("ServerProt sizes match the protocol table for all 256 opcodes", "[ServerProt]")
{
    static_assert(SERVER_SIZES.size() == ServerProt::COUNT);
    for (auto opcode = 0; opcode < 256; ++opcode)
    {
        CAPTURE(opcode);
        CHECK(ServerProt::GetSize(static_cast<u8>(opcode)) == FindSize(SERVER_SIZES, static_cast<u8>(opcode)));
    }
}

TEST_CASE("ServerProt marks exactly the zone sub-packets", "[ServerProt]")
{
    for (auto opcode = 0; opcode < 256; ++opcode)
    {
        CAPTURE(opcode);
        const auto isZone = std::ranges::find(ZONE_OPCODES, static_cast<u8>(opcode)) != ZONE_OPCODES.end();
        CHECK(ServerProt::IsZoneProt(static_cast<u8>(opcode)) == isZone);
    }
}

TEST_CASE("ServerProt names use the engine's names", "[ServerProt]")
{
    CHECK(ServerProt::GetName(188) == "PLAYER_INFO");
    CHECK(ServerProt::GetName(63) == "IF_SETTAB");
    CHECK(ServerProt::GetName(0) == "UNKNOWN");
}

TEST_CASE("ClientProt sizes match the protocol table for all 256 opcodes", "[ClientProt]")
{
    static_assert(CLIENT_SIZES.size() == ClientProt::COUNT);
    for (auto opcode = 0; opcode < 256; ++opcode)
    {
        CAPTURE(opcode);
        CHECK(ClientProt::GetSize(static_cast<u8>(opcode)) == FindSize(CLIENT_SIZES, static_cast<u8>(opcode)));
    }

    CHECK(ClientProt::GetName(181) == "NO_TIMEOUT");
}

TEST_CASE("Base37 encodes names", "[Base37]")
{
    CHECK(Base37::Encode("a") == 1);
    CHECK(Base37::Encode("z") == 26);
    CHECK(Base37::Encode("0") == 27);
    CHECK(Base37::Encode("9") == 36);
    CHECK(Base37::Encode("ab") == 39);
    CHECK(Base37::Encode("AB") == 39);
    CHECK(Base37::Encode("a b") == 1371);
    CHECK(Base37::Encode("a_b") == 1371);
    CHECK(Base37::Encode("  ab\t") == 39);
    CHECK(Base37::Encode("ab_") == 39);
    CHECK(Base37::Encode("") == 0);
    CHECK(Base37::Encode("abcdefghijklmnop") == Base37::Encode("abcdefghijkl"));
}

TEST_CASE("Base37 decodes names", "[Base37]")
{
    CHECK(Base37::Decode(39) == "ab");
    CHECK(Base37::Decode(1371) == "a_b");
    CHECK(Base37::Decode(Base37::Encode("zezima")) == "zezima");
    CHECK(Base37::Decode(Base37::Encode("bot 123")) == "bot_123");

    SECTION("invalid values decode as invalid_name")
    {
        CHECK(Base37::Decode(0) == Base37::INVALID_NAME);
        CHECK(Base37::Decode(37) == Base37::INVALID_NAME);
        CHECK(Base37::Decode(BASE37_LIMIT) == Base37::INVALID_NAME);
        CHECK(Base37::Decode(BASE37_LIMIT - 1) != Base37::INVALID_NAME);
    }

    SECTION("display names capitalise each word")
    {
        CHECK(Base37::ToDisplayName("hello_world") == "Hello World");
        CHECK(Base37::ToDisplayName("a_1") == "A 1");
        CHECK(Base37::ToDisplayName("") == "");
        CHECK(Base37::DecodeDisplayName(Base37::Encode("Zezima")) == "Zezima");
    }
}

TEST_CASE("WordPack packs text into nibbles", "[WordPack]")
{
    CHECK(WordPack::Pack("hello") == Bytes({0x61, 0xBB, 0x40}));
    CHECK(WordPack::Pack("HELLO") == Bytes({0x61, 0xBB, 0x40}));
    CHECK(WordPack::Pack("m") == Bytes({0xD0}));
    CHECK(WordPack::Pack("am") == Bytes({0x3D, 0x00}));
    CHECK(WordPack::Pack("~") == Bytes({0x00}));
    CHECK(WordPack::Pack("\xA3") == Bytes({0xFA}));
    CHECK(WordPack::Pack("").empty());
    CHECK(WordPack::Pack(std::string(100, 'e')) == std::vector<u8>(40, 0x11));
}

TEST_CASE("WordPack unpacks with sentence case", "[WordPack]")
{
    CHECK(WordPack::Unpack(Bytes({0x61, 0xBB, 0x40})) == "Hello ");
    CHECK(WordPack::Unpack(Bytes({0xD0})) == "M");
    CHECK(WordPack::Unpack(Bytes({0x3D, 0x00})) == "Am ");
    CHECK(WordPack::Unpack(Bytes({0xFA})) == "\xA3");
    CHECK(WordPack::Unpack(WordPack::Pack("hi. there! ok")) == "Hi. There! Ok");
    CHECK(WordPack::Unpack(WordPack::Pack("price: 5$ [x] @y")) == "Price: 5$ [x] @y");

    SECTION("unpacking stops once 100 characters are out")
    {
        CHECK(WordPack::Unpack(std::vector<u8>(60, 0x11)).size() == WordPack::MAX_UNPACK_LENGTH);
    }
}
