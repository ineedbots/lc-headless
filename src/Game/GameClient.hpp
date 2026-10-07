#pragma once

#include "../Core/ConfigFile.hpp"
#include "../Core/Logger.hpp"
#include "../Io/WebSocketClient.hpp"
#include "Decode/ServerPacketDecoder.hpp"
#include "Net/ClientPacketWriter.hpp"
#include "Net/ServerPacketReader.hpp"
#include "Protocol/ClientPacket_s.hpp"
#include "Protocol/ClientPackets.hpp"
#include "State/GameState_s.hpp"
#include "Tile_s.hpp"

enum class ClientStatus_e : u8
{
    Disconnected,
    InGame,
    LoggingOut,
    LoggedOut,
};

struct GameClientOptions_s
{
    bool autoReconnect = true;
    u32 reconnectAttempts = 3;
    std::chrono::milliseconds reconnectDelay = 2s;
    std::chrono::milliseconds loginTimeout = 15s;
    std::chrono::milliseconds keepaliveInterval = 1s;
    std::chrono::milliseconds serverSilenceTimeout = 15s;
};

// A single-threaded game session. The caller's loop drives it with Pump(); state reads and packet
// sends happen on that same thread. Queued packets go out together at the end of each Pump().
class GameClient
{
public:
    explicit GameClient(std::shared_ptr<const Config_s> config, std::shared_ptr<Logger> logger = Logger::GetDefault(), GameClientOptions_s options = {});

    GameClient(const GameClient&) = delete;
    GameClient& operator=(const GameClient&) = delete;

    void Login();
    void Pump(std::chrono::milliseconds maxWait = 0ms);
    void Logout(std::chrono::milliseconds timeout = 5s);
    void Disconnect() noexcept;

    [[nodiscard]] ClientStatus_e GetStatus() const;
    [[nodiscard]] bool IsInGame() const;
    [[nodiscard]] const GameState_s& GetState() const;
    [[nodiscard]] GameState_s TakeSnapshot() const;

    void Send(ClientPacket_s packet);
    void SendMove(MoveKind_e kind, std::span<const Tile_s> waypoints, bool run);
    void Flush();

private:
    using Clock = std::chrono::steady_clock;

    void Connect(bool reconnect);
    void ProcessInput();
    void Reconnect(std::string_view reason);
    void SendKeepaliveIfIdle();
    void LogNewMessages();

    std::shared_ptr<const Config_s> m_config;
    std::shared_ptr<Logger> m_logger;
    GameClientOptions_s m_options;

    WebSocketClient m_socket;
    std::optional<ServerPacketReader> m_reader;
    std::optional<ClientPacketWriter> m_writer;
    ServerPacketDecoder m_decoder;

    GameState_s m_state;
    std::vector<ClientPacket_s> m_outgoing;
    ClientStatus_e m_status = ClientStatus_e::Disconnected;
    Clock::time_point m_lastReceive;
    Clock::time_point m_lastSend;
    u64 m_loggedMessageCount = 0;
};
