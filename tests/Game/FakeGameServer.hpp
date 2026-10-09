#pragma once

#include "Cache/GameCache_s.hpp"
#include "Core/ConfigFile.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Io/Isaac.hpp"
#include "Io/NetSystem.hpp"

#include <ixwebsocket/IXWebSocket.h>
#include <ixwebsocket/IXWebSocketMessage.h>
#include <ixwebsocket/IXWebSocketServer.h>

struct ReceivedPacket_s
{
    ClientProt_e prot;
    std::vector<u8> payload;
};

// A scripted game server on loopback. The test config uses RSA exponent 1, so the login block
// arrives as plaintext and the server can seed both ISAAC streams the way the engine does.
class FakeGameServer
{
public:
    using Script = std::function<void(FakeGameServer& server, bool reconnect)>;

    // Not the 289 cache's 2458, so a client that clicks a fixed id instead of its cache's fails.
    static constexpr u16 LOGOUT_COMPONENT = 1234;
    static constexpr auto USERNAME = "bot";
    static constexpr auto PASSWORD = "secret";

    explicit FakeGameServer(Script onLogin = {});
    ~FakeGameServer();

    FakeGameServer(const FakeGameServer&) = delete;
    FakeGameServer& operator=(const FakeGameServer&) = delete;

    [[nodiscard]] std::string Url() const;
    [[nodiscard]] Config_s MakeConfig() const;
    [[nodiscard]] static AccountSettings_s MakeAccount();
    // An empty cache but for the logout button this server answers.
    [[nodiscard]] static std::shared_ptr<const GameCache_s> MakeCache();

    void SetLoginStatus(u8 status);
    // A stalled server accepts the connection but never answers the seed request.
    void SetStalled(bool stalled);
    // Clicks on the logout button are recorded but not answered, as during combat.
    void SetIgnoreLogout(bool ignore);
    void Send(ServerProt_e prot, std::span<const u8> payload = {});
    void Close();

    [[nodiscard]] bool WaitForPacket(ClientProt_e prot, std::size_t count = 1);
    [[nodiscard]] bool WaitForLogins(std::size_t count);
    [[nodiscard]] std::vector<ReceivedPacket_s> GetPackets(ClientProt_e prot) const;
    [[nodiscard]] std::vector<u8> GetLoginOpcodes() const;
    [[nodiscard]] std::vector<std::string> GetErrors() const;

private:
    enum class Stage_e : u8
    {
        SeedRequest,
        Login,
        InGame,
    };

    void OnMessage(ix::WebSocket& connection, const ix::WebSocketMessage& message);
    void HandleSeedRequest(ix::WebSocket& connection, std::span<const u8> bytes);
    void HandleLogin(ix::WebSocket& connection, std::span<const u8> bytes);
    void HandleGamePackets(ix::WebSocket& connection, std::span<const u8> bytes);
    void SendLocked(ServerProt_e prot, std::span<const u8> payload);
    void AddError(std::string error);

    template <typename TCondition>
    bool WaitFor(TCondition condition);

    NetSystem m_netSystem;
    Script m_onLogin;

    // Recursive because IXWebSocket can deliver a connection's Close on the thread that's sending to
    // it, inside sendBinary, and SendLocked holds the lock to keep the connection alive while it sends.
    mutable std::recursive_mutex m_mutex;
    std::condition_variable_any m_changed;
    ix::WebSocket* m_connection = nullptr;
    Stage_e m_stage = Stage_e::SeedRequest;
    std::optional<Isaac> m_fromClient;
    std::optional<Isaac> m_toClient;
    u8 m_loginStatus = 2;
    bool m_stalled = false;
    bool m_ignoreLogout = false;
    std::vector<u8> m_loginOpcodes;
    std::vector<ReceivedPacket_s> m_packets;
    std::vector<std::string> m_errors;

    std::unique_ptr<ix::WebSocketServer> m_server;
};
