#include "pch.hpp"

#include "Io/Socks5Handshake.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

namespace
{
    using Bytes = std::vector<u8>;

    Bytes ToBytes(std::string_view text)
    {
        return {text.begin(), text.end()};
    }

    Bytes Join(std::initializer_list<Bytes> parts)
    {
        auto joined = Bytes{};
        for (const auto& part : parts)
        {
            joined.insert(joined.end(), part.begin(), part.end());
        }

        return joined;
    }

    template <std::size_t SIZE>
    std::array<u8, SIZE> Reply(std::array<u8, SIZE> bytes)
    {
        return bytes;
    }

    template <typename TAction>
    std::string GetMessage(TAction action)
    {
        try
        {
            action();
        }
        catch (const std::exception& e)
        {
            return e.what();
        }

        return "";
    }
}

TEST_CASE("Socks5Handshake builds the greeting", "[Socks5]")
{
    CHECK(Socks5Handshake::BuildGreeting(false) == Bytes{0x05, 0x01, 0x00});
    CHECK(Socks5Handshake::BuildGreeting(true) == Bytes{0x05, 0x02, 0x00, 0x02});
}

TEST_CASE("Socks5Handshake builds the password request", "[Socks5]")
{
    CHECK(Socks5Handshake::BuildPasswordRequest("user", "pass") == Join({{0x01, 0x04}, ToBytes("user"), {0x04}, ToBytes("pass")}));

    const auto longest = std::string(255, 'u');
    const auto request = Socks5Handshake::BuildPasswordRequest(longest, longest);
    CHECK(request.size() == 1 + 1 + 255 + 1 + 255);
    CHECK(request[1] == 255);

    // The other field is a secret too, so neither value may reach the message.
    const auto tooLong = std::string(256, 'x');
    for (const auto& [username, password] : {std::pair{""s, "s3cret"s}, {"b0tuser"s, ""s}, {tooLong, "s3cret"s}, {"b0tuser"s, tooLong}})
    {
        CHECK_THROWS_AS(Socks5Handshake::BuildPasswordRequest(username, password), std::invalid_argument);

        const auto message = GetMessage([&]
        {
            static_cast<void>(Socks5Handshake::BuildPasswordRequest(username, password));
        });
        CHECK_THAT(message, !Catch::Matchers::ContainsSubstring("b0tuser") && !Catch::Matchers::ContainsSubstring("s3cret") && !Catch::Matchers::ContainsSubstring("xxx"));
    }
}

TEST_CASE("Socks5Handshake builds the connect request", "[Socks5]")
{
    SECTION("a name goes to the proxy to resolve")
    {
        CHECK(Socks5Handshake::BuildConnectRequest("example.com", 443) == Join({{0x05, 0x01, 0x00, 0x03, 0x0B}, ToBytes("example.com"), {0x01, 0xBB}}));
    }

    SECTION("an IPv4 literal goes as an address")
    {
        CHECK(Socks5Handshake::BuildConnectRequest("127.0.0.1", 80) == Bytes{0x05, 0x01, 0x00, 0x01, 0x7F, 0x00, 0x00, 0x01, 0x00, 0x50});
        CHECK(Socks5Handshake::BuildConnectRequest("255.255.255.255", 43594) == Bytes{0x05, 0x01, 0x00, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0xAA, 0x4A});
    }

    SECTION("hosts that only look like IPv4 literals go as names")
    {
        for (const auto* host : {"1.2.3", "1.2.3.4.5", "256.1.1.1", "1.2.3.x", " 1.2.3.4", "1.2.3.4 ", "-1.2.3.4", "1..2.3"})
        {
            const auto request = Socks5Handshake::BuildConnectRequest(host, 80);
            CHECK(request[3] == 0x03);
            CHECK(request[4] == std::string_view{host}.size());
        }
    }

    SECTION("a name of 255 bytes fits, and longer throws")
    {
        CHECK(Socks5Handshake::BuildConnectRequest(std::string(255, 'a'), 80).size() == 5 + 255 + 2);
        CHECK_THROWS_AS(Socks5Handshake::BuildConnectRequest(std::string(256, 'a'), 80), std::invalid_argument);
        CHECK_THROWS_AS(Socks5Handshake::BuildConnectRequest("", 80), std::invalid_argument);
    }
}

TEST_CASE("Socks5Handshake parses the method reply", "[Socks5]")
{
    CHECK(Socks5Handshake::ParseMethodReply(Reply<2>({0x05, 0x00}), false) == Socks5Method_e::NoAuthentication);
    CHECK(Socks5Handshake::ParseMethodReply(Reply<2>({0x05, 0x00}), true) == Socks5Method_e::NoAuthentication);
    CHECK(Socks5Handshake::ParseMethodReply(Reply<2>({0x05, 0x02}), true) == Socks5Method_e::UsernamePassword);

    const auto failure = [](std::array<u8, 2> reply, bool withPassword)
    {
        return GetMessage([&]
        {
            static_cast<void>(Socks5Handshake::ParseMethodReply(reply, withPassword));
        });
    };

    CHECK_THAT(failure({0x04, 0x00}, false), Catch::Matchers::StartsWith("not a SOCKS5 proxy"));
    CHECK(failure({0x05, 0xFF}, true) == "accepts none of the offered authentication methods");
    CHECK(failure({0x05, 0xFF}, false) == "accepts none of the offered authentication methods; it may need a username and password");
    CHECK(failure({0x05, 0x02}, false) == "chose an authentication method that wasn't offered");
    CHECK(failure({0x05, 0x01}, true) == "chose an authentication method that wasn't offered");
    CHECK_THROWS_AS(Socks5Handshake::ParseMethodReply(Reply<2>({0x05, 0x01}), true), std::runtime_error);
}

TEST_CASE("Socks5Handshake parses the password reply", "[Socks5]")
{
    CHECK_NOTHROW(Socks5Handshake::ParsePasswordReply(Reply<2>({0x01, 0x00})));
    CHECK_NOTHROW(Socks5Handshake::ParsePasswordReply(Reply<2>({0x05, 0x00})));

    const auto message = GetMessage([]
    {
        Socks5Handshake::ParsePasswordReply(Reply<2>({0x01, 0x01}));
    });
    CHECK(message == "rejected the username or password");
}

TEST_CASE("Socks5Handshake parses the connect reply", "[Socks5]")
{
    SECTION("the bound address types")
    {
        CHECK(Socks5Handshake::ParseConnectReply(Reply<4>({0x05, 0x00, 0x00, 0x01})) == Socks5AddressType_e::Ipv4);
        CHECK(Socks5Handshake::ParseConnectReply(Reply<4>({0x05, 0x00, 0x00, 0x03})) == Socks5AddressType_e::DomainName);
        CHECK(Socks5Handshake::ParseConnectReply(Reply<4>({0x05, 0x00, 0x00, 0x04})) == Socks5AddressType_e::Ipv6);
        CHECK_THROWS_AS(Socks5Handshake::ParseConnectReply(Reply<4>({0x05, 0x00, 0x00, 0x02})), std::runtime_error);
        CHECK_THROWS_AS(Socks5Handshake::ParseConnectReply(Reply<4>({0x04, 0x00, 0x00, 0x01})), std::runtime_error);
    }

    SECTION("each failure names its reply")
    {
        const auto expected = std::array{
            "general SOCKS server failure (reply 1)"s,
            "connection not allowed by ruleset (reply 2)"s,
            "network unreachable (reply 3)"s,
            "host unreachable (reply 4)"s,
            "connection refused (reply 5)"s,
            "TTL expired (reply 6)"s,
            "command not supported (reply 7)"s,
            "address type not supported (reply 8)"s,
            "unknown reply (reply 9)"s,
        };

        for (auto code = std::size_t{1}; code <= expected.size(); ++code)
        {
            const auto message = GetMessage([code]
            {
                static_cast<void>(Socks5Handshake::ParseConnectReply(Reply<4>({0x05, static_cast<u8>(code), 0x00, 0x01})));
            });
            CHECK(message == expected[code - 1]);
        }
    }
}

TEST_CASE("Socks5Handshake sizes the bound address", "[Socks5]")
{
    CHECK(Socks5Handshake::GetBoundAddressSize(Socks5AddressType_e::Ipv4, 0) == 6);
    CHECK(Socks5Handshake::GetBoundAddressSize(Socks5AddressType_e::Ipv6, 0) == 18);
    CHECK(Socks5Handshake::GetBoundAddressSize(Socks5AddressType_e::DomainName, 7) == 9);
}
