#pragma once

#include "../Console/Logger.hpp"
#include "ConnectionOptions_s.hpp"
#include "Link.hpp"
#include "NetLoop.hpp"

// The owner's handle on one connection. Constructing it starts connecting, and destroying it closes the connection;
// the close finishes on the loop without anything waiting for it. Bytes and state change only while the loop runs:
// in Pump or a wait, in another connection's, or in the loop's own Poll, Wait or Settle. The loop must outlive it.
class Connection
{
public:
    Connection(NetLoop& loop, const ConnectionOptions_s& options, std::shared_ptr<Logger> logger);
    ~Connection();

    Connection(const Connection&) = delete;
    Connection& operator=(const Connection&) = delete;

    // Never waits. Forgets a failure, and keeps the bytes already received readable.
    void Close() noexcept;
    // One binary message, queued; never waits on the network. Runs what the loop has ready first, so it reports
    // an ending that has already arrived.
    void Send(std::span<const u8> data);
    // Runs what the loop has ready, then throws ConnectionError if the connection failed, or returns its state.
    ConnectionState_e Pump();

    [[nodiscard]] std::size_t Available() const;
    void Peek(std::span<u8> destination) const;
    std::span<u8> Read(std::span<u8> destination);

    void WaitAvailable(std::size_t count);
    [[nodiscard]] bool WaitAvailable(std::size_t count, std::chrono::milliseconds timeout);
    void WaitOpen();
    [[nodiscard]] bool WaitOpen(std::chrono::milliseconds timeout);
    void WaitClosed();
    [[nodiscard]] bool WaitClosed(std::chrono::milliseconds timeout);

private:
    static void ThrowIfEnded(const LinkStatus_s& status);

    bool WaitAvailableUntil(std::size_t count, NetLoop::Deadline deadline);
    bool WaitOpenUntil(NetLoop::Deadline deadline);
    bool WaitClosedUntil(NetLoop::Deadline deadline);

    NetLoop& m_loop;
    std::shared_ptr<Link> m_link;
};
