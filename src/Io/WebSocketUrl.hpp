#pragma once

class WebSocketUrl
{
public:
    static constexpr auto SCHEME = "ws"sv;
    static constexpr auto SECURE_SCHEME = "wss"sv;

    WebSocketUrl() = delete;

    // Nullopt for text that isn't a URL.
    [[nodiscard]] static std::optional<std::string> GetScheme(const std::string& url);
    // A ws:// or wss:// URL.
    [[nodiscard]] static bool IsValid(const std::string& url);
};
