#include "pch.hpp"
#include "ZoneDecoder.hpp"

#include "../../Io/Packet.hpp"
#include "../Map/LocShape.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../ProtocolError.hpp"
#include "../State/Entity_s.hpp"
#include "../State/GameEvent_s.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Zone_s.hpp"
#include "../Tile_s.hpp"
#include "StateLog.hpp"

namespace
{
    constexpr auto POS_X_SHIFT = 4;
    constexpr auto POS_MASK = 0x7;
    constexpr auto SHAPE_SHIFT = 2;
    constexpr auto ANGLE_MASK = 0x3;
    constexpr auto OBJ_ID_MASK = 0x7FFF;
    constexpr auto ZONE_SHIFT = 3;

    struct ZoneTile_s
    {
        Tile_s tile;
        bool inBuildArea = false;
    };

    bool IsInBuildArea(s32 localX, s32 localZ)
    {
        return localX >= 0 && localZ >= 0 && localX < BuildArea_s::SIZE && localZ < BuildArea_s::SIZE;
    }

    std::optional<EntityRef_s> ToProjectileTarget(s16 target)
    {
        if (target > 0)
        {
            return EntityRef_s{.type = EntityType_e::Npc, .index = static_cast<u16>(target - 1)};
        }

        if (target < 0)
        {
            return EntityRef_s{.type = EntityType_e::Player, .index = static_cast<u16>(-target - 1)};
        }

        return std::nullopt;
    }

    u8 GetShape(u8 info)
    {
        return static_cast<u8>(info >> SHAPE_SHIFT);
    }

    u8 GetAngle(u8 info)
    {
        return static_cast<u8>(info & ANGLE_MASK);
    }
}

void ZoneDecoder::SetZone(Packet& packet)
{
    m_localX = packet.G1();
    m_localZ = packet.G1();
}

void ZoneDecoder::ResetZone(GameState_s& state) const
{
    const auto zone = GetZone(state);
    std::erase_if(state.groundItems, [&zone](const GroundItem_s& item)
    {
        return zone.Contains(item.tile);
    });

    const auto erased = std::erase_if(state.locChanges, [&zone](const LocChange_s& change)
    {
        return zone.Contains(change.tile);
    });

    if (erased > 0)
    {
        ++state.sceneChangeCount;
    }
}

void ZoneDecoder::DecodeSubPacket(u8 opcode, Packet& packet, GameState_s& state) const
{
    const auto pos = packet.G1();
    const auto localX = m_localX + ((pos >> POS_X_SHIFT) & POS_MASK);
    const auto localZ = m_localZ + (pos & POS_MASK);
    const auto inBuildArea = IsInBuildArea(localX, localZ);
    const auto tile = Tile_s{
        .x = state.buildArea.baseX + localX,
        .z = state.buildArea.baseZ + localZ,
        .level = state.localPlayer.tile.level,
    };

    switch (static_cast<ServerProt_e>(opcode))
    {
    case ServerProt_e::LocAddChange:
    {
        const auto info = packet.G1();
        const auto loc = packet.G2();
        if (inBuildArea)
        {
            SetLoc(state, tile, info, loc);
        }
        return;
    }
    case ServerProt_e::LocDel:
    {
        const auto info = packet.G1();
        if (inBuildArea)
        {
            SetLoc(state, tile, info, -1);
        }
        return;
    }
    case ServerProt_e::LocAnim:
    {
        const auto info = packet.G1();
        const auto seq = packet.G2();
        if (inBuildArea)
        {
            const auto shape = GetShape(info);
            StateLog::Push(state.locAnims, LocAnim_s{.tile = tile, .layer = LocShape::GetLayer(shape), .shape = shape, .angle = GetAngle(info), .seq = seq, .tick = state.tick});
        }
        return;
    }
    case ServerProt_e::ObjAdd:
    {
        const auto obj = packet.G2();
        const auto count = packet.G2();
        if (inBuildArea)
        {
            AddObj(state, tile, obj, count);
        }
        return;
    }
    case ServerProt_e::ObjDel:
    {
        const auto obj = packet.G2();
        if (inBuildArea)
        {
            DeleteObj(state, tile, obj);
        }
        return;
    }
    case ServerProt_e::ObjCount:
    {
        const auto obj = packet.G2();
        const auto oldCount = packet.G2();
        const auto newCount = packet.G2();
        if (inBuildArea)
        {
            CountObj(state, tile, obj, oldCount, newCount);
        }
        return;
    }
    case ServerProt_e::ObjReveal:
    {
        const auto obj = packet.G2();
        const auto count = packet.G2();
        const auto receiver = packet.G2();
        if (inBuildArea && receiver != state.pid)
        {
            AddObj(state, tile, obj, count);
        }
        return;
    }
    case ServerProt_e::LocMerge:
    {
        auto merge = LocMerge_s{.tile = tile, .tick = state.tick};
        const auto info = packet.G1();
        merge.shape = GetShape(info);
        merge.angle = GetAngle(info);
        merge.loc = packet.G2();
        merge.startCycle = packet.G2();
        merge.endCycle = packet.G2();
        merge.player = packet.G2();
        const auto east = packet.G1B();
        const auto south = packet.G1B();
        const auto west = packet.G1B();
        const auto north = packet.G1B();
        merge.min = Tile_s{.x = tile.x + std::min(east, west), .z = tile.z + std::min(south, north), .level = tile.level};
        merge.max = Tile_s{.x = tile.x + std::max(east, west), .z = tile.z + std::max(south, north), .level = tile.level};
        StateLog::Push(state.locMerges, std::move(merge));
        return;
    }
    case ServerProt_e::MapAnim:
    {
        const auto spotAnim = packet.G2();
        const auto height = packet.G1();
        const auto delay = packet.G2();
        if (inBuildArea)
        {
            StateLog::Push(state.mapAnims, MapAnim_s{.tile = tile, .spotAnim = spotAnim, .height = height, .delay = delay, .tick = state.tick});
        }
        return;
    }
    case ServerProt_e::MapProjAnim:
    {
        auto projectile = Projectile_s{.source = tile, .destination = tile, .tick = state.tick};
        const auto dx = packet.G1B();
        const auto dz = packet.G1B();
        projectile.destination.x += dx;
        projectile.destination.z += dz;
        projectile.target = ToProjectileTarget(packet.G2B());
        projectile.spotAnim = packet.G2();
        projectile.sourceHeight = packet.G1();
        projectile.destinationHeight = packet.G1();
        projectile.startDelay = packet.G2();
        projectile.endDelay = packet.G2();
        projectile.peak = packet.G1();
        projectile.arc = packet.G1();
        if (inBuildArea && IsInBuildArea(localX + dx, localZ + dz))
        {
            StateLog::Push(state.projectiles, projectile);
            StateLog::AddEvent(state, ProjectileLaunched_s{.projectile = std::move(projectile)});
        }
        return;
    }
    default:
        throw ProtocolError{std::format("Opcode {} ({}) is not a zone sub-packet", opcode, ServerProt::GetName(opcode))};
    }
}

void ZoneDecoder::DecodeEnclosed(Packet& packet, GameState_s& state) const
{
    while (packet.GetAvailable() > 0)
    {
        const auto opcode = packet.G1();
        if (!ServerProt::IsZoneProt(opcode))
        {
            throw ProtocolError{std::format("UPDATE_ZONE_PARTIAL_ENCLOSED holds opcode {}, which is not a zone sub-packet", opcode)};
        }

        DecodeSubPacket(opcode, packet, state);
    }
}

bool ZoneDecoder::IsActive(const GameState_s& state, const Tile_s& tile)
{
    const auto& local = state.localPlayer.tile;
    if (tile.level != local.level)
    {
        return false;
    }

    const auto zoneX = tile.x >> ZONE_SHIFT;
    const auto zoneZ = tile.z >> ZONE_SHIFT;
    if (std::abs(zoneX - (local.x >> ZONE_SHIFT)) > ACTIVE_ZONE_RADIUS || std::abs(zoneZ - (local.z >> ZONE_SHIFT)) > ACTIVE_ZONE_RADIUS)
    {
        return false;
    }

    const auto baseZoneX = state.buildArea.baseX >> ZONE_SHIFT;
    const auto baseZoneZ = state.buildArea.baseZ >> ZONE_SHIFT;
    return zoneX >= baseZoneX && zoneX < baseZoneX + BUILD_AREA_ZONES && zoneZ >= baseZoneZ && zoneZ < baseZoneZ + BUILD_AREA_ZONES;
}

void ZoneDecoder::PruneInactive(GameState_s& state)
{
    if (!state.placed || !state.buildArea.loaded)
    {
        return;
    }

    std::erase_if(state.groundItems, [&state](const GroundItem_s& item)
    {
        return !IsActive(state, item.tile);
    });

    const auto erased = std::erase_if(state.locChanges, [&state](const LocChange_s& change)
    {
        return !IsActive(state, change.tile);
    });

    if (erased > 0)
    {
        ++state.sceneChangeCount;
    }
}

Zone_s ZoneDecoder::GetZone(const GameState_s& state) const
{
    return {
        .x = state.buildArea.baseX + m_localX,
        .z = state.buildArea.baseZ + m_localZ,
        .level = state.localPlayer.tile.level,
    };
}

void ZoneDecoder::SetLoc(GameState_s& state, const Tile_s& tile, u8 info, s32 id)
{
    const auto shape = GetShape(info);
    const auto layer = LocShape::GetLayer(shape);
    const auto change = LocChange_s{.tile = tile, .layer = layer, .id = id, .shape = shape, .angle = GetAngle(info), .tick = state.tick};

    const auto existing = std::ranges::find_if(state.locChanges, [&tile, layer](const LocChange_s& other)
    {
        return other.tile == tile && other.layer == layer;
    });

    if (existing == state.locChanges.end())
    {
        state.locChanges.push_back(change);
    }
    else
    {
        *existing = change;
    }

    ++state.sceneChangeCount;
    StateLog::AddEvent(state, LocChanged_s{.change = change});
}

void ZoneDecoder::AddObj(GameState_s& state, const Tile_s& tile, u16 obj, s32 count)
{
    const auto item = GroundItem_s{.tile = tile, .id = obj, .count = count, .tick = state.tick};
    state.groundItems.push_back(item);
    StateLog::AddEvent(state, GroundItemAdded_s{.item = item});
}

void ZoneDecoder::DeleteObj(GameState_s& state, const Tile_s& tile, u16 obj)
{
    const auto id = obj & OBJ_ID_MASK;
    const auto found = std::ranges::find_if(state.groundItems, [&tile, id](const GroundItem_s& item)
    {
        return item.tile == tile && item.id == id;
    });

    if (found == state.groundItems.end())
    {
        return;
    }

    StateLog::AddEvent(state, GroundItemRemoved_s{.item = *found});
    state.groundItems.erase(found);
}

void ZoneDecoder::CountObj(GameState_s& state, const Tile_s& tile, u16 obj, u16 oldCount, u16 newCount)
{
    const auto id = obj & OBJ_ID_MASK;
    const auto found = std::ranges::find_if(state.groundItems, [&tile, id, oldCount](const GroundItem_s& item)
    {
        return item.tile == tile && item.id == id && item.count == oldCount;
    });

    if (found == state.groundItems.end())
    {
        return;
    }

    found->count = newCount;
    StateLog::AddEvent(state, GroundItemCountChanged_s{.item = *found, .previousCount = oldCount});
}
