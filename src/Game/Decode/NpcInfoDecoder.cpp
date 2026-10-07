#include "pch.hpp"
#include "NpcInfoDecoder.hpp"

#include "../../Io/Packet.hpp"
#include "../ProtocolError.hpp"
#include "../State/Entity_s.hpp"
#include "../State/GameEvent_s.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Npc_s.hpp"
#include "EntityInfo.hpp"
#include "StateLog.hpp"

namespace
{
    constexpr auto MASK_DAMAGE2 = 0x01u;
    constexpr auto MASK_ANIM = 0x02u;
    constexpr auto MASK_FACE_ENTITY = 0x04u;
    constexpr auto MASK_SAY = 0x08u;
    constexpr auto MASK_DAMAGE = 0x10u;
    constexpr auto MASK_CHANGE_TYPE = 0x20u;
    constexpr auto MASK_SPOT_ANIM = 0x40u;
    constexpr auto MASK_FACE_COORD = 0x80u;
    constexpr auto BITS_PER_BYTE = std::size_t{8};
}

void NpcInfoDecoder::Decode(std::span<const u8> payload, GameState_s& state)
{
    auto packet = Packet{payload};
    auto extended = std::vector<std::size_t>{};
    auto removed = std::vector<Npc_s>{};
    auto hits = std::vector<NpcHit_s>{};

    packet.GBitStart();
    auto npcs = EntityInfo::ReadTracked(packet, state.npcs, extended, removed, state.tick);
    const auto firstAdded = npcs.size();
    ReadNew(packet, state, npcs, extended);
    packet.GBitEnd();
    state.npcs = std::move(npcs);

    for (const auto position : extended)
    {
        ReadExtended(packet, state, state.npcs[position], hits);
    }

    if (packet.GetAvailable() != 0)
    {
        throw ProtocolError{std::format("NPC_INFO has {} bytes left after the last extended block", packet.GetAvailable())};
    }

    for (auto& npc : removed)
    {
        StateLog::AddEvent(state, NpcRemoved_s{.npc = std::move(npc)});
    }

    for (auto i = firstAdded; i < state.npcs.size(); ++i)
    {
        StateLog::AddEvent(state, NpcAdded_s{.npc = state.npcs[i]});
    }

    for (const auto& hit : hits)
    {
        StateLog::AddEvent(state, hit);
    }
}

void NpcInfoDecoder::ReadNew(Packet& packet, const GameState_s& state, std::vector<Npc_s>& npcs, std::vector<std::size_t>& extended)
{
    const auto bitLength = packet.GetLength() * BITS_PER_BYTE;
    while (packet.GetBitPos() + MIN_NEW_NPC_BITS <= bitLength)
    {
        const auto index = packet.GBit(INDEX_BITS);
        if (index == END_OF_LIST)
        {
            break;
        }

        const auto type = packet.GBit(TYPE_BITS);
        const auto dx = EntityInfo::ReadDelta(packet);
        const auto dz = EntityInfo::ReadDelta(packet);
        const auto jump = packet.GBit(EntityInfo::UPDATE_BITS) == 1;
        const auto hasExtended = packet.GBit(EntityInfo::UPDATE_BITS) == 1;

        if (std::ranges::find(npcs, static_cast<u16>(index), &Npc_s::index) != npcs.end())
        {
            throw ProtocolError{std::format("NPC_INFO adds NPC {}, which is already tracked", index)};
        }

        auto npc = Npc_s{};
        npc.index = static_cast<u16>(index);
        npc.type = static_cast<u16>(type);
        npc.tile = state.localPlayer.tile;
        npc.tile.x += dx;
        npc.tile.z += dz;
        npc.lastMovement = jump ? Movement_e::Teleport : Movement_e::Walk;
        npc.movedTick = state.tick;
        npc.addedTick = state.tick;

        npcs.push_back(std::move(npc));
        if (hasExtended)
        {
            extended.push_back(npcs.size() - 1);
        }
    }
}

void NpcInfoDecoder::ReadExtended(Packet& packet, GameState_s& state, Npc_s& npc, std::vector<NpcHit_s>& hits)
{
    const auto tick = state.tick;
    const auto mask = u32{packet.G1()};

    if ((mask & MASK_DAMAGE2) != 0)
    {
        EntityInfo::ReadHit(packet, npc, tick);
        hits.push_back({.index = npc.index, .hit = npc.hits.back()});
    }

    if ((mask & MASK_ANIM) != 0)
    {
        npc.animation = EntityInfo::ReadAnimation(packet, tick);
    }

    if ((mask & MASK_FACE_ENTITY) != 0)
    {
        npc.faceEntity = EntityInfo::ToFaceEntity(packet.G2());
    }

    if ((mask & MASK_SAY) != 0)
    {
        npc.say = OverheadText_s{.text = packet.GJStr(), .tick = tick};
    }

    if ((mask & MASK_DAMAGE) != 0)
    {
        EntityInfo::ReadHit(packet, npc, tick);
        hits.push_back({.index = npc.index, .hit = npc.hits.back()});
    }

    if ((mask & MASK_CHANGE_TYPE) != 0)
    {
        npc.type = packet.G2();
    }

    if ((mask & MASK_SPOT_ANIM) != 0)
    {
        npc.spotAnim = EntityInfo::ReadSpotAnim(packet, tick);
    }

    if ((mask & MASK_FACE_COORD) != 0)
    {
        npc.faceCoord = EntityInfo::ReadFaceCoord(packet, tick);
    }
}
