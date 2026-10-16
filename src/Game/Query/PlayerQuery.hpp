#pragma once

#include "../../Cache/GameCache_s.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Stat_s.hpp"

// What the tracked state says about the local player, read in place, so it's cheap to make and can't go stale.
class PlayerQuery
{
public:
    PlayerQuery(const GameState_s& state, const GameCache_s& cache);

    // Walking somewhere it asked to, or moved this tick.
    [[nodiscard]] bool IsMoving() const;
    [[nodiscard]] bool InCombat() const;
    [[nodiscard]] bool IsRunning() const;
    // Any of the slots the server sends; a slot outside them throws std::invalid_argument.
    [[nodiscard]] const Stat_s& GetStat(s32 stat) const;
    // As the main, side or chat modal.
    [[nodiscard]] bool IsInterfaceOpen(s32 id) const;
    // The text the server set on the component, or nullopt when it set none.
    [[nodiscard]] std::optional<std::string> GetComponentText(u16 com) const;

private:
    const GameState_s& m_state;
    const GameCache_s& m_cache;
};
