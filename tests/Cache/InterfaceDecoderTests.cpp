#include "pch.hpp"
#include "CacheWriter.hpp"

#include "Cache/CacheError.hpp"
#include "Cache/ClientCode_e.hpp"
#include "Cache/InterfaceDecoder.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

namespace
{
    constexpr auto LAYER = u8{0};
    constexpr auto UNUSED = u8{1};
    constexpr auto INV = u8{2};
    constexpr auto RECT = u8{3};
    constexpr auto TEXT = u8{4};
    constexpr auto GRAPHIC = u8{5};
    constexpr auto MODEL = u8{6};
    constexpr auto INV_TEXT = u8{7};
    constexpr auto UNKNOWN_TYPE = u8{8};
    constexpr auto BUTTON_OK = u8{1};
    constexpr auto BUTTON_TARGET = u8{2};
    constexpr auto BUTTON_CLOSE = u8{3};
    constexpr auto BUTTON_TOGGLE = u8{4};
    constexpr auto BUTTON_SELECT = u8{5};
    constexpr auto BUTTON_CONTINUE = u8{6};
    constexpr auto LOGOUT = u16{205};
    constexpr auto ADD_FRIEND = u16{201};
    constexpr auto WIDE_HOVER_LAYER = u16{300};

    // Every type and button type, with hover layers, conditions and scripts, before the logout button.
    std::vector<InterfaceComponent_s> MakeComponents()
    {
        return {
            {.id = 0, .layer = 0, .type = LAYER, .children = {1, 2, 3}},
            {.id = 1, .type = UNUSED},
            {.id = 2, .type = INV, .buttonType = BUTTON_TARGET, .width = 4, .height = 7, .objUse = true, .slotBackground = true, .options = {"Use", "", "Drop"}},
            {.id = 3, .type = RECT, .buttonType = BUTTON_CLOSE, .hoverLayer = WIDE_HOVER_LAYER},
            {.id = 10, .layer = 9, .type = TEXT, .buttonType = BUTTON_TOGGLE, .conditions = {{1, 5}, {2, 70}}, .scripts = {{1, 2, 0}, {}}},
            {.id = 11, .type = GRAPHIC, .buttonType = BUTTON_SELECT, .clientCode = ADD_FRIEND},
            {.id = 12, .type = MODEL, .buttonType = BUTTON_CONTINUE},
            {.id = 13, .type = INV_TEXT, .buttonType = BUTTON_OK, .options = {"Use"}},
            {.id = 2458, .layer = 2449, .type = TEXT, .buttonType = BUTTON_OK, .clientCode = LOGOUT},
        };
    }
}

TEST_CASE("InterfaceDecoder reads every component in order", "[InterfaceDecoder]")
{
    const auto components = InterfaceDecoder::Decode(CacheWriter::MakeInterfaces(MakeComponents()));
    const auto ids = std::vector<u16>{0, 1, 2, 3, 10, 11, 12, 13, 2458};
    REQUIRE(components.size() == ids.size());
    for (std::size_t i = 0; i < ids.size(); ++i)
    {
        CHECK(components[i].id == ids[i]);
    }

    CHECK(components[0].type == ComponentType_e::Layer);
    CHECK(components[7].type == ComponentType_e::InvText);
    CHECK(components[3].buttonType == ButtonType_e::Close);
    CHECK(components[5].buttonType == ButtonType_e::Select);
    CHECK(components[5].clientCode == ClientCode_e::AddFriend);
    CHECK(components[8].clientCode == ClientCode_e::Logout);
    CHECK(components[1].clientCode == ClientCode_e::None);
    CHECK(InterfaceDecoder::Decode(CacheWriter::MakeInterfaces({})).empty());
}

TEST_CASE("InterfaceDecoder reads conditions and scripts", "[InterfaceDecoder]")
{
    const auto components = InterfaceDecoder::Decode(CacheWriter::MakeInterfaces(MakeComponents()));
    const auto& toggle = components[4];
    CHECK(toggle.operands == std::vector<u16>{5, 70});
    REQUIRE(toggle.scripts.size() == 2);
    CHECK(toggle.scripts[0] == std::vector<u16>{1, 2, 0});
    CHECK(toggle.scripts[1].empty());
    CHECK(components[0].operands.empty());
    CHECK(components[0].scripts.empty());
}

TEST_CASE("InterfaceDecoder reads an inventory's size, use, backgrounds and options", "[InterfaceDecoder]")
{
    const auto components = InterfaceDecoder::Decode(CacheWriter::MakeInterfaces({
        {.id = 2, .type = INV, .width = 4, .height = 7, .objUse = true, .slotBackground = true, .options = {"Use", "", "Drop"}},
        {.id = 3, .type = INV, .width = 3, .height = 5},
    }));

    REQUIRE(components.size() == 2);
    const auto& backpack = components[0];
    CHECK(backpack.width == 4);
    CHECK(backpack.height == 7);
    CHECK(backpack.objUse);
    CHECK(backpack.hasSlotBackgrounds);
    CHECK(backpack.options == std::array<std::string, IfComponent_s::OPTION_COUNT>{"Use", "", "Drop", "", ""});

    const auto& plain = components[1];
    CHECK_FALSE(plain.objUse);
    CHECK_FALSE(plain.hasSlotBackgrounds);
    CHECK(plain.options == std::array<std::string, IfComponent_s::OPTION_COUNT>{});
}

TEST_CASE("InterfaceDecoder names the component that doesn't decode", "[InterfaceDecoder]")
{
    SECTION("data too short for its count")
    {
        CHECK_THROWS_WITH(InterfaceDecoder::Decode(std::vector<u8>(1)), "data is too short for its count");
    }

    SECTION("an unknown type")
    {
        auto components = MakeComponents();
        components[5].type = UNKNOWN_TYPE;
        CHECK_THROWS_WITH(InterfaceDecoder::Decode(CacheWriter::MakeInterfaces(components)), "component 11: unknown type 8");
    }

    SECTION("fields that run past the end")
    {
        auto data = CacheWriter::MakeInterfaces({{.id = 4, .type = RECT}});
        data.pop_back();
        CHECK_THROWS_WITH(InterfaceDecoder::Decode(data), "component 4: runs past the end of the data");
    }

    SECTION("a string without its newline")
    {
        auto data = CacheWriter::MakeInterfaces({{.id = 4, .type = GRAPHIC}});
        data.pop_back();
        CHECK_THROWS_WITH(InterfaceDecoder::Decode(data), "component 4: a string runs past the end without its newline");
    }

    SECTION("an id cut short")
    {
        auto data = CacheWriter::MakeInterfaces({{.id = 4, .type = RECT}});
        data.push_back(0);
        CHECK_THROWS_WITH(InterfaceDecoder::Decode(data), "data ends inside the id of the component after 4");

        const auto layerCutShort = std::to_array<u8>({0, 1, 0xFF, 0xFF, 0});
        CHECK_THROWS_WITH(InterfaceDecoder::Decode(layerCutShort), "data ends inside the id of the first component");
    }
}
