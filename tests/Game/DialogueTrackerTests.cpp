#include "pch.hpp"
#include "../Support/Cache/TestCache.hpp"

#include "Cache/GameCache_s.hpp"
#include "Game/Interface/DialogueTracker.hpp"
#include "Game/Interface/InterfaceView.hpp"
#include "Game/State/Interfaces_s.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    constexpr auto DIALOGUE = u16{500};
    constexpr auto CONTINUE = u16{503};

    GameCache_s MakeCache()
    {
        auto cache = GameCache_s{};
        // clang-format off
        TestCache::AddComponents(cache, {
            {.id = DIALOGUE, .root = DIALOGUE, .type = ComponentType_e::Layer, .width = 480, .height = 120, .children = {{.id = CONTINUE, .y = 80}}},
            {.id = CONTINUE, .root = DIALOGUE, .type = ComponentType_e::Text, .buttonType = ButtonType_e::Continue, .width = 480, .height = 17, .text = "Click here to continue", .buttonText = "Continue"},
        });
        // clang-format on
        return cache;
    }
}

TEST_CASE("DialogueTracker hides a continue button once it's clicked, until the modals change", "[DialogueTracker]")
{
    const auto cache = MakeCache();
    auto interfaces = Interfaces_s{.chatModal = DIALOGUE};
    const auto view = InterfaceView{cache, interfaces};
    auto tracker = DialogueTracker{};

    CHECK(tracker.FindContinue(view) == CONTINUE);

    tracker.NoteContinued(interfaces);
    CHECK_FALSE(tracker.FindContinue(view).has_value());

    ++interfaces.modalChanges;
    CHECK(tracker.FindContinue(view) == CONTINUE);
}

TEST_CASE("DialogueTracker counts a count dialog answered until the modals change", "[DialogueTracker]")
{
    auto interfaces = Interfaces_s{};
    auto tracker = DialogueTracker{};
    CHECK_FALSE(tracker.IsCountDialogOpen(interfaces));

    interfaces.countDialogOpen = true;
    CHECK(tracker.IsCountDialogOpen(interfaces));

    tracker.NoteAnswered(interfaces);
    CHECK_FALSE(tracker.IsCountDialogOpen(interfaces));

    ++interfaces.modalChanges;
    CHECK(tracker.IsCountDialogOpen(interfaces));
}
