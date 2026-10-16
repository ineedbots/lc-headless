#include "pch.hpp"
#include "BotMessenger.hpp"

#include "../Utils/StringUtils.hpp"

void BotMessenger::Register(std::string_view username, Receiver receiver)
{
    assert(receiver && "A bot message receiver must be callable");

    const auto [entry, added] = m_receivers.try_emplace(StringUtils::ToLower(username), std::move(receiver));
    assert(added && "Two accounts registered the same username");
    static_cast<void>(entry);
    static_cast<void>(added);
}

void BotMessenger::Unregister(std::string_view username)
{
    m_receivers.erase(StringUtils::ToLower(username));
}

std::optional<bool> BotMessenger::Send(std::string_view username, BotMessage_s message) const
{
    const auto receiver = m_receivers.find(StringUtils::ToLower(username));
    if (receiver == m_receivers.end())
    {
        return std::nullopt;
    }

    return receiver->second(std::move(message));
}
