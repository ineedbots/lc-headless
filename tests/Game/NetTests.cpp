#include "pch.hpp"

#include "Cache/GameCache_s.hpp"
#include "Config/AccountConfig_s.hpp"
#include "Config/Config_s.hpp"
#include "Config/Revision_e.hpp"
#include "Game/Error/ProtocolError.hpp"
#include "Game/Net/ClientPacketWriter.hpp"
#include "Game/Net/Error/LoginError.hpp"
#include "Game/Net/LoginHandshake.hpp"
#include "Game/Net/ServerPacketReader.hpp"
#include "Game/Protocol/Base37.hpp"
#include "Game/Protocol/ClientPacket_s.hpp"
#include "Game/Protocol/ClientPackets.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/Protocol.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Io/Isaac.hpp"
#include "Utils/BigUInt.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

namespace
{
    constexpr auto SEED = std::array<s32, 4>{1, 2, 3, 4};
    constexpr auto CRCS = std::array<s32, GameCache_s::CRC_COUNT>{1, 2, 3, 4, 5, 6, 7, 8, 9};
    const auto PROTOCOL = Protocol{Revision_e::Rev289};
    const auto PACKETS = ClientPackets{PROTOCOL};

    // Frames server packets the way the engine does: ISAAC on the opcode, then any length prefix.
    class ServerFramer
    {
    public:
        explicit ServerFramer(Protocol protocol = PROTOCOL)
            : m_isaac{SEED}
            , m_protocol{protocol}
        {
        }

        std::vector<u8> Frame(u8 opcode, const std::vector<u8>& payload)
        {
            auto bytes = std::vector<u8>{static_cast<u8>(opcode + static_cast<u32>(m_isaac.NextInt()))};
            const auto prot = m_protocol.FindServerProt(opcode);
            const auto size = prot ? m_protocol.GetSize(*prot) : 0;
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
        Protocol m_protocol;
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
        return login;
    }
}

TEST_CASE("ServerPacketReader frames each size kind", "[ServerPacketReader]")
{
    auto framer = ServerFramer{};
    auto reader = ServerPacketReader{SEED, PROTOCOL};
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

    auto reader = ServerPacketReader{SEED, PROTOCOL};
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

TEST_CASE("ServerPacketReader reads each revision's opcodes and rejects the other's", "[ServerPacketReader]")
{
    // 1 is 225's NPC_INFO and 60 is 289's OBJ_ADD; neither revision uses the other's.
    const auto protocol225 = Protocol{Revision_e::Rev225};
    auto framer = ServerFramer{protocol225};
    auto reader = ServerPacketReader{SEED, protocol225};
    reader.Append(Join({framer.Frame(1, {77}), framer.Frame(139, {0, 9})}));
    CheckPacket(reader.Next(), ServerProt_e::NpcInfo, {77});
    CheckPacket(reader.Next(), ServerProt_e::UpdatePid, {0, 9});

    auto later = ServerPacketReader{SEED, PROTOCOL};
    later.Append(ServerFramer{}.Frame(1, {}));
    CHECK_THROWS_WITH(later.Next(), "Server sent opcode 1, which revision 289 never sends");

    auto earlier = ServerPacketReader{SEED, protocol225};
    earlier.Append(ServerFramer{protocol225}.Frame(60, {}));
    CHECK_THROWS_WITH(earlier.Next(), "Server sent opcode 60, which revision 225 never sends");
}

TEST_CASE("ServerPacketReader reads 274's opcodes", "[ServerPacketReader]")
{
    // 197 is 274's NPC_INFO and 133 its UPDATE_PID; 12 is 289's TUT_OPEN, which 274 doesn't use.
    const auto protocol = Protocol{Revision_e::Rev274};
    auto framer = ServerFramer{protocol};
    auto reader = ServerPacketReader{SEED, protocol};
    reader.Append(Join({framer.Frame(197, {77}), framer.Frame(133, {0, 9, 1})}));
    CheckPacket(reader.Next(), ServerProt_e::NpcInfo, {77});
    CheckPacket(reader.Next(), ServerProt_e::UpdatePid, {0, 9, 1});

    auto other = ServerPacketReader{SEED, protocol};
    other.Append(ServerFramer{protocol}.Frame(12, {}));
    CHECK_THROWS_WITH(other.Next(), "Server sent opcode 12, which revision 274 never sends");
}

TEST_CASE("ServerPacketReader rejects an opcode the server never sends", "[ServerPacketReader]")
{
    auto framer = ServerFramer{};
    auto reader = ServerPacketReader{SEED, PROTOCOL};
    reader.Append(framer.Frame(0, {}));
    CHECK_THROWS_AS(reader.Next(), ProtocolError);
}

TEST_CASE("ClientPacketWriter encrypts opcodes and adds length bytes", "[ClientPacketWriter]")
{
    auto twin = Isaac{SEED};
    auto writer = ClientPacketWriter{SEED, PROTOCOL};
    auto bytes = std::vector<u8>{};
    writer.Write(PACKETS.NoTimeout(), bytes);
    writer.Write(PACKETS.ClientCheat("hi"), bytes);
    writer.Write(PACKETS.OpNpc(1, 7), bytes);

    const auto first = static_cast<u8>(181 + static_cast<u32>(twin.NextInt()));
    const auto second = static_cast<u8>(34 + static_cast<u32>(twin.NextInt()));
    const auto third = static_cast<u8>(252 + static_cast<u32>(twin.NextInt()));
    CHECK(bytes == std::vector<u8>{first, second, 3, 'h', 'i', '\n', third, 0, 7});
}

TEST_CASE("ClientPacketWriter rejects bad packets before using the cipher", "[ClientPacketWriter]")
{
    auto twin = Isaac{SEED};
    auto writer = ClientPacketWriter{SEED, PROTOCOL};
    auto bytes = std::vector<u8>{};

    CHECK_THROWS_AS(writer.Write({.prot = ClientProt_e::OpNpc1, .payload = {1, 2, 3}}, bytes), std::invalid_argument);
    CHECK_THROWS_AS(writer.Write({.prot = ClientProt_e::EventTracking}, bytes), std::invalid_argument);
    CHECK_THROWS_AS(writer.Write({.prot = ClientProt_e::ClientCheat, .payload = std::vector<u8>(256)}, bytes), std::invalid_argument);
    CHECK(bytes.empty());

    writer.Write(PACKETS.CloseModal(), bytes);
    CHECK(bytes == std::vector<u8>{static_cast<u8>(93 + static_cast<u32>(twin.NextInt()))});
}

TEST_CASE("ClientPacketWriter puts a 2-byte length before a VAR_SHORT payload", "[ClientPacketWriter]")
{
    auto twin = Isaac{SEED};
    auto writer = ClientPacketWriter{SEED, Protocol{Revision_e::Rev225}};
    auto bytes = std::vector<u8>{};
    writer.Write({.prot = ClientProt_e::EventTracking, .payload = std::vector<u8>(300, 7)}, bytes);

    REQUIRE(bytes.size() == 3 + 300);
    CHECK(bytes[0] == static_cast<u8>(81 + static_cast<u32>(twin.NextInt())));
    CHECK(bytes[1] == 0x01);
    CHECK(bytes[2] == 0x2C);
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
    const auto request = LoginHandshake::BuildLoginRequest(PROTOCOL, account, login, CRCS, SEED, false);

    // clang-format off
    const auto block = std::vector<u8>{
        10, 0, 0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0, 4, 0, 0, 0x05, 0x39, 'b', 'o', 't', '\n', 'p', 'w', '\n',
    };
    // clang-format on

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
        CHECK(LoginHandshake::BuildLoginRequest(PROTOCOL, account, login, CRCS, SEED, true).front() == LoginHandshake::RECONNECT_LOGIN);
    }
}

TEST_CASE("LoginHandshake builds a 225 login request with a one-byte revision", "[LoginHandshake]")
{
    const auto account = AccountSettings_s{.username = "bot", .password = "pw"};
    auto login = MakeLoginSettings();
    login.revision = Revision_e::Rev225;
    const auto request = LoginHandshake::BuildLoginRequest(Protocol{Revision_e::Rev225}, account, login, CRCS, SEED, false);
    const auto request289 = LoginHandshake::BuildLoginRequest(PROTOCOL, account, login, CRCS, SEED, false);

    REQUIRE(request.size() == request289.size() - 2);
    CHECK(request[0] == LoginHandshake::NORMAL_LOGIN);
    CHECK(request[1] == request.size() - 2);
    CHECK(request[2] == 225);
    CHECK(request[3] == 0);
    CHECK(std::ranges::equal(std::span{request}.subspan(4), std::span{request289}.subspan(6)));
}

TEST_CASE("LoginHandshake builds a 274 login request with the marker and a two-byte revision", "[LoginHandshake]")
{
    const auto account = AccountSettings_s{.username = "bot", .password = "pw"};
    auto login = MakeLoginSettings();
    login.revision = Revision_e::Rev274;
    const auto request = LoginHandshake::BuildLoginRequest(Protocol{Revision_e::Rev274}, account, login, CRCS, SEED, false);
    const auto request289 = LoginHandshake::BuildLoginRequest(PROTOCOL, account, login, CRCS, SEED, false);

    REQUIRE(request.size() == request289.size());
    CHECK(request[2] == 0xFF);
    CHECK(request[3] == 0x01);
    CHECK(request[4] == 0x12);
    CHECK(std::ranges::equal(std::span{request}.subspan(5), std::span{request289}.subspan(5)));
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
    CHECK(LoginError::Describe(6) == "revision, cache CRC or RSA key mismatch; do login.revision and client.cacheDirectory match this server?");
}
