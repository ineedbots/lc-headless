#pragma once

#include "../../Cache/GameCache_s.hpp"
#include "GameState_s.hpp"

// The questions more than one account writer asks of the state, so they agree on them.
class GameStateQueries
{
public:
    GameStateQueries() = delete;

    // The bank is open: the player is placed, and the cache names a bank whose root is the main modal.
    [[nodiscard]] static bool IsBankOpen(const GameCache_s& cache, const GameState_s& state);
};
