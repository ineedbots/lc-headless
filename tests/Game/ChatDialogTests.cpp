#include "pch.hpp"
#include "../Cache/TestCache.hpp"

#include "Cache/GameCache_s.hpp"
#include "Game/ChatDialog.hpp"
#include "Game/InterfaceView.hpp"
#include "Game/State/GameState_s.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    constexpr auto DIALOGUE = u16{500};
    constexpr auto SPEAKER = u16{501};
    constexpr auto LINE = u16{502};
    constexpr auto CONTINUE = u16{503};

    constexpr auto MENU = u16{600};
    constexpr auto MAKE_X = u16{601};
    constexpr auto MAKE_5 = u16{602};
    constexpr auto MAKE_1 = u16{603};
    constexpr auto MODEL = u16{604};
    constexpr auto TAN_ALL = u16{605};
    constexpr auto TAN_1 = u16{606};
    constexpr auto OPTION = u16{607};

    constexpr auto PANEL = u16{700};
    constexpr auto PANEL_INV = u16{701};
    constexpr auto PANEL_MODEL = u16{702};

    constexpr auto BOW = u16{60};
    constexpr auto RING = u16{70};

    IfComponent_s Button(u16 id, u16 root, std::string option, std::string text = {})
    {
        return {.id = id, .root = root, .type = ComponentType_e::Text, .buttonType = ButtonType_e::Ok, .width = 100, .height = 90, .text = std::move(text), .buttonText = std::move(option)};
    }

    // A dialogue page; a menu with a stacked product over a model, a stacked one named only by its options,
    // and a lone option; and a panel whose second slot shows a product drawn over it.
    GameCache_s MakeCache()
    {
        auto cache = GameCache_s{};
        TestCache::AddObj(cache, BOW, "Oak longbow (u)");
        TestCache::AddObj(cache, RING, "Gold ring");
        TestCache::AddComponents(cache, {
            {.id = DIALOGUE, .root = DIALOGUE, .type = ComponentType_e::Layer, .width = 480, .height = 120, .children = {{.id = SPEAKER}, {.id = LINE, .y = 20}, {.id = CONTINUE, .y = 80}}},
            {.id = SPEAKER, .root = DIALOGUE, .type = ComponentType_e::Text, .width = 480, .height = 17, .text = "@red@Hans"},
            {.id = LINE, .root = DIALOGUE, .type = ComponentType_e::Text, .width = 480, .height = 17, .text = "Hello\\nthere."},
            {.id = CONTINUE, .root = DIALOGUE, .type = ComponentType_e::Text, .buttonType = ButtonType_e::Continue, .width = 480, .height = 17, .text = "Click here to continue", .buttonText = "Continue"},

            {.id = MENU, .root = MENU, .type = ComponentType_e::Layer, .width = 480, .height = 120, .children = {
                {.id = MAKE_X, .x = 10}, {.id = MAKE_5, .x = 10}, {.id = MAKE_1, .x = 10}, {.id = MODEL, .x = 30, .y = 10},
                {.id = TAN_ALL, .x = 200}, {.id = TAN_1, .x = 200}, {.id = OPTION, .x = 350},
            }},
            Button(MAKE_X, MENU, "Make X"),
            Button(MAKE_5, MENU, "Make 5"),
            Button(MAKE_1, MENU, "Make 1", "\\n\\n\\n\\n@blu@Oak Long Bow"),
            {.id = MODEL, .root = MENU, .type = ComponentType_e::Model, .width = 32, .height = 32},
            Button(TAN_ALL, MENU, "Tan all @lre@Soft Leathers"),
            Button(TAN_1, MENU, "Tan 1 @lre@Soft Leathers"),
            Button(OPTION, MENU, "Ok", "Never mind"),

            {.id = PANEL, .root = PANEL, .type = ComponentType_e::Layer, .width = 480, .height = 300, .children = {{.id = PANEL_INV, .x = 20, .y = 20}, {.id = PANEL_MODEL, .x = 62, .y = 20}}},
            {.id = PANEL_INV, .root = PANEL, .type = ComponentType_e::Inv, .width = 4, .height = 1, .marginX = 10, .options = {"Make", "Make 5", "Make 10"}},
            {.id = PANEL_MODEL, .root = PANEL, .type = ComponentType_e::Model, .width = 32, .height = 32},
        });
        return cache;
    }
}

TEST_CASE("ChatDialog cleans text and reads make amounts", "[ChatDialog]")
{
    CHECK(ChatDialog::CleanText("\\n\\n\\n\\n@blu@Oak  Long Bow\n") == "Oak Long Bow");
    CHECK(ChatDialog::CleanText("@red@") == "");
    CHECK(ChatDialog::CleanText("a@b") == "a@b");

    CHECK(ChatDialog::ParseAmount("Make 10") == 10);
    CHECK(ChatDialog::ParseAmount("Smelt X @lre@Bronze") == MakeButton_s::X);
    CHECK(ChatDialog::ParseAmount("Tan all @lre@Soft Leathers") == MakeButton_s::ALL);
    CHECK_FALSE(ChatDialog::ParseAmount("Make").has_value());
    CHECK_FALSE(ChatDialog::ParseAmount("Ok").has_value());
    CHECK_FALSE(ChatDialog::ParseAmount("Make 0").has_value());
}

TEST_CASE("ChatDialog reads a dialogue page and its continue button", "[ChatDialog]")
{
    const auto cache = MakeCache();
    auto interfaces = Interfaces_s{};
    const auto view = InterfaceView{cache, interfaces};
    CHECK_FALSE(ChatDialog::FindContinue(view).has_value());
    CHECK(ChatDialog::GetTexts(view).empty());

    interfaces.chatModal = DIALOGUE;
    CHECK(ChatDialog::FindContinue(view) == CONTINUE);
    CHECK(ChatDialog::GetTexts(view) == std::vector<std::string>{"Hans", "Hello there.", "Click here to continue"});
    CHECK(ChatDialog::GetOptions(view).empty());

    interfaces.components[CONTINUE].hidden = true;
    CHECK_FALSE(ChatDialog::FindContinue(view).has_value());
}

TEST_CASE("ChatDialog tells make menus from options by their stacked buttons", "[ChatDialog]")
{
    const auto cache = MakeCache();
    auto interfaces = Interfaces_s{};
    interfaces.chatModal = MENU;
    const auto view = InterfaceView{cache, interfaces};

    const auto options = ChatDialog::GetOptions(view);
    REQUIRE(options.size() == 1);
    CHECK((options[0].com == OPTION && options[0].text == "Never mind"));

    auto products = ChatDialog::GetMakeProducts(view);
    REQUIRE(products.size() == 2);
    CHECK(products[0].name == "Oak Long Bow");
    CHECK(products[0].item == -1);
    REQUIRE(products[0].buttons.size() == 3);
    CHECK((products[0].buttons[0].com == MAKE_X && products[0].buttons[0].amount == MakeButton_s::X));
    CHECK((products[0].buttons[2].com == MAKE_1 && products[0].buttons[2].amount == 1));
    // Named by what follows the amount in its options.
    CHECK(products[1].name == "Soft Leathers");
    CHECK(products[1].buttons[0].amount == MakeButton_s::ALL);

    // The item drawn over the buttons, which names a product with no text.
    interfaces.components[MODEL].model = ComponentModel_s{.kind = ComponentModelKind_e::Object, .id = BOW};
    interfaces.components[MAKE_1].text = "";
    products = ChatDialog::GetMakeProducts(view);
    CHECK(products[0].item == BOW);
    CHECK(products[0].name == "Oak longbow (u)");

    // Without a chat modal, the main modal's.
    interfaces.chatModal = -1;
    interfaces.mainModal = MENU;
    CHECK(ChatDialog::GetMakeProducts(view).size() == 2);
    CHECK(ChatDialog::GetOptions(view).empty());
}

TEST_CASE("ChatDialog reads a make panel's products, drawn over its slots or in them", "[ChatDialog]")
{
    const auto cache = MakeCache();
    auto state = GameState_s{};
    auto& interfaces = state.interfaces;
    const auto view = InterfaceView{cache, interfaces};
    state.inventories[PANEL_INV] = Inventory_s{.com = PANEL_INV, .slots = {{.id = RING, .count = 1}, {.id = 1, .count = 1}, {}}};
    CHECK(ChatDialog::GetMakePanel(view, state).empty());

    interfaces.mainModal = PANEL;
    interfaces.components[PANEL_MODEL].model = ComponentModel_s{.kind = ComponentModelKind_e::Object, .id = BOW};
    const auto slots = ChatDialog::GetMakePanel(view, state);
    REQUIRE(slots.size() == 2);
    CHECK((slots[0].slot == 0 && slots[0].id == RING && slots[0].product == RING));
    CHECK((slots[1].com == PANEL_INV && slots[1].slot == 1 && slots[1].id == 1 && slots[1].product == BOW));
}
