#include "pch.hpp"
#include "CacheWriter.hpp"

#include "Cache/CacheError.hpp"
#include "Cache/LocType_s.hpp"
#include "Cache/MapDecoder.hpp"
#include "Cache/MapSquare.hpp"
#include "Cache/TextPool.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    constexpr auto SQUARE = u16{(50 << 8) | 50};
    constexpr auto BLOCK = u8{0x1};
    constexpr auto LINK_BELOW = u8{0x2};
    constexpr auto WALL = u8{0};
    constexpr auto WALL_DECOR = u8{4};
    constexpr auto CENTREPIECE = u8{10};
    constexpr auto GROUND_DECOR = u8{22};
    constexpr auto SOME_OPTION = u16{1};

    const auto EMPTY_LOCS = std::vector<u8>{0};

    // A land file where each tile in runs has those bytes, terminator included, and every other tile is empty.
    std::vector<u8> MakeLand(const std::map<std::size_t, std::vector<u8>>& runs)
    {
        auto land = std::vector<u8>{};
        for (auto bit = std::size_t{0}; bit < MapSquare::BlockedTiles{}.size(); ++bit)
        {
            const auto run = runs.find(bit);
            if (run == runs.end())
            {
                land.push_back(0);
                continue;
            }

            land.insert(land.end(), run->second.begin(), run->second.end());
        }

        return land;
    }

    LocType_s MakeType(u16 id, std::string_view name = {})
    {
        auto type = LocType_s{};
        type.id = id;
        type.name = name;
        return type;
    }

    std::vector<LocType_s> MakeNamedTypes(std::size_t count)
    {
        auto types = std::vector<LocType_s>{};
        for (std::size_t id = 0; id < count; ++id)
        {
            types.push_back(MakeType(static_cast<u16>(id), "Named"));
        }

        return types;
    }

    std::vector<u16> GetIds(std::span<const MapLoc_s> locs)
    {
        auto ids = std::vector<u16>{};
        for (const auto loc : locs)
        {
            ids.push_back(loc.id);
        }

        return ids;
    }

    std::string DecodeError(std::span<const u8> land, std::span<const u8> locs, std::span<const LocType_s> types)
    {
        try
        {
            static_cast<void>(MapDecoder::DecodeSquare(SQUARE, land, locs, types));
        }
        catch (const CacheError& e)
        {
            return e.what();
        }

        return "no error";
    }
}

TEST_CASE("MapDecoder reads map_index", "[MapDecoder]")
{
    const auto squares = std::to_array<u16>({SQUARE, 0x3035, 0x2635});
    const auto entries = MapDecoder::DecodeIndex(CacheWriter::MakeMapIndex(squares));
    REQUIRE(entries.size() == 3);
    CHECK(entries[1].square == 0x3035);
    CHECK(entries[1].landFile == 2);
    CHECK(entries[1].locFile == 3);
    CHECK(MapDecoder::DescribeSquare(entries[2].square) == "38_53");

    CHECK_THROWS_WITH(MapDecoder::DecodeIndex(std::vector<u8>(13)), "map_index is 13 bytes, not a multiple of 7");
}

TEST_CASE("MapDecoder keeps only the flags from each land tile", "[MapDecoder]")
{
    const auto tile = [](s32 x, s32 z)
    {
        return MapSquare::GetBit(0, x, z);
    };

    const auto land = MakeLand({
        {tile(1, 1), {1, 30}},
        {tile(1, 2), {2, 5, 50, 82, 0}},
        {tile(1, 3), {49, 7, 81, 0}},
        {tile(1, 4), {50, 51, 0}},
        {tile(1, 5), {51, 50, 0}},
        {tile(1, 6), {255, 50, 1, 9}},
    });

    const auto square = MapDecoder::DecodeSquare(SQUARE, land, EMPTY_LOCS, {});
    CHECK(square.GetX() == 50);
    CHECK(square.GetZ() == 50);
    CHECK_FALSE(square.IsBlocked(0, 1, 1));
    CHECK(square.IsBlocked(0, 1, 2));
    CHECK_FALSE(square.IsBlocked(0, 1, 3));
    CHECK_FALSE(square.IsBlocked(0, 1, 4));
    CHECK(square.IsBlocked(0, 1, 5));
    CHECK(square.IsBlocked(0, 1, 6));
    CHECK(square.GetLocs().empty());

    SECTION("a land file must be used up exactly")
    {
        auto shorter = land;
        shorter.pop_back();
        CHECK(DecodeError(shorter, EMPTY_LOCS, {}) == "square 50_50 land: ends early");

        auto longer = land;
        longer.push_back(0);
        CHECK(DecodeError(longer, EMPTY_LOCS, {}) == "square 50_50 land: 1 bytes are left over");
    }
}

TEST_CASE("MapDecoder unpacks locs and sorts them by tile", "[MapDecoder]")
{
    const auto types = MakeNamedTypes(300);
    const auto placements = std::to_array<LocPlacement_s>({
        {.id = 126, .level = 0, .x = 1, .z = 62, .shape = CENTREPIECE, .angle = 3},
        {.id = 126, .level = 0, .x = 3, .z = 61, .shape = WALL, .angle = 1},
        {.id = 254, .level = 3, .x = 63, .z = 63, .shape = GROUND_DECOR, .angle = 2},
        {.id = 254, .level = 0, .x = 1, .z = 62, .shape = WALL, .angle = 0},
    });

    const auto locFile = CacheWriter::MakeLocFile(placements);
    // The id deltas are 127 and 128, as are the first id's position deltas, so smarts of both sizes are read.
    CHECK(locFile[0] == 127);
    CHECK(locFile[1] == 127);
    CHECK(locFile[3] == 0x80);
    CHECK(locFile[4] == 128);

    const auto square = MapDecoder::DecodeSquare(SQUARE, CacheWriter::MakeLand(), locFile, types);
    CHECK(square.GetLocs().size() == 4);
    CHECK(GetIds(square.GetLocsAt(0, 1, 62)) == std::vector<u16>{126, 254});
    CHECK(GetIds(square.GetLocsAt(0, 3, 61)) == std::vector<u16>{126});
    CHECK(square.GetLocsAt(0, 2, 2).empty());

    const auto corner = square.GetLocsAt(3, 63, 63);
    REQUIRE(corner.size() == 1);
    CHECK(corner[0].id == 254);
    CHECK(corner[0].GetLevel() == 3);
    CHECK(corner[0].GetX() == 63);
    CHECK(corner[0].GetZ() == 63);
    CHECK(corner[0].GetShape() == GROUND_DECOR);
    CHECK(corner[0].GetAngle() == 2);

    const auto first = square.GetLocsAt(0, 1, 62)[0];
    CHECK(first.GetShape() == CENTREPIECE);
    CHECK(first.GetAngle() == 3);

    SECTION("a loc file must be used up exactly, and name types that exist")
    {
        auto longer = locFile;
        longer.push_back(0);
        CHECK(DecodeError(CacheWriter::MakeLand(), longer, types) == "square 50_50 locs: 1 bytes are left over");
        CHECK(DecodeError(CacheWriter::MakeLand(), locFile, std::span{types}.first(200)) == "square 50_50 locs: loc 254 has no type");
    }
}

TEST_CASE("MapDecoder moves everything on a bridge down a level", "[MapDecoder]")
{
    const auto land = CacheWriter::MakeLand(std::to_array<LandFlags_s>({
        {.level = 1, .x = 5, .z = 5, .flags = LINK_BELOW | BLOCK},
        {.level = 2, .x = 5, .z = 5, .flags = BLOCK},
        {.level = 1, .x = 6, .z = 6, .flags = BLOCK},
    }));

    const auto locs = CacheWriter::MakeLocFile(std::to_array<LocPlacement_s>({
        {.id = 0, .level = 0, .x = 5, .z = 5, .shape = CENTREPIECE},
        {.id = 1, .level = 1, .x = 5, .z = 5, .shape = CENTREPIECE},
        {.id = 2, .level = 2, .x = 5, .z = 5, .shape = CENTREPIECE},
        {.id = 3, .level = 1, .x = 6, .z = 6, .shape = CENTREPIECE},
    }));

    const auto square = MapDecoder::DecodeSquare(SQUARE, land, locs, MakeNamedTypes(4));
    CHECK(square.IsBlocked(0, 5, 5));
    CHECK(square.IsBlocked(1, 5, 5));
    CHECK_FALSE(square.IsBlocked(2, 5, 5));
    CHECK(square.IsBlocked(1, 6, 6));
    CHECK_FALSE(square.IsBlocked(0, 6, 6));

    CHECK(GetIds(square.GetLocsAt(0, 5, 5)) == std::vector<u16>{1});
    CHECK(GetIds(square.GetLocsAt(1, 5, 5)) == std::vector<u16>{2});
    CHECK(square.GetLocsAt(2, 5, 5).empty());
    CHECK(GetIds(square.GetLocsAt(1, 6, 6)) == std::vector<u16>{3});
    CHECK(square.GetLocs().size() == 3);
}

TEST_CASE("MapDecoder drops decoration", "[MapDecoder]")
{
    auto types = std::vector<LocType_s>{};
    const auto addType = [&types](std::string_view name, bool blockWalk, bool active, u16 op)
    {
        auto type = MakeType(static_cast<u16>(types.size()), name);
        type.blockWalk = blockWalk;
        type.active = active;
        type.ops[0] = op;
        types.push_back(type);
    };

    addType({}, false, true, TextPool::NO_OPTION);
    addType("Flowers", false, false, TextPool::NO_OPTION);
    addType({}, false, false, SOME_OPTION);
    addType({}, true, false, TextPool::NO_OPTION);
    addType({}, true, true, TextPool::NO_OPTION);
    addType({}, true, false, TextPool::NO_OPTION);
    addType({}, true, false, TextPool::NO_OPTION);
    addType({}, true, false, TextPool::NO_OPTION);

    const auto locs = CacheWriter::MakeLocFile(std::to_array<LocPlacement_s>({
        {.id = 0, .x = 1, .shape = GROUND_DECOR},
        {.id = 1, .x = 2, .shape = GROUND_DECOR},
        {.id = 2, .x = 3, .shape = GROUND_DECOR},
        {.id = 3, .x = 4, .shape = WALL},
        {.id = 4, .x = 5, .shape = GROUND_DECOR},
        {.id = 5, .x = 6, .shape = GROUND_DECOR},
        {.id = 6, .x = 7, .shape = WALL_DECOR},
        {.id = 7, .x = 8, .shape = CENTREPIECE},
    }));

    const auto square = MapDecoder::DecodeSquare(SQUARE, CacheWriter::MakeLand(), locs, types);
    CHECK(GetIds(square.GetLocs()) == std::vector<u16>{1, 2, 3, 4, 7});
}
