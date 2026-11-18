#include "pch.hpp"
#include "EventOutbox.hpp"

#include "EventLimits.hpp"

bool EventOutbox::TryPush(std::shared_ptr<const std::string> text)
{
    assert(text);

    if (m_messages.size() >= EventLimits::MAX_OUTBOX_ITEMS || text->size() > EventLimits::MAX_OUTBOX_BYTES - m_bytes)
    {
        return false;
    }

    m_messages.push_back(std::move(text));
    m_bytes += m_messages.back()->size();
    return true;
}

std::shared_ptr<const std::string> EventOutbox::Front() const
{
    return m_messages.empty() ? nullptr : m_messages.front();
}

void EventOutbox::Pop()
{
    if (m_messages.empty())
    {
        return;
    }

    m_bytes -= m_messages.front()->size();
    m_messages.pop_front();
}

std::size_t EventOutbox::Size() const
{
    return m_messages.size();
}

std::size_t EventOutbox::Bytes() const
{
    return m_bytes;
}
