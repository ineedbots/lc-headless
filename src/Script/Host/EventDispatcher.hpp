#pragma once

#include "../../Cache/GameCache_s.hpp"
#include "../../Console/Logger.hpp"
#include "../../Game/State/GameEvent_s.hpp"
#include "../../Game/State/GameState_s.hpp"
#include "ScriptHooks.hpp"

// Passes what the server sent since the bot last looked to its hooks: game events, chat messages, and the
// backpack's changes slot by slot. It stops before the next one once the script isn't running.
class EventDispatcher
{
public:
    // What happened before now isn't passed on, as for a script that has just loaded.
    void SkipToPresent(const GameState_s& state, const GameCache_s& cache);
    void DispatchEvents(const GameState_s& state, const GameCache_s& cache, ScriptHooks& hooks, Logger& logger);
    void DispatchMessages(const GameState_s& state, ScriptHooks& hooks);

private:
    void DispatchEvent(const GameEvent_s& event, const GameState_s& state, const GameCache_s& cache, ScriptHooks& hooks);
    void DispatchBackpack(const GameState_s& state, const GameCache_s& cache, ScriptHooks& hooks);

    u64 m_lastEvent = 0;
    u64 m_lastMessage = 0;
    // The backpack as the bot last saw it, which inventory_changed reports changes to, slot by slot.
    std::vector<Item_s> m_backpack;
};
