#include "pch.hpp"
#include "StateLog.hpp"

#include "../State/GameState_s.hpp"
#include "../State/Social_s.hpp"

void StateLog::AddMessage(GameState_s& state, MessageType_e type, std::string sender, u64 sender37, u8 rights, std::string text)
{
    auto message = ChatMessage_s{
        .sequence = ++state.messageCount,
        .tick = state.tick,
        .type = type,
        .sender = std::move(sender),
        .sender37 = sender37,
        .rights = rights,
        .text = std::move(text),
    };

    Push(state.messages, std::move(message), GameState_s::MAX_MESSAGES);
}
