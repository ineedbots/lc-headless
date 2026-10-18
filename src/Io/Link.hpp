#pragma once

#include "ReceiveBuffer.hpp"

enum class ConnectionState_e : u8
{
    Connecting,
    Open,
    Closing,
    Closed,
};

struct LinkStatus_s
{
    ConnectionState_e state = ConnectionState_e::Connecting;
    bool failed = false;
    std::string reason;
};

// One connection's I/O side and what it has received. Its pending handlers share it with its Connection, so it
// can finish closing after the Connection is gone. The Mark calls ignore a call that doesn't apply in the current
// state, so the first ending wins.
class Link
{
public:
    virtual ~Link() = default;

    Link(const Link&) = delete;
    Link& operator=(const Link&) = delete;

    virtual void Close() noexcept = 0;
    virtual void Send(std::span<const u8> data) = 0;

    [[nodiscard]] const LinkStatus_s& GetStatus() const;
    [[nodiscard]] const ReceiveBuffer& GetReceived() const;
    [[nodiscard]] ReceiveBuffer& GetReceived();

protected:
    Link() = default;

    [[nodiscard]] bool IsConnecting() const;
    [[nodiscard]] bool IsOpen() const;
    void MarkOpen();
    void MarkClosing();
    void MarkFailed(std::string reason);
    void MarkEnded(std::string reason);
    void MarkClosed();
    void ForgetFailure();
    void Receive(std::span<const u8> bytes);

private:
    [[nodiscard]] bool IsLive() const;

    LinkStatus_s m_status;
    ReceiveBuffer m_received;
};
