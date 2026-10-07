#pragma once

// The server answered a login with a status other than success.
class LoginError : public std::runtime_error
{
public:
    explicit LoginError(u8 status, std::string_view detail = {});

    [[nodiscard]] u8 GetStatus() const noexcept;
    [[nodiscard]] bool IsRetryable() const noexcept;

    [[nodiscard]] static std::string_view Describe(u8 status);

private:
    u8 m_status;
};
