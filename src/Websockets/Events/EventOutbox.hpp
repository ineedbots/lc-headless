#pragma once

class EventOutbox
{
public:
    [[nodiscard]] bool TryPush(std::shared_ptr<const std::string> text);
    [[nodiscard]] std::shared_ptr<const std::string> Front() const;
    void Pop();

    [[nodiscard]] std::size_t Size() const;
    [[nodiscard]] std::size_t Bytes() const;

private:
    std::deque<std::shared_ptr<const std::string>> m_messages;
    std::size_t m_bytes = 0;
};
