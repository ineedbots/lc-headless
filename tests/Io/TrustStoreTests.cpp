#include "pch.hpp"

#include "Io/TrustStore.hpp"

#include <boost/asio/ssl/context.hpp>
#include <catch2/catch_test_macros.hpp>

#ifdef _WIN32
TEST_CASE("TrustStore loads the Windows root store", "[TrustStore]")
{
    auto context = boost::asio::ssl::context{boost::asio::ssl::context::tls_client};
    CHECK(TrustStore::LoadSystemRoots(context) > 0);
}
#endif
