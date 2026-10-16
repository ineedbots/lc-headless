#include "pch.hpp"

#include "Io/WebSocketUrl.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("WebSocketUrl reads the scheme", "[WebSocketUrl]")
{
    CHECK(WebSocketUrl::GetScheme("wss://w1.2004scape.org:43595") == "wss");
    CHECK(WebSocketUrl::GetScheme("ws://localhost:8888") == "ws");
    CHECK(WebSocketUrl::GetScheme("https://2004scape.org") == "https");
    CHECK_FALSE(WebSocketUrl::GetScheme("not a url"));
}

TEST_CASE("WebSocketUrl takes only ws:// and wss:// URLs", "[WebSocketUrl]")
{
    CHECK(WebSocketUrl::IsValid("wss://w1.2004scape.org:43595"));
    CHECK(WebSocketUrl::IsValid("ws://localhost:8888"));
    CHECK_FALSE(WebSocketUrl::IsValid("https://2004scape.org"));
    CHECK_FALSE(WebSocketUrl::IsValid(""));
}
