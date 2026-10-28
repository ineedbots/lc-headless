#include "pch.hpp"
#include "../Support/Cache/CacheWriter.hpp"

#include "Cache/Error/CacheError.hpp"
#include "Cache/LocTypeDecoder.hpp"
#include "Cache/LocType_s.hpp"
#include "Cache/NpcTypeDecoder.hpp"
#include "Cache/NpcType_s.hpp"
#include "Cache/ObjTypeDecoder.hpp"
#include "Cache/ObjType_s.hpp"
#include "Cache/RevisionedOpcode_s.hpp"
#include "Cache/TextPool.hpp"
#include "Cache/TypeDecoder.hpp"
#include "Cache/VarpTypeDecoder.hpp"
#include "Cache/VarpType_s.hpp"
#include "Config/Revision_e.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
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
            for (auto i = std::size_t{0}; i < size; ++i)
            {
                packet.P1(0x5A);
            }
        }
    }

    void PutCounted(Packet& packet, s32 opcode, s32 count, std::size_t itemSize)
    {
        packet.P1(opcode);
        packet.P1(count);
        for (auto i = std::size_t{0}; i < static_cast<std::size_t>(count) * itemSize; ++i)
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

    std::vector<LocType_s> DecodeLocs(const std::vector<std::vector<u8>>& definitions, TextPool& text, Revision_e revision = Revision_e::Rev289)
    {
        const auto files = CacheWriter::MakeTypeFiles(definitions);
        return LocTypeDecoder::Decode(files.dat, files.idx, text, revision);
    }

    std::vector<NpcType_s> DecodeNpcs(const std::vector<std::vector<u8>>& definitions, TextPool& text, Revision_e revision = Revision_e::Rev289)
    {
        const auto files = CacheWriter::MakeTypeFiles(definitions);
        return NpcTypeDecoder::Decode(files.dat, files.idx, text, revision);
    }

    std::vector<ObjType_s> DecodeObjs(const std::vector<std::vector<u8>>& definitions, TextPool& text, Revision_e revision = Revision_e::Rev289)
    {
        const auto files = CacheWriter::MakeTypeFiles(definitions);
        return ObjTypeDecoder::Decode(files.dat, files.idx, text, revision);
    }

    std::vector<VarpType_s> DecodeVarps(const std::vector<std::vector<u8>>& definitions, Revision_e revision = Revision_e::Rev289)
    {
        const auto files = CacheWriter::MakeTypeFiles(definitions);
        return VarpTypeDecoder::Decode(files.dat, files.idx, revision);
    }

    bool IsActive(std::vector<u8> opcodes, Revision_e revision = Revision_e::Rev289)
    {
        opcodes.push_back(0);

        auto text = TextPool{};
        return DecodeLocs({opcodes}, text, revision)[0].active;
    }

    std::string DecodeLocsError(const TypeFiles_s& files)
    {
        auto text = TextPool{};
        try
        {
            static_cast<void>(LocTypeDecoder::Decode(files.dat, files.idx, text, Revision_e::Rev289));
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

// The market's catalog reads both: a strung bow is the one of its name with a wear model, and a pile-size model
// repeats its stackable's name without being an item.
TEST_CASE("TypeDecoder marks wearable objs and a stackable's pile-size models", "[TypeDecoder]")
{
    auto coins = Packet{};
    PutString(coins, 2, "Coins");
    coins.P1(11);
    coins.P1(100);
    coins.P2(1);
    coins.P2(2);
    coins.P1(0);

    auto bow = Packet{};
    PutString(bow, 2, "Maple longbow");
    bow.P1(23);
    bow.P2(512);
    bow.P1(0);
    bow.P1(0);

    auto text = TextPool{};
    const auto objs = DecodeObjs({ToBytes(coins), CacheWriter::MakeDefinition("Coins"), ToBytes(bow), CacheWriter::MakeDefinition("Maple longbow")}, text);
    CHECK_FALSE(objs[0].stackVariant);
    CHECK(objs[1].stackVariant);
    CHECK_FALSE(objs[2].stackVariant);
    CHECK(objs[2].equippable);
    CHECK_FALSE(objs[3].equippable);
    CHECK_FALSE(objs[0].equippable);
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

TEST_CASE("Every type decoder rejects incomplete framing before reading definitions", "[TypeDecoder][FramingCoverage]")
{
    const auto kind = GENERATE("loc"sv, "npc"sv, "obj"sv, "varp"sv);
    CAPTURE(kind);
    const auto decode = [kind](const TypeFiles_s& files)
    {
        auto text = TextPool{};
        if (kind == "loc") return LocTypeDecoder::Decode(files.dat, files.idx, text, Revision_e::Rev289).size();
        if (kind == "npc") return NpcTypeDecoder::Decode(files.dat, files.idx, text, Revision_e::Rev289).size();
        if (kind == "obj") return ObjTypeDecoder::Decode(files.dat, files.idx, text, Revision_e::Rev289).size();
        return VarpTypeDecoder::Decode(files.dat, files.idx, Revision_e::Rev289).size();
    };
    const auto complete = CacheWriter::MakeTypeFiles({std::vector<u8>{0}});
    auto files = complete;
    auto expected = std::string{};
    SECTION("a zero-byte data header")
    {
        files.dat.clear();
        expected = std::format("{0}.dat or {0}.idx is too short for its count", kind);
    }
    SECTION("a one-byte data header")
    {
        files.dat.resize(1);
        expected = std::format("{0}.dat or {0}.idx is too short for its count", kind);
    }
    SECTION("a zero-byte index header")
    {
        files.idx.clear();
        expected = std::format("{0}.dat or {0}.idx is too short for its count", kind);
    }
    SECTION("a one-byte index header")
    {
        files.idx.resize(1);
        expected = std::format("{0}.dat or {0}.idx is too short for its count", kind);
    }
    SECTION("a missing size entry")
    {
        files.idx.resize(2);
        expected = std::format("{}.idx is 2 bytes, too short for 1 sizes", kind);
    }
    SECTION("a partial size entry")
    {
        files.idx.resize(3);
        expected = std::format("{}.idx is 3 bytes, too short for 1 sizes", kind);
    }
    SECTION("a definition larger than the data file")
    {
        files.idx.back() = 2;
        expected = std::format("{0} 0: runs past the end of {0}.dat", kind);
    }
    CHECK_THROWS_AS(decode(files), CacheError);
    CHECK_THROWS_WITH(decode(files), expected);
    CHECK(decode(complete) == 1);
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

TEST_CASE("VarpTypeDecoder keeps each varp's client code and drops its other opcodes", "[TypeDecoder]")
{
    auto packet = Packet{};
    PutValues(packet, {1, 2}, 1);
    PutValues(packet, {3, 4, 6, 8, 11, 13}, 0);
    PutValues(packet, {7, 12}, 4);
    packet.P1(5);
    packet.P2(173);
    PutString(packet, 10, "debug name");
    packet.P1(0);

    const auto varps = DecodeVarps({ToBytes(packet), std::vector<u8>{0}});
    REQUIRE(varps.size() == 2);
    CHECK(varps[0].id == 0);
    CHECK(varps[0].clientCode == 173);
    CHECK(varps[1].id == 1);
    CHECK(varps[1].clientCode == 0);
}

TEST_CASE("VarpTypeDecoder rejects an unknown opcode", "[TypeDecoder]")
{
    CHECK_THROWS_WITH(DecodeVarps({std::vector<u8>{9, 0}}), "varp 0: unknown opcode 9");
}

TEST_CASE("TypeDecoder finds an opcode's revisions in its table", "[TypeDecoder]")
{
    constexpr auto TABLE = std::to_array({
        RevisionedOpcode_s::AddedIn(1, Revision_e::Rev274),
        RevisionedOpcode_s::RemovedIn(2, Revision_e::Rev289),
    });

    CHECK(TypeDecoder::HasOpcode(Revision_e::Rev225, 3, TABLE));
    CHECK(TypeDecoder::HasOpcode(Revision_e::Rev289, 3, TABLE));
    CHECK_FALSE(TypeDecoder::HasOpcode(Revision_e::Rev225, 1, TABLE));
    CHECK(TypeDecoder::HasOpcode(Revision_e::Rev274, 1, TABLE));
    CHECK(TypeDecoder::HasOpcode(Revision_e::Rev289, 1, TABLE));
    CHECK(TypeDecoder::HasOpcode(Revision_e::Rev225, 2, TABLE));
    CHECK(TypeDecoder::HasOpcode(Revision_e::Rev274, 2, TABLE));
    CHECK_FALSE(TypeDecoder::HasOpcode(Revision_e::Rev289, 2, TABLE));
}

TEST_CASE("TypeDecoder reads the flags only 225 has, and later revisions reject them", "[TypeDecoder]")
{
    const auto flag = [](u8 opcode)
    {
        return std::vector<std::vector<u8>>{CacheWriter::MakeDefinition("Rock", {}, std::vector<u8>{opcode})};
    };

    auto text = TextPool{};
    CHECK(DecodeLocs(flag(25), text, Revision_e::Rev225)[0].name == "Rock");
    CHECK(DecodeNpcs(flag(16), text, Revision_e::Rev225)[0].name == "Rock");
    CHECK(DecodeObjs(flag(9), text, Revision_e::Rev225)[0].name == "Rock");

    const auto revision = GENERATE(Revision_e::Rev274, Revision_e::Rev289);
    CAPTURE(static_cast<u16>(revision));
    CHECK_THROWS_WITH(DecodeLocs(flag(25), text, revision), "loc 0: unknown opcode 25");
    CHECK_THROWS_WITH(DecodeNpcs(flag(16), text, revision), "npc 0: unknown opcode 16");
    CHECK_THROWS_WITH(DecodeObjs(flag(9), text, revision), "obj 0: unknown opcode 9");
}

TEST_CASE("TypeDecoder reads the opcodes 274 shares with 289", "[TypeDecoder]")
{
    const auto definition = [](const std::vector<u8>& opcode)
    {
        return std::vector<std::vector<u8>>{CacheWriter::MakeDefinition("", {}, opcode)};
    };

    auto text = TextPool{};
    const auto revision = GENERATE(Revision_e::Rev274, Revision_e::Rev289);
    CAPTURE(static_cast<u16>(revision));

    for (const auto& opcode : {std::vector<u8>{5, 1, 0, 7}, std::vector<u8>{74}, std::vector<u8>{75, 1}})
    {
        CAPTURE(opcode[0]);
        CHECK_NOTHROW(DecodeLocs(definition(opcode), text, revision));
    }

    for (const auto& opcode : {std::vector<u8>{99}, std::vector<u8>{100, 0}, std::vector<u8>{101, 0}, std::vector<u8>{102, 0, 0}, std::vector<u8>{103, 0, 0}})
    {
        CAPTURE(opcode[0]);
        CHECK_NOTHROW(DecodeNpcs(definition(opcode), text, revision));
    }

    for (const auto& opcode : {std::vector<u8>{110, 0, 0}, std::vector<u8>{111, 0, 0}, std::vector<u8>{112, 0, 0}, std::vector<u8>{113, 0}, std::vector<u8>{114, 0}})
    {
        CAPTURE(opcode[0]);
        CHECK_NOTHROW(DecodeObjs(definition(opcode), text, revision));
    }

    CHECK_NOTHROW(DecodeVarps(definition({11}), revision));
}

TEST_CASE("TypeDecoder rejects the opcodes only 289 has when it reads 274", "[TypeDecoder]")
{
    const auto definition = [](const std::vector<u8>& opcode)
    {
        return std::vector<std::vector<u8>>{CacheWriter::MakeDefinition("", {}, opcode)};
    };

    auto text = TextPool{};
    CHECK_THROWS_WITH(DecodeLocs(definition({77, 0, 1, 0, 0xFF, 0xFF}), text, Revision_e::Rev274), "loc 0: unknown opcode 77");
    CHECK_THROWS_WITH(DecodeObjs(definition({115, 1}), text, Revision_e::Rev274), "obj 0: unknown opcode 115");
    CHECK_THROWS_WITH(DecodeVarps(definition({12, 0, 0, 0, 0}), Revision_e::Rev274), "varp 0: unknown opcode 12");
    CHECK_THROWS_WITH(DecodeVarps(definition({13}), Revision_e::Rev274), "varp 0: unknown opcode 13");
}

TEST_CASE("TypeDecoder rejects the opcodes 289 added when it reads 225", "[TypeDecoder]")
{
    const auto opcode = [](u8 value)
    {
        return std::vector<std::vector<u8>>{std::vector<u8>{value, 0, 0, 0, 0}};
    };

    auto text = TextPool{};
    for (const auto value : {u8{5}, u8{74}, u8{75}, u8{77}})
    {
        CAPTURE(value);
        CHECK_THROWS_WITH(DecodeLocs(opcode(value), text, Revision_e::Rev225), std::format("loc 0: unknown opcode {}", value));
    }

    for (const auto value : {u8{99}, u8{100}, u8{101}, u8{102}, u8{103}})
    {
        CAPTURE(value);
        CHECK_THROWS_WITH(DecodeNpcs(opcode(value), text, Revision_e::Rev225), std::format("npc 0: unknown opcode {}", value));
    }

    for (const auto value : {u8{110}, u8{111}, u8{112}, u8{113}, u8{114}, u8{115}})
    {
        CAPTURE(value);
        CHECK_THROWS_WITH(DecodeObjs(opcode(value), text, Revision_e::Rev225), std::format("obj 0: unknown opcode {}", value));
    }

    for (const auto value : {u8{11}, u8{12}, u8{13}})
    {
        CAPTURE(value);
        CHECK_THROWS_WITH(DecodeVarps(opcode(value), Revision_e::Rev225), std::format("varp 0: unknown opcode {}", value));
    }
}

TEST_CASE("TypeDecoder works out whether a 225 loc is active from its shaped models", "[TypeDecoder]")
{
    CHECK_FALSE(IsActive({}, Revision_e::Rev225));
    CHECK(IsActive({1, 1, 0, 7, 10}, Revision_e::Rev225));
    CHECK_FALSE(IsActive({1, 1, 0, 7, 22}, Revision_e::Rev225));
    CHECK_FALSE(IsActive({1, 0}, Revision_e::Rev225));
    CHECK(IsActive({30, 'O', 'p', 'e', 'n', '\n'}, Revision_e::Rev225));
}
