#include "pch.hpp"
#include "EntityStatus.hpp"

#include "Entity_s.hpp"

bool EntityStatus::IsMoving(const Entity_s& entity, u64 tick)
{
    return entity.lastMovement != Movement_e::None && entity.movedTick == tick;
}

bool EntityStatus::InCombat(const Entity_s& entity, u64 tick)
{
    return !entity.hits.empty() && tick - entity.hits.back().tick <= COMBAT_TICKS;
}

bool EntityStatus::TookDamage(const Entity_s& entity, u64 tick, u64 ticks)
{
    return std::ranges::any_of(entity.hits, [tick, ticks](const Hit_s& hit)
    {
        return hit.damage > 0 && hit.tick + ticks >= tick;
    });
}
