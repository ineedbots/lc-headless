#include "pch.hpp"

#include "Config/AccountConfig_s.hpp"
#include "Config/ConfigOverrides.hpp"
#include "Config/Config_s.hpp"
#include "Config/ServerSettings_s.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("ConfigOverrides keeps client.jsonc's config for an account that replaces nothing", "[ConfigOverrides]")
{
    auto shared = Config_s{};
    shared.server.url = "ws://shared:80";
    const auto config = std::make_shared<const Config_s>(shared);

    CHECK(ConfigOverrides::ForAccount(config, AccountConfig_s{}) == config);
}

TEST_CASE("ConfigOverrides puts an account's server in place of client.jsonc's", "[ConfigOverrides]")
{
    auto shared = Config_s{};
    shared.server.url = "ws://shared:80";
    shared.scripting.scriptsDirectory = "shared-scripts";
    const auto config = std::make_shared<const Config_s>(shared);

    auto account = AccountConfig_s{};
    account.server = ServerSettings_s{.url = "wss://own:443", .origin = "https://own"};

    const auto own = ConfigOverrides::ForAccount(config, account);

    REQUIRE(own != config);
    CHECK(own->server.url == "wss://own:443");
    CHECK(own->server.origin == "https://own");
    CHECK(own->scripting.scriptsDirectory == "shared-scripts");
    CHECK(config->server.url == "ws://shared:80");
}
