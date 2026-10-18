#include "pch.hpp"

#include "Config/AccountConfig_s.hpp"
#include "Config/ConfigOverrides.hpp"
#include "Config/Config_s.hpp"
#include "Config/ProxySettings_s.hpp"
#include "Config/ServerSettings_s.hpp"
#include "Config/Transport_e.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("ConfigOverrides keeps client.jsonc's config for an account that replaces nothing", "[ConfigOverrides]")
{
    auto shared = Config_s{};
    shared.server.host = "shared";
    const auto config = std::make_shared<const Config_s>(shared);

    CHECK(ConfigOverrides::ForAccount(config, AccountConfig_s{}) == config);
}

TEST_CASE("ConfigOverrides puts an account's server in place of client.jsonc's", "[ConfigOverrides]")
{
    auto shared = Config_s{};
    shared.server.host = "shared";
    shared.scripting.scriptsDirectory = "shared-scripts";
    const auto config = std::make_shared<const Config_s>(shared);

    auto account = AccountConfig_s{};
    account.server = ServerSettings_s{.transport = Transport_e::Wss, .host = "own", .port = 443, .origin = "https://own"};

    const auto own = ConfigOverrides::ForAccount(config, account);

    REQUIRE(own != config);
    CHECK(own->server.transport == Transport_e::Wss);
    CHECK(own->server.host == "own");
    CHECK(own->server.port == 443);
    CHECK(own->server.origin == "https://own");
    CHECK(own->scripting.scriptsDirectory == "shared-scripts");
    CHECK(config->server.host == "shared");
}

TEST_CASE("ConfigOverrides puts an account's proxy in place of client.jsonc's", "[ConfigOverrides]")
{
    auto shared = Config_s{};
    shared.server.host = "shared";
    shared.proxy.host = "shared-proxy";
    const auto config = std::make_shared<const Config_s>(shared);

    SECTION("its own proxy")
    {
        auto account = AccountConfig_s{};
        account.proxy = ProxySettings_s{.host = "own-proxy", .port = 9050};

        const auto own = ConfigOverrides::ForAccount(config, account);
        REQUIRE(own != config);
        CHECK(own->proxy.host == "own-proxy");
        CHECK(own->proxy.port == 9050);
        CHECK(own->server.host == "shared");
        CHECK(config->proxy.host == "shared-proxy");
    }

    SECTION("an empty host connects that account directly")
    {
        auto account = AccountConfig_s{};
        account.proxy = ProxySettings_s{};
        CHECK(ConfigOverrides::ForAccount(config, account)->proxy.host.empty());
    }

    SECTION("both at once")
    {
        auto account = AccountConfig_s{};
        account.server = ServerSettings_s{.host = "own", .port = 80};
        account.proxy = ProxySettings_s{.host = "own-proxy"};

        const auto own = ConfigOverrides::ForAccount(config, account);
        CHECK(own->server.host == "own");
        CHECK(own->proxy.host == "own-proxy");
    }
}
