#pragma once

#include "../../Io/Packet.hpp"
#include "../ProtocolError.hpp"
#include "../State/Entity_s.hpp"

// Pieces PLAYER_INFO and NPC_INFO share: the tracked-list walk, steps, and common extended blocks.
class EntityInfo
{
public:
    static constexpr u32 UPDATE_BITS = 1;
    static constexpr u32 MOVE_TYPE_BITS = 2;
    static constexpr u32 DIRECTION_BITS = 3;
    static constexpr u32 DELTA_BITS = 5;
    static constexpr u32 COUNT_BITS = 8;
    static constexpr s32 MOVE_NONE = 0;
    static constexpr s32 MOVE_WALK = 1;
    static constexpr s32 MOVE_RUN = 2;
    static constexpr s32 MOVE_REMOVE = 3;
    static constexpr u16 NO_TARGET = 0xFFFF;
    static constexpr u16 NO_ID = 0xFFFF;

    EntityInfo() = delete;

    static void Step(Entity_s& entity, s32 direction);
    [[nodiscard]] static s32 ReadDelta(Packet& packet);
    [[nodiscard]] static std::optional<EntityRef_s> ToFaceEntity(u16 target);
    [[nodiscard]] static Animation_s ReadAnimation(Packet& packet, u64 tick);
    [[nodiscard]] static SpotAnim_s ReadSpotAnim(Packet& packet, u64 tick);
    [[nodiscard]] static FineCoord_s ReadFaceCoord(Packet& packet, u64 tick);
    static void ReadHit(Packet& packet, Entity_s& entity, u64 tick);
    static void ReadMovement(Packet& packet, s32 moveType, Entity_s& entity, u64 tick);

    // Walks the first `count` entries of the tracked list in server order, applies their movement,
    // and returns the survivors in the same order. Positions in the result whose entity carries an
    // extended block are appended to `extended`. Entities the server removes, and any tracked past
    // `count`, are moved to `removed`.
    template <typename TEntity>
    [[nodiscard]] static std::vector<TEntity> ReadTracked(Packet& packet, std::vector<TEntity>& tracked, std::vector<std::size_t>& extended, std::vector<TEntity>& removed, u64 tick)
    {
        const auto count = static_cast<std::size_t>(packet.GBit(COUNT_BITS));
        if (count > tracked.size())
        {
            throw ProtocolError{std::format("Info update lists {} tracked entities, but only {} are tracked", count, tracked.size())};
        }

        auto survivors = std::vector<TEntity>{};
        survivors.reserve(count);
        for (std::size_t i = 0; i < count; ++i)
        {
            auto& entity = tracked[i];
            if (packet.GBit(UPDATE_BITS) == 0)
            {
                survivors.push_back(std::move(entity));
                continue;
            }

            const auto moveType = packet.GBit(MOVE_TYPE_BITS);
            if (moveType == MOVE_REMOVE)
            {
                removed.push_back(std::move(entity));
                continue;
            }

            ReadMovement(packet, moveType, entity, tick);
            const auto hasExtended = moveType == MOVE_NONE || packet.GBit(UPDATE_BITS) == 1;
            survivors.push_back(std::move(entity));
            if (hasExtended)
            {
                extended.push_back(survivors.size() - 1);
            }
        }

        for (auto i = count; i < tracked.size(); ++i)
        {
            removed.push_back(std::move(tracked[i]));
        }

        return survivors;
    }
};
