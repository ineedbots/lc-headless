#pragma once

#include "FakeGameServer.hpp"

// What FakeGameServer sends on login in the client tests: a rebuild, the PID, the local player placed
// at home, one NPC two tiles east, coins one tile north-east, logs in the inventory and a welcome message.
// A reconnect only gets the rebuild and the placement, as the session carries on.
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

    TestWorld() = delete;

    static void Send(FakeGameServer& server, bool reconnect);
};
