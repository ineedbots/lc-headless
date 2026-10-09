#pragma once

#include "../../Cache/GameCache_s.hpp"
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

// The login exchange on an open socket, one step at a time. Advance sends each request when its turn
// comes and reads each response once all of it has arrived, so it never waits; the caller owns the
// timeout. Bytes after the login response stay in the socket. The account, the login settings and the
// CRCs must outlive the handshake.
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

    LoginHandshake(const AccountSettings_s& account, const LoginSettings_s& login, std::span<const s32, GameCache_s::CRC_COUNT> crcs, bool reconnect);

    // The result once the server has accepted the login, or nullopt while a response is still on its
    // way. Throws LoginError when the server refuses.
    [[nodiscard]] std::optional<LoginResult_s> Advance(WebSocketClient& socket);
    [[nodiscard]] std::string_view GetWaitingFor() const;

    [[nodiscard]] static std::vector<u8> BuildSeedRequest(std::string_view username);
    [[nodiscard]] static std::vector<u8> BuildLoginRequest(const AccountSettings_s& account, const LoginSettings_s& login, std::span<const s32, GameCache_s::CRC_COUNT> crcs, std::span<const s32, LoginResult_s::SEED_SIZE> seed, bool reconnect);
    [[nodiscard]] static std::array<s32, LoginResult_s::SEED_SIZE> MakeSeed(s64 serverSeed);
    // The server-to-client cipher's seed: each word of the login seed plus 50.
    [[nodiscard]] static std::array<s32, LoginResult_s::SEED_SIZE> GetInboundSeed(std::span<const s32, LoginResult_s::SEED_SIZE> seed);

private:
    enum class Stage_e : u8
    {
        SendSeedRequest,
        SeedResponse,
        ServerSeed,
        LoginResponse,
        LoginDetails,
        HopTimer,
        Done,
    };

    [[nodiscard]] static std::optional<std::vector<u8>> TryReceive(WebSocketClient& socket, std::size_t count);

    const AccountSettings_s& m_account;
    const LoginSettings_s& m_login;
    std::span<const s32, GameCache_s::CRC_COUNT> m_crcs;
    bool m_reconnect;
    Stage_e m_stage = Stage_e::SendSeedRequest;
    LoginResult_s m_result;
};
