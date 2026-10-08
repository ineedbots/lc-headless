#include "pch.hpp"

#include "Script/BotMessenger.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("BotMessenger delivers to the account with that username, in any case", "[BotMessenger]")
{
    auto messenger = BotMessenger{};
    auto received = std::vector<BotMessage_s>{};
    auto accepting = true;
    messenger.Register("Mule1", [&received, &accepting](BotMessage_s message)
    {
        if (!accepting)
        {
            return false;
        }

        received.push_back(std::move(message));
        return true;
    });

    CHECK(messenger.Send("mule1", BotMessage_s{.sender = "bot1", .json = "{\"x\": 1}"}) == std::optional{true});
    CHECK(messenger.Send("MULE1", BotMessage_s{.sender = "bot2", .json = "2"}) == std::optional{true});
    REQUIRE(received.size() == 2);
    CHECK(received[0].sender == "bot1");
    CHECK(received[0].json == "{\"x\": 1}");
    CHECK(received[1].sender == "bot2");

    SECTION("a receiver can turn a message down")
    {
        accepting = false;
        CHECK(messenger.Send("mule1", BotMessage_s{.sender = "bot1", .json = "3"}) == std::optional{false});
        CHECK(received.size() == 2);
    }

    SECTION("an unknown username isn't sent anywhere")
    {
        CHECK_FALSE(messenger.Send("mule2", BotMessage_s{.sender = "bot1", .json = "3"}).has_value());
    }

    SECTION("an account that unregistered is unknown")
    {
        messenger.Unregister("MULE1");
        CHECK_FALSE(messenger.Send("mule1", BotMessage_s{.sender = "bot1", .json = "3"}).has_value());
    }
}
