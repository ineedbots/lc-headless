#include "pch.hpp"
#include "Connection.hpp"

#include "../Config/Transport_e.hpp"
#include "../Console/Logger.hpp"
#include "ConnectionOptions_s.hpp"
#include "Error/ConnectionClosedError.hpp"
#include "Error/ConnectionError.hpp"
#include "Link.hpp"
#include "NetLoop.hpp"
#include "ReceiveBuffer.hpp"

namespace
{
    using Clock = NetLoop::Clock;

    const ConnectionOptions_s& Validated(const ConnectionOptions_s& options)
    {
        if (options.host.empty())
        {
            throw std::invalid_argument{"Connection options: host must not be empty"};
        }

        if (options.port == 0)
        {
            throw std::invalid_argument{"Connection options: port must not be 0"};
        }

        if (options.connectTimeout <= 0ms)
        {
            throw std::invalid_argument{"Connection options: connectTimeout must be positive"};
        }

        if (options.transport == Transport_e::Wss && options.tlsCaFile.empty())
        {
            throw std::invalid_argument{"Connection options: tlsCaFile must not be empty for wss"};
        }

        return options;
    }

    NetLoop::Deadline MakeDeadline(std::chrono::milliseconds timeout)
    {
        const auto now = Clock::now();
        if (timeout <= 0ms)
        {
            return now;
        }

        // Compared in milliseconds: converting milliseconds::max() to the clock's ticks would overflow.
        const auto untilClockEnds = std::chrono::floor<std::chrono::milliseconds>(Clock::time_point::max() - now);
        if (timeout >= untilClockEnds)
        {
            return std::nullopt;
        }

        return now + timeout;
    }

    bool IsPast(const NetLoop::Deadline& deadline)
    {
        return deadline && Clock::now() >= *deadline;
    }
}

Connection::Connection(NetLoop& loop, const ConnectionOptions_s& options, std::shared_ptr<Logger> logger)
    : m_loop{loop}
    , m_link{loop.Open(Validated(options), std::move(logger))}
{
}

Connection::~Connection()
{
    Close();
}

void Connection::Close() noexcept
{
    m_link->Close();
}

void Connection::Send(std::span<const u8> data)
{
    // Polled first, so a close that has already arrived is reported here rather than at the next pump.
    m_loop.Poll();

    const auto& status = m_link->GetStatus();
    ThrowIfEnded(status);
    assert(status.state == ConnectionState_e::Open && "Send called before the connection opened");

    m_link->Send(data);
}

ConnectionState_e Connection::Pump()
{
    m_loop.Poll();

    const auto& status = m_link->GetStatus();
    if (status.failed)
    {
        throw ConnectionError{status.reason};
    }

    return status.state;
}

std::size_t Connection::Available() const
{
    return m_link->GetReceived().Available();
}

void Connection::Peek(std::span<u8> destination) const
{
    m_link->GetReceived().Peek(destination);
}

std::span<u8> Connection::Read(std::span<u8> destination)
{
    return m_link->GetReceived().Read(destination);
}

void Connection::WaitAvailable(std::size_t count)
{
    WaitAvailableUntil(count, std::nullopt);
}

bool Connection::WaitAvailable(std::size_t count, std::chrono::milliseconds timeout)
{
    return WaitAvailableUntil(count, MakeDeadline(timeout));
}

void Connection::WaitOpen()
{
    WaitOpenUntil(std::nullopt);
}

bool Connection::WaitOpen(std::chrono::milliseconds timeout)
{
    return WaitOpenUntil(MakeDeadline(timeout));
}

void Connection::WaitClosed()
{
    WaitClosedUntil(std::nullopt);
}

bool Connection::WaitClosed(std::chrono::milliseconds timeout)
{
    return WaitClosedUntil(MakeDeadline(timeout));
}

void Connection::ThrowIfEnded(const LinkStatus_s& status)
{
    if (status.state != ConnectionState_e::Closing && status.state != ConnectionState_e::Closed)
    {
        return;
    }

    if (status.failed)
    {
        throw ConnectionError{status.reason};
    }

    throw ConnectionClosedError{status.reason};
}

bool Connection::WaitAvailableUntil(std::size_t count, NetLoop::Deadline deadline)
{
    while (true)
    {
        m_loop.Poll();
        if (Available() >= count)
        {
            return true;
        }

        ThrowIfEnded(m_link->GetStatus());
        if (IsPast(deadline))
        {
            return false;
        }

        m_loop.Wait(deadline);
    }
}

bool Connection::WaitOpenUntil(NetLoop::Deadline deadline)
{
    while (true)
    {
        m_loop.Poll();
        if (m_link->GetStatus().state == ConnectionState_e::Open)
        {
            return true;
        }

        ThrowIfEnded(m_link->GetStatus());
        if (IsPast(deadline))
        {
            return false;
        }

        m_loop.Wait(deadline);
    }
}

bool Connection::WaitClosedUntil(NetLoop::Deadline deadline)
{
    while (true)
    {
        m_loop.Poll();

        const auto& status = m_link->GetStatus();
        if (status.state == ConnectionState_e::Closed)
        {
            if (status.failed)
            {
                throw ConnectionError{status.reason};
            }

            return true;
        }

        if (IsPast(deadline))
        {
            return false;
        }

        m_loop.Wait(deadline);
    }
}
