#pragma once

// A message one script sent another, as the JSON text of the value it sent: each VM has its own heap, so
// the receiver gets a copy.
struct BotMessage_s
{
    std::string sender;
    std::string json;
};

// Passes messages between the scripts in one process. Each account registers a receiver under its
// username, which senders give in any case, and unregisters before it goes away.
class BotMessenger
{
public:
    static constexpr std::size_t MAX_MESSAGE_SIZE = 64 * 1024;

    // Takes the message, or returns false when it can't now.
    using Receiver = std::function<bool(BotMessage_s message)>;

    void Register(std::string_view username, Receiver receiver);
    void Unregister(std::string_view username);
    // Empty when no account has that username; otherwise whether its receiver took the message.
    [[nodiscard]] std::optional<bool> Send(std::string_view username, BotMessage_s message) const;

private:
    std::unordered_map<std::string, Receiver> m_receivers;
};
