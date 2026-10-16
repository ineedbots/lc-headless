#include "pch.hpp"
#include "EventDispatcher.hpp"

#include "../../Cache/GameCache_s.hpp"
#include "../../Cache/ObjType_s.hpp"
#include "../../Console/Logger.hpp"
#include "../../Game/GameTick.hpp"
#include "../../Game/Map/WorldMap.hpp"
#include "../../Game/State/GameEvent_s.hpp"
#include "../../Game/State/GameState_s.hpp"
#include "../../Game/State/Npc_s.hpp"
#include "../../Game/State/Player_s.hpp"
#include "../../Game/State/Social_s.hpp"
#include "../../Game/State/Stat_e.hpp"
#include "../../Game/State/Zone_s.hpp"
#include "../Convert/PyObjects.hpp"
#include "../Convert/PyValue.hpp"
#include "../ScriptVm.hpp"
#include "ScriptHooks.hpp"

#include <pocketpy.h>

namespace
{
    constexpr auto INVENTORY_CHANGED = "inventory_changed"sv;

    // rs2b0t's ChatLine type, as names rather than the webclient's numbers.
    std::optional<std::string_view> DescribeChatType(MessageType_e type)
    {
        switch (type)
        {
        case MessageType_e::Game:
            return "game"sv;
        case MessageType_e::Public:
            return "public"sv;
        case MessageType_e::Private:
            return "private"sv;
        case MessageType_e::TradeRequest:
            return "trade_request"sv;
        case MessageType_e::DuelRequest:
            return "duel_request"sv;
        case MessageType_e::Say:
            return std::nullopt;
        }

        return std::nullopt;
    }

    void FromOptionalString(py_OutRef out, std::string_view text)
    {
        if (text.empty())
        {
            py_newnone(out);
            return;
        }

        PyValue::FromString(out, text);
    }
}

void EventDispatcher::SkipToPresent(const GameState_s& state, const GameCache_s& cache)
{
    m_lastEvent = state.eventCount;
    m_lastMessage = state.messageCount;

    const auto* backpack = state.FindInventory(cache.inventoryComponent);
    m_backpack = backpack ? backpack->slots : std::vector<Item_s>{};
}

void EventDispatcher::DispatchEvents(const GameState_s& state, const GameCache_s& cache, ScriptHooks& hooks, Logger& logger)
{
    const auto events = state.GetEventsAfter(m_lastEvent);
    if (!events.empty() && events.front()->sequence != m_lastEvent + 1)
    {
        logger.Warning("{} game events were dropped before the script saw them", events.front()->sequence - m_lastEvent - 1);
    }

    for (const auto* event : events)
    {
        m_lastEvent = event->sequence;

        if (hooks.IsRunning())
        {
            DispatchEvent(*event, state, cache, hooks);
        }
    }
}

void EventDispatcher::DispatchMessages(const GameState_s& state, ScriptHooks& hooks)
{
    for (const auto* message : state.GetMessagesAfter(m_lastMessage))
    {
        m_lastMessage = message->sequence;

        const auto type = DescribeChatType(message->type);
        if (!hooks.IsRunning() || !type)
        {
            continue;
        }

        if (hooks.Has("chat_message"))
        {
            hooks.GetVm().Activate();
            PyValue::FromString(py_r0(), *type);
            FromOptionalString(py_r1(), message->sender);
            PyValue::FromString(py_r2(), message->text);
            hooks.Call("chat_message", std::array{py_r0(), py_r1(), py_r2()});
        }

        hooks.GetVm().Activate();
        PyValue::FromString(py_r0(), message->sender);
        PyValue::FromString(py_r1(), message->text);

        switch (message->type)
        {
        case MessageType_e::Game:
            hooks.Call("server_message", std::array{py_r1()});
            break;
        case MessageType_e::Private:
            hooks.Call("private_message", std::array{py_r0(), py_r1()});
            break;
        case MessageType_e::TradeRequest:
            hooks.Call("trade_request", std::array{py_r0()});
            break;
        case MessageType_e::DuelRequest:
            hooks.Call("duel_request", std::array{py_r0()});
            break;
        case MessageType_e::Public:
        case MessageType_e::Say:
            break;
        }
    }
}

void EventDispatcher::DispatchEvent(const GameEvent_s& event, const GameState_s& state, const GameCache_s& cache, ScriptHooks& hooks)
{
    const auto& data = event.data;
    const auto tick = state.tick;
    hooks.GetVm().Activate();

    const auto one = std::array{py_r0()};
    const auto two = std::array{py_r0(), py_r1()};
    const auto three = std::array{py_r0(), py_r1(), py_r2()};

    if (const auto* added = std::get_if<NpcAdded_s>(&data); added && hooks.Has("npc_spawned"))
    {
        const auto* current = state.FindNpc(added->npc.index);
        PyObjects::FromNpc(py_r0(), current ? *current : added->npc, tick, cache);
        hooks.Call("npc_spawned", one);
    }
    else if (const auto* removed = std::get_if<NpcRemoved_s>(&data); removed && hooks.Has("npc_despawned"))
    {
        PyObjects::FromNpc(py_r0(), removed->npc, tick, cache);
        hooks.Call("npc_despawned", one);
    }
    else if (const auto* npcHit = std::get_if<NpcHit_s>(&data); npcHit && hooks.Has("npc_damaged"))
    {
        const auto* npc = state.FindNpc(npcHit->index);
        if (npc == nullptr)
        {
            py_newnone(py_r0());
        }
        else
        {
            PyObjects::FromNpc(py_r0(), *npc, tick, cache);
        }

        py_newint(py_r1(), npcHit->hit.damage);
        hooks.Call("npc_damaged", two);
    }
    else if (const auto* playerAdded = std::get_if<PlayerAdded_s>(&data); playerAdded && hooks.Has("player_spawned"))
    {
        const auto* current = state.FindPlayer(playerAdded->player.index);
        PyObjects::FromPlayer(py_r0(), current ? *current : playerAdded->player, tick);
        hooks.Call("player_spawned", one);
    }
    else if (const auto* playerRemoved = std::get_if<PlayerRemoved_s>(&data); playerRemoved && hooks.Has("player_despawned"))
    {
        PyObjects::FromPlayer(py_r0(), playerRemoved->player, tick);
        hooks.Call("player_despawned", one);
    }
    else if (const auto* playerHit = std::get_if<PlayerHit_s>(&data); playerHit && hooks.Has("player_damaged"))
    {
        const auto* player = state.FindPlayer(playerHit->index);
        if (player == nullptr)
        {
            py_newnone(py_r0());
        }
        else
        {
            PyObjects::FromPlayer(py_r0(), *player, tick);
        }

        py_newint(py_r1(), playerHit->hit.damage);
        hooks.Call("player_damaged", two);
    }
    else if (const auto* localHit = std::get_if<LocalHit_s>(&data); localHit && hooks.Has("damaged"))
    {
        py_newint(py_r0(), localHit->hit.damage);
        hooks.Call("damaged", one);
    }
    else if (const auto* itemAdded = std::get_if<GroundItemAdded_s>(&data); itemAdded && hooks.Has("ground_item_spawned"))
    {
        PyObjects::FromGroundItem(py_r0(), itemAdded->item, cache);
        hooks.Call("ground_item_spawned", one);
    }
    else if (const auto* itemRemoved = std::get_if<GroundItemRemoved_s>(&data); itemRemoved && hooks.Has("ground_item_despawned"))
    {
        PyObjects::FromGroundItem(py_r0(), itemRemoved->item, cache);
        hooks.Call("ground_item_despawned", one);
    }
    else if (const auto* itemCount = std::get_if<GroundItemCountChanged_s>(&data); itemCount && hooks.Has("ground_item_changed"))
    {
        PyObjects::FromGroundItem(py_r0(), itemCount->item, cache);
        py_newint(py_r1(), itemCount->previousCount);
        hooks.Call("ground_item_changed", two);
    }
    else if (const auto* loc = std::get_if<LocChanged_s>(&data); loc && hooks.Has("loc_changed"))
    {
        const auto& change = loc->change;
        const auto scene = SceneLoc_s{.tile = change.tile, .layer = change.layer, .id = change.id, .shape = change.shape, .angle = change.angle, .changed = true};
        PyObjects::FromLoc(py_r0(), scene, cache);
        hooks.Call("loc_changed", one);
    }
    else if (const auto* inventory = std::get_if<InventoryChanged_s>(&data); inventory && inventory->com == cache.inventoryComponent)
    {
        DispatchBackpack(state, cache, hooks);
    }
    else if (const auto* said = std::get_if<NpcSaid_s>(&data); said && hooks.Has("npc_say"))
    {
        const auto* npc = state.FindNpc(said->index);
        if (npc == nullptr)
        {
            py_newnone(py_r0());
        }
        else
        {
            PyObjects::FromNpc(py_r0(), *npc, tick, cache);
        }

        PyValue::FromString(py_r1(), said->text);
        hooks.Call("npc_say", two);
    }
    else if (const auto* projectile = std::get_if<ProjectileLaunched_s>(&data); projectile && hooks.Has("projectile"))
    {
        PyObjects::FromProjectile(py_r0(), projectile->projectile);
        hooks.Call("projectile", one);
    }
    else if (const auto* stat = std::get_if<StatChanged_s>(&data))
    {
        // death.rs2 empties hitpoints before it says "Oh dear you are dead!"; the stat is the surer sign.
        if (stat->stat == static_cast<u8>(Stat_e::Hitpoints) && stat->previous.level > 0 && stat->current.level == 0)
        {
            hooks.Call("death");
            hooks.GetVm().Activate();
        }

        if (stat->current.xp != stat->previous.xp && hooks.Has("skill_xp"))
        {
            py_newint(py_r0(), stat->stat);
            py_newint(py_r1(), stat->current.xp);
            py_newint(py_r2(), stat->current.xp - stat->previous.xp);
            hooks.Call("skill_xp", three);
        }

        if (stat->current.baseLevel != stat->previous.baseLevel && hooks.Has("skill_level"))
        {
            hooks.GetVm().Activate();
            py_newint(py_r0(), stat->stat);
            py_newint(py_r1(), stat->current.baseLevel);
            py_newint(py_r2(), stat->previous.baseLevel);
            hooks.Call("skill_level", three);
        }
    }
    else if (const auto* varp = std::get_if<VarpChanged_s>(&data); varp && hooks.Has("varp_changed"))
    {
        py_newint(py_r0(), varp->varp);
        py_newint(py_r1(), varp->value);
        py_newint(py_r2(), varp->previous);
        hooks.Call("varp_changed", three);
    }
    else if (std::holds_alternative<ModalChanged_s>(data))
    {
        hooks.Call("interface_changed");
    }
    else if (const auto* reboot = std::get_if<RebootStarted_s>(&data); reboot && hooks.Has("system_update"))
    {
        py_newint(py_r0(), std::chrono::duration_cast<std::chrono::seconds>(reboot->ticks * GameTick::DURATION).count());
        hooks.Call("system_update", one);
    }
}

// The backpack's changes since the bot last saw it, one call per slot, as rs2b0t's inventory.changed.
void EventDispatcher::DispatchBackpack(const GameState_s& state, const GameCache_s& cache, ScriptHooks& hooks)
{
    const auto* inventory = state.FindInventory(cache.inventoryComponent);
    const auto previous = std::exchange(m_backpack, inventory ? inventory->slots : std::vector<Item_s>{});

    if (!hooks.Has(INVENTORY_CHANGED))
    {
        return;
    }

    const auto& current = m_backpack;
    const auto size = std::max(current.size(), previous.size());
    for (auto slot = std::size_t{0}; slot < size && hooks.IsRunning(); ++slot)
    {
        const auto now = slot < current.size() ? current[slot] : Item_s{};
        const auto before = slot < previous.size() ? previous[slot] : Item_s{};
        if (now.id == before.id && now.count == before.count)
        {
            continue;
        }

        const auto* type = cache.FindObj(now.id);
        hooks.GetVm().Activate();
        py_newint(py_r0(), static_cast<s64>(slot));
        py_newint(py_r1(), now.id);
        FromOptionalString(py_r2(), type ? type->name : std::string_view{});
        py_newint(py_r3(), now.count);
        py_newint(py_r4(), before.id);
        py_newint(py_r5(), before.count);
        hooks.Call(INVENTORY_CHANGED, std::array{py_r0(), py_r1(), py_r2(), py_r3(), py_r4(), py_r5()});
    }
}
