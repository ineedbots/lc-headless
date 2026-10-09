#include "pch.hpp"
#include "CacheWriter.hpp"

#include "Cache/CacheError.hpp"
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
    constexpr auto REPORT_ABUSE = u16{201};
    constexpr auto UNUSED_CODE = u16{999};
    constexpr auto WIDE_HOVER_LAYER = u16{300};

    // Every type and button type, with hover layers, conditions and scripts, before the logout button.
    std::vector<InterfaceComponent_s> MakeComponents()
    {
        return {
            {.id = 0, .layer = 0, .type = LAYER, .children = {1, 2, 3}},
            {.id = 1, .type = UNUSED},
            {.id = 2, .type = INV, .buttonType = BUTTON_TARGET},
            {.id = 3, .type = RECT, .buttonType = BUTTON_CLOSE, .hoverLayer = WIDE_HOVER_LAYER},
            {.id = 10, .layer = 9, .type = TEXT, .buttonType = BUTTON_TOGGLE, .conditions = {{1, 5}, {2, 70}}, .scripts = {{1, 2, 0}, {}}},
            {.id = 11, .type = GRAPHIC, .buttonType = BUTTON_SELECT, .clientCode = REPORT_ABUSE},
            {.id = 12, .type = MODEL, .buttonType = BUTTON_CONTINUE},
            {.id = 13, .type = INV_TEXT, .buttonType = BUTTON_OK},
            {.id = 2458, .layer = 2449, .type = TEXT, .buttonType = BUTTON_OK, .clientCode = LOGOUT},
        };
    }
}

TEST_CASE("InterfaceDecoder finds a component by its client code", "[InterfaceDecoder]")
{
    const auto data = CacheWriter::MakeInterfaces(MakeComponents());
    CHECK(InterfaceDecoder::FindClientCode(data, LOGOUT) == std::optional<u16>{2458});
    CHECK(InterfaceDecoder::FindClientCode(data, REPORT_ABUSE) == std::optional<u16>{11});
    CHECK(InterfaceDecoder::FindClientCode(data, UNUSED_CODE) == std::nullopt);
    CHECK(InterfaceDecoder::FindClientCode(CacheWriter::MakeInterfaces({}), LOGOUT) == std::nullopt);
}

TEST_CASE("InterfaceDecoder stops at the first component with the code", "[InterfaceDecoder]")
{
    const auto data = CacheWriter::MakeInterfaces({
        {.id = 5, .layer = 4, .type = TEXT, .buttonType = BUTTON_OK, .clientCode = LOGOUT},
        {.id = 6, .type = TEXT, .buttonType = BUTTON_OK, .clientCode = LOGOUT},
        {.id = 7, .type = UNKNOWN_TYPE},
    });

    CHECK(InterfaceDecoder::FindClientCode(data, LOGOUT) == std::optional<u16>{5});
}

TEST_CASE("InterfaceDecoder names the component that doesn't decode", "[InterfaceDecoder]")
{
    SECTION("data too short for its count")
    {
        CHECK_THROWS_WITH(InterfaceDecoder::FindClientCode(std::vector<u8>(1), LOGOUT), "data is too short for its count");
    }

    SECTION("an unknown type")
    {
        auto components = MakeComponents();
        components[5].type = UNKNOWN_TYPE;
        CHECK_THROWS_WITH(InterfaceDecoder::FindClientCode(CacheWriter::MakeInterfaces(components), LOGOUT), "component 11: unknown type 8");
    }

    SECTION("fields that run past the end")
    {
        auto data = CacheWriter::MakeInterfaces({{.id = 4, .type = RECT}});
        data.pop_back();
        CHECK_THROWS_WITH(InterfaceDecoder::FindClientCode(data, LOGOUT), "component 4: runs past the end of the data");
    }

    SECTION("a string without its newline")
    {
        auto data = CacheWriter::MakeInterfaces({{.id = 4, .type = GRAPHIC}});
        data.pop_back();
        CHECK_THROWS_WITH(InterfaceDecoder::FindClientCode(data, LOGOUT), "component 4: a string runs past the end without its newline");
    }

    SECTION("an id cut short")
    {
        auto data = CacheWriter::MakeInterfaces({{.id = 4, .type = RECT}});
        data.push_back(0);
        CHECK_THROWS_WITH(InterfaceDecoder::FindClientCode(data, LOGOUT), "data ends inside the id of the component after 4");

        const auto layerCutShort = std::to_array<u8>({0, 1, 0xFF, 0xFF, 0});
        CHECK_THROWS_WITH(InterfaceDecoder::FindClientCode(layerCutShort, LOGOUT), "data ends inside the id of the first component");
    }
}
