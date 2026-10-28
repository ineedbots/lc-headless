#include "pch.hpp"
#include "Script/Convert/PyObjects.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("Python component labels cover every wire type and preserve unknown fallbacks", "[PyObjects][BindingBoundaryCoverage]")
{
    const auto types = std::array{"layer", "unused", "inv", "rect", "text", "graphic", "model", "invtext"};
    for (auto i = std::size_t{0}; i < types.size(); ++i)
    {
        CHECK(PyObjects::GetTypeName(static_cast<ComponentType_e>(i)) == types[i]);
    }
    CHECK(PyObjects::GetTypeName(static_cast<ComponentType_e>(255)) == "unknown");
    CHECK_FALSE(PyObjects::GetButtonName(ButtonType_e::None));
    const auto buttons = std::array{"ok", "target", "close", "toggle", "select", "continue"};
    for (auto i = std::size_t{0}; i < buttons.size(); ++i)
    {
        CHECK(PyObjects::GetButtonName(static_cast<ButtonType_e>(i + 1)) == buttons[i]);
    }
    CHECK_FALSE(PyObjects::GetButtonName(static_cast<ButtonType_e>(255)));
}
