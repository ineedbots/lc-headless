#include "pch.hpp"
#include "GameActions.hpp"

#include "../Cache/GameCache_s.hpp"
#include "../Cache/LocType_s.hpp"
#include "../Core/Logger.hpp"
#include "GameClient.hpp"
#include "Map/LocShape.hpp"
#include "Map/PathFinder.hpp"
#include "Map/WorldMap.hpp"
#include "Protocol/Base37.hpp"
#include "Protocol/ClientPacket_s.hpp"
#include "Protocol/ClientPackets.hpp"
#include "State/GameState_s.hpp"
#include "State/Zone_s.hpp"
#include "Tile_s.hpp"

namespace
{
    constexpr auto ANGLE_NORTH = u8{1};
    constexpr auto ANGLE_SOUTH = u8{3};
    constexpr auto SIDE_COUNT = 4;
    constexpr auto SIDE_MASK = 0xF;
    constexpr auto LAYERS = std::to_array<LocLayer_e>({LocLayer_e::Wall, LocLayer_e::WallDecor, LocLayer_e::Ground, LocLayer_e::GroundDecor});

    RouteTarget_s MakeAreaTarget(const Tile_s& tile, u8 width = 1, u8 length = 1, u8 forceApproach = 0)
    {
        return {.kind = RouteKind_e::Area, .tile = tile, .width = width, .length = length, .forceApproach = forceApproach};
    }

    // interactWithLoc turns the sides a loc forbids with the loc.
    u8 TurnForceApproach(u8 forceApproach, u8 angle)
    {
        if (angle == 0)
        {
            return forceApproach;
        }

        return static_cast<u8>(((forceApproach << angle) & SIDE_MASK) + (forceApproach >> (SIDE_COUNT - angle)));
    }

    // Centrepieces and ground decor are reached as an area of the type's size, and everything else as a wall.
    RouteTarget_s MakeLocTarget(const SceneLoc_s& loc, const LocType_s* type)
    {
        const auto isArea = loc.shape == LocShape::CENTREPIECE_STRAIGHT || loc.shape == LocShape::CENTREPIECE_DIAGONAL || loc.shape == LocShape::GROUND_DECOR;
        if (!isArea)
        {
            return {.kind = RouteKind_e::Wall, .tile = loc.tile, .shape = loc.shape, .angle = loc.angle};
        }

        if (type == nullptr)
        {
            return MakeAreaTarget(loc.tile);
        }

        const auto turned = loc.angle == ANGLE_NORTH || loc.angle == ANGLE_SOUTH;
        const auto width = turned ? type->length : type->width;
        const auto length = turned ? type->width : type->length;
        return MakeAreaTarget(loc.tile, width, length, TurnForceApproach(type->forceApproach, loc.angle));
    }
}

GameActions::GameActions(GameClient& client)
    : m_client{client}
{
}

bool GameActions::WalkTo(const Tile_s& destination, bool run)
{
    if (const auto route = FindWalkRoute(GetMap(), GetStart(), destination))
    {
        m_client.SendMove(MoveKind_e::GameClick, *route, run);
        return true;
    }

    if (GetMap().Contains(destination))
    {
        LogNoRoute(destination, "not walking");
        return false;
    }

    LogNoRoute(destination, "walking in a straight line");
    WalkPath(std::span{&destination, 1}, run);
    return true;
}

void GameActions::WalkPath(std::span<const Tile_s> waypoints, bool run)
{
    m_client.SendMove(MoveKind_e::GameClick, waypoints, run);
}

void GameActions::InteractNpc(u16 npcIndex, u8 op)
{
    const auto tile = GetNpcTile(npcIndex);
    Approach(FindEntityRoute(GetMap(), GetStart(), tile), tile, ClientPackets::OpNpc(op, npcIndex));
}

void GameActions::InteractPlayer(u16 playerIndex, u8 op)
{
    const auto tile = GetPlayerTile(playerIndex);
    Approach(FindEntityRoute(GetMap(), GetStart(), tile), tile, ClientPackets::OpPlayer(op, playerIndex));
}

void GameActions::InteractLoc(const Tile_s& tile, u16 loc, u8 op)
{
    ApproachLoc(tile, loc, ClientPackets::OpLoc(op, tile, loc));
}

void GameActions::InteractLocVia(std::span<const Tile_s> waypoints, const Tile_s& tile, u16 loc, u8 op)
{
    ApproachVia(waypoints, ClientPackets::OpLoc(op, tile, loc));
}

void GameActions::InteractGroundItem(const Tile_s& tile, u16 obj, u8 op)
{
    Approach(FindGroundItemRoute(GetMap(), GetStart(), tile), tile, ClientPackets::OpObj(op, tile, obj));
}

void GameActions::InteractGroundItemVia(std::span<const Tile_s> waypoints, const Tile_s& tile, u16 obj, u8 op)
{
    ApproachVia(waypoints, ClientPackets::OpObj(op, tile, obj));
}

void GameActions::UseItemOnNpc(const ItemRef_s& item, u16 npcIndex)
{
    const auto tile = GetNpcTile(npcIndex);
    Approach(FindEntityRoute(GetMap(), GetStart(), tile), tile, ClientPackets::OpNpcU(npcIndex, item));
}

void GameActions::UseItemOnPlayer(const ItemRef_s& item, u16 playerIndex)
{
    const auto tile = GetPlayerTile(playerIndex);
    Approach(FindEntityRoute(GetMap(), GetStart(), tile), tile, ClientPackets::OpPlayerU(playerIndex, item));
}

void GameActions::UseItemOnLoc(const ItemRef_s& item, const Tile_s& tile, u16 loc)
{
    ApproachLoc(tile, loc, ClientPackets::OpLocU(tile, loc, item));
}

void GameActions::UseItemOnGroundItem(const ItemRef_s& item, const Tile_s& tile, u16 obj)
{
    Approach(FindGroundItemRoute(GetMap(), GetStart(), tile), tile, ClientPackets::OpObjU(tile, obj, item));
}

void GameActions::UseItemOnItem(const ItemRef_s& item, const ItemRef_s& target)
{
    m_client.Send(ClientPackets::OpHeldU(target, item));
}

void GameActions::CastOnNpc(u16 spellCom, u16 npcIndex)
{
    const auto tile = GetNpcTile(npcIndex);
    Approach(FindEntityRoute(GetMap(), GetStart(), tile), tile, ClientPackets::OpNpcT(npcIndex, spellCom));
}

void GameActions::CastOnPlayer(u16 spellCom, u16 playerIndex)
{
    const auto tile = GetPlayerTile(playerIndex);
    Approach(FindEntityRoute(GetMap(), GetStart(), tile), tile, ClientPackets::OpPlayerT(playerIndex, spellCom));
}

void GameActions::CastOnLoc(u16 spellCom, const Tile_s& tile, u16 loc)
{
    ApproachLoc(tile, loc, ClientPackets::OpLocT(tile, loc, spellCom));
}

void GameActions::CastOnGroundItem(u16 spellCom, const Tile_s& tile, u16 obj)
{
    Approach(FindGroundItemRoute(GetMap(), GetStart(), tile), tile, ClientPackets::OpObjT(tile, obj, spellCom));
}

void GameActions::CastOnItem(u16 spellCom, const ItemRef_s& item)
{
    m_client.Send(ClientPackets::OpHeldT(item, spellCom));
}

void GameActions::OperateItem(const ItemRef_s& item, u8 op)
{
    m_client.Send(ClientPackets::OpHeld(op, item));
}

void GameActions::InventoryButton(const ItemRef_s& item, u8 op)
{
    m_client.Send(ClientPackets::InvButton(op, item));
}

void GameActions::MoveItem(u16 com, u16 fromSlot, u16 toSlot, DragMode_e mode)
{
    m_client.Send(ClientPackets::InvButtonD(com, fromSlot, toSlot, mode));
}

void GameActions::ClickButton(u16 com)
{
    m_client.Send(ClientPackets::IfButton(com));
}

void GameActions::ClickComponent(u16 com, ButtonType_e buttonType)
{
    switch (buttonType)
    {
    case ButtonType_e::Ok:
    case ButtonType_e::Toggle:
    case ButtonType_e::Select:
        m_client.Send(ClientPackets::IfButton(com));
        return;
    case ButtonType_e::Continue:
        m_client.Send(ClientPackets::ResumePauseButton(com));
        return;
    case ButtonType_e::Close:
        m_client.Send(ClientPackets::CloseModal());
        return;
    case ButtonType_e::None:
    case ButtonType_e::Target:
        return;
    }
}

void GameActions::ContinueDialogue()
{
    // The engine resumes whichever script waits on a pause button and ignores the component.
    const auto chatModal = m_client.GetState().interfaces.chatModal;
    m_client.Send(ClientPackets::ResumePauseButton(static_cast<u16>(std::max(chatModal, 0))));
}

void GameActions::AnswerCountDialog(s32 value)
{
    m_client.Send(ClientPackets::ResumePCountDialog(value));
}

void GameActions::CloseInterfaces()
{
    m_client.Send(ClientPackets::CloseModal());
}

void GameActions::Say(std::string_view text, ChatColour_e colour, ChatEffect_e effect)
{
    m_client.Send(ClientPackets::MessagePublic(text, colour, effect));
}

void GameActions::SendPrivateMessage(std::string_view name, std::string_view text)
{
    m_client.Send(ClientPackets::MessagePrivate(Base37::Encode(name), text));
}

void GameActions::SendCommand(std::string_view command)
{
    m_client.Send(ClientPackets::ClientCheat(command));
}

void GameActions::AddFriend(std::string_view name)
{
    m_client.Send(ClientPackets::FriendListAdd(Base37::Encode(name)));
}

void GameActions::RemoveFriend(std::string_view name)
{
    m_client.Send(ClientPackets::FriendListDel(Base37::Encode(name)));
}

void GameActions::AddIgnore(std::string_view name)
{
    m_client.Send(ClientPackets::IgnoreListAdd(Base37::Encode(name)));
}

void GameActions::RemoveIgnore(std::string_view name)
{
    m_client.Send(ClientPackets::IgnoreListDel(Base37::Encode(name)));
}

std::optional<ItemRef_s> GameActions::FindItem(u16 com, u16 obj) const
{
    const auto* const inventory = m_client.GetState().FindInventory(com);
    if (inventory == nullptr)
    {
        return std::nullopt;
    }

    const auto& slots = inventory->slots;
    const auto found = std::ranges::find(slots, s32{obj}, &Item_s::id);
    if (found == slots.end())
    {
        return std::nullopt;
    }

    return ItemRef_s{.obj = obj, .slot = static_cast<u16>(found - slots.begin()), .com = com};
}

std::optional<std::vector<Tile_s>> GameActions::FindWalkRoute(const WorldMap& map, const Tile_s& start, const Tile_s& destination)
{
    return FindRoute(map, start, {{.kind = RouteKind_e::Tile, .tile = destination, .tryNearest = true}});
}

// The webclient reaches an NPC of any size, or a player, as the 1x1 area on its tile.
std::optional<std::vector<Tile_s>> GameActions::FindEntityRoute(const WorldMap& map, const Tile_s& start, const Tile_s& tile)
{
    return FindRoute(map, start, {MakeAreaTarget(tile)});
}

std::optional<std::vector<Tile_s>> GameActions::FindGroundItemRoute(const WorldMap& map, const Tile_s& start, const Tile_s& tile)
{
    return FindRoute(map, start, {{.kind = RouteKind_e::Tile, .tile = tile}, MakeAreaTarget(tile)});
}

std::optional<std::vector<Tile_s>> GameActions::FindLocRoute(const WorldMap& map, const Tile_s& start, const Tile_s& tile, u16 loc)
{
    const auto target = GetLocTarget(map, tile, loc);
    if (!target)
    {
        return std::nullopt;
    }

    return FindRoute(map, start, {*target});
}

void GameActions::Approach(const std::optional<std::vector<Tile_s>>& route, const Tile_s& destination, ClientPacket_s action)
{
    if (route)
    {
        m_client.SendMove(MoveKind_e::OpClick, *route, false);
    }
    else
    {
        // The webclient sends the op when tryMove finds nothing, and the server walks as far as it can.
        LogNoRoute(destination, "sending the op alone");
    }

    m_client.Send(std::move(action));
}

void GameActions::ApproachVia(std::span<const Tile_s> waypoints, ClientPacket_s action)
{
    m_client.SendMove(MoveKind_e::OpClick, waypoints, false);
    m_client.Send(std::move(action));
}

// Without the loc in the map, the walk goes straight to its tile, as it did before there was a map.
void GameActions::ApproachLoc(const Tile_s& tile, u16 loc, ClientPacket_s action)
{
    const auto target = GetLocTarget(GetMap(), tile, loc);
    if (!target)
    {
        ApproachVia(std::span{&tile, 1}, std::move(action));
        return;
    }

    Approach(FindRoute(GetMap(), GetStart(), {*target}), tile, std::move(action));
}

const WorldMap& GameActions::GetMap() const
{
    return m_client.GetMap();
}

const Tile_s& GameActions::GetStart() const
{
    return m_client.GetState().localPlayer.tile;
}

std::optional<std::vector<Tile_s>> GameActions::FindRoute(const WorldMap& map, const Tile_s& start, std::initializer_list<RouteTarget_s> targets)
{
    for (const auto& target : targets)
    {
        if (auto route = PathFinder::FindPath(map, start, target))
        {
            return route;
        }
    }

    return std::nullopt;
}

std::optional<RouteTarget_s> GameActions::GetLocTarget(const WorldMap& map, const Tile_s& tile, u16 loc)
{
    for (const auto layer : LAYERS)
    {
        const auto scene = map.GetLoc(tile, layer);
        if (scene && scene->id == loc)
        {
            return MakeLocTarget(*scene, map.GetCache().FindLoc(loc));
        }
    }

    return std::nullopt;
}

void GameActions::LogNoRoute(const Tile_s& destination, std::string_view instead) const
{
    const auto& start = GetStart();
    m_client.GetLogger().Verbose("No route from ({}, {}, {}) to ({}, {}, {}); {}", start.x, start.z, start.level, destination.x, destination.z, destination.level, instead);
}

Tile_s GameActions::GetNpcTile(u16 npcIndex) const
{
    const auto* const npc = m_client.GetState().FindNpc(npcIndex);
    if (npc == nullptr)
    {
        throw std::invalid_argument{std::format("NPC {} isn't in view, so the server would reject the interaction", npcIndex)};
    }

    return npc->tile;
}

Tile_s GameActions::GetPlayerTile(u16 playerIndex) const
{
    const auto* const player = m_client.GetState().FindPlayer(playerIndex);
    if (player == nullptr)
    {
        throw std::invalid_argument{std::format("Player {} isn't in view, so the server would reject the interaction", playerIndex)};
    }

    return player->tile;
}
