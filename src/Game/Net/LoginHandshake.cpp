#include "pch.hpp"
#include "LoginHandshake.hpp"

#include "../../Core/ConfigFile.hpp"
#include "../../Io/Packet.hpp"
#include "../../Io/WebSocketClient.hpp"
#include "../Protocol/Base37.hpp"
#include "LoginError.hpp"

namespace
{
    using Clock = std::chrono::steady_clock;

    constexpr auto SEED_HEADER_SIZE = std::size_t{8};
    constexpr auto SERVER_SEED_SIZE = std::size_t{8};
    constexpr auto RSA_MARKER = 10;
    constexpr auto CLIENT_UID = 1337;
    constexpr auto REVISION_MARKER = 0xFF;
    constexpr auto LOGIN_SERVER_SHIFT = 16;
    constexpr auto LOGIN_SERVER_MASK = u64{0x1F};
    constexpr auto MAX_RANDOM_SEED = 99999999;
    constexpr auto MAX_BODY_SIZE = std::size_t{255};
    constexpr auto WORD_BITS = 32;

    std::vector<u8> Receive(WebSocketClient& socket, std::size_t count, Clock::time_point deadline, std::string_view what)
    {
        const auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(deadline - Clock::now());
        if (!socket.WaitAvailable(count, std::max(remaining, 0ms)))
        {
            throw std::runtime_error{std::format("Login timed out waiting for the {}", what)};
        }

        auto bytes = std::vector<u8>(count);
        socket.Read(bytes);
        return bytes;
    }

    std::vector<u8> ToVector(std::span<const u8> bytes)
    {
        return {bytes.begin(), bytes.end()};
    }
}

LoginResult_s LoginHandshake::Run(WebSocketClient& socket, const AccountSettings_s& account, const LoginSettings_s& login, bool reconnect, std::chrono::milliseconds timeout)
{
    const auto deadline = Clock::now() + timeout;

    socket.Send(BuildSeedRequest(account.username));
    const auto seedStatus = Receive(socket, SEED_HEADER_SIZE + 1, deadline, "seed response").back();
    if (seedStatus != STATUS_SEED_OK)
    {
        throw LoginError{seedStatus};
    }

    const auto serverSeedBytes = Receive(socket, SERVER_SEED_SIZE, deadline, "server seed");
    auto result = LoginResult_s{.seed = MakeSeed(Packet{serverSeedBytes}.G8())};

    socket.Send(BuildLoginRequest(account, login, result.seed, reconnect));
    const auto status = Receive(socket, 1, deadline, "login response").front();
    if (status == STATUS_LOGGED_IN)
    {
        const auto details = Receive(socket, 2, deadline, "staff level and mouse tracking flag");
        result.staffLevel = details[0];
        result.mouseTracking = details[1] == 1;
        return result;
    }

    if (status == STATUS_RECONNECTED)
    {
        result.reconnected = true;
        return result;
    }

    if (status == STATUS_HOP_TIMER)
    {
        const auto seconds = Receive(socket, 1, deadline, "hop timer").front();
        throw LoginError{status, std::format("{} seconds left", seconds)};
    }

    throw LoginError{status};
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
