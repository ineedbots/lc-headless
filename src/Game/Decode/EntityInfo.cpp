#include "pch.hpp"
#include "EntityInfo.hpp"

#include "../../Io/Packet.hpp"
#include "../State/Entity_s.hpp"

namespace
{
    constexpr auto DIRECTION_DX = std::to_array<s32>({-1, 0, 1, -1, 1, -1, 0, 1});
    constexpr auto DIRECTION_DZ = std::to_array<s32>({1, 1, 1, 0, 0, -1, -1, -1});
    constexpr auto DELTA_SIGN_LIMIT = 15;
    constexpr auto DELTA_RANGE = 32;
    constexpr auto PLAYER_TARGET_OFFSET = u16{32768};
    constexpr auto SPOT_HEIGHT_SHIFT = 16;
    constexpr auto SPOT_DELAY_MASK = 0xFFFF;
}

void EntityInfo::Step(Entity_s& entity, s32 direction)
{
    assert(direction >= 0 && direction < static_cast<s32>(DIRECTION_DX.size()) && "Direction is a 3-bit field");
    entity.tile.x += DIRECTION_DX[static_cast<std::size_t>(direction)];
    entity.tile.z += DIRECTION_DZ[static_cast<std::size_t>(direction)];
}

s32 EntityInfo::ReadDelta(Packet& packet)
{
    const auto delta = packet.GBit(DELTA_BITS);
    return delta > DELTA_SIGN_LIMIT ? delta - DELTA_RANGE : delta;
}

std::optional<EntityRef_s> EntityInfo::ToFaceEntity(u16 target)
{
    if (target == NO_TARGET)
    {
        return std::nullopt;
    }

    if (target >= PLAYER_TARGET_OFFSET)
    {
        return EntityRef_s{.type = EntityType_e::Player, .index = static_cast<u16>(target - PLAYER_TARGET_OFFSET)};
    }

    return EntityRef_s{.type = EntityType_e::Npc, .index = target};
}

Animation_s EntityInfo::ReadAnimation(Packet& packet, u64 tick)
{
    const auto id = packet.G2();
    const auto delay = packet.G1();
    return {.id = id == NO_ID ? -1 : id, .delay = delay, .tick = tick};
}

SpotAnim_s EntityInfo::ReadSpotAnim(Packet& packet, u64 tick)
{
    const auto id = packet.G2();
    const auto info = packet.G4();
    return {
        .id = id == NO_ID ? -1 : id,
        .height = info >> SPOT_HEIGHT_SHIFT,
        .delay = info & SPOT_DELAY_MASK,
        .tick = tick,
    };
}

FineCoord_s EntityInfo::ReadFaceCoord(Packet& packet, u64 tick)
{
    const auto x = packet.G2();
    const auto z = packet.G2();
    return {.x = x, .z = z, .tick = tick};
}

void EntityInfo::ReadHit(Packet& packet, Entity_s& entity, u64 tick)
{
    auto hit = Hit_s{.tick = tick};
    hit.damage = packet.G1();
    hit.type = packet.G1();
    hit.health = packet.G1();
    hit.maxHealth = packet.G1();

    if (!entity.hits.empty() && entity.hits.back().tick != tick)
    {
        entity.hits.clear();
    }

    entity.hits.push_back(hit);
}

void EntityInfo::ReadMovement(Packet& packet, s32 moveType, Entity_s& entity, u64 tick)
{
    if (moveType == MOVE_NONE)
    {
        return;
    }

    Step(entity, packet.GBit(DIRECTION_BITS));
    entity.lastMovement = Movement_e::Walk;
    entity.movedTick = tick;
    if (moveType != MOVE_RUN)
    {
        return;
    }

    Step(entity, packet.GBit(DIRECTION_BITS));
    entity.lastMovement = Movement_e::Run;
}
