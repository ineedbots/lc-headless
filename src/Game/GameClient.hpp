#pragma once

#include "../Cache/GameCache_s.hpp"
#include "../Config/AccountConfig_s.hpp"
#include "../Config/Config_s.hpp"
#include "../Console/Logger.hpp"
#include "../Io/Connection.hpp"
#include "../Io/NetLoop.hpp"
#include "Decode/ServerPacketDecoder.hpp"
#include "InputTracker.hpp"
#include "Map/WorldMap.hpp"
#include "Net/ClientPacketWriter.hpp"
#include "Net/LoginHandshake.hpp"
#include "Net/LoginQueue.hpp"
#include "Net/RetrySchedule.hpp"
#include "Net/ServerPacketReader.hpp"
#include "Protocol/ClientPacket_s.hpp"
#include "Protocol/ClientPackets.hpp"
#include "Protocol/Protocol.hpp"
#include "Protocol/ServerProt.hpp"
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
    // Shared by clients that take turns at every login attempt; without one, each attempt starts when it's due.
    std::shared_ptr<LoginQueue> loginQueue;
};

// Single-threaded, and only waits when told to: Pump() does the work, waiting for data at most maxWait.
// Login() and Logout() are blocking conveniences over BeginLogin() and RequestLogout().
class GameClient
{
public:
    // A client made alone gets a loop of its own; AccountRunner gives every account the same one.
    GameClient(std::shared_ptr<const Config_s> config, std::shared_ptr<const GameCache_s> cache, AccountSettings_s account, std::shared_ptr<Logger> logger = Logger::GetDefault(), GameClientOptions_s options = {}, std::shared_ptr<NetLoop> net = NetLoop::Create());

    GameClient(const GameClient&) = delete;
    GameClient& operator=(const GameClient&) = delete;

    void BeginLogin();
    void Login();
    void Pump(std::chrono::milliseconds maxWait = 0ms);
    // Abandons a login or reconnect in progress.
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
    [[nodiscard]] const Protocol& GetProtocol() const;
    [[nodiscard]] const ClientPackets& GetPackets() const;

    // While a 225 server tracks input, each packet sent here also records the click that would have sent it.
    void Send(ClientPacket_s packet);
    void SendMove(MoveKind_e kind, std::span<const Tile_s> waypoints, bool run);
    // A send that fails counts as a dropped connection, as it does in Pump.
    void Flush();

private:
    using Clock = std::chrono::steady_clock;

    void PumpConnecting(std::chrono::milliseconds maxWait);
    void PumpSession(std::chrono::milliseconds maxWait);
    void StartAttempt();
    void AdvanceAttempt(std::chrono::milliseconds maxWait);
    void FinishLogin(const LoginResult_s& result);
    void LoseConnection(std::string_view reason);
    void BeginReconnect(std::string_view reason);
    [[nodiscard]] bool ScheduleRetry(std::string_view error, bool retryable);
    // The time an attempt due at earliest may start, after the turns of any clients ahead of it.
    [[nodiscard]] Clock::time_point TakeTurn(Clock::time_point earliest) const;
    [[nodiscard]] bool ContinueLogout();
    void ProcessInput();
    // Sends what a packet the decoder just read asks for in reply.
    void Reply(ServerProt_e prot);
    void WarnAboutStaleSquares();
    void SendReports(const std::vector<std::vector<u8>>& reports);
    void SendKeepaliveIfIdle();
    void LogNewMessages();

    std::shared_ptr<const Config_s> m_config;
    std::shared_ptr<const GameCache_s> m_cache;
    AccountSettings_s m_account;
    std::shared_ptr<Logger> m_logger;
    GameClientOptions_s m_options;
    // Declared before every member built from it.
    Protocol m_protocol;
    ClientPackets m_packets;

    // Declared before the connection, which needs it to outlive it.
    std::shared_ptr<NetLoop> m_net;
    // Resetting it closes the connection, and the close finishes on the loop without waiting.
    std::optional<Connection> m_connection;
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
    // Keyed by MapSquare::GetId, so each stale square is warned about once.
    std::unordered_set<u16> m_warnedSquares;
    InputTracker m_tracker;
    u32 m_loginCount = 0;

    std::optional<LoginHandshake> m_handshake;
    bool m_reconnecting = false;
    RetrySchedule m_retries;
    std::string m_lostReason;
    Clock::time_point m_attemptDeadline;

    std::chrono::milliseconds m_logoutTimeout{};
    Clock::time_point m_logoutDeadline;
    Clock::time_point m_nextLogoutClick;
};
