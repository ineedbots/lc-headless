#include "pch.hpp"
#include "../Cache/TestCache.hpp"

#include "Cache/GameCache_s.hpp"
#include "Game/InterfaceView.hpp"
#include "Game/State/Interfaces_s.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    constexpr auto OPTIONS = u16{400};
    constexpr auto OPTION_ONE = u16{401};
    constexpr auto OPTION_TWO = u16{402};
    constexpr auto TITLE = u16{403};

    // The trade screen, and a chat box of two options, each a text component that's its own button.
    GameCache_s MakeCache()
    {
        auto cache = GameCache_s{};
        TestCache::SetTradeScreen(cache);
        TestCache::AddComponents(cache, {
            {.id = OPTIONS, .root = OPTIONS, .type = ComponentType_e::Layer, .width = 480, .height = 120, .children = {
                {.id = TITLE, .x = 0, .y = 0},
                {.id = OPTION_ONE, .x = 0, .y = 31},
                {.id = OPTION_TWO, .x = 0, .y = 63},
            }},
            {.id = TITLE, .root = OPTIONS, .type = ComponentType_e::Text, .width = 480, .height = 17, .text = "Select an Option"},
            {.id = OPTION_ONE, .root = OPTIONS, .type = ComponentType_e::Text, .buttonType = ButtonType_e::Ok, .width = 480, .height = 17, .text = "option1", .buttonText = "Ok"},
            {.id = OPTION_TWO, .root = OPTIONS, .type = ComponentType_e::Text, .buttonType = ButtonType_e::Ok, .width = 480, .height = 17, .text = "option2", .buttonText = "Ok"},
        });
        return cache;
    }

    std::vector<u16> Ids(const std::vector<const IfComponent_s*>& components)
    {
        auto ids = std::vector<u16>{};
        for (const auto* const component : components)
        {
            ids.push_back(component->id);
        }

        return ids;
    }
}

TEST_CASE("InterfaceView lists the open interfaces once each", "[InterfaceView]")
{
    const auto cache = MakeCache();
    auto interfaces = Interfaces_s{};
    interfaces.mainModal = TestCache::TRADE_SCREEN;
    interfaces.chatModal = OPTIONS;
    interfaces.tabs[0] = 50;
    interfaces.tabs[3] = 50;
    const auto view = InterfaceView{cache, interfaces};

    CHECK(view.GetOpenRoots() == std::vector<u16>{TestCache::TRADE_SCREEN, OPTIONS, 50});
    CHECK(view.IsOpen(OPTIONS));
    CHECK_FALSE(view.IsOpen(TestCache::TRADE_ACCEPT));
}

TEST_CASE("InterfaceView prefers what the server set to what the cache has", "[InterfaceView]")
{
    const auto cache = MakeCache();
    auto interfaces = Interfaces_s{};
    interfaces.mainModal = TestCache::TRADE_SCREEN;
    const auto view = InterfaceView{cache, interfaces};
    const auto& label = *view.Find(TestCache::TRADE_ACCEPT_LABEL);
    const auto& status = *view.Find(TestCache::TRADE_STATUS);
    const auto& statusLayer = *view.Find(TestCache::TRADE_STATUS_LAYER);

    CHECK(view.GetText(label) == "Accept");
    CHECK(view.GetColour(label) == 0x00C000);
    CHECK(view.IsVisible(label));
    // The status is under a layer that starts hidden.
    CHECK(view.IsHidden(statusLayer));
    CHECK_FALSE(view.IsVisible(status));

    interfaces.components[TestCache::TRADE_ACCEPT_LABEL].text = "Accepted";
    interfaces.components[TestCache::TRADE_ACCEPT_LABEL].colour = 0xFF0000;
    interfaces.components[TestCache::TRADE_STATUS_LAYER].hidden = false;
    CHECK(view.GetText(label) == "Accepted");
    CHECK(view.GetColour(label) == 0xFF0000);
    CHECK(view.IsVisible(status));

    interfaces.mainModal = -1;
    CHECK_FALSE(view.IsVisible(label));
}

TEST_CASE("InterfaceView places components by their layers' offsets, positions and scroll", "[InterfaceView]")
{
    const auto cache = MakeCache();
    auto interfaces = Interfaces_s{};
    const auto view = InterfaceView{cache, interfaces};
    const auto position = [&view](u16 id)
    {
        const auto point = view.GetPosition(*view.Find(id));
        return std::pair{point.x, point.y};
    };

    CHECK(position(TestCache::TRADE_SCREEN) == std::pair{0, 0});
    CHECK(position(TestCache::TRADE_ACCEPT) == std::pair{224, 173});
    CHECK(position(TestCache::TRADE_STATUS) == std::pair{5, 2});

    interfaces.components[TestCache::TRADE_STATUS_LAYER].position = ComponentPosition_s{.x = 10, .y = 20};
    interfaces.components[TestCache::TRADE_SCREEN].scrollPosition = 7;
    CHECK(position(TestCache::TRADE_STATUS) == std::pair{15, 15});
}

TEST_CASE("InterfaceView walks an interface in drawing order and finds visible text", "[InterfaceView]")
{
    const auto cache = MakeCache();
    auto interfaces = Interfaces_s{};
    interfaces.chatModal = OPTIONS;
    const auto view = InterfaceView{cache, interfaces};

    CHECK(Ids(view.GetTree(TestCache::TRADE_SCREEN)) == std::vector<u16>{300, 301, 302, 303, 304, 305, 306, 307, 308, 309});
    CHECK(view.GetTree(999).empty());

    CHECK(Ids(view.FindText("OPTION2")) == std::vector<u16>{OPTION_TWO});
    // The trade screen isn't open, so its label isn't found unless it's asked for by root.
    CHECK(view.FindText("Accept").empty());
    CHECK(view.FindText("Accept", TestCache::TRADE_SCREEN).empty());
    interfaces.mainModal = TestCache::TRADE_SCREEN;
    CHECK(Ids(view.FindText("accept", TestCache::TRADE_SCREEN)) == std::vector<u16>{TestCache::TRADE_ACCEPT_LABEL});
}

TEST_CASE("InterfaceView finds the button a click on a component hits", "[InterfaceView]")
{
    const auto cache = MakeCache();
    auto interfaces = Interfaces_s{};
    interfaces.mainModal = TestCache::TRADE_SCREEN;
    interfaces.chatModal = OPTIONS;
    const auto view = InterfaceView{cache, interfaces};

    // The label isn't a button; the rect under it is.
    const auto* const accept = view.ButtonAt(*view.Find(TestCache::TRADE_ACCEPT_LABEL));
    REQUIRE(accept != nullptr);
    CHECK(accept->id == TestCache::TRADE_ACCEPT);

    // A dialogue option is a text component that's its own button.
    const auto* const option = view.ButtonAt(*view.Find(OPTION_ONE));
    REQUIRE(option != nullptr);
    CHECK(option->id == OPTION_ONE);

    // Nothing to click under the title.
    CHECK(view.ButtonAt(*view.Find(TITLE)) == nullptr);
}
