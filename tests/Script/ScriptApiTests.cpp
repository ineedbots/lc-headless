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
#include "Game/State/GameState_s.hpp"
#include "Game/State/Stat_s.hpp"
#include "Game/Tile_s.hpp"
#include "Script/ScriptApi.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    // A client that never logs in: queries read the world's state and map, and actions only get as far as
    // checking their targets, since sending throws without a session.
    class ApiFixture
    {
    public:
        ApiFixture()
            : client{std::make_shared<const Config_s>(), world.cache, FakeGameServer::MakeAccount(), capture.GetLogger()}
            , actions{client}
            , api{world.state, world.map, actions}
        {
        }

        LogCapture capture;
        QueryWorld world;
        GameClient client;
        GameActions actions;
        ScriptApi api;
    };
}

TEST_CASE("ScriptApi reads stats, modals and run mode", "[ScriptApi]")
{
    auto fixture = ApiFixture{};
    auto& state = fixture.world.state;
    const auto& api = fixture.api;

    state.stats[3] = Stat_s{.xp = 1154, .level = 7, .baseLevel = 10};
    CHECK(api.GetStat(3).level == 7);
    CHECK_THROWS_AS(api.GetStat(-1), std::invalid_argument);
    CHECK_THROWS_AS(api.GetStat(static_cast<s32>(GameState_s::STAT_COUNT)), std::invalid_argument);

    state.interfaces.mainModal = 5292;
    CHECK(api.IsInterfaceOpen(5292));
    CHECK_FALSE(api.IsInterfaceOpen(-1));

    CHECK_FALSE(api.IsRunning());
    state.varps[TestCache::RUN_VARP] = 1;
    CHECK(api.IsRunning());
}

TEST_CASE("ScriptApi actions report targets that are gone", "[ScriptApi]")
{
    auto fixture = ApiFixture{};
    auto& api = fixture.api;
    const auto bones = InventoryItem_s{.com = TestCache::INVENTORY, .slot = 2, .id = QueryWorld::BONES, .count = 1};

    CHECK_FALSE(api.InteractNpc(99, MenuOp::ATTACK));
    CHECK_FALSE(api.InteractPlayer(99, 1));
    CHECK_FALSE(api.InteractGroundItem(QueryWorld::BONES, Fixtures::HOME, Fixtures::HOME, MenuOp::TAKE));
    CHECK_FALSE(api.ItemOp({.com = TestCache::INVENTORY, .slot = 1, .id = QueryWorld::BONES}, MenuOp::DROP));
    CHECK_FALSE(api.ItemOp({.com = TestCache::INVENTORY, .slot = 40, .id = QueryWorld::BONES}, MenuOp::DROP));
    CHECK_FALSE(api.UseItemOnNpc(bones, 99));

    // The targets exist, so these get as far as sending, which needs a session.
    CHECK_THROWS_AS(api.InteractGroundItem(QueryWorld::BONES, Fixtures::HOME + 2, Fixtures::HOME + 2, MenuOp::TAKE), std::runtime_error);
    CHECK_THROWS_AS(api.ItemOp(bones, MenuOp::DROP), std::runtime_error);
}

TEST_CASE("ScriptApi keeps the strongest stop request until it's taken", "[ScriptApi]")
{
    auto fixture = ApiFixture{};
    auto& api = fixture.api;

    CHECK(api.TakeStopRequest() == StopRequest_e::None);
    api.RequestStop(StopRequest_e::Account);
    api.RequestStop(StopRequest_e::Script);
    CHECK(api.TakeStopRequest() == StopRequest_e::Account);
    CHECK(api.TakeStopRequest() == StopRequest_e::None);
}

TEST_CASE("ScriptApi finds routes on the player's level", "[ScriptApi]")
{
    auto fixture = ApiFixture{};
    const auto& api = fixture.api;

    CHECK(api.IsReachable(Fixtures::HOME, Fixtures::HOME + 5));
    CHECK_FALSE(api.IsReachable(Fixtures::HOME + 3, Fixtures::HOME));
    CHECK(api.FindPath(Fixtures::HOME, Fixtures::HOME + 5) == std::vector<Tile_s>{QueryWorld::Offset(0, 5)});
    CHECK_FALSE(api.FindPath(Fixtures::HOME + 3, Fixtures::HOME).has_value());
}
