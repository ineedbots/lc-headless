#include "pch.hpp"
#include "CacheWriter.hpp"

#include "Cache/CacheError.hpp"
#include "Cache/JagArchive.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    std::vector<u8> ToBytes(std::string_view text)
    {
        return {text.begin(), text.end()};
    }

    std::vector<ArchiveEntry_s> MakeEntries()
    {
        return {
            {.name = "loc.dat", .data = ToBytes("the loc definitions")},
            {.name = "MAP_INDEX", .data = ToBytes("seven bytes a square")},
            {.name = "empty", .data = {}},
        };
    }

    std::vector<u8> ToBytes(const Packet& packet)
    {
        const auto data = packet.GetData();
        return {data.begin(), data.end()};
    }
}

TEST_CASE("JagArchive hashes names as the webclient does", "[JagArchive]")
{
    CHECK(JagArchive::HashName("loc.dat") == 682978269);
    CHECK(JagArchive::HashName("map_index") == 1987120305);
    CHECK(JagArchive::HashName("obj.idx") == -1667598946);
    CHECK(JagArchive::HashName("OBJ.IDX") == -1667598946);
    CHECK(JagArchive::HashName("") == 0);
}

TEST_CASE("JagArchive reads entries packed either way", "[JagArchive]")
{
    const auto compressWhole = GENERATE(false, true);
    const auto archive = JagArchive{CacheWriter::MakeArchive(MakeEntries(), compressWhole)};

    CHECK(archive.Read("loc.dat") == ToBytes("the loc definitions"));
    CHECK(archive.Read("map_index") == ToBytes("seven bytes a square"));
    CHECK(archive.Read("empty") == std::vector<u8>{});
    CHECK_FALSE(archive.Read("npc.dat").has_value());
}

TEST_CASE("JagArchive takes the first of two entries with the same name", "[JagArchive]")
{
    const auto archive = JagArchive{CacheWriter::MakeArchive({
        {.name = "loc.dat", .data = ToBytes("first")},
        {.name = "LOC.DAT", .data = ToBytes("second")},
    }, false)};

    CHECK(archive.Read("loc.dat") == ToBytes("first"));
}

TEST_CASE("JagArchive rejects a header or table that doesn't fit", "[JagArchive]")
{
    CHECK_THROWS_WITH(JagArchive{std::vector<u8>(3)}, ContainsSubstring("too short for its header"));

    SECTION("a compressed archive shorter than its packed size")
    {
        auto bytes = CacheWriter::MakeArchive(MakeEntries(), true);
        bytes.resize(bytes.size() - 1);
        CHECK_THROWS_AS(JagArchive{bytes}, CacheError);
    }

    SECTION("a table longer than the archive")
    {
        auto packet = Packet{};
        packet.P3(4);
        packet.P3(4);
        packet.P2(3);
        packet.P2(0);
        CHECK_THROWS_WITH(JagArchive{ToBytes(packet)}, ContainsSubstring("table of 3 entries runs past"));
    }

    SECTION("an entry past the end of the data")
    {
        auto packet = Packet{};
        packet.P3(12);
        packet.P3(12);
        packet.P2(1);
        packet.P4(JagArchive::HashName("loc.dat"));
        packet.P3(50);
        packet.P3(50);
        CHECK_THROWS_WITH(JagArchive{ToBytes(packet)}, ContainsSubstring("entry 0 runs past"));
    }

    SECTION("an entry that doesn't unpack to its listed size")
    {
        auto packed = CacheWriter::Bzip2Headerless(ToBytes("twelve bytes"));
        auto packet = Packet{};
        const auto bodySize = static_cast<s32>(2 + 10 + packed.size());
        packet.P3(bodySize);
        packet.P3(bodySize);
        packet.P2(1);
        packet.P4(JagArchive::HashName("loc.dat"));
        packet.P3(13);
        packet.P3(static_cast<s32>(packed.size()));
        packet.PData(packed);
        const auto archive = JagArchive{ToBytes(packet)};
        CHECK_THROWS_WITH(archive.Read("loc.dat"), ContainsSubstring("loc.dat: bzip2 data unpacks to 12 bytes, not 13"));
    }
}
