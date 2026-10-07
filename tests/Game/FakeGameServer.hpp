#pragma once

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

    static constexpr u16 LOGOUT_COMPONENT = 2458;
    static constexpr auto USERNAME = "bot";
    static constexpr auto PASSWORD = "secret";

    explicit FakeGameServer(Script onLogin = {});
    ~FakeGameServer();

    FakeGameServer(const FakeGameServer&) = delete;
    FakeGameServer& operator=(const FakeGameServer&) = delete;

    [[nodiscard]] std::string Url() const;
    [[nodiscard]] Config_s MakeConfig() const;

    void SetLoginStatus(u8 status);
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

    mutable std::mutex m_mutex;
    std::condition_variable m_changed;
    ix::WebSocket* m_connection = nullptr;
    Stage_e m_stage = Stage_e::SeedRequest;
    std::optional<Isaac> m_fromClient;
    std::optional<Isaac> m_toClient;
    u8 m_loginStatus = 2;
    std::vector<u8> m_loginOpcodes;
    std::vector<ReceivedPacket_s> m_packets;
    std::vector<std::string> m_errors;

    std::unique_ptr<ix::WebSocketServer> m_server;
};
