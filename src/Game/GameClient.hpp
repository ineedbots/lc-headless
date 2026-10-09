#pragma once

#include "../Cache/GameCache_s.hpp"
#include "../Core/ConfigFile.hpp"
#include "../Core/Logger.hpp"
#include "../Io/WebSocketClient.hpp"
#include "Decode/ServerPacketDecoder.hpp"
#include "Map/WorldMap.hpp"
#include "Net/ClientPacketWriter.hpp"
#include "Net/LoginHandshake.hpp"
#include "Net/ServerPacketReader.hpp"
#include "Protocol/ClientPacket_s.hpp"
#include "Protocol/ClientPackets.hpp"
#include "State/GameState_s.hpp"
#include "Tile_s.hpp"

enum class ClientStatus_e : u8
{
    Disconnected,
    // Logging in, or reconnecting after the connection dropped.
    Connecting,
    InGame,
    LoggingOut,
    LoggedOut,
};

struct GameClientOptions_s
{
    bool autoReconnect = true;
    // Attempts at a login or a reconnect, enough with the doubling delay to ride out a server restart
    // of a couple of minutes. Only failures that trying again can fix are retried.
    u32 connectAttempts = 10;
    // The wait after the first failed attempt, doubling after each one up to maxRetryDelay.
    std::chrono::milliseconds retryDelay = 2s;
    std::chrono::milliseconds maxRetryDelay = 30s;
    std::chrono::milliseconds loginTimeout = 15s;
    std::chrono::milliseconds keepaliveInterval = 1s;
    std::chrono::milliseconds serverSilenceTimeout = 15s;
};

// A single-threaded game session that only waits when told to. The caller's loop drives it with Pump(),
// which advances a login or reconnect in progress, applies what the server sent, brings the map up to
// date with it, and sends the queued packets, waiting for data at most maxWait. State reads and sends
// happen on that same thread. Login() and Logout() are blocking conveniences over BeginLogin() and
// RequestLogout().
class GameClient
{
public:
    GameClient(std::shared_ptr<const Config_s> config, std::shared_ptr<const GameCache_s> cache, AccountSettings_s account, std::shared_ptr<Logger> logger = Logger::GetDefault(), GameClientOptions_s options = {});

    GameClient(const GameClient&) = delete;
    GameClient& operator=(const GameClient&) = delete;

    void BeginLogin();
    void Login();
    // Throws LoginError when a login is refused, ConnectionLostError when a dropped connection can't be
    // restored, and ProtocolError when the server's data can't be followed.
    void Pump(std::chrono::milliseconds maxWait = 0ms);
    // Clicks logout, and again every few seconds until the server agrees or the timeout passes. Abandons
    // a login or reconnect in progress.
    void RequestLogout(std::chrono::milliseconds timeout = 5s);
    void Logout(std::chrono::milliseconds timeout = 5s);
    void Disconnect() noexcept;

    [[nodiscard]] ClientStatus_e GetStatus() const;
    [[nodiscard]] bool IsInGame() const;
    // Counts successful logins and reconnects, so a change since the last look means a new connection.
    [[nodiscard]] u32 GetLoginCount() const;
    [[nodiscard]] const GameState_s& GetState() const;
    [[nodiscard]] GameState_s TakeSnapshot() const;
    [[nodiscard]] const GameCache_s& GetCache() const;
    [[nodiscard]] const WorldMap& GetMap() const;
    [[nodiscard]] Logger& GetLogger() const;

    void Send(ClientPacket_s packet);
    void SendMove(MoveKind_e kind, std::span<const Tile_s> waypoints, bool run);
    void Flush();

private:
    using Clock = std::chrono::steady_clock;

    void PumpConnecting(std::chrono::milliseconds maxWait);
    void PumpSession(std::chrono::milliseconds maxWait);
    void StartAttempt();
    void AdvanceAttempt(std::chrono::milliseconds maxWait);
    void FinishLogin(const LoginResult_s& result);
    void BeginReconnect(std::string_view reason);
    [[nodiscard]] bool ScheduleRetry(std::string_view error, bool retryable);
    [[nodiscard]] bool ContinueLogout();
    void ReleaseSocket() noexcept;
    void FreeClosedSockets() noexcept;
    void ProcessInput();
    void SendKeepaliveIfIdle();
    void LogNewMessages();

    std::shared_ptr<const Config_s> m_config;
    std::shared_ptr<const GameCache_s> m_cache;
    AccountSettings_s m_account;
    std::shared_ptr<Logger> m_logger;
    GameClientOptions_s m_options;

    std::unique_ptr<WebSocketClient> m_socket;
    // Connections being closed. IXWebSocket waits up to about 300 ms for a peer's close reply, so a
    // closed socket is set aside and freed once it reports Closed, rather than waited for.
    std::vector<std::unique_ptr<WebSocketClient>> m_closingSockets;
    std::optional<ServerPacketReader> m_reader;
    std::optional<ClientPacketWriter> m_writer;
    ServerPacketDecoder m_decoder;

    GameState_s m_state;
    WorldMap m_map;
    std::vector<ClientPacket_s> m_outgoing;
    ClientStatus_e m_status = ClientStatus_e::Disconnected;
    Clock::time_point m_lastReceive;
    Clock::time_point m_lastSend;
    u64 m_loggedMessageCount = 0;
    u32 m_loginCount = 0;

    std::optional<LoginHandshake> m_handshake;
    bool m_reconnecting = false;
    u32 m_attempt = 0;
    std::string m_lostReason;
    Clock::time_point m_attemptDeadline;
    std::optional<Clock::time_point> m_retryAt;

    std::chrono::milliseconds m_logoutTimeout{};
    Clock::time_point m_logoutDeadline;
    Clock::time_point m_nextLogoutClick;
};
