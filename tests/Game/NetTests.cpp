#include "pch.hpp"

#include "Core/BigUInt.hpp"
#include "Core/ConfigFile.hpp"
#include "Game/Net/ClientPacketWriter.hpp"
#include "Game/Net/LoginError.hpp"
#include "Game/Net/LoginHandshake.hpp"
#include "Game/Net/ServerPacketReader.hpp"
#include "Game/Protocol/Base37.hpp"
#include "Game/Protocol/ClientPacket_s.hpp"
#include "Game/Protocol/ClientPackets.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Game/ProtocolError.hpp"
#include "Io/Isaac.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    constexpr auto SEED = std::array<s32, 4>{1, 2, 3, 4};

    // Frames server packets the way the engine does: ISAAC on the opcode, then any length prefix.
    class ServerFramer
    {
    public:
        ServerFramer()
            : m_isaac{SEED}
        {
        }

        std::vector<u8> Frame(u8 opcode, const std::vector<u8>& payload)
        {
            auto bytes = std::vector<u8>{static_cast<u8>(opcode + static_cast<u32>(m_isaac.NextInt()))};
            const auto size = ServerProt::GetSize(opcode);
            if (size == ServerProt::VAR_BYTE)
            {
                bytes.push_back(static_cast<u8>(payload.size()));
            }
            else if (size == ServerProt::VAR_SHORT)
            {
                bytes.push_back(static_cast<u8>(payload.size() >> 8));
                bytes.push_back(static_cast<u8>(payload.size()));
            }

            bytes.insert(bytes.end(), payload.begin(), payload.end());
            return bytes;
        }

    private:
        Isaac m_isaac;
    };

    std::vector<u8> Join(std::initializer_list<std::vector<u8>> parts)
    {
        auto bytes = std::vector<u8>{};
        for (const auto& part : parts)
        {
            bytes.insert(bytes.end(), part.begin(), part.end());
        }

        return bytes;
    }

    void CheckPacket(const std::optional<ServerPacket_s>& packet, ServerProt_e prot, const std::vector<u8>& payload)
    {
        REQUIRE(packet.has_value());
        CHECK(packet->prot == prot);
        CHECK(packet->payload == payload);
    }

    LoginSettings_s MakeLoginSettings()
    {
        auto login = LoginSettings_s{};
        login.rsaModulus = BigUInt::Parse("0x" + std::string(128, 'f'));
        login.rsaExponent = BigUInt::Parse("1");
        for (std::size_t i = 0; i < login.crcs.size(); ++i)
        {
            login.crcs[i] = static_cast<s32>(i + 1);
        }

        return login;
    }
}

TEST_CASE("ServerPacketReader frames each size kind", "[ServerPacketReader]")
{
    auto framer = ServerFramer{};
    auto reader = ServerPacketReader{SEED};
    reader.Append(Join({
        framer.Frame(195, {77}),
        framer.Frame(23, {}),
        framer.Frame(196, {'h', 'i', '\n'}),
        framer.Frame(59, {0, 5, 'o', 'k', '\n'}),
    }));

    CheckPacket(reader.Next(), ServerProt_e::UpdateRunEnergy, {77});
    CheckPacket(reader.Next(), ServerProt_e::IfClose, {});
    CheckPacket(reader.Next(), ServerProt_e::MessageGame, {'h', 'i', '\n'});
    CheckPacket(reader.Next(), ServerProt_e::IfSetText, {0, 5, 'o', 'k', '\n'});
    CHECK_FALSE(reader.Next().has_value());
    CHECK(reader.GetBuffered() == 0);
}

TEST_CASE("ServerPacketReader waits for split frames and decrypts each opcode once", "[ServerPacketReader]")
{
    auto framer = ServerFramer{};
    const auto stream = Join({
        framer.Frame(59, std::vector<u8>(300, 'a')),
        framer.Frame(154, {3, 0, 0, 4, 0x82, 10}),
    });

    auto reader = ServerPacketReader{SEED};
    auto packets = std::vector<ServerPacket_s>{};
    for (const auto byte : stream)
    {
        reader.Append(std::span{&byte, 1});
        while (auto packet = reader.Next())
        {
            packets.push_back(std::move(*packet));
        }
    }

    REQUIRE(packets.size() == 2);
    CHECK(packets[0].prot == ServerProt_e::IfSetText);
    CHECK(packets[0].payload.size() == 300);
    CHECK(packets[1].prot == ServerProt_e::UpdateStat);
    CHECK(packets[1].payload == std::vector<u8>{3, 0, 0, 4, 0x82, 10});
}

TEST_CASE("ServerPacketReader rejects an opcode the server never sends", "[ServerPacketReader]")
{
    auto framer = ServerFramer{};
    auto reader = ServerPacketReader{SEED};
    reader.Append(framer.Frame(0, {}));
    CHECK_THROWS_AS(reader.Next(), ProtocolError);
}

TEST_CASE("ClientPacketWriter encrypts opcodes and adds length bytes", "[ClientPacketWriter]")
{
    auto twin = Isaac{SEED};
    auto writer = ClientPacketWriter{SEED};
    auto bytes = std::vector<u8>{};
    writer.Write(ClientPackets::NoTimeout(), bytes);
    writer.Write(ClientPackets::ClientCheat("hi"), bytes);
    writer.Write(ClientPackets::OpNpc(1, 7), bytes);

    const auto first = static_cast<u8>(181 + static_cast<u32>(twin.NextInt()));
    const auto second = static_cast<u8>(34 + static_cast<u32>(twin.NextInt()));
    const auto third = static_cast<u8>(252 + static_cast<u32>(twin.NextInt()));
    CHECK(bytes == std::vector<u8>{first, second, 3, 'h', 'i', '\n', third, 0, 7});
}

TEST_CASE("ClientPacketWriter rejects bad packets before using the cipher", "[ClientPacketWriter]")
{
    auto twin = Isaac{SEED};
    auto writer = ClientPacketWriter{SEED};
    auto bytes = std::vector<u8>{};

    CHECK_THROWS_AS(writer.Write({.prot = ClientProt_e::OpNpc1, .payload = {1, 2, 3}}, bytes), std::invalid_argument);
    CHECK_THROWS_AS(writer.Write({.prot = static_cast<ClientProt_e>(0)}, bytes), std::invalid_argument);
    CHECK_THROWS_AS(writer.Write({.prot = ClientProt_e::ClientCheat, .payload = std::vector<u8>(256)}, bytes), std::invalid_argument);
    CHECK(bytes.empty());

    writer.Write(ClientPackets::CloseModal(), bytes);
    CHECK(bytes == std::vector<u8>{static_cast<u8>(93 + static_cast<u32>(twin.NextInt()))});
}

TEST_CASE("LoginHandshake builds the seed request", "[LoginHandshake]")
{
    const auto loginServer = static_cast<u8>((Base37::Encode("bot") >> 16) & 0x1F);
    CHECK(LoginHandshake::BuildSeedRequest("bot") == std::vector<u8>{14, loginServer});
}

TEST_CASE("LoginHandshake builds the login request", "[LoginHandshake]")
{
    const auto account = AccountSettings_s{.username = "bot", .password = "pw"};
    const auto login = MakeLoginSettings();
    const auto request = LoginHandshake::BuildLoginRequest(account, login, SEED, false);

    const auto block = std::vector<u8>{
        10, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0, 4, 0, 0, 0x05, 0x39, 'b', 'o', 't', '\n', 'p', 'w', '\n',
    };

    auto expected = std::vector<u8>{16, 0, 0xFF, 0x01, 0x21, 0};
    for (auto crc = u8{1}; crc <= 9; ++crc)
    {
        expected.insert(expected.end(), {0, 0, 0, crc});
    }

    expected.push_back(static_cast<u8>(block.size()));
    expected.insert(expected.end(), block.begin(), block.end());
    expected[1] = static_cast<u8>(expected.size() - 2);
    CHECK(request == expected);

    SECTION("a reconnect uses opcode 18")
    {
        CHECK(LoginHandshake::BuildLoginRequest(account, login, SEED, true).front() == LoginHandshake::RECONNECT_LOGIN);
    }
}

TEST_CASE("LoginHandshake seeds", "[LoginHandshake]")
{
    const auto seed = LoginHandshake::MakeSeed(0x0123456789ABCDEF);
    CHECK(seed[0] >= 0);
    CHECK(seed[0] <= 99999999);
    CHECK(seed[1] >= 0);
    CHECK(seed[1] <= 99999999);
    CHECK(seed[2] == 0x01234567);
    CHECK(seed[3] == std::bit_cast<s32>(0x89ABCDEFu));

    const auto inbound = LoginHandshake::GetInboundSeed(std::array<s32, 4>{1, -1, std::numeric_limits<s32>::max(), 0});
    CHECK(inbound == std::array<s32, 4>{51, 49, std::numeric_limits<s32>::min() + 49, 50});
}

TEST_CASE("LoginError describes the status", "[LoginError]")
{
    const auto rejected = LoginError{3};
    CHECK(rejected.GetStatus() == 3);
    CHECK_FALSE(rejected.IsRetryable());
    CHECK(std::string_view{rejected.what()}.find("invalid username or password") != std::string_view::npos);

    CHECK(LoginError{16}.IsRetryable());
    CHECK(LoginError::Describe(99) == "unexpected response");
}
