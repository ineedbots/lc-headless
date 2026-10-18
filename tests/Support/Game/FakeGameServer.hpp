#pragma once

#include "../Io/ServerThread.hpp"
#include "Cache/GameCache_s.hpp"
#include "Config/AccountConfig_s.hpp"
#include "Config/Config_s.hpp"
#include "Config/Revision_e.hpp"
#include "Config/ServerSettings_s.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Io/Isaac.hpp"
#include "Io/Packet.hpp"

#include <boost/asio/awaitable.hpp>
#include <boost/asio/ip/tcp.hpp>
#include <boost/beast/websocket/stream.hpp>

struct ReceivedPacket_s
{
    ClientProt_e prot;
    std::vector<u8> payload;
};

// One client's socket and the writes waiting for it, in order; a nullopt closes the connection. Touched only on the
// server's thread.
struct FakeServerClient_s
{
    explicit FakeServerClient_s(boost::asio::ip::tcp::socket tcp);

    boost::beast::websocket::stream<boost::asio::ip::tcp::socket> socket;
    std::deque<std::optional<std::vector<u8>>> outgoing;
    bool writing = false;
};

// A scripted game server on loopback, speaking one revision. The test config uses RSA exponent 1, so the
// login block arrives as plaintext and the server can seed both ISAAC streams the way the engine does.
// Like the 225 engine, a 225 server sends its seed as soon as the connection opens.
class FakeGameServer
{
public:
    using Script = std::function<void(FakeGameServer& server, bool reconnect)>;

    // Not the 289 cache's 2458, so a client that clicks a fixed id instead of its cache's fails.
    static constexpr u16 LOGOUT_COMPONENT = 1234;
    static constexpr auto USERNAME = "bot";
    static constexpr auto PASSWORD = "secret";

    explicit FakeGameServer(Script onLogin = {}, Revision_e revision = Revision_e::Rev289);
    ~FakeGameServer();

    FakeGameServer(const FakeGameServer&) = delete;
    FakeGameServer& operator=(const FakeGameServer&) = delete;

    [[nodiscard]] ServerSettings_s MakeServerSettings() const;
    [[nodiscard]] Revision_e GetRevision() const;
    [[nodiscard]] Config_s MakeConfig() const;
    [[nodiscard]] static AccountSettings_s MakeAccount();
    // An empty cache but for the logout button this server answers.
    [[nodiscard]] static std::shared_ptr<const GameCache_s> MakeCache(Revision_e revision = Revision_e::Rev289);

    // 225 also logs a staff account in, with 18.
    void SetLoginStatus(u8 status);
    // A stalled server accepts the connection but never sends the seed.
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
    using Client = std::shared_ptr<FakeServerClient_s>;

    enum class Stage_e : u8
    {
        SeedRequest,
        Login,
        InGame,
    };

    boost::asio::awaitable<void> Accept();
    boost::asio::awaitable<void> Serve(boost::asio::ip::tcp::socket socket);
    void OnMessage(const Client& client, std::span<const u8> bytes);
    void HandleSeedRequest(const Client& client, std::span<const u8> bytes);
    void SendSeed(const Client& client, bool withHeader);
    [[nodiscard]] bool ReadRevision(Packet& packet) const;
    [[nodiscard]] bool IsLoggedIn(u8 status) const;
    void HandleLogin(const Client& client, std::span<const u8> bytes);
    void HandleGamePackets(const Client& client, std::span<const u8> bytes);
    void SendLocked(ServerProt_e prot, std::span<const u8> payload);
    // Safe from any thread: the write is queued on the server's thread, in the order of the calls.
    void Write(const Client& client, std::optional<std::vector<u8>> bytes);
    static void WriteNext(const Client& client);
    void AddError(std::string error);

    template <typename TCondition>
    bool WaitFor(TCondition condition);

    Script m_onLogin;
    Revision_e m_revision;

    mutable std::mutex m_mutex;
    std::condition_variable m_changed;
    Stage_e m_stage = Stage_e::SeedRequest;
    std::optional<Isaac> m_fromClient;
    std::optional<Isaac> m_toClient;
    u8 m_loginStatus = 2;
    bool m_stalled = false;
    bool m_ignoreLogout = false;
    std::vector<u8> m_loginOpcodes;
    std::vector<ReceivedPacket_s> m_packets;
    std::vector<std::string> m_errors;

    // Before the acceptor and the clients, whose sockets need its io_context; the destructor stops it first.
    ServerThread m_thread;
    boost::asio::ip::tcp::acceptor m_acceptor;
    u16 m_port = 0;
    // The client in game, under m_mutex.
    Client m_client;
};
