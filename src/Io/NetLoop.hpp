#pragma once

#include "../Console/Logger.hpp"
#include "ConnectionOptions_s.hpp"
#include "Link.hpp"

// Every link a loop opens does its I/O on the thread that runs the loop: in Poll, Wait and Settle, and so in a
// Connection's Pump and waits. Wake is the only member another thread may call. Abstract so that no shared header
// names an Asio type (TransportDesign.md §1, Headers).
class NetLoop
{
public:
    using Clock = std::chrono::steady_clock;
    using Deadline = std::optional<Clock::time_point>;

    [[nodiscard]] static std::shared_ptr<NetLoop> Create();

    virtual ~NetLoop() = default;

    NetLoop(const NetLoop&) = delete;
    NetLoop& operator=(const NetLoop&) = delete;

    // Starts connecting and returns at once. Connection's constructor is the caller.
    [[nodiscard]] virtual std::shared_ptr<Link> Open(const ConnectionOptions_s& options, std::shared_ptr<Logger> logger) = 0;
    // Runs what is ready, without waiting.
    virtual void Poll() = 0;
    // Waits until something happens or the deadline passes, then runs whatever is ready. Nullopt waits for something.
    virtual void Wait(Deadline deadline) = 0;
    // Runs the loop until every link it opened has finished, or the deadline passes.
    virtual void Settle(Clock::time_point deadline) = 0;
    // Ends a Wait early. Safe from any thread.
    virtual void Wake() noexcept = 0;

protected:
    NetLoop() = default;
};
