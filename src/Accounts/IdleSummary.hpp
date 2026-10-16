#pragma once

#include "../Console/Logger.hpp"
#include "../Game/State/GameState_s.hpp"

// What an account without a script logs now and then: where the player is, and what's around them.
class IdleSummary
{
public:
    IdleSummary() = delete;

    static void Log(Logger& logger, const GameState_s& state);
};
