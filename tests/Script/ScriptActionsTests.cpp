#include "pch.hpp"
#include "../Support/Cache/TestCache.hpp"
#include "../Support/Game/FakeGameServer.hpp"
#include "../Support/Game/Fixtures.hpp"
#include "../Support/Game/QueryWorld.hpp"
#include "../Support/LogCapture.hpp"

#include "Config/Config_s.hpp"
#include "Game/GameActions.hpp"
#include "Game/GameClient.hpp"
#include "Game/Menu/MenuOp.hpp"
#include "Game/Query/InventoryItem_s.hpp"
#include "Script/ScriptActions.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    // A client that never logs in: actions only get as far as checking their targets, since sending throws
    // without a session.
    class ActionsFixture
    {
    public:
        ActionsFixture()
            : client{std::make_shared<const Config_s>(), world.cache, FakeGameServer::MakeAccount(), capture.GetLogger()}
            , gameActions{client}
            , actions{world.state, world.map, gameActions}
        {
        }

        LogCapture capture;
        QueryWorld world;
        GameClient client;
        GameActions gameActions;
        ScriptActions actions;
    };
}

TEST_CASE("ScriptActions report targets that are gone", "[ScriptActions]")
{
    auto fixture = ActionsFixture{};
    auto& actions = fixture.actions;
    const auto bones = InventoryItem_s{.com = TestCache::INVENTORY, .slot = 2, .id = QueryWorld::BONES, .count = 1};

    CHECK_FALSE(actions.InteractNpc(99, MenuOp::ATTACK));
    CHECK_FALSE(actions.InteractPlayer(99, 1));
    CHECK_FALSE(actions.InteractGroundItem(QueryWorld::BONES, Fixtures::HOME, Fixtures::HOME, MenuOp::TAKE));
    CHECK_FALSE(actions.ItemOp({.com = TestCache::INVENTORY, .slot = 1, .id = QueryWorld::BONES}, MenuOp::DROP));
    CHECK_FALSE(actions.ItemOp({.com = TestCache::INVENTORY, .slot = 40, .id = QueryWorld::BONES}, MenuOp::DROP));
    CHECK_FALSE(actions.UseItemOnNpc(bones, 99));

    // The targets exist, so these get as far as sending, which needs a session.
    CHECK_THROWS_AS(actions.InteractGroundItem(QueryWorld::BONES, Fixtures::HOME + 2, Fixtures::HOME + 2, MenuOp::TAKE), std::runtime_error);
    CHECK_THROWS_AS(actions.ItemOp(bones, MenuOp::DROP), std::runtime_error);
}

TEST_CASE("ScriptActions have nothing to continue or answer without a dialogue", "[ScriptActions]")
{
    auto fixture = ActionsFixture{};
    auto& actions = fixture.actions;

    CHECK_FALSE(actions.FindContinue().has_value());
    CHECK_FALSE(actions.ContinueDialogue());
    CHECK_FALSE(actions.IsCountDialogOpen());
    CHECK_FALSE(actions.AnswerCountDialog(5));
    CHECK_FALSE(actions.IsAppearanceScreenOpen());
}
