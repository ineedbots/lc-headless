#pragma once

#include "ServerThread.hpp"
#include "Io/Socks5Handshake.hpp"

#include <boost/asio/awaitable.hpp>
#include <boost/asio/ip/tcp.hpp>

struct Socks5Request_s
{
    Socks5AddressType_e type = Socks5AddressType_e::Ipv4;
    std::string host;
    u16 port = 0;
};

struct Socks5Credentials_s
{
    std::string username;
    std::string password;
};

// What the proxy has seen. Read through FakeSocks5Proxy::GetRecord, which copies it under the lock.
struct ProxyRecord_s
{
    std::size_t accepted = 0;
    std::vector<Socks5Request_s> requests;
    std::vector<Socks5Credentials_s> credentials;
};

// A SOCKS5 proxy on 127.0.0.1, on a port the system picks. After a success reply it connects to the target, over
// IPv4 only, and relays bytes both ways until either side closes. Settings apply to connections accepted after them.
class FakeSocks5Proxy
{
public:
    FakeSocks5Proxy();
    ~FakeSocks5Proxy();

    FakeSocks5Proxy(const FakeSocks5Proxy&) = delete;
    FakeSocks5Proxy& operator=(const FakeSocks5Proxy&) = delete;

    [[nodiscard]] u16 GetPort() const;
    [[nodiscard]] ProxyRecord_s GetRecord() const;

    // Requires these credentials; without them, only no authentication is offered.
    void SetCredentials(std::string username, std::string password);
    // The connect reply's code; success by default.
    void SetReply(u8 code);
    // The success reply's bound address type; IPv4 by default.
    void SetBoundAddress(Socks5AddressType_e type);
    // Accepts the connection and never answers the greeting.
    void SetStalled(bool stalled);
    // Sent in the same write as the success reply, standing in for a server that speaks first.
    void SetGreetingWithReply(std::vector<u8> bytes);

private:
    struct Settings_s
    {
        std::optional<Socks5Credentials_s> credentials;
        u8 reply = Socks5Handshake::SUCCEEDED;
        Socks5AddressType_e boundAddress = Socks5AddressType_e::Ipv4;
        bool stalled = false;
        std::vector<u8> greeting;
    };

    boost::asio::awaitable<void> Accept();
    boost::asio::awaitable<void> Serve(boost::asio::ip::tcp::socket client);
    boost::asio::awaitable<std::optional<Socks5Request_s>> Negotiate(boost::asio::ip::tcp::socket& client, const Settings_s& settings);
    void Record(const std::function<void(ProxyRecord_s&)>& change);

    mutable std::mutex m_mutex;
    Settings_s m_settings;
    ProxyRecord_s m_record;

    // Before the acceptor and the sockets, which need its io_context; the destructor stops it first.
    ServerThread m_thread;
    boost::asio::ip::tcp::acceptor m_acceptor;
    u16 m_port = 0;
    // Stalled connections, held open until the proxy goes. Touched only on the proxy's thread.
    std::vector<boost::asio::ip::tcp::socket> m_stalled;
};
