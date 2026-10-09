#include "pch.hpp"
#include "CacheWriter.hpp"

#include "Cache/CacheError.hpp"
#include "Cache/LocType_s.hpp"
#include "Cache/NpcType_s.hpp"
#include "Cache/ObjType_s.hpp"
#include "Cache/TextPool.hpp"
#include "Cache/TypeDecoder.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    std::vector<u8> ToBytes(const Packet& packet)
    {
        const auto data = packet.GetData();
        return {data.begin(), data.end()};
    }

    void PutString(Packet& packet, s32 opcode, std::string_view text)
    {
        packet.P1(opcode);
        packet.PJStr(text);
    }

    void PutValues(Packet& packet, std::initializer_list<s32> opcodes, std::size_t size)
    {
        for (const auto opcode : opcodes)
        {
            packet.P1(opcode);
            for (std::size_t i = 0; i < size; ++i)
            {
                packet.P1(0x5A);
            }
        }
    }

    void PutCounted(Packet& packet, s32 opcode, s32 count, std::size_t itemSize)
    {
        packet.P1(opcode);
        packet.P1(count);
        for (std::size_t i = 0; i < static_cast<std::size_t>(count) * itemSize; ++i)
        {
            packet.P1(0x33);
        }
    }

    std::vector<u8> MakeEveryLocOpcode()
    {
        auto packet = Packet{};
        packet.P1(1);
        packet.P1(2);
        packet.P2(100);
        packet.P1(10);
        packet.P2(101);
        packet.P1(22);
        PutString(packet, 2, "Tree");
        PutString(packet, 3, "A commonly found tree.");
        packet.P1(5);
        packet.P1(1);
        packet.P2(102);
        packet.P1(14);
        packet.P1(2);
        packet.P1(15);
        packet.P1(3);
        PutValues(packet, {17, 18, 21, 22, 23, 62, 64, 73}, 0);
        packet.P1(19);
        packet.P1(1);
        PutValues(packet, {28, 29, 39, 75}, 1);
        PutValues(packet, {24, 60, 65, 66, 67, 68, 70, 71, 72}, 2);
        PutString(packet, 30, "Chop down");
        PutString(packet, 31, "HIDDEN");
        PutString(packet, 34, "Search");
        PutString(packet, 35, "Dropped");
        PutString(packet, 38, "Dropped too");
        PutCounted(packet, 40, 2, 4);
        packet.P1(69);
        packet.P1(0b0101);
        packet.P1(77);
        packet.P2(300);
        packet.P1(2);
        packet.P2(1);
        packet.P2(2);
        packet.P2(0xFFFF);
        packet.P1(0);
        return ToBytes(packet);
    }

    std::vector<u8> MakeEveryNpcOpcode()
    {
        auto packet = Packet{};
        PutCounted(packet, 1, 2, 2);
        PutString(packet, 2, "Man");
        PutString(packet, 3, "One of RuneScape's many citizens.");
        packet.P1(12);
        packet.P1(2);
        PutValues(packet, {13, 14, 90, 91, 92, 97, 98, 102, 103}, 2);
        PutValues(packet, {17}, 8);
        PutString(packet, 30, "Talk-to");
        PutString(packet, 31, "Attack");
        PutString(packet, 32, "hidden");
        PutString(packet, 33, "Pickpocket");
        PutString(packet, 39, "Dropped");
        PutCounted(packet, 40, 1, 4);
        PutCounted(packet, 60, 2, 2);
        PutValues(packet, {93, 99}, 0);
        packet.P1(95);
        packet.P2(2);
        PutValues(packet, {100, 101}, 1);
        packet.P1(0);
        return ToBytes(packet);
    }

    std::vector<u8> MakeEveryObjOpcode()
    {
        auto packet = Packet{};
        PutValues(packet, {1, 4, 5, 6, 7, 8, 10, 24, 26, 78, 79, 90, 91, 92, 93, 95, 110, 111, 112}, 2);
        PutString(packet, 2, "Bronze axe");
        PutString(packet, 3, "A woodcutter's axe.");
        packet.P1(11);
        packet.P1(12);
        packet.P4(16);
        packet.P1(16);
        PutValues(packet, {23, 25}, 3);
        PutString(packet, 30, "Use");
        PutString(packet, 32, "hidden");
        PutString(packet, 33, "Light");
        PutString(packet, 35, "hidden");
        PutString(packet, 36, "Wield");
        PutString(packet, 39, "Destroy");
        PutCounted(packet, 40, 1, 4);
        packet.P1(97);
        packet.P2(0);
        PutValues(packet, {100, 101, 102, 103, 104, 105, 106, 107, 108, 109}, 4);
        PutValues(packet, {113, 114, 115}, 1);
        packet.P1(0);
        return ToBytes(packet);
    }

    std::vector<LocType_s> DecodeLocs(const std::vector<std::vector<u8>>& definitions, TextPool& text)
    {
        const auto files = CacheWriter::MakeTypeFiles(definitions);
        return TypeDecoder::DecodeLocs(files.dat, files.idx, text);
    }

    std::vector<NpcType_s> DecodeNpcs(const std::vector<std::vector<u8>>& definitions, TextPool& text)
    {
        const auto files = CacheWriter::MakeTypeFiles(definitions);
        return TypeDecoder::DecodeNpcs(files.dat, files.idx, text);
    }

    std::vector<ObjType_s> DecodeObjs(const std::vector<std::vector<u8>>& definitions, TextPool& text)
    {
        const auto files = CacheWriter::MakeTypeFiles(definitions);
        return TypeDecoder::DecodeObjs(files.dat, files.idx, text);
    }

    bool IsActive(std::vector<u8> opcodes)
    {
        opcodes.push_back(0);
        auto text = TextPool{};
        return DecodeLocs({opcodes}, text)[0].active;
    }

    std::string DecodeLocsError(const TypeFiles_s& files)
    {
        auto text = TextPool{};
        try
        {
            static_cast<void>(TypeDecoder::DecodeLocs(files.dat, files.idx, text));
        }
        catch (const CacheError& e)
        {
            return e.what();
        }

        return "no error";
    }
}

TEST_CASE("TypeDecoder reads every loc opcode", "[TypeDecoder]")
{
    auto text = TextPool{};
    const auto locs = DecodeLocs({MakeEveryLocOpcode(), CacheWriter::MakeDefinition("Rock")}, text);
    REQUIRE(locs.size() == 2);

    const auto& tree = locs[0];
    CHECK(tree.id == 0);
    CHECK(tree.name == "Tree");
    CHECK(tree.examine == "A commonly found tree.");
    CHECK(tree.width == 2);
    CHECK(tree.length == 3);
    CHECK_FALSE(tree.blockWalk);
    CHECK_FALSE(tree.blockRange);
    CHECK(tree.active);
    CHECK(tree.forceApproach == 0b0101);
    CHECK(text.GetOption(tree.ops[0]) == "Chop down");
    CHECK(tree.ops[1] == TextPool::NO_OPTION);
    CHECK(tree.ops[2] == TextPool::NO_OPTION);
    CHECK(text.GetOption(tree.ops[4]) == "Search");
    CHECK(text.GetOptionCount() == 3);

    const auto& rock = locs[1];
    CHECK(rock.id == 1);
    CHECK(rock.name == "Rock");
    CHECK(rock.examine.empty());
    CHECK(rock.width == 1);
    CHECK(rock.length == 1);
    CHECK(rock.blockWalk);
    CHECK(rock.blockRange);
    CHECK_FALSE(rock.active);
    CHECK(rock.forceApproach == 0);
}

TEST_CASE("TypeDecoder reads every NPC opcode", "[TypeDecoder]")
{
    auto text = TextPool{};
    auto chicken = Packet{};
    PutString(chicken, 2, "Chicken");
    chicken.P1(95);
    chicken.P2(0);
    chicken.P1(0);
    const auto npcs = DecodeNpcs({MakeEveryNpcOpcode(), ToBytes(chicken)}, text);
    REQUIRE(npcs.size() == 2);

    const auto& man = npcs[0];
    CHECK(man.name == "Man");
    CHECK(man.examine == "One of RuneScape's many citizens.");
    CHECK(man.size == 2);
    CHECK(man.combatLevel == std::optional<u16>{2});
    CHECK(text.GetOption(man.ops[0]) == "Talk-to");
    CHECK(text.GetOption(man.ops[1]) == "Attack");
    CHECK(man.ops[2] == TextPool::NO_OPTION);
    CHECK(text.GetOption(man.ops[3]) == "Pickpocket");
    CHECK(man.ops[4] == TextPool::NO_OPTION);

    CHECK(npcs[1].name == "Chicken");
    CHECK(npcs[1].size == 1);
    CHECK_FALSE(npcs[1].combatLevel.has_value());
}

TEST_CASE("TypeDecoder reads every obj opcode", "[TypeDecoder]")
{
    auto text = TextPool{};
    const auto objs = DecodeObjs({MakeEveryObjOpcode(), CacheWriter::MakeDefinition("Coins", {}, std::vector<u8>{11})}, text);
    REQUIRE(objs.size() == 2);

    const auto& axe = objs[0];
    CHECK(axe.name == "Bronze axe");
    CHECK(axe.examine == "A woodcutter's axe.");
    CHECK(axe.stackable);
    CHECK(axe.members);
    CHECK(axe.cost == 16);
    CHECK_FALSE(axe.noteOf.has_value());
    CHECK(text.GetOption(axe.ops[0]) == "Use");
    CHECK(axe.ops[2] == TextPool::NO_OPTION);
    CHECK(text.GetOption(axe.ops[3]) == "Light");
    CHECK(text.GetOption(axe.inventoryOps[0]) == "hidden");
    CHECK(text.GetOption(axe.inventoryOps[1]) == "Wield");
    CHECK(text.GetOption(axe.inventoryOps[4]) == "Destroy");

    CHECK(objs[1].name == "Coins");
    CHECK(objs[1].stackable);
    CHECK_FALSE(objs[1].members);
    CHECK(objs[1].cost == 1);
}

TEST_CASE("TypeDecoder works out whether a loc is active as the webclient does", "[TypeDecoder]")
{
    CHECK_FALSE(IsActive({}));
    CHECK(IsActive({5, 1, 0, 7}));
    CHECK(IsActive({1, 1, 0, 7, 10}));
    CHECK_FALSE(IsActive({1, 1, 0, 7, 22}));
    CHECK_FALSE(IsActive({1, 0}));
    CHECK(IsActive({1, 1, 0, 7, 22, 5, 1, 0, 8}));
    CHECK(IsActive({30, 'h', 'i', 'd', 'd', 'e', 'n', '\n'}));
    CHECK_FALSE(IsActive({30, 'O', 'p', 'e', 'n', '\n', 19, 0}));
    CHECK(IsActive({19, 1}));
}

TEST_CASE("TypeDecoder lets opcode 74 clear a loc's blocking", "[TypeDecoder]")
{
    auto text = TextPool{};
    const auto locs = DecodeLocs({std::vector<u8>{74, 0}}, text);
    CHECK_FALSE(locs[0].blockWalk);
    CHECK_FALSE(locs[0].blockRange);
}

TEST_CASE("TypeDecoder makes banknotes from their linked objs", "[TypeDecoder]")
{
    const auto note = [](u16 link)
    {
        auto packet = Packet{};
        packet.P1(97);
        packet.P2(link);
        packet.P1(98);
        packet.P2(799);
        packet.P1(0);
        return ToBytes(packet);
    };

    auto logs = Packet{};
    PutString(logs, 2, "Logs");
    logs.P1(12);
    logs.P4(4);
    logs.P1(16);
    logs.P1(0);

    auto text = TextPool{};
    const auto objs = DecodeObjs({ToBytes(logs), CacheWriter::MakeDefinition("Apple"), note(0), note(1)}, text);
    CHECK(objs[2].name == "Logs");
    CHECK(objs[2].members);
    CHECK(objs[2].cost == 4);
    CHECK(objs[2].stackable);
    CHECK(objs[2].noteOf == std::optional<u16>{0});
    CHECK(objs[2].examine == "Swap this note at any bank for a Logs.");
    CHECK(objs[3].examine == "Swap this note at any bank for an Apple.");
    CHECK_FALSE(objs[3].members);
    CHECK_FALSE(objs[0].noteOf.has_value());

    CHECK_THROWS_WITH(DecodeObjs({note(5)}, text), ContainsSubstring("obj 0: its certlink 5 isn't an obj"));
}

TEST_CASE("TypeDecoder rejects definitions that don't decode to their size", "[TypeDecoder]")
{
    SECTION("an unknown opcode")
    {
        auto text = TextPool{};
        CHECK_THROWS_WITH(DecodeNpcs({CacheWriter::MakeDefinition("Chicken"), std::vector<u8>{200, 0}}, text), "npc 1: unknown opcode 200");
    }

    SECTION("a definition that ends early")
    {
        auto files = CacheWriter::MakeTypeFiles({std::vector<u8>{17, 0, 0}});
        CHECK(DecodeLocsError(files) == "loc 0: ends at byte 2 of its 3");
    }

    SECTION("a definition that runs past its size")
    {
        auto files = CacheWriter::MakeTypeFiles({std::vector<u8>{14, 2, 0}, std::vector<u8>{0}});
        files.idx[3] = 2;
        files.idx[5] = 2;
        CHECK(DecodeLocsError(files) == "loc 0: runs past the end of its 2 bytes");
    }

    SECTION("counts that differ")
    {
        auto files = CacheWriter::MakeTypeFiles({std::vector<u8>{0}});
        files.idx[1] = 2;
        CHECK(DecodeLocsError(files) == "loc.idx lists 2 definitions, but loc.dat has 1");
    }

    SECTION("bytes after the last definition")
    {
        auto files = CacheWriter::MakeTypeFiles({std::vector<u8>{0}});
        files.dat.push_back(0);
        CHECK(DecodeLocsError(files) == "loc.dat has 1 bytes after its last definition");
    }

    SECTION("a string without its newline")
    {
        const auto files = CacheWriter::MakeTypeFiles({std::vector<u8>{2, 'T', 'r', 'e', 'e'}});
        CHECK(DecodeLocsError(files) == "loc 0: a string runs past the end without its newline");
    }
}
