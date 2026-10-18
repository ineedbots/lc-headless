#include "pch.hpp"
#include "Link.hpp"

#include "ReceiveBuffer.hpp"

namespace
{
    constexpr auto CLOSED_REASON = "Connection closed"sv;
}

const LinkStatus_s& Link::GetStatus() const
{
    return m_status;
}

const ReceiveBuffer& Link::GetReceived() const
{
    return m_received;
}

ReceiveBuffer& Link::GetReceived()
{
    return m_received;
}

bool Link::IsConnecting() const
{
    return m_status.state == ConnectionState_e::Connecting;
}

bool Link::IsOpen() const
{
    return m_status.state == ConnectionState_e::Open;
}

void Link::MarkOpen()
{
    if (IsConnecting())
    {
        m_status.state = ConnectionState_e::Open;
    }
}

void Link::MarkClosing()
{
    if (IsLive())
    {
        m_status = LinkStatus_s{.state = ConnectionState_e::Closing, .reason = std::string{CLOSED_REASON}};
    }
}

void Link::MarkFailed(std::string reason)
{
    if (IsLive())
    {
        m_status = LinkStatus_s{.state = ConnectionState_e::Closing, .failed = true, .reason = std::move(reason)};
    }
}

void Link::MarkEnded(std::string reason)
{
    if (IsOpen())
    {
        m_status = LinkStatus_s{.state = ConnectionState_e::Closing, .reason = std::move(reason)};
    }
}

void Link::MarkClosed()
{
    m_status.state = ConnectionState_e::Closed;
}

void Link::ForgetFailure()
{
    m_status.failed = false;
    m_status.reason = CLOSED_REASON;
}

void Link::Receive(std::span<const u8> bytes)
{
    if (IsOpen())
    {
        m_received.Append(bytes);
    }
}

bool Link::IsLive() const
{
    return IsConnecting() || IsOpen();
}
