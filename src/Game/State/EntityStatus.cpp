#include "pch.hpp"
#include "EntityStatus.hpp"

#include "../../Cache/SeqDecoder.hpp"
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

s32 EntityStatus::GetAnimation(const Entity_s& entity, u64 tick, std::optional<u32> length)
{
    const auto& animation = entity.animation;
    if (animation.id == -1 || !length)
    {
        return animation.id;
    }

    // It starts after its delay, in client cycles too, and plays into the tick its last cycle falls in.
    const auto cycles = u64{animation.delay} + *length;
    const auto ends = animation.tick + (cycles + SeqDecoder::CYCLES_PER_TICK - 1) / SeqDecoder::CYCLES_PER_TICK;
    return tick < ends ? animation.id : -1;
}
