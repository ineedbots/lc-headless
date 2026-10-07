#pragma once

#include "../../Core/ConfigFile.hpp"
#include "../../Io/WebSocketClient.hpp"

struct LoginResult_s
{
    static constexpr std::size_t SEED_SIZE = 4;

    bool reconnected = false;
    u8 staffLevel = 0;
    bool mouseTracking = false;
    std::array<s32, SEED_SIZE> seed{};
};

class LoginHandshake
{
public:
    static constexpr u8 SEED_REQUEST = 14;
    static constexpr u8 NORMAL_LOGIN = 16;
    static constexpr u8 RECONNECT_LOGIN = 18;
    static constexpr u8 STATUS_SEED_OK = 0;
    static constexpr u8 STATUS_LOGGED_IN = 2;
    static constexpr u8 STATUS_RECONNECTED = 15;
    static constexpr u8 STATUS_HOP_TIMER = 21;
    static constexpr u32 SERVER_SEED_OFFSET = 50;

    LoginHandshake() = delete;

    // Runs the login exchange on an open socket. Bytes after the login response stay in the socket.
    [[nodiscard]] static LoginResult_s Run(WebSocketClient& socket, const AccountSettings_s& account, const LoginSettings_s& login, bool reconnect, std::chrono::milliseconds timeout);

    [[nodiscard]] static std::vector<u8> BuildSeedRequest(std::string_view username);
    [[nodiscard]] static std::vector<u8> BuildLoginRequest(const AccountSettings_s& account, const LoginSettings_s& login, std::span<const s32, LoginResult_s::SEED_SIZE> seed, bool reconnect);
    [[nodiscard]] static std::array<s32, LoginResult_s::SEED_SIZE> MakeSeed(s64 serverSeed);
    // The server-to-client cipher's seed: each word of the login seed plus 50.
    [[nodiscard]] static std::array<s32, LoginResult_s::SEED_SIZE> GetInboundSeed(std::span<const s32, LoginResult_s::SEED_SIZE> seed);
};
