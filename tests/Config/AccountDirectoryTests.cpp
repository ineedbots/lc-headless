#include "pch.hpp"
#include "../Support/TempFolder.hpp"

#include "Config/AccountConfig_s.hpp"
#include "Config/AccountDirectory.hpp"
#include "Config/Error/ConfigError.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

namespace
{
    std::string MakeAccount(std::string_view username, bool enabled = true)
    {
        return std::format(R"json({{"username": "{}", "password": "pw", "enabled": {}}})json", username, enabled ? "true" : "false");
    }
}

TEST_CASE("AccountDirectory loads the enabled account files in name order", "[AccountDirectory]")
{
    const auto folder = TempFolder{"rs2004-account-directory-tests"};
    folder.WriteFile("zed.jsonc", MakeAccount("zed"));
    folder.WriteFile("alice.jsonc", MakeAccount("alice"));
    folder.WriteFile("off.jsonc", MakeAccount("off", false));
    folder.WriteFile("notes.txt", "not an account");
    folder.WriteFile("example.jsonc.sample", MakeAccount("sample"));

    const auto accounts = AccountDirectory::LoadEnabled(folder.GetPath());

    REQUIRE(accounts.size() == 2);
    CHECK(accounts[0].name == "alice");
    CHECK(accounts[0].file == folder.GetPath() / "alice.jsonc");
    CHECK(accounts[1].name == "zed");
}

TEST_CASE("AccountDirectory needs an enabled account", "[AccountDirectory]")
{
    const auto folder = TempFolder{"rs2004-account-directory-tests"};
    folder.WriteFile("off.jsonc", MakeAccount("off", false));

    CHECK_THROWS_AS(AccountDirectory::LoadEnabled(folder.GetPath()), ConfigError);
    CHECK_THROWS_WITH(AccountDirectory::LoadEnabled(folder.GetPath()), Catch::Matchers::EndsWith("no enabled account files"));
}

TEST_CASE("AccountDirectory rejects two files for one username, in any case", "[AccountDirectory]")
{
    const auto folder = TempFolder{"rs2004-account-directory-tests"};
    folder.WriteFile("first.jsonc", MakeAccount("Bot1"));
    folder.WriteFile("second.jsonc", MakeAccount("bot1"));

    CHECK_THROWS_WITH(AccountDirectory::LoadEnabled(folder.GetPath()), "Accounts first and second have the same username");
}

TEST_CASE("AccountDirectory ignores a disabled file's username", "[AccountDirectory]")
{
    const auto folder = TempFolder{"rs2004-account-directory-tests"};
    folder.WriteFile("first.jsonc", MakeAccount("bot1"));
    folder.WriteFile("second.jsonc", MakeAccount("bot1", false));

    CHECK(AccountDirectory::LoadEnabled(folder.GetPath()).size() == 1);
}
