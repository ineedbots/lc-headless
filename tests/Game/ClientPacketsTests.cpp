#include "pch.hpp"

#include "Game/Net/ClientPacketWriter.hpp"
#include "Game/Protocol/Base37.hpp"
#include "Game/Protocol/ClientPacket_s.hpp"
#include "Game/Protocol/ClientPackets.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Tile_s.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    constexpr auto TILE = Tile_s{.x = 3200, .z = 3201, .level = 0};

    std::vector<u8> Bytes(std::initializer_list<u8> bytes)
    {
        return bytes;
    }

    void CheckPacket(const ClientPacket_s& packet, ClientProt_e prot, const std::vector<u8>& payload)
    {
        CHECK(packet.prot == prot);
        CHECK(packet.payload == payload);
        CHECK_NOTHROW(ClientPacketWriter::Validate(packet));
    }
}

TEST_CASE("ClientPackets builds moves", "[ClientPackets]")
{
    SECTION("a game click with a later waypoint offset from the start")
    {
        const auto waypoints = std::array{Tile_s{.x = 3200, .z = 3200}, Tile_s{.x = 3205, .z = 3198}};
        CheckPacket(ClientPackets::Move(MoveKind_e::GameClick, waypoints, true), ClientProt_e::MoveGameClick, Bytes({1, 0x0C, 0x80, 0x0C, 0x80, 5, 0xFE}));
    }

    SECTION("an op click to a single tile")
    {
        CheckPacket(ClientPackets::Move(MoveKind_e::OpClick, std::span{&TILE, 1}, false), ClientProt_e::MoveOpClick, Bytes({0, 0x0C, 0x80, 0x0C, 0x81}));
    }

    SECTION("a minimap click adds the 14-byte trailer")
    {
        const auto packet = ClientPackets::Move(MoveKind_e::MinimapClick, std::span{&TILE, 1}, false);
        CHECK(packet.prot == ClientProt_e::MoveMinimapClick);
        CHECK(packet.payload.size() == 5 + 14);
    }

    SECTION("bad waypoint lists throw")
    {
        CHECK_THROWS_AS(ClientPackets::Move(MoveKind_e::GameClick, {}, false), std::invalid_argument);

        const auto tooMany = std::vector<Tile_s>(ClientPackets::MAX_WAYPOINTS + 1, TILE);
        CHECK_THROWS_AS(ClientPackets::Move(MoveKind_e::GameClick, tooMany, false), std::invalid_argument);

        const auto tooFar = std::array{TILE, Tile_s{.x = TILE.x + 128, .z = TILE.z}};
        CHECK_THROWS_AS(ClientPackets::Move(MoveKind_e::GameClick, tooFar, false), std::invalid_argument);

        const auto negative = Tile_s{.x = -1, .z = 0};
        CHECK_THROWS_AS(ClientPackets::Move(MoveKind_e::GameClick, std::span{&negative, 1}, false), std::invalid_argument);
    }
}

TEST_CASE("ClientPackets picks the opcode from the option number", "[ClientPackets]")
{
    CheckPacket(ClientPackets::OpNpc(1, 300), ClientProt_e::OpNpc1, Bytes({0x01, 0x2C}));
    CheckPacket(ClientPackets::OpNpc(5, 300), ClientProt_e::OpNpc5, Bytes({0x01, 0x2C}));
    CheckPacket(ClientPackets::OpPlayer(4, 2), ClientProt_e::OpPlayer4, Bytes({0x00, 0x02}));
    CheckPacket(ClientPackets::OpLoc(2, TILE, 1276), ClientProt_e::OpLoc2, Bytes({0x0C, 0x80, 0x0C, 0x81, 0x04, 0xFC}));
    CheckPacket(ClientPackets::OpObj(3, TILE, 995), ClientProt_e::OpObj3, Bytes({0x0C, 0x80, 0x0C, 0x81, 0x03, 0xE3}));
    CheckPacket(ClientPackets::OpHeld(1, {.obj = 1, .slot = 2, .com = 3}), ClientProt_e::OpHeld1, Bytes({0, 1, 0, 2, 0, 3}));
    CheckPacket(ClientPackets::InvButton(2, {.obj = 1, .slot = 2, .com = 3}), ClientProt_e::InvButton2, Bytes({0, 1, 0, 2, 0, 3}));

    CHECK_THROWS_AS(ClientPackets::OpNpc(0, 1), std::invalid_argument);
    CHECK_THROWS_AS(ClientPackets::OpLoc(6, TILE, 1), std::invalid_argument);
}

TEST_CASE("ClientPackets builds targeted and use packets", "[ClientPackets]")
{
    const auto use = ItemRef_s{.obj = 4, .slot = 5, .com = 6};
    CheckPacket(ClientPackets::OpNpcT(7, 1152), ClientProt_e::OpNpcT, Bytes({0, 7, 0x04, 0x80}));
    CheckPacket(ClientPackets::OpNpcU(7, use), ClientProt_e::OpNpcU, Bytes({0, 7, 0, 4, 0, 5, 0, 6}));
    CheckPacket(ClientPackets::OpLocU(TILE, 1, use), ClientProt_e::OpLocU, Bytes({0x0C, 0x80, 0x0C, 0x81, 0, 1, 0, 4, 0, 5, 0, 6}));
    CheckPacket(ClientPackets::OpObjT(TILE, 1, 2), ClientProt_e::OpObjT, Bytes({0x0C, 0x80, 0x0C, 0x81, 0, 1, 0, 2}));
    CheckPacket(ClientPackets::OpHeldU({.obj = 1, .slot = 2, .com = 3}, use), ClientProt_e::OpHeldU, Bytes({0, 1, 0, 2, 0, 3, 0, 4, 0, 5, 0, 6}));
    CheckPacket(ClientPackets::OpHeldT({.obj = 1, .slot = 2, .com = 3}, 9), ClientProt_e::OpHeldT, Bytes({0, 1, 0, 2, 0, 3, 0, 9}));
    CheckPacket(ClientPackets::OpPlayerU(2, use), ClientProt_e::OpPlayerU, Bytes({0, 2, 0, 4, 0, 5, 0, 6}));
}

TEST_CASE("ClientPackets builds interface packets", "[ClientPackets]")
{
    CheckPacket(ClientPackets::IfButton(2458), ClientProt_e::IfButton, Bytes({0x09, 0x9A}));
    CheckPacket(ClientPackets::ResumePauseButton(356), ClientProt_e::ResumePauseButton, Bytes({0x01, 0x64}));
    CheckPacket(ClientPackets::ResumePCountDialog(-2), ClientProt_e::ResumePCountDialog, Bytes({0xFF, 0xFF, 0xFF, 0xFE}));
    CheckPacket(ClientPackets::InvButtonD(5382, 1, 2, DragMode_e::Insert), ClientProt_e::InvButtonD, Bytes({0x15, 0x06, 0, 1, 0, 2, 1}));
    CheckPacket(ClientPackets::CloseModal(), ClientProt_e::CloseModal, {});
    CheckPacket(ClientPackets::NoTimeout(), ClientProt_e::NoTimeout, {});
    CheckPacket(ClientPackets::TutClickSide(3), ClientProt_e::TutClickSide, Bytes({3}));

    const auto design = IdkDesign_s{.female = true, .kits = {0, 1, 2, 3, 4, 5, 255}, .colours = {6, 7, 8, 9, 10}};
    CheckPacket(ClientPackets::IdkSaveDesign(design), ClientProt_e::IdkSaveDesign, Bytes({1, 0, 1, 2, 3, 4, 5, 255, 6, 7, 8, 9, 10}));
}

TEST_CASE("ClientPackets builds chat and social packets", "[ClientPackets]")
{
    CheckPacket(ClientPackets::MessagePublic("hello", ChatColour_e::Red, ChatEffect_e::Wave), ClientProt_e::MessagePublic, Bytes({1, 1, 0x61, 0xBB, 0x40}));
    CheckPacket(ClientPackets::MessagePrivate(Base37::Encode("ab"), "hello"), ClientProt_e::MessagePrivate, Bytes({0, 0, 0, 0, 0, 0, 0, 39, 0x61, 0xBB, 0x40}));
    CheckPacket(ClientPackets::ClientCheat("tele"), ClientProt_e::ClientCheat, Bytes({'t', 'e', 'l', 'e', '\n'}));
    CheckPacket(ClientPackets::ChatSetMode(3, 2, 1), ClientProt_e::ChatSetMode, Bytes({3, 2, 1}));
    CheckPacket(ClientPackets::FriendListAdd(39), ClientProt_e::FriendListAdd, Bytes({0, 0, 0, 0, 0, 0, 0, 39}));
    CheckPacket(ClientPackets::IgnoreListDel(39), ClientProt_e::IgnoreListDel, Bytes({0, 0, 0, 0, 0, 0, 0, 39}));
    CheckPacket(ClientPackets::ReportAbuse(39, 11, true), ClientProt_e::ReportAbuse, Bytes({0, 0, 0, 0, 0, 0, 0, 39, 11, 1}));

    CHECK_THROWS_AS(ClientPackets::ClientCheat(std::string(ClientPackets::MAX_CHEAT_LENGTH + 1, 'a')), std::invalid_argument);
    CHECK_THROWS_AS(ClientPackets::ClientCheat("a\nb"), std::invalid_argument);
    CHECK_THROWS_AS(ClientPackets::ChatSetMode(4, 0, 0), std::invalid_argument);
    CHECK_THROWS_AS(ClientPackets::ReportAbuse(39, 12, false), std::invalid_argument);
    CHECK_THROWS_AS(ClientPackets::MessagePublic("hi", static_cast<ChatColour_e>(12)), std::invalid_argument);
}
