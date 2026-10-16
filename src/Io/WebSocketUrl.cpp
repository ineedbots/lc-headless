#include "pch.hpp"
#include "WebSocketUrl.hpp"

#include <ixwebsocket/IXUrlParser.h>

std::optional<std::string> WebSocketUrl::GetScheme(const std::string& url)
{
    auto protocol = std::string{};
    auto host = std::string{};
    auto path = std::string{};
    auto query = std::string{};
    auto port = 0;
    if (!ix::UrlParser::parse(url, protocol, host, path, query, port))
    {
        return std::nullopt;
    }

    return protocol;
}

bool WebSocketUrl::IsValid(const std::string& url)
{
    const auto scheme = GetScheme(url);
    return scheme == SCHEME || scheme == SECURE_SCHEME;
}
