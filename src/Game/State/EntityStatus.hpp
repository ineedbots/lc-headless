#pragma once

#include "Entity_s.hpp"

// What a player's or an NPC's tracked state says it's doing, on a given tick.
class EntityStatus
{
public:
    // In combat for this many ticks after a hit.
    static constexpr u64 COMBAT_TICKS = 8;

    EntityStatus() = delete;

    [[nodiscard]] static bool IsMoving(const Entity_s& entity, u64 tick);
    [[nodiscard]] static bool InCombat(const Entity_s& entity, u64 tick);
    // A hit that did damage landed within the last ticks.
    [[nodiscard]] static bool TookDamage(const Entity_s& entity, u64 tick, u64 ticks);
};
