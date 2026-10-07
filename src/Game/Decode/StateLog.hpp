#pragma once

#include "../State/GameEvent_s.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Social_s.hpp"

class StateLog
{
public:
    StateLog() = delete;

    template <typename T>
    static void Push(std::deque<T>& log, T entry, std::size_t limit = GameState_s::MAX_EFFECTS)
    {
        log.push_back(std::move(entry));
        while (log.size() > limit)
        {
            log.pop_front();
        }
    }

    static void AddMessage(GameState_s& state, MessageType_e type, std::string sender, u64 sender37, u8 rights, std::string text);
    static void AddEvent(GameState_s& state, GameEventData data);
};
