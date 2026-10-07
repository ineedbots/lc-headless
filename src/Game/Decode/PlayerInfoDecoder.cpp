#include "pch.hpp"
#include "PlayerInfoDecoder.hpp"

#include "../../Io/Packet.hpp"
#include "../Protocol/Base37.hpp"
#include "../Protocol/WordPack.hpp"
#include "../ProtocolError.hpp"
#include "../State/Entity_s.hpp"
#include "../State/GameEvent_s.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Player_s.hpp"
#include "../State/Social_s.hpp"
#include "EntityInfo.hpp"
#include "StateLog.hpp"

namespace
{
    constexpr auto MASK_APPEARANCE = 0x001u;
    constexpr auto MASK_ANIM = 0x002u;
    constexpr auto MASK_FACE_ENTITY = 0x004u;
    constexpr auto MASK_SAY = 0x008u;
    constexpr auto MASK_DAMAGE = 0x010u;
    constexpr auto MASK_FACE_COORD = 0x020u;
    constexpr auto MASK_CHAT = 0x040u;
    constexpr auto MASK_BIG = 0x080u;
    constexpr auto MASK_SPOT_ANIM = 0x100u;
    constexpr auto MASK_EXACT_MOVE = 0x200u;
    constexpr auto MASK_DAMAGE2 = 0x400u;
    constexpr auto BITS_PER_BYTE = std::size_t{8};

    constexpr auto TRANSFORM_MARKER = 0xFFFF;
    constexpr auto BODY_KIT_BASE = 0x100;
    constexpr auto OBJECT_BASE = 0x200;
    constexpr auto NO_ANIM = u16{0xFFFF};

    s32 ReadAnimId(Packet& packet)
    {
        const auto id = packet.G2();
        return id == NO_ANIM ? -1 : id;
    }

    WearSlot_s ToWearSlot(s32 value)
    {
        if (value >= OBJECT_BASE)
        {
            return {.kind = WearKind_e::Object, .id = static_cast<u16>(value - OBJECT_BASE)};
        }

        return {.kind = WearKind_e::BodyKit, .id = static_cast<u16>(value - BODY_KIT_BASE)};
    }

    std::string GetName(const Player_s& player)
    {
        return player.appearance ? player.appearance->name : std::string{};
    }

    u64 GetName37(const Player_s& player)
    {
        return player.appearance ? player.appearance->name37 : 0;
    }

    Tile_s ToAbsolute(const GameState_s& state, s32 localX, s32 localZ, s32 level)
    {
        return {.x = state.buildArea.baseX + localX, .z = state.buildArea.baseZ + localZ, .level = level};
    }

    GameEventData ToHitEvent(const Player_s& player, bool isLocal)
    {
        if (isLocal)
        {
            return LocalHit_s{.hit = player.hits.back()};
        }

        return PlayerHit_s{.index = player.index, .hit = player.hits.back()};
    }
}

void PlayerInfoDecoder::Decode(std::span<const u8> payload, GameState_s& state)
{
    ++state.tick;

    auto packet = Packet{payload};
    auto extended = std::vector<ExtendedTarget_s>{};
    auto removed = std::vector<Player_s>{};
    auto hits = std::vector<GameEventData>{};

    packet.GBitStart();
    ReadLocal(packet, state, extended);

    auto trackedExtended = std::vector<std::size_t>{};
    auto players = EntityInfo::ReadTracked(packet, state.players, trackedExtended, removed, state.tick);
    for (const auto position : trackedExtended)
    {
        extended.push_back({.isLocal = false, .position = position});
    }

    const auto firstAdded = players.size();
    ReadNew(packet, state, players, extended);
    packet.GBitEnd();
    state.players = std::move(players);

    for (const auto& target : extended)
    {
        auto& player = target.isLocal ? state.localPlayer : state.players[target.position];
        ReadExtended(packet, state, player, target.isLocal, hits);
    }

    if (packet.GetAvailable() != 0)
    {
        throw ProtocolError{std::format("PLAYER_INFO has {} bytes left after the last extended block", packet.GetAvailable())};
    }

    for (auto& player : removed)
    {
        StateLog::AddEvent(state, PlayerRemoved_s{.player = std::move(player)});
    }

    for (auto i = firstAdded; i < state.players.size(); ++i)
    {
        StateLog::AddEvent(state, PlayerAdded_s{.player = state.players[i]});
    }

    for (auto& hit : hits)
    {
        StateLog::AddEvent(state, std::move(hit));
    }
}

void PlayerInfoDecoder::Reset()
{
    m_appearances.clear();
}

Appearance_s PlayerInfoDecoder::ReadAppearance(std::span<const u8> bytes)
{
    auto packet = Packet{bytes};
    auto appearance = Appearance_s{};
    appearance.gender = packet.G1();
    appearance.headIcons = packet.G1();

    for (std::size_t slot = 0; slot < appearance.wear.size(); ++slot)
    {
        const auto high = packet.G1();
        if (high == 0)
        {
            continue;
        }

        // A transformed player sends the NPC type instead of the rest of the wear slots.
        const auto value = (high << 8) | packet.G1();
        if (slot == 0 && value == TRANSFORM_MARKER)
        {
            appearance.npcTransform = packet.G2();
            break;
        }

        appearance.wear[slot] = ToWearSlot(value);
    }

    for (auto& colour : appearance.colours)
    {
        colour = packet.G1();
    }

    appearance.readyAnim = ReadAnimId(packet);
    appearance.turnAnim = ReadAnimId(packet);
    appearance.walkAnim = ReadAnimId(packet);
    appearance.walkBackAnim = ReadAnimId(packet);
    appearance.walkLeftAnim = ReadAnimId(packet);
    appearance.walkRightAnim = ReadAnimId(packet);
    appearance.runAnim = ReadAnimId(packet);
    appearance.name37 = std::bit_cast<u64>(packet.G8());
    appearance.name = Base37::DecodeDisplayName(appearance.name37);
    appearance.combatLevel = packet.G1();
    appearance.totalLevel = packet.G2();
    return appearance;
}

void PlayerInfoDecoder::ReadLocal(Packet& packet, GameState_s& state, std::vector<ExtendedTarget_s>& extended)
{
    if (packet.GBit(EntityInfo::UPDATE_BITS) == 0)
    {
        return;
    }

    auto& local = state.localPlayer;
    const auto moveType = packet.GBit(EntityInfo::MOVE_TYPE_BITS);
    if (moveType != MOVE_PLACE)
    {
        EntityInfo::ReadMovement(packet, moveType, local, state.tick);
        if (moveType == EntityInfo::MOVE_NONE || packet.GBit(EntityInfo::UPDATE_BITS) == 1)
        {
            extended.push_back({.isLocal = true});
        }

        return;
    }

    if (!state.buildArea.loaded)
    {
        throw ProtocolError{"PLAYER_INFO placed the local player before any REBUILD_NORMAL"};
    }

    const auto level = packet.GBit(LEVEL_BITS);
    const auto localX = packet.GBit(LOCAL_COORD_BITS);
    const auto localZ = packet.GBit(LOCAL_COORD_BITS);
    const auto jump = packet.GBit(EntityInfo::UPDATE_BITS) == 1;
    local.tile = ToAbsolute(state, localX, localZ, level);
    local.lastMovement = jump ? Movement_e::Teleport : Movement_e::Walk;
    local.movedTick = state.tick;
    state.placed = true;

    if (packet.GBit(EntityInfo::UPDATE_BITS) == 1)
    {
        extended.push_back({.isLocal = true});
    }
}

void PlayerInfoDecoder::ReadNew(Packet& packet, GameState_s& state, std::vector<Player_s>& players, std::vector<ExtendedTarget_s>& extended)
{
    const auto bitLength = packet.GetLength() * BITS_PER_BYTE;
    while (packet.GetBitPos() + INDEX_BITS <= bitLength)
    {
        const auto index = packet.GBit(INDEX_BITS);
        if (index == END_OF_LIST)
        {
            break;
        }

        const auto dx = EntityInfo::ReadDelta(packet);
        const auto dz = EntityInfo::ReadDelta(packet);
        const auto jump = packet.GBit(EntityInfo::UPDATE_BITS) == 1;
        const auto hasExtended = packet.GBit(EntityInfo::UPDATE_BITS) == 1;

        if (std::ranges::find(players, static_cast<u16>(index), &Player_s::index) != players.end())
        {
            throw ProtocolError{std::format("PLAYER_INFO adds player {}, which is already tracked", index)};
        }

        auto player = Player_s{};
        player.index = static_cast<u16>(index);
        player.tile = state.localPlayer.tile;
        player.tile.x += dx;
        player.tile.z += dz;
        player.lastMovement = jump ? Movement_e::Teleport : Movement_e::Walk;
        player.movedTick = state.tick;
        player.addedTick = state.tick;

        const auto cached = m_appearances.find(player.index);
        if (cached != m_appearances.end())
        {
            player.appearance = cached->second;
        }

        players.push_back(std::move(player));
        if (hasExtended)
        {
            extended.push_back({.isLocal = false, .position = players.size() - 1});
        }
    }
}

void PlayerInfoDecoder::ReadExtended(Packet& packet, GameState_s& state, Player_s& player, bool isLocal, std::vector<GameEventData>& hits)
{
    const auto tick = state.tick;
    auto mask = u32{packet.G1()};
    if ((mask & MASK_BIG) != 0)
    {
        mask |= u32{packet.G1()} << 8;
    }

    if ((mask & MASK_APPEARANCE) != 0)
    {
        auto bytes = std::vector<u8>(packet.G1());
        packet.GData(bytes);
        auto appearance = ReadAppearance(bytes);
        if (!isLocal)
        {
            m_appearances.insert_or_assign(player.index, appearance);
        }

        player.appearance = std::move(appearance);
    }

    if ((mask & MASK_ANIM) != 0)
    {
        player.animation = EntityInfo::ReadAnimation(packet, tick);
    }

    if ((mask & MASK_FACE_ENTITY) != 0)
    {
        player.faceEntity = EntityInfo::ToFaceEntity(packet.G2());
    }

    if ((mask & MASK_SAY) != 0)
    {
        auto text = packet.GJStr();
        player.say = OverheadText_s{.text = text, .tick = tick};
        if (player.appearance)
        {
            StateLog::AddMessage(state, MessageType_e::Say, GetName(player), GetName37(player), 0, std::move(text));
        }
    }

    if ((mask & MASK_DAMAGE) != 0)
    {
        EntityInfo::ReadHit(packet, player, tick);
        hits.push_back(ToHitEvent(player, isLocal));
    }

    if ((mask & MASK_FACE_COORD) != 0)
    {
        player.faceCoord = EntityInfo::ReadFaceCoord(packet, tick);
    }

    if ((mask & MASK_CHAT) != 0)
    {
        ReadChat(packet, state, player);
    }

    if ((mask & MASK_SPOT_ANIM) != 0)
    {
        player.spotAnim = EntityInfo::ReadSpotAnim(packet, tick);
    }

    if ((mask & MASK_EXACT_MOVE) != 0)
    {
        const auto startX = packet.G1();
        const auto startZ = packet.G1();
        const auto endX = packet.G1();
        const auto endZ = packet.G1();
        auto exactMove = ExactMove_s{.tick = tick};
        exactMove.start = ToAbsolute(state, startX, startZ, player.tile.level);
        exactMove.end = ToAbsolute(state, endX, endZ, player.tile.level);
        exactMove.startCycle = packet.G2();
        exactMove.endCycle = packet.G2();
        exactMove.direction = packet.G1();
        player.exactMove = exactMove;
    }

    if ((mask & MASK_DAMAGE2) != 0)
    {
        EntityInfo::ReadHit(packet, player, tick);
        hits.push_back(ToHitEvent(player, isLocal));
    }
}

void PlayerInfoDecoder::ReadChat(Packet& packet, GameState_s& state, Player_s& player)
{
    auto chat = PublicChat_s{.tick = state.tick};
    chat.colour = packet.G1();
    chat.effect = packet.G1();
    chat.rights = packet.G1();

    auto packed = std::vector<u8>(packet.G1());
    packet.GData(packed);
    chat.text = WordPack::Unpack(packed);

    StateLog::AddMessage(state, MessageType_e::Public, GetName(player), GetName37(player), chat.rights, chat.text);
    player.chat = std::move(chat);
}
