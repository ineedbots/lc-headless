#include "pch.hpp"

#include "Config/Revision_e.hpp"
#include "Game/Net/ClientPacketWriter.hpp"
#include "Game/Protocol/Base37.hpp"
#include "Game/Protocol/ClientPacket_s.hpp"
#include "Game/Protocol/ClientPackets.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/Protocol.hpp"
#include "Game/Tile_s.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

namespace
{
    constexpr auto TILE = Tile_s{.x = 3200, .z = 3201, .level = 0};
    const auto PROTOCOL = Protocol{Revision_e::Rev289};
    const auto PACKETS = ClientPackets{PROTOCOL};

    std::vector<u8> Bytes(std::initializer_list<u8> bytes)
    {
        return bytes;
    }

    void CheckPacket(const ClientPacket_s& packet, ClientProt_e prot, const std::vector<u8>& payload)
    {
        CHECK(packet.prot == prot);
        CHECK(packet.payload == payload);
        CHECK_NOTHROW(ClientPacketWriter::Validate(PROTOCOL, packet));
    }
}

TEST_CASE("ClientPackets encodes idle notifications and plain chat for every revision", "[ClientPackets][NativeBoundaryCoverage]")
{
    const auto revision = GENERATE(Revision_e::Rev225, Revision_e::Rev274, Revision_e::Rev289);
    const auto protocol = Protocol{revision};
    const auto packets = ClientPackets{protocol};
    const auto idle = packets.IdleTimer();
    CHECK(idle.prot == ClientProt_e::IdleTimer);
    CHECK(idle.payload.empty());
    CHECK_NOTHROW(ClientPacketWriter::Validate(protocol, idle));

    const auto chat = packets.MessagePublic("hello");
    CHECK(chat.prot == ClientProt_e::MessagePublic);
    CHECK(chat.payload == Bytes({0, 0, 0x61, 0xBB, 0x40}));
    CHECK_NOTHROW(ClientPacketWriter::Validate(protocol, chat));
}

TEST_CASE("ClientPackets builds moves", "[ClientPackets]")
{
    SECTION("a game click with a later waypoint offset from the start")
    {
        const auto waypoints = std::array{Tile_s{.x = 3200, .z = 3200}, Tile_s{.x = 3205, .z = 3198}};
        CheckPacket(PACKETS.Move(MoveKind_e::GameClick, waypoints, true), ClientProt_e::MoveGameClick, Bytes({1, 0x0C, 0x80, 0x0C, 0x80, 5, 0xFE}));
    }

    SECTION("an op click to a single tile")
    {
        CheckPacket(PACKETS.Move(MoveKind_e::OpClick, std::span{&TILE, 1}, false), ClientProt_e::MoveOpClick, Bytes({0, 0x0C, 0x80, 0x0C, 0x81}));
    }

    SECTION("a minimap click adds the 14-byte trailer")
    {
        const auto packet = PACKETS.Move(MoveKind_e::MinimapClick, std::span{&TILE, 1}, false);
        CHECK(packet.prot == ClientProt_e::MoveMinimapClick);
        CHECK(packet.payload.size() == 5 + 14);
    }

    SECTION("bad waypoint lists throw")
    {
        CHECK_THROWS_AS(PACKETS.Move(MoveKind_e::GameClick, {}, false), std::invalid_argument);

        const auto tooMany = std::vector<Tile_s>(ClientPackets::MAX_WAYPOINTS + 1, TILE);
        CHECK_THROWS_AS(PACKETS.Move(MoveKind_e::GameClick, tooMany, false), std::invalid_argument);

        const auto tooFar = std::array{TILE, Tile_s{.x = TILE.x + 128, .z = TILE.z}};
        CHECK_THROWS_AS(PACKETS.Move(MoveKind_e::GameClick, tooFar, false), std::invalid_argument);

        const auto negative = Tile_s{.x = -1, .z = 0};
        CHECK_THROWS_AS(PACKETS.Move(MoveKind_e::GameClick, std::span{&negative, 1}, false), std::invalid_argument);
    }
}

TEST_CASE("ClientPackets picks the opcode from the option number", "[ClientPackets]")
{
    CheckPacket(PACKETS.OpNpc(1, 300), ClientProt_e::OpNpc1, Bytes({0x01, 0x2C}));
    CheckPacket(PACKETS.OpNpc(5, 300), ClientProt_e::OpNpc5, Bytes({0x01, 0x2C}));
    CheckPacket(PACKETS.OpPlayer(4, 2), ClientProt_e::OpPlayer4, Bytes({0x00, 0x02}));
    CheckPacket(PACKETS.OpLoc(2, TILE, 1276), ClientProt_e::OpLoc2, Bytes({0x0C, 0x80, 0x0C, 0x81, 0x04, 0xFC}));
    CheckPacket(PACKETS.OpObj(3, TILE, 995), ClientProt_e::OpObj3, Bytes({0x0C, 0x80, 0x0C, 0x81, 0x03, 0xE3}));
    CheckPacket(PACKETS.OpHeld(1, {.obj = 1, .slot = 2, .com = 3}), ClientProt_e::OpHeld1, Bytes({0, 1, 0, 2, 0, 3}));
    CheckPacket(PACKETS.InvButton(2, {.obj = 1, .slot = 2, .com = 3}), ClientProt_e::InvButton2, Bytes({0, 1, 0, 2, 0, 3}));

    CHECK_THROWS_AS(PACKETS.OpNpc(0, 1), std::invalid_argument);
    CHECK_THROWS_AS(PACKETS.OpLoc(6, TILE, 1), std::invalid_argument);
}

TEST_CASE("ClientPackets builds targeted and use packets", "[ClientPackets]")
{
    const auto use = ItemRef_s{.obj = 4, .slot = 5, .com = 6};
    CheckPacket(PACKETS.OpNpcT(7, 1152), ClientProt_e::OpNpcT, Bytes({0, 7, 0x04, 0x80}));
    CheckPacket(PACKETS.OpNpcU(7, use), ClientProt_e::OpNpcU, Bytes({0, 7, 0, 4, 0, 5, 0, 6}));
    CheckPacket(PACKETS.OpLocU(TILE, 1, use), ClientProt_e::OpLocU, Bytes({0x0C, 0x80, 0x0C, 0x81, 0, 1, 0, 4, 0, 5, 0, 6}));
    CheckPacket(PACKETS.OpObjT(TILE, 1, 2), ClientProt_e::OpObjT, Bytes({0x0C, 0x80, 0x0C, 0x81, 0, 1, 0, 2}));
    CheckPacket(PACKETS.OpHeldU({.obj = 1, .slot = 2, .com = 3}, use), ClientProt_e::OpHeldU, Bytes({0, 1, 0, 2, 0, 3, 0, 4, 0, 5, 0, 6}));
    CheckPacket(PACKETS.OpHeldT({.obj = 1, .slot = 2, .com = 3}, 9), ClientProt_e::OpHeldT, Bytes({0, 1, 0, 2, 0, 3, 0, 9}));
    CheckPacket(PACKETS.OpPlayerU(2, use), ClientProt_e::OpPlayerU, Bytes({0, 2, 0, 4, 0, 5, 0, 6}));
}

TEST_CASE("ClientPackets builds interface packets", "[ClientPackets]")
{
    CheckPacket(PACKETS.IfButton(2458), ClientProt_e::IfButton, Bytes({0x09, 0x9A}));
    CheckPacket(PACKETS.ResumePauseButton(356), ClientProt_e::ResumePauseButton, Bytes({0x01, 0x64}));
    CheckPacket(PACKETS.ResumePCountDialog(-2), ClientProt_e::ResumePCountDialog, Bytes({0xFF, 0xFF, 0xFF, 0xFE}));
    CheckPacket(PACKETS.InvButtonD(5382, 1, 2, DragMode_e::Insert), ClientProt_e::InvButtonD, Bytes({0x15, 0x06, 0, 1, 0, 2, 1}));
    CheckPacket(PACKETS.CloseModal(), ClientProt_e::CloseModal, {});
    CheckPacket(PACKETS.NoTimeout(), ClientProt_e::NoTimeout, {});
    CheckPacket(PACKETS.TutClickSide(3), ClientProt_e::TutClickSide, Bytes({3}));

    const auto design = IdkDesign_s{.female = true, .kits = {0, 1, 2, 3, 4, 5, 255}, .colours = {6, 7, 8, 9, 10}};
    CheckPacket(PACKETS.IdkSaveDesign(design), ClientProt_e::IdkSaveDesign, Bytes({1, 0, 1, 2, 3, 4, 5, 255, 6, 7, 8, 9, 10}));
}

TEST_CASE("ClientPackets builds chat and social packets", "[ClientPackets]")
{
    CheckPacket(PACKETS.MessagePublic("hello", ChatColour_e::Red, ChatEffect_e::Wave), ClientProt_e::MessagePublic, Bytes({1, 1, 0x61, 0xBB, 0x40}));
    CheckPacket(PACKETS.MessagePrivate(Base37::Encode("ab"), "hello"), ClientProt_e::MessagePrivate, Bytes({0, 0, 0, 0, 0, 0, 0, 39, 0x61, 0xBB, 0x40}));
    CheckPacket(PACKETS.ClientCheat("tele"), ClientProt_e::ClientCheat, Bytes({'t', 'e', 'l', 'e', '\n'}));
    CheckPacket(PACKETS.ChatSetMode(3, 2, 1), ClientProt_e::ChatSetMode, Bytes({3, 2, 1}));
    CheckPacket(PACKETS.FriendListAdd(39), ClientProt_e::FriendListAdd, Bytes({0, 0, 0, 0, 0, 0, 0, 39}));
    CheckPacket(PACKETS.IgnoreListDel(39), ClientProt_e::IgnoreListDel, Bytes({0, 0, 0, 0, 0, 0, 0, 39}));
    CheckPacket(PACKETS.ReportAbuse(39, 11, true), ClientProt_e::ReportAbuse, Bytes({0, 0, 0, 0, 0, 0, 0, 39, 11, 1}));

    CHECK_THROWS_AS(PACKETS.ClientCheat(std::string(ClientPackets::MAX_CHEAT_LENGTH + 1, 'a')), std::invalid_argument);
    CHECK_THROWS_AS(PACKETS.ClientCheat("a\nb"), std::invalid_argument);
    CHECK_THROWS_AS(PACKETS.ChatSetMode(4, 0, 0), std::invalid_argument);
    CHECK_THROWS_AS(PACKETS.ReportAbuse(39, 12, false), std::invalid_argument);
    CHECK_THROWS_AS(PACKETS.MessagePublic("hi", static_cast<ChatColour_e>(12)), std::invalid_argument);
}

TEST_CASE("ClientPackets rejects a packet the revision doesn't have", "[ClientPackets]")
{
    const auto packets = ClientPackets{Protocol{Revision_e::Rev225}};
    CHECK_THROWS_AS(packets.MapBuildComplete(), std::invalid_argument);
    CHECK_THROWS_AS(packets.EventAppletFocus(true), std::invalid_argument);
    CHECK_THROWS_AS(packets.OpPlayer(5, 1), std::invalid_argument);
    CHECK(packets.OpPlayer(4, 1).prot == ClientProt_e::OpPlayer4);
}

TEST_CASE("ClientPackets builds 225's drags and camera position", "[ClientPackets]")
{
    const auto protocol = Protocol{Revision_e::Rev225};
    const auto packets = ClientPackets{protocol};

    const auto drag = packets.InvButtonD(5382, 1, 2, DragMode_e::Swap);
    CHECK(drag.payload == Bytes({0x15, 0x06, 0, 1, 0, 2}));
    CHECK_NOTHROW(ClientPacketWriter::Validate(protocol, drag));
    CHECK_THROWS_AS(packets.InvButtonD(5382, 1, 2, DragMode_e::Insert), std::invalid_argument);

    const auto camera = packets.EventCameraPosition(128, 1024);
    CHECK(camera.payload == Bytes({0, 128, 4, 0, 0, 0}));
    CHECK_NOTHROW(ClientPacketWriter::Validate(protocol, camera));
    CheckPacket(PACKETS.EventCameraPosition(128, 1024), ClientProt_e::EventCameraPosition, Bytes({0, 128, 4, 0}));
}

TEST_CASE("ClientPackets builds 274's packets in 289's layout", "[ClientPackets]")
{
    const auto protocol = Protocol{Revision_e::Rev274};
    const auto packets = ClientPackets{protocol};

    const auto drag = packets.InvButtonD(5382, 1, 2, DragMode_e::Insert);
    CHECK(drag.payload == Bytes({0x15, 0x06, 0, 1, 0, 2, 1}));
    CHECK_NOTHROW(ClientPacketWriter::Validate(protocol, drag));

    const auto camera = packets.EventCameraPosition(128, 1024);
    CHECK(camera.payload == Bytes({0, 128, 4, 0}));
    CHECK_NOTHROW(ClientPacketWriter::Validate(protocol, camera));

    CHECK(packets.OpPlayer(5, 1).prot == ClientProt_e::OpPlayer5);
    CHECK_NOTHROW(packets.MapBuildComplete());
    CHECK_THROWS_AS(packets.RebuildGetMaps({}), std::invalid_argument);
    CHECK_THROWS_AS(packets.EventTracking(std::vector<u8>{1}), std::invalid_argument);
}

TEST_CASE("ClientPackets numbers chat effects as the revision does", "[ClientPackets]")
{
    const auto revision = GENERATE(Revision_e::Rev225, Revision_e::Rev274);
    const auto packets = ClientPackets{Protocol{revision}};
    CAPTURE(static_cast<u16>(revision));

    CHECK(packets.MessagePublic("hi", ChatColour_e::Yellow, ChatEffect_e::Wave).payload[1] == 1);
    CHECK(packets.MessagePublic("hi", ChatColour_e::Yellow, ChatEffect_e::Scroll).payload[1] == 2);
    CHECK(PACKETS.MessagePublic("hi", ChatColour_e::Yellow, ChatEffect_e::Wave2).payload[1] == 2);
    CHECK(PACKETS.MessagePublic("hi", ChatColour_e::Yellow, ChatEffect_e::Scroll).payload[1] == 4);

    const auto effect = GENERATE(ChatEffect_e::Wave2, ChatEffect_e::Shake, ChatEffect_e::Slide);
    CAPTURE(static_cast<u8>(effect));
    CHECK_THROWS_WITH(packets.MessagePublic("hi", ChatColour_e::Yellow, effect), std::format("Revision {} has only the wave and scroll chat effects", static_cast<u16>(revision)));
    CHECK_NOTHROW(PACKETS.MessagePublic("hi", ChatColour_e::Yellow, effect));
}

TEST_CASE("ClientPackets builds 225's map requests and input reports", "[ClientPackets]")
{
    const auto protocol = Protocol{Revision_e::Rev225};
    const auto packets = ClientPackets{protocol};

    const auto requests = std::to_array<MapRequest_s>({{.file = MapFile_e::Land, .x = 50, .z = 51}, {.file = MapFile_e::Locs, .x = 50, .z = 51}});
    const auto maps = packets.RebuildGetMaps(requests);
    CHECK(maps.prot == ClientProt_e::RebuildGetMaps);
    CHECK(maps.payload == Bytes({0, 50, 51, 1, 50, 51}));
    CHECK(packets.RebuildGetMaps({}).payload.empty());
    CHECK_NOTHROW(ClientPacketWriter::Validate(protocol, maps));

    const auto report = std::vector<u8>(ClientPackets::MAX_TRACKING_REPORT, 7);
    const auto tracking = packets.EventTracking(report);
    CHECK(tracking.prot == ClientProt_e::EventTracking);
    CHECK(tracking.payload == report);
    CHECK_NOTHROW(ClientPacketWriter::Validate(protocol, tracking));
    CHECK_THROWS_AS(packets.EventTracking({}), std::invalid_argument);
    CHECK_THROWS_AS(packets.EventTracking(std::vector<u8>(ClientPackets::MAX_TRACKING_REPORT + 1)), std::invalid_argument);

    CHECK_THROWS_AS(PACKETS.RebuildGetMaps({}), std::invalid_argument);
    CHECK_THROWS_AS(PACKETS.EventTracking(report), std::invalid_argument);
}
