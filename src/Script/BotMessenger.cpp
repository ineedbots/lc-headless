#include "pch.hpp"
#include "BotMessenger.hpp"

namespace
{
    std::string ToLower(std::string_view text)
    {
        auto lower = std::string{text};
        std::ranges::transform(lower, lower.begin(), [](char character)
        {
            return static_cast<char>(std::tolower(static_cast<unsigned char>(character)));
        });

        return lower;
    }
}

void BotMessenger::Register(std::string_view username, Receiver receiver)
{
    assert(receiver && "A bot message receiver must be callable");
    const auto [entry, added] = m_receivers.try_emplace(ToLower(username), std::move(receiver));
    assert(added && "Two accounts registered the same username");
    static_cast<void>(entry);
    static_cast<void>(added);
}

void BotMessenger::Unregister(std::string_view username)
{
    m_receivers.erase(ToLower(username));
}

std::optional<bool> BotMessenger::Send(std::string_view username, BotMessage_s message) const
{
    const auto receiver = m_receivers.find(ToLower(username));
    if (receiver == m_receivers.end())
    {
        return std::nullopt;
    }

    return receiver->second(std::move(message));
}
