#pragma once

#include <boost/asio/ssl/context.hpp>

// Which certificates a wss connection trusts, from server.tlsCaFile.
class TrustStore
{
public:
    static constexpr auto SYSTEM = "SYSTEM"sv;
    static constexpr auto NONE = "NONE"sv;

    TrustStore() = delete;

    // SYSTEM trusts the platform's roots, NONE verifies nothing, and anything else is a PEM bundle's path.
    static void Configure(boost::asio::ssl::context& context, const std::string& caFile);
    // How many roots it added: the Windows store's count, or 0 where OpenSSL finds them itself.
    static std::size_t LoadSystemRoots(boost::asio::ssl::context& context);
};
