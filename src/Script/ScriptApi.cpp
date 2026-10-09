#include "pch.hpp"
#include "ScriptApi.hpp"

#include "../Cache/GameCache_s.hpp"
#include "../Cache/LocType_s.hpp"
#include "../Cache/NpcType_s.hpp"
#include "../Cache/ObjType_s.hpp"
#include "../Cache/TextPool.hpp"
#include "../Game/GameActions.hpp"
#include "../Game/Map/PathFinder.hpp"
#include "../Game/Map/WorldMap.hpp"
#include "../Game/Protocol/ClientPackets.hpp"
#include "../Game/State/Entity_s.hpp"
#include "../Game/State/GameState_s.hpp"
#include "../Game/State/Npc_s.hpp"
#include "../Game/State/Player_s.hpp"
#include "../Game/State/Stat_s.hpp"
#include "../Game/State/Zone_s.hpp"
#include "../Game/Tile_s.hpp"
#include "BotMessenger.hpp"

namespace
{
    constexpr auto MENU_SIZE = std::size_t{5};
    constexpr auto TAKE_SLOT = std::size_t{2};
    constexpr auto DROP_SLOT = std::size_t{4};
    constexpr auto LAYERS = std::to_array<LocLayer_e>({LocLayer_e::Wall, LocLayer_e::WallDecor, LocLayer_e::Ground, LocLayer_e::GroundDecor});

    // A target's options by slot, as its right-click menu lists them; empty where there's none.
    using Menu = std::array<std::string_view, MENU_SIZE>;

    bool MatchesId(std::span<const s32> ids, s32 id)
    {
        return ids.empty() || std::ranges::find(ids, id) != ids.end();
    }

    bool EqualsIgnoringCase(std::string_view left, std::string_view right)
    {
        return std::ranges::equal(left, right, [](char a, char b)
        {
            return std::tolower(static_cast<unsigned char>(a)) == std::tolower(static_cast<unsigned char>(b));
        });
    }

    bool MatchesName(std::span<const std::string> names, std::string_view name)
    {
        if (names.empty())
        {
            return true;
        }

        return !name.empty() && std::ranges::any_of(names, [name](const std::string& wanted)
        {
            return EqualsIgnoringCase(wanted, name);
        });
    }

    // Nearest first, keeping the given order between equal distances.
    template <typename T, typename TTile>
    void SortByDistance(std::vector<T>& candidates, const Tile_s& from, TTile getTile)
    {
        std::ranges::stable_sort(candidates, {}, [&from, &getTile](const T& candidate)
        {
            return from.GetDistance(getTile(candidate));
        });
    }

    // The nearest candidate that accept takes; ties go to the first in the given order.
    template <typename T, typename TTile, typename TAccept>
    std::optional<T> FindNearest(std::vector<T> candidates, const Tile_s& from, TTile getTile, TAccept accept)
    {
        SortByDistance(candidates, from, getTile);
        const auto found = std::ranges::find_if(candidates, accept);
        if (found == candidates.end())
        {
            return std::nullopt;
        }

        return *found;
    }

    Menu MakeMenu(const GameCache_s& cache, std::span<const u16> ops)
    {
        auto menu = Menu{};
        for (std::size_t slot = 0; slot < menu.size() && slot < ops.size(); ++slot)
        {
            menu[slot] = cache.GetOption(ops[slot]);
        }

        return menu;
    }

    std::string DescribeMenu(const Menu& menu)
    {
        auto text = std::string{};
        for (std::size_t slot = 0; slot < menu.size(); ++slot)
        {
            if (menu[slot].empty())
            {
                continue;
            }

            if (!text.empty())
            {
                text += ", ";
            }

            std::format_to(std::back_inserter(text), "{} ({})", menu[slot], slot + 1);
        }

        return text.empty() ? "none" : text;
    }

    u8 ChooseOption(const Menu& menu, std::string_view text, std::string_view target)
    {
        const auto found = std::ranges::find_if(menu, [text](std::string_view option)
        {
            return !option.empty() && EqualsIgnoringCase(option, text);
        });

        if (found == menu.end())
        {
            throw std::invalid_argument{std::format("{} has no option '{}'; its options are {}", target, text, DescribeMenu(menu))};
        }

        return static_cast<u8>(found - menu.begin() + 1);
    }

    std::string DescribeType(std::string_view kind, s32 id, std::string_view name)
    {
        if (name.empty())
        {
            return std::format("{} {}", kind, id);
        }

        return std::format("{} ({} {})", name, kind, id);
    }

    template <typename T>
    const T& RequireType(const T* type, std::string_view kind, s32 id)
    {
        if (type == nullptr)
        {
            throw std::invalid_argument{std::format("{} {} isn't in the cache, so its options can only be chosen by number", kind, id)};
        }

        return *type;
    }
}

ScriptApi::ScriptApi(const GameState_s& state, const WorldMap& map, GameActions& actions, BotMessenger* messenger, std::string username)
    : m_state{state}
    , m_map{map}
    , m_actions{actions}
    , m_messenger{messenger}
    , m_username{std::move(username)}
{
}

const GameState_s& ScriptApi::GetState() const
{
    return m_state;
}

const WorldMap& ScriptApi::GetMap() const
{
    return m_map;
}

const GameCache_s& ScriptApi::GetCache() const
{
    return m_map.GetCache();
}

const Player_s& ScriptApi::GetLocalPlayer() const
{
    return m_state.localPlayer;
}

Tile_s ScriptApi::GetPosition() const
{
    return m_state.localPlayer.tile;
}

Tile_s ScriptApi::ToTile(s32 x, s32 z) const
{
    return {.x = x, .z = z, .level = m_state.localPlayer.tile.level};
}

bool ScriptApi::IsMoving() const
{
    return m_state.walkDestination.has_value() || IsMoving(m_state.localPlayer, m_state.tick);
}

bool ScriptApi::InCombat() const
{
    return InCombat(m_state.localPlayer, m_state.tick);
}

bool ScriptApi::IsRunning() const
{
    return m_state.GetVarp(GetCache().runVarp) == 1;
}

const Stat_s& ScriptApi::GetStat(s32 stat) const
{
    if (stat < 0 || static_cast<std::size_t>(stat) >= m_state.stats.size())
    {
        throw std::invalid_argument{std::format("stat {} is not 0 to {}", stat, m_state.stats.size() - 1)};
    }

    return m_state.stats[static_cast<std::size_t>(stat)];
}

bool ScriptApi::IsInterfaceOpen(s32 id) const
{
    const auto& interfaces = m_state.interfaces;
    return id >= 0 && (interfaces.mainModal == id || interfaces.sideModal == id || interfaces.chatModal == id);
}

std::optional<std::string> ScriptApi::GetComponentText(u16 com) const
{
    const auto found = m_state.interfaces.components.find(com);
    if (found == m_state.interfaces.components.end())
    {
        return std::nullopt;
    }

    return found->second.text;
}

std::vector<Npc_s> ScriptApi::GetNpcs(const SearchFilter_s& filter) const
{
    auto found = std::vector<Npc_s>{};
    for (const auto& npc : m_state.npcs)
    {
        if (Matches(npc.tile, filter, npc.type, GetNpcName(npc.type)))
        {
            found.push_back(npc);
        }
    }

    return found;
}

std::optional<Npc_s> ScriptApi::GetNearestNpc(const SearchFilter_s& filter, std::optional<bool> inCombat, bool reachable) const
{
    auto candidates = GetNpcs(filter);
    if (inCombat)
    {
        std::erase_if(candidates, [this, &inCombat](const Npc_s& npc)
        {
            return InCombat(npc, m_state.tick) != *inCombat;
        });
    }

    const auto here = GetPosition();
    const auto getTile = [](const Npc_s& npc)
    {
        return npc.tile;
    };

    return FindNearest(std::move(candidates), here, getTile, [this, reachable, &here](const Npc_s& npc)
    {
        return !reachable || GameActions::FindEntityRoute(m_map, here, npc.tile).has_value();
    });
}

std::optional<Npc_s> ScriptApi::GetNpc(u16 index) const
{
    const auto* npc = m_state.FindNpc(index);
    if (npc == nullptr)
    {
        return std::nullopt;
    }

    return *npc;
}

std::vector<Player_s> ScriptApi::GetPlayers(std::optional<s32> radius) const
{
    const auto filter = SearchFilter_s{.radius = radius};
    auto found = std::vector<Player_s>{};
    for (const auto& player : m_state.players)
    {
        if (Matches(player.tile, filter, 0, {}))
        {
            found.push_back(player);
        }
    }

    return found;
}

std::optional<Player_s> ScriptApi::GetPlayerByName(std::string_view name) const
{
    const auto* player = m_state.FindPlayerByName(name);
    if (player == nullptr)
    {
        return std::nullopt;
    }

    return *player;
}

std::vector<GroundItem_s> ScriptApi::GetGroundItems(const SearchFilter_s& filter) const
{
    auto found = std::vector<GroundItem_s>{};
    for (const auto& item : m_state.groundItems)
    {
        if (Matches(item.tile, filter, item.id, GetObjName(item.id)))
        {
            found.push_back(item);
        }
    }

    return found;
}

std::optional<GroundItem_s> ScriptApi::GetNearestGroundItem(const SearchFilter_s& filter, bool reachable) const
{
    const auto here = GetPosition();
    const auto getTile = [](const GroundItem_s& item)
    {
        return item.tile;
    };

    return FindNearest(GetGroundItems(filter), here, getTile, [this, reachable, &here](const GroundItem_s& item)
    {
        return !reachable || GameActions::FindGroundItemRoute(m_map, here, item.tile).has_value();
    });
}

std::optional<SceneLoc_s> ScriptApi::GetLocAt(s32 x, s32 z, std::optional<LocLayer_e> layer) const
{
    const auto tile = ToTile(x, z);
    if (layer)
    {
        return m_map.GetLoc(tile, *layer);
    }

    auto removed = std::optional<SceneLoc_s>{};
    for (const auto each : LAYERS)
    {
        const auto loc = m_map.GetLoc(tile, each);
        if (!loc)
        {
            continue;
        }

        if (loc->id >= 0)
        {
            return loc;
        }

        if (!removed)
        {
            removed = loc;
        }
    }

    return removed;
}

std::vector<SceneLoc_s> ScriptApi::GetLocs(const SearchFilter_s& filter, std::optional<LocLayer_e> layer) const
{
    const auto here = GetPosition();
    auto locs = m_map.GetLocs(here.level);
    std::erase_if(locs, [this, &filter, &layer](const SceneLoc_s& loc)
    {
        return (layer && loc.layer != *layer) || !Matches(loc.tile, filter, loc.id, GetLocName(loc.id));
    });

    SortByDistance(locs, here, [](const SceneLoc_s& loc)
    {
        return loc.tile;
    });

    return locs;
}

std::optional<SceneLoc_s> ScriptApi::GetNearestLoc(const SearchFilter_s& filter, std::optional<LocLayer_e> layer, bool reachable) const
{
    const auto here = GetPosition();
    const auto getTile = [](const SceneLoc_s& loc)
    {
        return loc.tile;
    };

    return FindNearest(GetLocs(filter, layer), here, getTile, [this, reachable, &here](const SceneLoc_s& loc)
    {
        return !reachable || GameActions::FindLocRoute(m_map, here, loc.tile, static_cast<u16>(loc.id)).has_value();
    });
}

std::vector<InventoryItem_s> ScriptApi::GetInventory(u16 com) const
{
    auto items = std::vector<InventoryItem_s>{};
    const auto* inventory = m_state.FindInventory(com);
    if (inventory == nullptr)
    {
        return items;
    }

    for (std::size_t slot = 0; slot < inventory->slots.size(); ++slot)
    {
        const auto& item = inventory->slots[slot];
        if (item.id < 0)
        {
            continue;
        }

        items.push_back({.com = com, .slot = static_cast<u16>(slot), .id = item.id, .count = item.count});
    }

    return items;
}

s32 ScriptApi::CountItems(const SearchFilter_s& filter, u16 com) const
{
    auto total = 0;
    for (const auto& item : GetInventory(com))
    {
        if (MatchesId(filter.ids, item.id) && MatchesName(filter.names, GetObjName(item.id)))
        {
            total += item.count;
        }
    }

    return total;
}

std::optional<InventoryItem_s> ScriptApi::FindItem(const SearchFilter_s& filter, u16 com) const
{
    const auto items = GetInventory(com);
    const auto found = std::ranges::find_if(items, [this, &filter](const InventoryItem_s& item)
    {
        return MatchesId(filter.ids, item.id) && MatchesName(filter.names, GetObjName(item.id));
    });

    if (found == items.end())
    {
        return std::nullopt;
    }

    return *found;
}

s32 ScriptApi::GetEmptySlots() const
{
    const auto& cache = GetCache();
    return cache.inventorySize - static_cast<s32>(GetInventory(cache.inventoryComponent).size());
}

std::optional<u8> ScriptApi::FindNpcOp(u16 index, std::string_view text) const
{
    const auto* const npc = m_state.FindNpc(index);
    if (npc == nullptr)
    {
        return std::nullopt;
    }

    const auto& type = RequireType(GetCache().FindNpc(npc->type), "NPC", npc->type);
    return ChooseOption(MakeMenu(GetCache(), type.ops), text, DescribeType("NPC", type.id, type.name));
}

u8 ScriptApi::FindPlayerOp(std::string_view text) const
{
    auto menu = Menu{};
    for (std::size_t slot = 0; slot < menu.size() && slot < m_state.playerOps.size(); ++slot)
    {
        if (m_state.playerOps[slot])
        {
            menu[slot] = m_state.playerOps[slot]->text;
        }
    }

    return ChooseOption(menu, text, "a player");
}

u8 ScriptApi::FindLocOp(u16 loc, std::string_view text) const
{
    const auto& type = RequireType(GetCache().FindLoc(loc), "loc", loc);
    return ChooseOption(MakeMenu(GetCache(), type.ops), text, DescribeType("loc", type.id, type.name));
}

u8 ScriptApi::FindGroundItemOp(u16 obj, std::string_view text) const
{
    const auto& type = RequireType(GetCache().FindObj(obj), "item", obj);
    auto menu = MakeMenu(GetCache(), type.ops);
    if (menu[TAKE_SLOT].empty())
    {
        menu[TAKE_SLOT] = TAKE_OPTION;
    }

    return ChooseOption(menu, text, DescribeType("item", type.id, type.name));
}

u8 ScriptApi::FindItemOp(s32 obj, std::string_view text) const
{
    const auto& type = RequireType(GetCache().FindObj(obj), "item", obj);
    auto menu = MakeMenu(GetCache(), type.inventoryOps);
    if (menu[DROP_SLOT].empty())
    {
        menu[DROP_SLOT] = DROP_OPTION;
    }

    return ChooseOption(menu, text, DescribeType("item", type.id, type.name));
}

bool ScriptApi::IsReachable(s32 x, s32 z) const
{
    const auto target = RouteTarget_s{.kind = RouteKind_e::Tile, .tile = ToTile(x, z)};
    return PathFinder::FindPath(m_map, GetPosition(), target).has_value();
}

std::optional<std::vector<Tile_s>> ScriptApi::FindPath(s32 x, s32 z) const
{
    return GameActions::FindWalkRoute(m_map, GetPosition(), ToTile(x, z));
}

bool ScriptApi::WalkTo(s32 x, s32 z, bool run)
{
    return m_actions.WalkTo(ToTile(x, z), run);
}

void ScriptApi::WalkPath(std::span<const Tile_s> points, bool run)
{
    m_actions.WalkPath(points, run);
}

bool ScriptApi::InteractNpc(u16 index, u8 op)
{
    if (m_state.FindNpc(index) == nullptr)
    {
        return false;
    }

    m_actions.InteractNpc(index, op);
    return true;
}

bool ScriptApi::InteractPlayer(u16 index, u8 op)
{
    if (m_state.FindPlayer(index) == nullptr)
    {
        return false;
    }

    m_actions.InteractPlayer(index, op);
    return true;
}

void ScriptApi::InteractLoc(u16 loc, s32 x, s32 z, u8 op)
{
    m_actions.InteractLoc(ToTile(x, z), loc, op);
}

void ScriptApi::InteractLocVia(std::span<const Tile_s> waypoints, u16 loc, s32 x, s32 z, u8 op)
{
    m_actions.InteractLocVia(waypoints, ToTile(x, z), loc, op);
}

bool ScriptApi::InteractGroundItem(u16 obj, s32 x, s32 z, u8 op)
{
    const auto tile = ToTile(x, z);
    if (!HasGroundItem(obj, tile))
    {
        return false;
    }

    m_actions.InteractGroundItem(tile, obj, op);
    return true;
}

bool ScriptApi::ItemOp(const InventoryItem_s& item, u8 op)
{
    if (!HasItem(item))
    {
        return false;
    }

    m_actions.OperateItem(ToItemRef(item), op);
    return true;
}

bool ScriptApi::InventoryButton(const InventoryItem_s& item, u8 op)
{
    if (!HasItem(item))
    {
        return false;
    }

    m_actions.InventoryButton(ToItemRef(item), op);
    return true;
}

void ScriptApi::MoveItem(u16 com, u16 fromSlot, u16 toSlot)
{
    m_actions.MoveItem(com, fromSlot, toSlot);
}

bool ScriptApi::UseItemOnNpc(const InventoryItem_s& item, u16 npcIndex)
{
    if (!HasItem(item) || m_state.FindNpc(npcIndex) == nullptr)
    {
        return false;
    }

    m_actions.UseItemOnNpc(ToItemRef(item), npcIndex);
    return true;
}

bool ScriptApi::UseItemOnPlayer(const InventoryItem_s& item, u16 playerIndex)
{
    if (!HasItem(item) || m_state.FindPlayer(playerIndex) == nullptr)
    {
        return false;
    }

    m_actions.UseItemOnPlayer(ToItemRef(item), playerIndex);
    return true;
}

bool ScriptApi::UseItemOnLoc(const InventoryItem_s& item, u16 loc, s32 x, s32 z)
{
    if (!HasItem(item))
    {
        return false;
    }

    m_actions.UseItemOnLoc(ToItemRef(item), ToTile(x, z), loc);
    return true;
}

bool ScriptApi::UseItemOnGroundItem(const InventoryItem_s& item, u16 obj, s32 x, s32 z)
{
    const auto tile = ToTile(x, z);
    if (!HasItem(item) || !HasGroundItem(obj, tile))
    {
        return false;
    }

    m_actions.UseItemOnGroundItem(ToItemRef(item), tile, obj);
    return true;
}

bool ScriptApi::UseItemOnItem(const InventoryItem_s& item, const InventoryItem_s& target)
{
    if (!HasItem(item) || !HasItem(target))
    {
        return false;
    }

    m_actions.UseItemOnItem(ToItemRef(item), ToItemRef(target));
    return true;
}

bool ScriptApi::CastOnNpc(u16 spellCom, u16 npcIndex)
{
    if (m_state.FindNpc(npcIndex) == nullptr)
    {
        return false;
    }

    m_actions.CastOnNpc(spellCom, npcIndex);
    return true;
}

bool ScriptApi::CastOnPlayer(u16 spellCom, u16 playerIndex)
{
    if (m_state.FindPlayer(playerIndex) == nullptr)
    {
        return false;
    }

    m_actions.CastOnPlayer(spellCom, playerIndex);
    return true;
}

void ScriptApi::CastOnLoc(u16 spellCom, u16 loc, s32 x, s32 z)
{
    m_actions.CastOnLoc(spellCom, ToTile(x, z), loc);
}

bool ScriptApi::CastOnGroundItem(u16 spellCom, u16 obj, s32 x, s32 z)
{
    const auto tile = ToTile(x, z);
    if (!HasGroundItem(obj, tile))
    {
        return false;
    }

    m_actions.CastOnGroundItem(spellCom, tile, obj);
    return true;
}

bool ScriptApi::CastOnItem(u16 spellCom, const InventoryItem_s& item)
{
    if (!HasItem(item))
    {
        return false;
    }

    m_actions.CastOnItem(spellCom, ToItemRef(item));
    return true;
}

void ScriptApi::ClickButton(u16 com)
{
    m_actions.ClickButton(com);
}

void ScriptApi::ContinueDialogue()
{
    m_actions.ContinueDialogue();
}

void ScriptApi::AnswerCountDialog(s32 value)
{
    m_actions.AnswerCountDialog(value);
}

void ScriptApi::CloseInterfaces()
{
    m_actions.CloseInterfaces();
}

void ScriptApi::SetRun(bool run)
{
    const auto& cache = GetCache();
    m_actions.ClickButton(run ? cache.runOnButton : cache.runOffButton);
}

void ScriptApi::Say(std::string_view text)
{
    m_actions.Say(text);
}

void ScriptApi::SendPrivateMessage(std::string_view name, std::string_view text)
{
    m_actions.SendPrivateMessage(name, text);
}

void ScriptApi::SendCommand(std::string_view command)
{
    m_actions.SendCommand(command);
}

void ScriptApi::AddFriend(std::string_view name)
{
    m_actions.AddFriend(name);
}

void ScriptApi::RemoveFriend(std::string_view name)
{
    m_actions.RemoveFriend(name);
}

void ScriptApi::AddIgnore(std::string_view name)
{
    m_actions.AddIgnore(name);
}

void ScriptApi::RemoveIgnore(std::string_view name)
{
    m_actions.RemoveIgnore(name);
}

std::optional<bool> ScriptApi::SendBotMessage(std::string_view username, std::string json)
{
    if (json.size() > BotMessenger::MAX_MESSAGE_SIZE)
    {
        throw std::invalid_argument{std::format("The message is {} bytes as JSON, over the limit of {}", json.size(), BotMessenger::MAX_MESSAGE_SIZE)};
    }

    if (m_messenger == nullptr)
    {
        return std::nullopt;
    }

    return m_messenger->Send(username, BotMessage_s{.sender = m_username, .json = std::move(json)});
}

void ScriptApi::RequestStop(StopRequest_e request)
{
    m_stopRequest = std::max(m_stopRequest, request);
}

StopRequest_e ScriptApi::TakeStopRequest()
{
    return std::exchange(m_stopRequest, StopRequest_e::None);
}

bool ScriptApi::IsMoving(const Entity_s& entity, u64 tick)
{
    return entity.lastMovement != Movement_e::None && entity.movedTick == tick;
}

bool ScriptApi::InCombat(const Entity_s& entity, u64 tick)
{
    return !entity.hits.empty() && tick - entity.hits.back().tick <= COMBAT_TICKS;
}

bool ScriptApi::Matches(const Tile_s& tile, const SearchFilter_s& filter, s32 id, std::string_view name) const
{
    if (!MatchesId(filter.ids, id) || !MatchesName(filter.names, name))
    {
        return false;
    }

    if (!filter.radius)
    {
        return true;
    }

    const auto& here = GetPosition();
    return tile.level == here.level && here.GetDistance(tile) <= *filter.radius;
}

std::string_view ScriptApi::GetNpcName(s32 type) const
{
    const auto* const npc = GetCache().FindNpc(type);
    return npc == nullptr ? std::string_view{} : npc->name;
}

std::string_view ScriptApi::GetObjName(s32 obj) const
{
    const auto* const type = GetCache().FindObj(obj);
    return type == nullptr ? std::string_view{} : type->name;
}

std::string_view ScriptApi::GetLocName(s32 loc) const
{
    const auto* const type = GetCache().FindLoc(loc);
    return type == nullptr ? std::string_view{} : type->name;
}

bool ScriptApi::HasItem(const InventoryItem_s& item) const
{
    const auto* inventory = m_state.FindInventory(item.com);
    return inventory != nullptr && item.slot < inventory->slots.size() && inventory->slots[item.slot].id == item.id;
}

bool ScriptApi::HasGroundItem(u16 obj, const Tile_s& tile) const
{
    return std::ranges::any_of(m_state.groundItems, [obj, &tile](const GroundItem_s& item)
    {
        return item.id == obj && item.tile == tile;
    });
}

ItemRef_s ScriptApi::ToItemRef(const InventoryItem_s& item)
{
    return {.obj = static_cast<u16>(item.id), .slot = item.slot, .com = item.com};
}
