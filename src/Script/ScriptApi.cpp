#include "pch.hpp"
#include "ScriptApi.hpp"

#include "../Cache/ClientCode_e.hpp"
#include "../Cache/GameCache_s.hpp"
#include "../Cache/IfComponent_s.hpp"
#include "../Game/GameActions.hpp"
#include "../Game/Interface/DialogueTracker.hpp"
#include "../Game/Map/InteractionRoutes.hpp"
#include "../Game/Map/PathFinder.hpp"
#include "../Game/Map/WorldMap.hpp"
#include "../Game/Menu/Menus.hpp"
#include "../Game/Nav/NavPoint_s.hpp"
#include "../Game/Nav/Navigation.hpp"
#include "../Game/Protocol/ClientPackets.hpp"
#include "../Game/Query/EntityQuery.hpp"
#include "../Game/Query/InventoryItem_s.hpp"
#include "../Game/Query/InventoryQuery.hpp"
#include "../Game/Query/SearchFilter_s.hpp"
#include "../Game/State/EntityStatus.hpp"
#include "../Game/State/Entity_s.hpp"
#include "../Game/State/GameState_s.hpp"
#include "../Game/State/Npc_s.hpp"
#include "../Game/State/Player_s.hpp"
#include "../Game/State/Stat_s.hpp"
#include "../Game/State/Zone_s.hpp"
#include "../Game/Tile_s.hpp"
#include "BotMessenger.hpp"

ScriptApi::ScriptApi(const GameState_s& state, const WorldMap& map, GameActions& actions, BotMessenger* messenger, std::string username, std::shared_ptr<const Navigation> navigation)
    : m_state{state}
    , m_map{map}
    , m_actions{actions}
    , m_messenger{messenger}
    , m_username{std::move(username)}
    , m_navigation{std::move(navigation)}
{
}

std::optional<NavPath_s> ScriptApi::FindWorldPath(NavPoint_s from, NavPoint_s to, const NavFindOptions_s& options) const
{
    if (!m_navigation)
    {
        return std::nullopt;
    }

    return WorldPathFinder::FindPath(*m_navigation, from, to, options);
}

const Navigation* ScriptApi::GetNavigation() const
{
    return m_navigation.get();
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

ScriptApi::Menu ScriptApi::GetNpcMenu(const GameCache_s& cache, s32 npc)
{
    return Menus::GetNpcMenu(cache, npc);
}

ScriptApi::Menu ScriptApi::GetLocMenu(const GameCache_s& cache, s32 loc)
{
    return Menus::GetLocMenu(cache, loc);
}

ScriptApi::Menu ScriptApi::GetGroundItemMenu(const GameCache_s& cache, s32 obj)
{
    return Menus::GetGroundItemMenu(cache, obj);
}

ScriptApi::Menu ScriptApi::GetItemMenu(const GameCache_s& cache, s32 obj)
{
    return Menus::GetItemMenu(cache, obj);
}

std::optional<ScriptApi::Menu> ScriptApi::GetInventoryMenu(const GameCache_s& cache, u16 com)
{
    return Menus::GetInventoryMenu(cache, com);
}

ScriptApi::Menu ScriptApi::GetPlayerMenu() const
{
    return Menus::GetPlayerMenu(m_state);
}

bool ScriptApi::CanReachEntity(const Tile_s& tile) const
{
    return InteractionRoutes::FindEntityRoute(m_map, GetPosition(), tile).has_value();
}

bool ScriptApi::CanReachGroundItem(const Tile_s& tile) const
{
    return InteractionRoutes::FindGroundItemRoute(m_map, GetPosition(), tile).has_value();
}

bool ScriptApi::CanReachLoc(const Tile_s& tile, u16 loc) const
{
    return InteractionRoutes::FindLocRoute(m_map, GetPosition(), tile, loc).has_value();
}

Tile_s ScriptApi::ToTile(s32 x, s32 z) const
{
    return {.x = x, .z = z, .level = m_state.localPlayer.tile.level};
}

bool ScriptApi::IsMoving() const
{
    return m_state.walkDestination.has_value() || EntityStatus::IsMoving(m_state.localPlayer, m_state.tick);
}

bool ScriptApi::InCombat() const
{
    return EntityStatus::InCombat(m_state.localPlayer, m_state.tick);
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

InterfaceView ScriptApi::GetInterfaces() const
{
    return InterfaceView{GetCache(), m_state.interfaces};
}

std::optional<u16> ScriptApi::FindContinue() const
{
    return m_dialogue.FindContinue(GetInterfaces());
}

bool ScriptApi::IsCountDialogOpen() const
{
    return m_dialogue.IsCountDialogOpen(m_state.interfaces);
}

std::vector<ChatOption_s> ScriptApi::GetChatOptions() const
{
    return ChatDialog::GetOptions(GetInterfaces());
}

std::vector<std::string> ScriptApi::GetChatTexts() const
{
    return ChatDialog::GetTexts(GetInterfaces());
}

std::vector<MakeProduct_s> ScriptApi::GetMakeProducts() const
{
    return ChatDialog::GetMakeProducts(GetInterfaces());
}

std::vector<MakeSlot_s> ScriptApi::GetMakePanel() const
{
    return ChatDialog::GetMakePanel(GetInterfaces(), m_state);
}

std::vector<Npc_s> ScriptApi::GetNpcs(const SearchFilter_s& filter) const
{
    return EntityQuery{m_state, m_map}.GetNpcs(filter);
}

std::optional<Npc_s> ScriptApi::GetNearestNpc(const SearchFilter_s& filter, std::optional<bool> inCombat, bool reachable) const
{
    return EntityQuery{m_state, m_map}.GetNearestNpc(filter, inCombat, reachable);
}

std::optional<Npc_s> ScriptApi::GetNpc(u16 index) const
{
    return EntityQuery{m_state, m_map}.GetNpc(index);
}

std::vector<Player_s> ScriptApi::GetPlayers(std::optional<s32> radius) const
{
    return EntityQuery{m_state, m_map}.GetPlayers(radius);
}

std::optional<Player_s> ScriptApi::GetPlayerByName(std::string_view name) const
{
    return EntityQuery{m_state, m_map}.GetPlayerByName(name);
}

std::vector<GroundItem_s> ScriptApi::GetGroundItems(const SearchFilter_s& filter) const
{
    return EntityQuery{m_state, m_map}.GetGroundItems(filter);
}

std::optional<GroundItem_s> ScriptApi::GetNearestGroundItem(const SearchFilter_s& filter, bool reachable) const
{
    return EntityQuery{m_state, m_map}.GetNearestGroundItem(filter, reachable);
}

std::optional<SceneLoc_s> ScriptApi::GetLocAt(s32 x, s32 z, std::optional<LocLayer_e> layer) const
{
    return EntityQuery{m_state, m_map}.GetLocAt(ToTile(x, z), layer);
}

std::vector<SceneLoc_s> ScriptApi::GetLocs(const SearchFilter_s& filter, std::optional<LocLayer_e> layer) const
{
    return EntityQuery{m_state, m_map}.GetLocs(filter, layer);
}

std::optional<SceneLoc_s> ScriptApi::GetNearestLoc(const SearchFilter_s& filter, std::optional<LocLayer_e> layer, bool reachable) const
{
    return EntityQuery{m_state, m_map}.GetNearestLoc(filter, layer, reachable);
}

std::vector<InventoryItem_s> ScriptApi::GetInventory(u16 com) const
{
    return InventoryQuery{m_state, GetCache()}.GetInventory(com);
}

s32 ScriptApi::CountItems(const SearchFilter_s& filter, u16 com) const
{
    return InventoryQuery{m_state, GetCache()}.CountItems(filter, com);
}

std::optional<InventoryItem_s> ScriptApi::FindItem(const SearchFilter_s& filter, u16 com) const
{
    return InventoryQuery{m_state, GetCache()}.FindItem(filter, com);
}

s32 ScriptApi::GetEmptySlots() const
{
    return InventoryQuery{m_state, GetCache()}.GetEmptySlots();
}

std::optional<u8> ScriptApi::FindNpcOp(u16 index, std::string_view text) const
{
    return Menus::FindNpcOp(m_state, GetCache(), index, text);
}

u8 ScriptApi::FindPlayerOp(std::string_view text) const
{
    return Menus::FindPlayerOp(m_state, text);
}

u8 ScriptApi::FindLocOp(u16 loc, std::string_view text) const
{
    return Menus::FindLocOp(GetCache(), loc, text);
}

u8 ScriptApi::FindGroundItemOp(u16 obj, std::string_view text) const
{
    return Menus::FindGroundItemOp(GetCache(), obj, text);
}

u8 ScriptApi::FindInventoryOption(u16 com, std::string_view text) const
{
    return Menus::FindInventoryOption(GetCache(), com, text);
}

u8 ScriptApi::FindItemOp(s32 obj, std::string_view text) const
{
    return Menus::FindItemOp(GetCache(), obj, text);
}

bool ScriptApi::IsReachable(s32 x, s32 z) const
{
    const auto target = RouteTarget_s{.kind = RouteKind_e::Tile, .tile = ToTile(x, z)};
    return PathFinder::FindPath(m_map, GetPosition(), target).has_value();
}

bool ScriptApi::CanStep(s32 fromX, s32 fromZ, s32 toX, s32 toZ) const
{
    return PathFinder::CanStep(m_map, ToTile(fromX, fromZ), ToTile(toX, toZ));
}

std::optional<std::vector<Tile_s>> ScriptApi::FindPath(s32 x, s32 z) const
{
    return InteractionRoutes::FindWalkRoute(m_map, GetPosition(), ToTile(x, z));
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

bool ScriptApi::ClickComponent(u16 com)
{
    const auto view = GetInterfaces();
    const auto* const component = view.Find(com);
    if (component == nullptr)
    {
        throw std::invalid_argument{std::format("the cache has no component {}", com)};
    }

    if (component->buttonType == ButtonType_e::None || component->buttonType == ButtonType_e::Target)
    {
        throw std::invalid_argument{std::format("component {} isn't a button a click uses", com)};
    }

    if (!view.IsVisible(*component))
    {
        return false;
    }

    m_actions.ClickComponent(com, component->buttonType);
    return true;
}

bool ScriptApi::ClickText(std::string_view text, std::optional<u16> root)
{
    const auto view = GetInterfaces();
    for (const auto* const found : view.FindText(text, root))
    {
        if (const auto* const button = view.ButtonAt(*found))
        {
            m_actions.ClickComponent(button->id, button->buttonType);
            return true;
        }
    }

    return false;
}

bool ScriptApi::ContinueDialogue()
{
    const auto com = FindContinue();
    if (!com)
    {
        return false;
    }

    m_actions.ContinueDialogue(*com);
    m_dialogue.NoteContinued(m_state.interfaces);
    return true;
}

bool ScriptApi::AnswerCountDialog(s32 value)
{
    if (!IsCountDialogOpen())
    {
        return false;
    }

    m_actions.AnswerCountDialog(value);
    m_dialogue.NoteAnswered(m_state.interfaces);
    return true;
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

void ScriptApi::RequestRelog(std::chrono::seconds delay)
{
    m_relogRequest = delay;
}

std::optional<std::chrono::seconds> ScriptApi::TakeRelogRequest()
{
    return std::exchange(m_relogRequest, std::nullopt);
}

bool ScriptApi::CanSetRun() const
{
    const auto view = GetInterfaces();
    const auto* const button = view.Find(GetCache().runOnButton);
    return button != nullptr && view.IsOpen(button->root);
}

bool ScriptApi::IsAppearanceScreenOpen() const
{
    return FindAcceptDesign() != nullptr;
}

// As the webclient's Accept does: the design, then the button, whose script closes the screen.
bool ScriptApi::SetAppearance(const IdkDesign_s& design)
{
    const auto* const accept = FindAcceptDesign();
    if (accept == nullptr)
    {
        return false;
    }

    m_actions.SaveDesign(design);
    m_actions.ClickButton(accept->id);
    return true;
}

void ScriptApi::SetStepTime(s64 milliseconds)
{
    m_stepTime = milliseconds;
}

s64 ScriptApi::GetStepTime() const
{
    return m_stepTime;
}

void ScriptApi::NoteProgress()
{
    m_lastProgress = m_stepTime;
}

std::optional<s64> ScriptApi::GetLastProgress() const
{
    return m_lastProgress;
}

bool ScriptApi::HasItem(const InventoryItem_s& item) const
{
    return InventoryQuery{m_state, GetCache()}.HasItem(item);
}

bool ScriptApi::HasGroundItem(u16 obj, const Tile_s& tile) const
{
    return EntityQuery{m_state, m_map}.HasGroundItem(obj, tile);
}

ItemRef_s ScriptApi::ToItemRef(const InventoryItem_s& item)
{
    return {.obj = static_cast<u16>(item.id), .slot = item.slot, .com = item.com};
}

const IfComponent_s* ScriptApi::FindAcceptDesign() const
{
    const auto mainModal = m_state.interfaces.mainModal;
    if (mainModal < 0)
    {
        return nullptr;
    }

    return GetInterfaces().FindClientCode(static_cast<u16>(mainModal), ClientCode_e::AcceptDesign);
}
