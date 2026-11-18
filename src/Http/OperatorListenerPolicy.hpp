#pragma once

class OperatorListenerPolicy
{
public:
    OperatorListenerPolicy() = delete;

    static constexpr std::size_t MAX_CONNECTIONS = 128;
    static constexpr std::size_t MAX_HEADER_BYTES = 16384;
    static constexpr std::size_t MAX_BUFFERED_BYTES = 16384;
    static constexpr auto HTTP_READ_TIMEOUT = 10s;
    static constexpr auto HTTP_WRITE_TIMEOUT = 5s;
    static constexpr auto SHUTDOWN_TIMEOUT = 2s;
    static constexpr auto WEBSOCKET_HANDSHAKE_TIMEOUT = 10s;
    static constexpr auto WEBSOCKET_IDLE_TIMEOUT = 60s;
    static constexpr auto WEBSOCKET_WRITE_TIMEOUT = 10s;
};
