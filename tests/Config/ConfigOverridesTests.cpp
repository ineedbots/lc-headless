#include "pch.hpp"

#include "Config/AccountConfig_s.hpp"
#include "Config/ConfigOverrides.hpp"
#include "Config/Config_s.hpp"
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
