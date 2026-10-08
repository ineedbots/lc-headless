#include "pch.hpp"
#include "LoginHandshake.hpp"

#include "../../Core/ConfigFile.hpp"
#include "../../Io/Packet.hpp"
#include "../../Io/WebSocketClient.hpp"
#include "../Protocol/Base37.hpp"
#include "LoginError.hpp"

namespace
{
    constexpr auto SEED_HEADER_SIZE = std::size_t{8};
    constexpr auto SERVER_SEED_SIZE = std::size_t{8};
    constexpr auto LOGIN_DETAILS_SIZE = std::size_t{2};
    constexpr auto RSA_MARKER = 10;
    constexpr auto CLIENT_UID = 1337;
    constexpr auto REVISION_MARKER = 0xFF;
    constexpr auto LOGIN_SERVER_SHIFT = 16;
    constexpr auto LOGIN_SERVER_MASK = u64{0x1F};
    constexpr auto MAX_RANDOM_SEED = 99999999;
    constexpr auto MAX_BODY_SIZE = std::size_t{255};
    constexpr auto WORD_BITS = 32;

    std::vector<u8> ToVector(std::span<const u8> bytes)
    {
        return {bytes.begin(), bytes.end()};
    }
}

LoginHandshake::LoginHandshake(const AccountSettings_s& account, const LoginSettings_s& login, bool reconnect)
    : m_account{account}
    , m_login{login}
    , m_reconnect{reconnect}
{
}

std::optional<LoginResult_s> LoginHandshake::Advance(WebSocketClient& socket)
{
    while (true)
    {
        switch (m_stage)
        {
        case Stage_e::SendSeedRequest:
            socket.Send(BuildSeedRequest(m_account.username));
            m_stage = Stage_e::SeedResponse;
            break;
        case Stage_e::SeedResponse:
        {
            const auto header = TryReceive(socket, SEED_HEADER_SIZE + 1);
            if (!header)
            {
                return std::nullopt;
            }

            if (header->back() != STATUS_SEED_OK)
            {
                throw LoginError{header->back()};
            }

            m_stage = Stage_e::ServerSeed;
            break;
        }
        case Stage_e::ServerSeed:
        {
            const auto serverSeed = TryReceive(socket, SERVER_SEED_SIZE);
            if (!serverSeed)
            {
                return std::nullopt;
            }

            m_result.seed = MakeSeed(Packet{*serverSeed}.G8());
            socket.Send(BuildLoginRequest(m_account, m_login, m_result.seed, m_reconnect));
            m_stage = Stage_e::LoginResponse;
            break;
        }
        case Stage_e::LoginResponse:
        {
            const auto response = TryReceive(socket, 1);
            if (!response)
            {
                return std::nullopt;
            }

            const auto status = response->front();
            if (status == STATUS_RECONNECTED)
            {
                m_result.reconnected = true;
                m_stage = Stage_e::Done;
                return m_result;
            }

            if (status == STATUS_LOGGED_IN)
            {
                m_stage = Stage_e::LoginDetails;
                break;
            }

            if (status == STATUS_HOP_TIMER)
            {
                m_stage = Stage_e::HopTimer;
                break;
            }

            throw LoginError{status};
        }
        case Stage_e::LoginDetails:
        {
            const auto details = TryReceive(socket, LOGIN_DETAILS_SIZE);
            if (!details)
            {
                return std::nullopt;
            }

            m_result.staffLevel = (*details)[0];
            m_result.mouseTracking = (*details)[1] == 1;
            m_stage = Stage_e::Done;
            return m_result;
        }
        case Stage_e::HopTimer:
        {
            const auto seconds = TryReceive(socket, 1);
            if (!seconds)
            {
                return std::nullopt;
            }

            throw LoginError{STATUS_HOP_TIMER, std::format("{} seconds left", seconds->front())};
        }
        case Stage_e::Done:
            return m_result;
        }
    }
}

std::string_view LoginHandshake::GetWaitingFor() const
{
    switch (m_stage)
    {
    case Stage_e::SendSeedRequest:
    case Stage_e::SeedResponse:
        return "seed response";
    case Stage_e::ServerSeed:
        return "server seed";
    case Stage_e::LoginResponse:
        return "login response";
    case Stage_e::LoginDetails:
        return "staff level and mouse tracking flag";
    case Stage_e::HopTimer:
        return "hop timer";
    case Stage_e::Done:
        return "nothing";
    }

    assert(false && "Unhandled login stage");
    return "login";
}

std::vector<u8> LoginHandshake::BuildSeedRequest(std::string_view username)
{
    // The engine ignores the login-server byte, but it's derived the way the webclient derives it.
    const auto loginServer = (Base37::Encode(username) >> LOGIN_SERVER_SHIFT) & LOGIN_SERVER_MASK;
    auto packet = Packet{};
    packet.P1(SEED_REQUEST);
    packet.P1(static_cast<s32>(loginServer));
    return ToVector(packet.GetData());
}

std::vector<u8> LoginHandshake::BuildLoginRequest(const AccountSettings_s& account, const LoginSettings_s& login, std::span<const s32, LoginResult_s::SEED_SIZE> seed, bool reconnect)
{
    auto block = Packet{};
    block.P1(RSA_MARKER);
    for (const auto word : seed)
    {
        block.P4(word);
    }

    block.P4(CLIENT_UID);
    block.PJStr(account.username);
    block.PJStr(account.password);
    block.RsaEnc(login.rsaModulus, login.rsaExponent);

    auto packet = Packet{};
    packet.P1(reconnect ? RECONNECT_LOGIN : NORMAL_LOGIN);
    packet.P1(0);
    const auto bodyStart = packet.GetPos();
    packet.P1(REVISION_MARKER);
    packet.P2(login.revision);
    packet.P1(login.lowMemory ? 1 : 0);
    for (const auto crc : login.crcs)
    {
        packet.P4(crc);
    }

    packet.PData(block.GetData());

    const auto bodySize = packet.GetPos() - bodyStart;
    if (bodySize > MAX_BODY_SIZE)
    {
        throw std::length_error{std::format("Login body is {} bytes, more than a 1-byte length can hold", bodySize)};
    }

    packet.PSize1(bodySize);
    return ToVector(packet.GetData());
}

std::array<s32, LoginResult_s::SEED_SIZE> LoginHandshake::MakeSeed(s64 serverSeed)
{
    auto random = std::random_device{};
    auto distribution = std::uniform_int_distribution<s32>{0, MAX_RANDOM_SEED};
    const auto first = distribution(random);
    const auto second = distribution(random);
    return {first, second, static_cast<s32>(serverSeed >> WORD_BITS), static_cast<s32>(serverSeed)};
}

std::array<s32, LoginResult_s::SEED_SIZE> LoginHandshake::GetInboundSeed(std::span<const s32, LoginResult_s::SEED_SIZE> seed)
{
    auto inbound = std::array<s32, LoginResult_s::SEED_SIZE>{};
    for (std::size_t i = 0; i < inbound.size(); ++i)
    {
        inbound[i] = static_cast<s32>(static_cast<u32>(seed[i]) + SERVER_SEED_OFFSET);
    }

    return inbound;
}

std::optional<std::vector<u8>> LoginHandshake::TryReceive(WebSocketClient& socket, std::size_t count)
{
    if (socket.Available() < count)
    {
        return std::nullopt;
    }

    auto bytes = std::vector<u8>(count);
    socket.Read(bytes);
    return bytes;
}
