#pragma once

#include "FakeGameServer.hpp"
#include "Game/State/BuildArea_s.hpp"

// What FakeGameServer sends on login in the client tests, in the server's revision: a rebuild, the PID, the
// local player placed at home, one NPC two tiles east, coins one tile north-east, logs in the inventory and a
// welcome message, then a second PLAYER_INFO for the next tick. A 225 rebuild lists one map square, with CRCs
// no cache has.
// A reconnect only gets the rebuild, the placement and the next tick, as the session carries on.
class TestWorld
{
public:
    static constexpr u16 NPC_INDEX = 100;
    static constexpr u16 NPC_TYPE = 50;
    static constexpr u16 INVENTORY = 3214;
    static constexpr u16 COINS = 995;
    static constexpr u16 COIN_COUNT = 10;
    static constexpr u16 LOGS = 1511;
    static constexpr u16 LOG_COUNT = 3;
    static constexpr auto WELCOME = "Welcome to RuneScape.";
    static constexpr auto SQUARE_225 = BuildSquare_s{.x = 50, .z = 50, .landCrc = 1, .locCrc = 2};

    TestWorld() = delete;

    static void Send(FakeGameServer& server, bool reconnect);
};
