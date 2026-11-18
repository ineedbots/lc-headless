#pragma once

#include "Type/IdleSummary_s.hpp"
#include "Console/Logger.hpp"
#include "Game/State/Type/GameState_s.hpp"

// What an account without a script logs now and then: where the player is, and what's around them.
class IdleSummary
{
public:
    IdleSummary() = delete;

    static IdleSummary_s Capture(const GameState_s& state);
    static void Log(Logger& logger, const IdleSummary_s& summary);
};
