#include "pch.hpp"
#include "../LogCapture.hpp"
#include "../TempFolder.hpp"
#include "CacheWriter.hpp"

#include "Cache/CacheError.hpp"
#include "Cache/CacheLoader.hpp"
#include "Cache/CacheStore.hpp"
#include "Cache/GameCache_s.hpp"
#include "Cache/MapSquare.hpp"
#include "Io/Packet.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    constexpr auto SQUARE = u16{(50 << 8) | 50};
    constexpr auto SQUARE_WITHOUT_FILES = u16{(51 << 8) | 50};
    constexpr auto WALL = u8{0};
    constexpr auto CENTREPIECE = u8{10};
    constexpr auto GROUND_DECOR = u8{22};
    constexpr auto BLOCK = u8{0x1};
    constexpr auto IF_LAYER = u8{0};
    constexpr auto IF_INV = u8{2};
    constexpr auto IF_TEXT = u8{4};
    constexpr auto IF_GRAPHIC = u8{5};
    constexpr auto BUTTON_OK = u8{1};
    constexpr auto BUTTON_SELECT = u8{5};
    constexpr auto EQUALS = u8{1};
    constexpr auto PUSH_VARP = u16{5};
    constexpr auto END_SCRIPT = u16{0};
    constexpr auto LOGOUT_CLIENT_CODE = u16{205};
    constexpr auto BANK_CLIENT_CODE = u16{206};
    constexpr auto VARP_SCOPE = u8{1};
    constexpr auto VARP_CLIENT_CODE = u8{5};
    constexpr auto VARP_STRING = u8{10};
    constexpr auto RUN_CLIENT_CODE = u8{7};
    constexpr auto BRIGHTNESS_CLIENT_CODE = u8{1};
    constexpr auto BRIGHTNESS_VARP = u16{0};
    constexpr auto RUN_VARP = u16{2};
    constexpr auto LOGOUT_LAYER = u16{20};
    constexpr auto LOGOUT_BUTTON = u16{21};
    constexpr auto BANK = u16{30};
    constexpr auto BANK_INVENTORY = u16{31};
    constexpr auto INVENTORY = u16{32};
    constexpr auto EQUIPMENT = u16{33};
    constexpr auto BRIGHTNESS_BUTTON = u16{40};
    constexpr auto RUN_OFF_BUTTON = u16{41};
    constexpr auto RUN_ON_BUTTON = u16{42};

    // A select button as the webclient reads one: its first script pushes the varp, and its first
    // condition's operand is the value a click sets.
    InterfaceComponent_s MakeVarpButton(u16 id, u16 varp, u16 value)
    {
        return {.id = id, .type = IF_GRAPHIC, .buttonType = BUTTON_SELECT, .conditions = {{EQUALS, value}}, .scripts = {{PUSH_VARP, varp, END_SCRIPT}}};
    }

    InterfaceComponent_s& FindComponent(StoreContents_s& contents, u16 id)
    {
        const auto found = std::ranges::find(contents.interfaces, id, &InterfaceComponent_s::id);
        REQUIRE(found != contents.interfaces.end());
        return *found;
    }

    StoreContents_s MakeContents()
    {
        auto contents = StoreContents_s{};
        contents.locs = {
            CacheWriter::MakeDefinition("Door", {"Open"}),
            CacheWriter::MakeDefinition("", {}, std::vector<u8>{17}),
            CacheWriter::MakeDefinition("Tree", {"Chop down"}, std::vector<u8>{14, 2, 15, 2}),
        };

        contents.npcs = {
            CacheWriter::MakeDefinition("Man", {"Talk-to"}),
            CacheWriter::MakeDefinition("Chicken", {"", "Attack"}, std::vector<u8>{95, 0, 1}),
        };

        contents.objs = {
            CacheWriter::MakeDefinition("Logs"),
            CacheWriter::MakeDefinition("", {}, std::vector<u8>{97, 0, 0, 98, 0, 5}),
        };

        contents.varps = {
            CacheWriter::MakeDefinition("", {}, std::vector<u8>{VARP_SCOPE, 1, VARP_CLIENT_CODE, 0, BRIGHTNESS_CLIENT_CODE}),
            CacheWriter::MakeDefinition("", {}, std::vector<u8>{VARP_STRING, 'x', '\n'}),
            CacheWriter::MakeDefinition("", {}, std::vector<u8>{VARP_CLIENT_CODE, 0, RUN_CLIENT_CODE}),
        };

        contents.interfaces = {
            {.id = LOGOUT_LAYER, .layer = LOGOUT_LAYER, .type = IF_LAYER, .children = {LOGOUT_BUTTON}},
            {.id = LOGOUT_BUTTON, .type = IF_TEXT, .buttonType = BUTTON_OK, .clientCode = LOGOUT_CLIENT_CODE},
            {.id = BANK, .layer = BANK, .type = IF_INV, .clientCode = BANK_CLIENT_CODE, .width = 8, .height = 36, .options = {"Withdraw 1"}},
            {.id = BANK_INVENTORY, .layer = BANK_INVENTORY, .type = IF_INV, .width = 4, .height = 7, .options = {"Deposit 1", "Deposit 5"}},
            {.id = INVENTORY, .layer = INVENTORY, .type = IF_INV, .width = 4, .height = 7, .objUse = true},
            {.id = EQUIPMENT, .layer = EQUIPMENT, .type = IF_INV, .width = 3, .height = 5, .slotBackground = true, .options = {"Remove"}},
            MakeVarpButton(BRIGHTNESS_BUTTON, BRIGHTNESS_VARP, 0),
            MakeVarpButton(RUN_OFF_BUTTON, RUN_VARP, 0),
            MakeVarpButton(RUN_ON_BUTTON, RUN_VARP, 1),
        };

        contents.squares = {{
            .square = SQUARE,
            .land = CacheWriter::MakeLand(std::to_array<LandFlags_s>({{.level = 0, .x = 10, .z = 11, .flags = BLOCK}})),
            .locs = CacheWriter::MakeLocFile(std::to_array<LocPlacement_s>({
                {.id = 0, .x = 10, .z = 10, .shape = WALL, .angle = 1},
                {.id = 1, .x = 11, .z = 11, .shape = GROUND_DECOR},
                {.id = 2, .x = 20, .z = 20, .shape = CENTREPIECE},
            })),
        }};

        contents.squaresWithoutFiles = {SQUARE_WITHOUT_FILES};
        return contents;
    }

    class LoaderFixture
    {
    public:
        LoaderFixture()
            : folder{"rs2004-cache-loader-tests"}
            , writer{CacheWriter::MakeStore(MakeContents())}
        {
        }

        [[nodiscard]] std::string LoadError()
        {
            static_cast<void>(writer.Write(folder.GetPath()));
            try
            {
                static_cast<void>(CacheLoader::Load(folder.GetPath(), *capture.GetLogger()));
            }
            catch (const CacheError& e)
            {
                return e.what();
            }

            return "no error";
        }

        [[nodiscard]] std::string Prefix() const
        {
            return folder.GetPath().string() + ": ";
        }

        [[nodiscard]] bool HasLog(LogLevel_e level, std::string_view text) const
        {
            return std::ranges::any_of(capture.GetEntries(), [level, text](const CapturedLog_s& entry)
            {
                return entry.level == level && entry.message.find(text) != std::string::npos;
            });
        }

        LogCapture capture;
        TempFolder folder;
        CacheWriter writer;
    };
}

TEST_CASE("CacheLoader loads a whole store", "[CacheLoader]")
{
    auto fixture = LoaderFixture{};
    static_cast<void>(fixture.writer.Write(fixture.folder.GetPath()));
    const auto cache = CacheLoader::Load(fixture.folder.GetPath(), *fixture.capture.GetLogger());

    CHECK(cache.crcs[0] == 0);
    for (auto file = u32{1}; file < GameCache_s::CRC_COUNT; ++file)
    {
        CHECK(cache.crcs[file] == Packet::GetCrc(fixture.writer.Get(CacheStore::ARCHIVES, file)));
    }

    CHECK(cache.logoutComponent == LOGOUT_BUTTON);
    CHECK(cache.bankComponent == BANK);
    CHECK(cache.bankInventoryComponent == BANK_INVENTORY);
    CHECK(cache.inventoryComponent == INVENTORY);
    CHECK(cache.inventorySize == 28);
    CHECK(cache.equipmentComponent == EQUIPMENT);
    CHECK(cache.runVarp == RUN_VARP);
    CHECK(cache.runOffButton == RUN_OFF_BUTTON);
    CHECK(cache.runOnButton == RUN_ON_BUTTON);

    REQUIRE(cache.locs.size() == 3);
    const auto* const tree = cache.FindLoc(2);
    REQUIRE(tree != nullptr);
    CHECK(tree->name == "Tree");
    CHECK(tree->width == 2);
    CHECK(cache.GetOption(tree->ops[0]) == "Chop down");
    CHECK(cache.FindNpc(1)->combatLevel == std::optional<u16>{1});
    CHECK(cache.GetOption(cache.FindNpc(1)->ops[1]) == "Attack");
    CHECK(cache.FindObj(1)->noteOf == std::optional<u16>{0});
    CHECK(cache.FindObj(1)->name == "Logs");
    CHECK(cache.FindLoc(3) == nullptr);
    CHECK(cache.FindNpc(-1) == nullptr);

    const auto* const square = cache.FindSquare(50, 50);
    REQUIRE(square != nullptr);
    CHECK(square->IsBlocked(0, 10, 11));
    CHECK_FALSE(square->IsBlocked(0, 10, 10));
    REQUIRE(square->GetLocs().size() == 2);
    CHECK(square->GetLocs()[0].id == 0);
    CHECK(square->GetLocs()[0].GetAngle() == 1);
    CHECK(square->GetLocs()[1].id == 2);
    CHECK(cache.FindSquare(51, 50) == nullptr);
    CHECK(cache.FindSquare(-1, 50) == nullptr);

    CHECK(fixture.HasLog(LogLevel_e::Info, "3 locs, 2 NPCs, 2 objs, 1 map squares with 2 locs"));
    CHECK(fixture.HasLog(LogLevel_e::Warning, "1 map square in map_index has no files; it loads as open ground"));
}

TEST_CASE("CacheLoader's cache keeps its text when moved", "[CacheLoader]")
{
    auto fixture = LoaderFixture{};
    static_cast<void>(fixture.writer.Write(fixture.folder.GetPath()));
    auto loaded = CacheLoader::Load(fixture.folder.GetPath(), *fixture.capture.GetLogger());
    const auto shared = std::make_shared<const GameCache_s>(std::move(loaded));
    CHECK(shared->FindLoc(0)->name == "Door");
    CHECK(shared->GetOption(shared->FindLoc(0)->ops[0]) == "Open");
}

TEST_CASE("CacheLoader names the folder and file that failed", "[CacheLoader]")
{
    auto fixture = LoaderFixture{};

    SECTION("a folder without a store")
    {
        const auto missing = fixture.folder.GetPath() / "missing";
        CHECK_THROWS_WITH(CacheLoader::Load(missing, *fixture.capture.GetLogger()),
                          missing.string() + ": main_file_cache.dat not found; set client.cacheDirectory to the folder that holds the server's cache");
    }

    SECTION("a missing config archive")
    {
        fixture.writer.Put(CacheStore::ARCHIVES, 2, {});
        CHECK(fixture.LoadError() == fixture.Prefix() + "store 0 file 2 (config): not in the cache");
    }

    SECTION("a missing entry")
    {
        fixture.writer.Put(CacheStore::ARCHIVES, 2, CacheWriter::MakeArchive({{.name = "loc.dat", .data = {0, 0}}, {.name = "loc.idx", .data = {0, 0}}}, false));
        CHECK(fixture.LoadError() == fixture.Prefix() + "store 0 file 2 (config): npc.dat not found");
    }

    SECTION("a definition that doesn't decode")
    {
        auto contents = MakeContents();
        contents.objs[1] = {200, 0};
        fixture.writer = CacheWriter::MakeStore(contents);
        CHECK(fixture.LoadError() == fixture.Prefix() + "store 0 file 2 (config): obj 1: unknown opcode 200");
    }

    SECTION("a varp that doesn't decode")
    {
        auto contents = MakeContents();
        contents.varps[1] = {9, 0};
        fixture.writer = CacheWriter::MakeStore(contents);
        CHECK(fixture.LoadError() == fixture.Prefix() + "store 0 file 2 (config): varp 1: unknown opcode 9");
    }

    SECTION("no run varp")
    {
        auto contents = MakeContents();
        contents.varps.pop_back();
        fixture.writer = CacheWriter::MakeStore(contents);
        CHECK(fixture.LoadError() == fixture.Prefix() + "store 0 file 2 (config): no varp has client code 7, which marks the run varp");
    }

    SECTION("a missing interface archive")
    {
        fixture.writer.Put(CacheStore::ARCHIVES, 3, {});
        CHECK(fixture.LoadError() == fixture.Prefix() + "store 0 file 3 (interface): not in the cache");
    }

    SECTION("an interface archive without its data")
    {
        fixture.writer.Put(CacheStore::ARCHIVES, 3, CacheWriter::MakeArchive({{.name = "filler.dat", .data = {1}}}, false));
        CHECK(fixture.LoadError() == fixture.Prefix() + "store 0 file 3 (interface): data not found");
    }

    SECTION("no logout button")
    {
        auto contents = MakeContents();
        FindComponent(contents, LOGOUT_BUTTON).clientCode = 0;
        fixture.writer = CacheWriter::MakeStore(contents);
        CHECK(fixture.LoadError() == fixture.Prefix() + "store 0 file 3 (interface): no component has client code 205, which marks the logout button");
    }

    SECTION("no bank")
    {
        auto contents = MakeContents();
        FindComponent(contents, BANK).clientCode = 0;
        fixture.writer = CacheWriter::MakeStore(contents);
        CHECK(fixture.LoadError() == fixture.Prefix() + "store 0 file 3 (interface): no component has client code 206, which marks the bank");
    }

    SECTION("no backpack")
    {
        auto contents = MakeContents();
        FindComponent(contents, INVENTORY).objUse = false;
        fixture.writer = CacheWriter::MakeStore(contents);
        CHECK(fixture.LoadError() == fixture.Prefix() + "store 0 file 3 (interface): no inventory lets its items be used, which marks the backpack");
    }

    SECTION("no worn equipment")
    {
        auto contents = MakeContents();
        FindComponent(contents, EQUIPMENT).slotBackground = false;
        fixture.writer = CacheWriter::MakeStore(contents);
        CHECK(fixture.LoadError() == fixture.Prefix() + "store 0 file 3 (interface): no inventory has slot backgrounds, which marks the worn equipment");
    }

    SECTION("no backpack beside the bank")
    {
        auto contents = MakeContents();
        FindComponent(contents, BANK_INVENTORY).options = {"Store 1"};
        fixture.writer = CacheWriter::MakeStore(contents);
        CHECK(fixture.LoadError() == fixture.Prefix() + "store 0 file 3 (interface): no inventory has a Deposit option, which marks the backpack beside the bank");
    }

    SECTION("no run off button")
    {
        auto contents = MakeContents();
        FindComponent(contents, RUN_OFF_BUTTON).scripts = {{PUSH_VARP, RUN_VARP + 1, END_SCRIPT}};
        fixture.writer = CacheWriter::MakeStore(contents);
        CHECK(fixture.LoadError() == fixture.Prefix() + "store 0 file 3 (interface): no select button sets varp 2 to 0, which marks the run off button");
    }

    SECTION("no run on button")
    {
        auto contents = MakeContents();
        FindComponent(contents, RUN_ON_BUTTON).buttonType = BUTTON_OK;
        fixture.writer = CacheWriter::MakeStore(contents);
        CHECK(fixture.LoadError() == fixture.Prefix() + "store 0 file 3 (interface): no select button sets varp 2 to 1, which marks the run on button");
    }

    SECTION("a component that doesn't decode")
    {
        auto contents = MakeContents();
        contents.interfaces[0].type = 9;
        fixture.writer = CacheWriter::MakeStore(contents);
        CHECK(fixture.LoadError() == fixture.Prefix() + "store 0 file 3 (interface): component 20: unknown type 9");
    }

    SECTION("a damaged map file")
    {
        fixture.writer.Put(CacheStore::MAPS, 1, {1, 2, 3, 4, 5, 6, 7, 8, 0, 1});
        CHECK_THAT(fixture.LoadError(), ContainsSubstring(fixture.Prefix() + "store 4 file 1 (square 50_50 locs): gzip data is damaged"));
    }

    SECTION("a map file too short for its version")
    {
        fixture.writer.Put(CacheStore::MAPS, 0, {1});
        CHECK(fixture.LoadError() == fixture.Prefix() + "store 4 file 0 (square 50_50 land): map file is 1 bytes, too short for its version");
    }

    SECTION("a square that doesn't decode")
    {
        auto contents = MakeContents();
        contents.squares[0].locs = CacheWriter::MakeLocFile(std::to_array<LocPlacement_s>({{.id = 9}}));
        fixture.writer = CacheWriter::MakeStore(contents);
        CHECK(fixture.LoadError() == fixture.Prefix() + "square 50_50 locs: loc 9 has no type");
    }
}
