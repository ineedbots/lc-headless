#include "pch.hpp"
#include "GameStateQueries.hpp"

bool GameStateQueries::IsBankOpen(const GameCache_s& cache, const GameState_s& state)
{
    if (!state.placed || cache.bankComponent == 0)
    {
        return false;
    }

    const auto* const bank = cache.FindComponent(static_cast<s32>(cache.bankComponent));
    return bank != nullptr && bank->root != 0 && state.interfaces.mainModal == static_cast<s32>(bank->root);
}
