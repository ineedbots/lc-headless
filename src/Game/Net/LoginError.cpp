#include "pch.hpp"
#include "LoginError.hpp"

namespace
{
    struct LoginStatus_s
    {
        u8 status;
        std::string_view description;
        bool retryable;
    };

    constexpr auto STATUSES = std::to_array<LoginStatus_s>({
        {1, "server busy, try again in 2 seconds", true},
        {3, "invalid username or password", false},
        {4, "account disabled", false},
        {5, "account already logged in, or its last logout is still pending", true},
        {6, "revision, cache CRC or RSA key mismatch", false},
        {7, "world full or connection limit reached", true},
        {8, "login service unavailable", true},
        {9, "login limit exceeded", true},
        {10, "bad session ID", false},
        {11, "login rejected", true},
        {12, "members world, but the account is free-to-play", false},
        {13, "player save failed to load", true},
        {14, "server shutting down", true},
        {16, "too many login attempts, rate limited", true},
        {17, "standing in a members area on a free world", false},
        {20, "invalid login server", false},
        {21, "recently logged in to another world", true},
    });

    const LoginStatus_s* Find(u8 status)
    {
        const auto found = std::ranges::find(STATUSES, status, &LoginStatus_s::status);
        return found == STATUSES.end() ? nullptr : &*found;
    }

    std::string BuildMessage(u8 status, std::string_view detail)
    {
        auto message = std::format("Login failed with status {} ({})", status, LoginError::Describe(status));
        if (!detail.empty())
        {
            std::format_to(std::back_inserter(message), ": {}", detail);
        }

        return message;
    }
}

LoginError::LoginError(u8 status, std::string_view detail)
    : std::runtime_error{BuildMessage(status, detail)}
    , m_status{status}
{
}

u8 LoginError::GetStatus() const noexcept
{
    return m_status;
}

bool LoginError::IsRetryable() const noexcept
{
    const auto* const status = Find(m_status);
    return status != nullptr && status->retryable;
}

std::string_view LoginError::Describe(u8 status)
{
    const auto* const found = Find(status);
    if (found == nullptr)
    {
        return "unexpected response";
    }

    return found->description;
}
