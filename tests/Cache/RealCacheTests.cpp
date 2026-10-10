#include "pch.hpp"
#include "../LogCapture.hpp"

#include "Cache/CacheLoader.hpp"
#include "Cache/GameCache_s.hpp"
#include "Cache/MapSquare.hpp"
#include "Game/ChatDialog.hpp"
#include "Game/InterfaceView.hpp"
#include "Game/Map/CollisionFlag.hpp"
#include "Game/Map/WorldMap.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/State/Interfaces_s.hpp"
#include "Game/State/Zone_s.hpp"
#include "Game/Tile_s.hpp"

#include <catch2/catch_test_macros.hpp>

// These read the 289 cache from the folder in RS2004_CACHE_DIR, such as ../289server/engine/data/pack,
// and skip when it isn't set.
namespace
{
    constexpr auto CACHE_DIR_VARIABLE = "RS2004_CACHE_DIR";

    std::optional<std::filesystem::path> GetCacheDirectory()
    {
        // MSVC deprecates getenv in favour of _dupenv_s, which other platforms don't have.
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable : 4996)
#endif
        const auto* const value = std::getenv(CACHE_DIR_VARIABLE);
#ifdef _MSC_VER
#pragma warning(pop)
#endif
        if (value == nullptr || *value == '\0')
        {
            return std::nullopt;
        }

        return std::filesystem::path{value};
    }

    // Loaded once for every test here; the load time goes to the test output.
    std::shared_ptr<const GameCache_s> GetRealCache()
    {
        static const auto cache = []
        {
            auto capture = LogCapture{};
            auto loaded = std::make_shared<const GameCache_s>(CacheLoader::Load(*GetCacheDirectory(), *capture.GetLogger()));
            for (const auto& entry : capture.GetEntries())
            {
                UNSCOPED_INFO(entry.message);
            }

            return loaded;
        }();

        return cache;
    }

    const GameCache_s& RequireRealCache()
    {
        if (!GetCacheDirectory())
        {
            SKIP("Set RS2004_CACHE_DIR to a 289 cache folder to run this test");
        }

        return *GetRealCache();
    }

    std::vector<std::string_view> GetOptions(const GameCache_s& cache, std::span<const u16> ops)
    {
        auto options = std::vector<std::string_view>{};
        for (const auto op : ops)
        {
            options.push_back(cache.GetOption(op));
        }

        return options;
    }
}

TEST_CASE("The real cache gives the server's CRCs", "[RealCache]")
{
    const auto& cache = RequireRealCache();
    const auto expected = std::array<u32, GameCache_s::CRC_COUNT>{0x00000000, 0xde5b3345, 0x6026f8fe, 0x07550309, 0x9a13636e, 0xca2717bd, 0x368f1792, 0x1b1fb6b2, 0xa7129379};
    for (std::size_t i = 0; i < expected.size(); ++i)
    {
        CHECK(std::bit_cast<u32>(cache.crcs[i]) == expected[i]);
    }
}

TEST_CASE("The real cache gives the server's components and run varp", "[RealCache]")
{
    const auto& cache = RequireRealCache();
    CHECK(cache.logoutComponent == 2458);
    CHECK(cache.inventoryComponent == 3214);
    CHECK(cache.inventorySize == 28);
    CHECK(cache.equipmentComponent == 1688);
    CHECK(cache.bankComponent == 5382);
    CHECK(cache.bankInventoryComponent == 2006);
    CHECK(cache.runOffButton == 152);
    CHECK(cache.runOnButton == 153);
    CHECK(cache.runVarp == 173);
}

TEST_CASE("The real cache has every type and square", "[RealCache]")
{
    const auto& cache = RequireRealCache();
    CHECK(cache.locs.size() == 5116);
    CHECK(cache.npcs.size() == 1596);
    CHECK(cache.objs.size() == 4089);
    CHECK(cache.text.GetOptionCount() == 219 + 1);
    CHECK(cache.squares.size() == 534);

    auto locCount = std::size_t{0};
    auto blockedCount = std::size_t{0};
    for (const auto& [id, square] : cache.squares)
    {
        locCount += square.GetLocs().size();
        for (auto level = 0; level < MapSquare::LEVELS; ++level)
        {
            for (auto x = 0; x < MapSquare::SIZE; ++x)
            {
                for (auto z = 0; z < MapSquare::SIZE; ++z)
                {
                    blockedCount += square.IsBlocked(level, x, z) ? 1 : 0;
                }
            }
        }
    }

    CHECK(locCount == 567454);
    CHECK(blockedCount == 543497);
}

TEST_CASE("The real cache's NPCs", "[RealCache]")
{
    const auto& cache = RequireRealCache();
    const auto* const chicken = cache.FindNpc(41);
    REQUIRE(chicken != nullptr);
    CHECK(chicken->name == "Chicken");
    CHECK(cache.GetOption(chicken->ops[1]) == "Attack");
    CHECK(chicken->size == 1);
    CHECK(chicken->combatLevel == std::optional<u16>{1});

    const auto* const man = cache.FindNpc(1);
    REQUIRE(man != nullptr);
    CHECK(man->name == "Man");
    const auto options = GetOptions(cache, man->ops);
    CHECK(std::ranges::find(options, "Talk-to") != options.end());
    CHECK(std::ranges::find(options, "Attack") != options.end());
    CHECK(std::ranges::find(options, "Pickpocket") != options.end());
}

TEST_CASE("The real cache's objs", "[RealCache]")
{
    const auto& cache = RequireRealCache();
    CHECK(cache.FindObj(995)->name == "Coins");
    CHECK(cache.FindObj(995)->stackable);
    CHECK(cache.FindObj(526)->name == "Bones");
    CHECK(cache.GetOption(cache.FindObj(526)->inventoryOps[0]) == "Bury");
    CHECK(cache.FindObj(1511)->name == "Logs");
    CHECK(cache.GetOption(cache.FindObj(1511)->ops[3]) == "Light");

    const auto* const note = cache.FindObj(1512);
    REQUIRE(note != nullptr);
    CHECK(note->noteOf == std::optional<u16>{1511});
    CHECK(note->name == "Logs");
    CHECK(note->stackable);
}

TEST_CASE("The real cache's locs", "[RealCache]")
{
    const auto& cache = RequireRealCache();
    const auto* const tree = cache.FindLoc(1276);
    REQUIRE(tree != nullptr);
    CHECK(tree->name == "Tree");
    CHECK(tree->width == 2);
    CHECK(tree->length == 2);
    CHECK(cache.GetOption(tree->ops[0]) == "Chop down");

    CHECK(cache.FindLoc(1530)->name == "Door");
    CHECK(cache.GetOption(cache.FindLoc(1530)->ops[0]) == "Open");

    const auto* const booth = cache.FindLoc(2213);
    REQUIRE(booth != nullptr);
    CHECK(booth->name == "Bank booth");
    const auto options = GetOptions(cache, booth->ops);
    CHECK(std::ranges::find(options, "Use") != options.end());
    CHECK(std::ranges::find(options, "Use-quickly") != options.end());
    CHECK(booth->blockWalk);
    CHECK_FALSE(booth->blockRange);

    const auto* const square = cache.FindSquare(38, 53);
    REQUIRE(square != nullptr);
    const auto locs = square->GetLocsAt(1, 2444 - 38 * MapSquare::SIZE, 3424 - 53 * MapSquare::SIZE);
    const auto found = std::ranges::find(locs, u16{2213}, &MapLoc_s::id);
    REQUIRE(found != locs.end());
    CHECK(found->GetShape() == 10);
    CHECK(found->GetAngle() == 1);
}

TEST_CASE("The real cache's map builds an area's collision", "[RealCache]")
{
    static_cast<void>(RequireRealCache());
    constexpr auto BOOTH = Tile_s{.x = 2444, .z = 3424, .level = 1};
    constexpr auto RADIUS_ZONES = 6;
    auto state = GameState_s{};
    const auto zoneX = BOOTH.x / Zone_s::SIZE;
    const auto zoneZ = BOOTH.z / Zone_s::SIZE;
    state.buildArea = BuildArea_s{.loaded = true, .centreZoneX = zoneX, .centreZoneZ = zoneZ, .baseX = (zoneX - RADIUS_ZONES) * Zone_s::SIZE, .baseZ = (zoneZ - RADIUS_ZONES) * Zone_s::SIZE};
    state.sceneChangeCount = 1;

    auto map = WorldMap{GetRealCache()};
    const auto start = std::chrono::steady_clock::now();
    map.Update(state);
    const auto elapsed = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now() - start);
    UNSCOPED_INFO(std::format("Rebuilt the area in {} us", elapsed.count()));

    const auto booth = map.GetLoc(BOOTH, LocLayer_e::Ground);
    REQUIRE(booth.has_value());
    CHECK(booth->id == 2213);
    const auto local = Tile_s{.x = BOOTH.x - state.buildArea.baseX, .z = BOOTH.z - state.buildArea.baseZ};
    CHECK((map.GetCollision(BOOTH.level).GetFlags(local.x, local.z) & CollisionFlag::LOC) != 0);
    CHECK_FALSE(map.GetLocs(BOOTH.level).empty());
}

TEST_CASE("The real cache's interfaces click as the webclient's do", "[RealCache]")
{
    constexpr auto TRADE_SCREEN = u16{3323};
    constexpr auto TRADE_ACCEPT = u16{3420};
    constexpr auto TRADE_ACCEPT_LABEL = u16{3421};
    constexpr auto TWO_OPTIONS = u16{2459};
    constexpr auto TITLE = u16{2460};

    const auto& cache = RequireRealCache();
    UNSCOPED_INFO(std::format("{} interface components", cache.components.size()));
    auto interfaces = Interfaces_s{};
    interfaces.mainModal = TRADE_SCREEN;
    interfaces.chatModal = TWO_OPTIONS;
    const auto view = InterfaceView{cache, interfaces};

    // trademain's "Accept" is a label over an unlabelled rect, which is what a click on it hits.
    const auto labels = view.FindText("Accept", TRADE_SCREEN);
    REQUIRE(labels.size() == 1);
    CHECK(labels[0]->id == TRADE_ACCEPT_LABEL);
    const auto* const accept = view.ButtonAt(*labels[0]);
    REQUIRE(accept != nullptr);
    CHECK(accept->id == TRADE_ACCEPT);
    CHECK(accept->type == ComponentType_e::Rect);
    CHECK(accept->buttonType == ButtonType_e::Ok);

    // multi2's options are text components that are their own Ok buttons; its title isn't a button.
    for (const auto id : {u16{2461}, u16{2462}})
    {
        CAPTURE(id);
        const auto* const option = view.Find(id);
        REQUIRE(option != nullptr);
        CHECK(option->type == ComponentType_e::Text);
        CHECK(option->buttonType == ButtonType_e::Ok);
        CHECK(option->root == TWO_OPTIONS);
        const auto* const hit = view.ButtonAt(*option);
        REQUIRE(hit != nullptr);
        CHECK(hit->id == id);
    }

    CHECK(view.Find(TITLE)->buttonType == ButtonType_e::None);
    CHECK(view.GetText(*view.Find(TITLE)) == "Select an Option");

    // The backpack's menu offers its items' options; the bank's and the worn equipment's, their own.
    const auto& backpack = *cache.FindComponent(cache.inventoryComponent);
    const auto& bank = *cache.FindComponent(cache.bankComponent);
    const auto& worn = *cache.FindComponent(cache.equipmentComponent);
    CHECK((backpack.objOps && !bank.objOps && !worn.objOps));
    CHECK(bank.options[0] == "Withdraw 1");
    CHECK(worn.options[0] == "Remove");
    CHECK((backpack.marginX == 10 && backpack.marginY == 4));
}

TEST_CASE("The real cache's dialogues and make menus are recognised by their shape", "[RealCache]")
{
    constexpr auto TWO_OPTIONS = u16{2459};
    constexpr auto SKILL_MULTI2 = u16{8866};
    constexpr auto MODEL_A = u16{8869};
    constexpr auto MAKE1_A = u16{8874};
    constexpr auto SMELTING = u16{2400};
    constexpr auto SMELTING_BRONZE_MODEL = u16{2405};
    constexpr auto TANNER = u16{679};
    constexpr auto JEWELLERY = u16{4161};
    constexpr auto RINGS_INV = u16{4233};
    constexpr auto RINGS1 = u16{4246};
    constexpr auto BRONZE_BAR = u16{2349};
    constexpr auto GOLD_RING = u16{1635};

    const auto& cache = RequireRealCache();
    auto state = GameState_s{};
    auto& interfaces = state.interfaces;
    const auto view = InterfaceView{cache, interfaces};

    SECTION("multi2's options, and no make menu")
    {
        interfaces.chatModal = TWO_OPTIONS;
        interfaces.components[2461].text = "Yes please.";
        interfaces.components[2462].text = "@red@No thanks.";
        const auto options = ChatDialog::GetOptions(view);
        REQUIRE(options.size() == 2);
        CHECK((options[0].com == 2461 && options[0].text == "Yes please."));
        CHECK((options[1].com == 2462 && options[1].text == "No thanks."));
        CHECK(ChatDialog::GetMakeProducts(view).empty());
        CHECK_FALSE(ChatDialog::FindContinue(view).has_value());
    }

    SECTION("skill_multi2's stacked buttons, one product each, named by their text")
    {
        interfaces.chatModal = SKILL_MULTI2;
        interfaces.components[MAKE1_A].text = "\n\n\n\nOak Long Bow";
        interfaces.components[MODEL_A].model = ComponentModel_s{.kind = ComponentModelKind_e::Object, .id = BRONZE_BAR};
        const auto products = ChatDialog::GetMakeProducts(view);
        REQUIRE(products.size() == 2);
        CHECK(products[0].name == "Oak Long Bow");
        CHECK(products[0].item == BRONZE_BAR);
        auto amounts = std::vector<s32>{};
        for (const auto& button : products[0].buttons)
        {
            amounts.push_back(button.amount);
        }

        CHECK(amounts == std::vector<s32>{MakeButton_s::X, 10, 5, 1});
        CHECK(products[0].buttons.back().com == MAKE1_A);
        // The second has no text of its own, so it's named by what's drawn over it, which is nothing here.
        CHECK(products[1].item == -1);
        CHECK(ChatDialog::GetOptions(view).empty());
        // In drawing order, which puts the buttons before the prompt.
        CHECK(ChatDialog::GetTexts(view) == std::vector<std::string>{"Oak Long Bow", "What would you like to make?"});
    }

    SECTION("the furnace's bars")
    {
        interfaces.chatModal = SMELTING;
        interfaces.components[SMELTING_BRONZE_MODEL].model = ComponentModel_s{.kind = ComponentModelKind_e::Object, .id = BRONZE_BAR};
        const auto products = ChatDialog::GetMakeProducts(view);
        REQUIRE(products.size() == 8);
        CHECK(products[0].name == "Bronze");
        CHECK(products[0].item == BRONZE_BAR);
        CHECK(products[1].name == "Iron");
        CHECK(products[0].buttons.size() == 4);
    }

    SECTION("the tanner's leathers, in the main modal, with Tan all")
    {
        interfaces.mainModal = TANNER;
        const auto products = ChatDialog::GetMakeProducts(view);
        REQUIRE_FALSE(products.empty());
        // The name is the text the player reads, price and all.
        CHECK(products[0].name == "Soft leather: 1 gp");
        CHECK(std::ranges::any_of(products[0].buttons, [](const MakeButton_s& button) { return button.amount == MakeButton_s::ALL; }));
    }

    SECTION("jewellery's products are drawn over placeholder slots")
    {
        // The first slot shows its own item; the model over the second shows that slot's product.
        constexpr auto PLACEHOLDER = 1;
        interfaces.mainModal = JEWELLERY;
        state.inventories[RINGS_INV] = Inventory_s{.com = RINGS_INV, .slots = {{.id = GOLD_RING, .count = 1}, {.id = PLACEHOLDER, .count = 1}}};
        interfaces.components[RINGS1].model = ComponentModel_s{.kind = ComponentModelKind_e::Object, .id = BRONZE_BAR};
        const auto slots = ChatDialog::GetMakePanel(view, state);
        REQUIRE(slots.size() == 2);
        CHECK((slots[0].com == RINGS_INV && slots[0].slot == 0 && slots[0].product == GOLD_RING));
        CHECK((slots[1].slot == 1 && slots[1].id == PLACEHOLDER && slots[1].product == BRONZE_BAR));
    }
}
