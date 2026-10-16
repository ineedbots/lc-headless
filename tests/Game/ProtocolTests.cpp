#include "pch.hpp"

#include "Config/Revision_e.hpp"
#include "Game/Protocol/Base37.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/Protocol.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Game/Protocol/WordPack.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>

namespace
{
    struct ProtRow_s
    {
        std::string_view name;
        u8 opcode;
        s32 size;
    };

    // Every opcode and size from the engines' ServerGameProt.ts, ServerGameZoneProt.ts and ClientGameProt.ts,
    // as in RevisionDesign.md's Appendix A.
    // clang-format off
    constexpr auto SERVER_ROWS_225 = std::to_array<ProtRow_s>({
        {"NPC_INFO", 1, -2}, {"IF_SETCOLOUR", 2, 4}, {"CAM_MOVETO", 3, 6}, {"MESSAGE_GAME", 4, -1}, {"UPDATE_ZONE_PARTIAL_FOLLOWS", 7, 2},
        {"SYNTH_SOUND", 12, 5}, {"CAM_SHAKE", 13, 4}, {"IF_OPENCHAT", 14, 2}, {"UPDATE_INV_STOP_TRANSMIT", 15, 2}, {"UNSET_MAP_FLAG", 19, 0},
        {"DATA_LOC_DONE", 20, 2}, {"UPDATE_IGNORELIST", 21, -2}, {"UPDATE_RUNWEIGHT", 22, 2}, {"LOC_MERGE", 23, 14}, {"HINT_ARROW", 25, 6},
        {"IF_SETHIDE", 26, 3}, {"IF_OPENMAIN_SIDE", 28, 4}, {"CHAT_FILTER_SETTINGS", 32, 3}, {"MESSAGE_PRIVATE", 41, -1}, {"LOC_ANIM", 42, 4},
        {"UPDATE_REBOOT_TIMER", 43, 2}, {"UPDATE_STAT", 44, 6}, {"IF_SETOBJECT", 46, 6}, {"OBJ_DEL", 49, 3}, {"OBJ_REVEAL", 50, 7},
        {"MIDI_SONG", 54, -1}, {"LOC_ADD_CHANGE", 59, 4}, {"UPDATE_RUNENERGY", 68, 1}, {"MAP_PROJANIM", 69, 15}, {"CAM_LOOKAT", 74, 6},
        {"LOC_DEL", 76, 2}, {"DATA_LAND_DONE", 80, 2}, {"IF_SETTAB_ACTIVE", 84, 1}, {"IF_SETMODEL", 87, 4}, {"UPDATE_INV_FULL", 98, -2},
        {"IF_SETRECOL", 103, 6}, {"TUT_FLASH", 126, 1}, {"IF_CLOSE", 129, 0}, {"DATA_LAND", 132, -2}, {"FINISH_TRACKING", 133, 0},
        {"UPDATE_ZONE_FULL_FOLLOWS", 135, 2}, {"RESET_ANIMS", 136, 0}, {"UPDATE_PID", 139, 2}, {"LAST_LOGIN_INFO", 140, 9}, {"LOGOUT", 142, 0},
        {"IF_SETANIM", 146, 4}, {"VARP_SMALL", 150, 3}, {"OBJ_COUNT", 151, 7}, {"UPDATE_FRIENDLIST", 152, 9},
        {"UPDATE_ZONE_PARTIAL_ENCLOSED", 162, -2}, {"IF_SETTAB", 167, 3}, {"IF_OPENMAIN", 168, 2}, {"VARP_LARGE", 175, 6}, {"PLAYER_INFO", 184, -2},
        {"TUT_OPEN", 185, 2}, {"MAP_ANIM", 191, 6}, {"RESET_CLIENT_VARCACHE", 193, 0}, {"IF_OPENSIDE", 195, 2}, {"IF_SETPLAYERHEAD", 197, 2},
        {"IF_SETTEXT", 201, -2}, {"IF_SETNPCHEAD", 204, 4}, {"IF_SETPOSITION", 209, 6}, {"MIDI_JINGLE", 212, -2}, {"UPDATE_INV_PARTIAL", 213, -2},
        {"DATA_LOC", 220, -2}, {"OBJ_ADD", 223, 5}, {"ENABLE_TRACKING", 226, 0}, {"REBUILD_NORMAL", 237, -2}, {"CAM_RESET", 239, 0},
        {"P_COUNTDIALOG", 243, 0}, {"SET_MULTIWAY", 254, 1}
    });

    constexpr auto SERVER_ROWS_289 = std::to_array<ProtRow_s>({
        {"TUT_OPEN", 12, 2}, {"CHAT_FILTER_SETTINGS", 13, 3}, {"IF_SETOBJECT", 18, 6}, {"SET_PLAYER_OP", 21, -1}, {"IF_CLOSE", 23, 0},
        {"UPDATE_INV_STOP_TRANSMIT", 28, 2}, {"MIDI_JINGLE", 29, 4}, {"IF_SETPLAYERHEAD", 30, 2}, {"P_COUNTDIALOG", 35, 0},
        {"UPDATE_RUNWEIGHT", 46, 2}, {"UPDATE_IGNORELIST", 47, -2}, {"IF_OPENMAIN_SIDE", 55, 4}, {"IF_SETTEXT", 59, -2}, {"OBJ_ADD", 60, 5},
        {"IF_SETTAB", 63, 3}, {"NPC_INFO", 65, -2}, {"OBJ_DEL", 71, 3}, {"CAM_MOVETO", 73, 6}, {"VARP_SMALL", 75, 3}, {"UPDATE_INV_PARTIAL", 76, -2},
        {"IF_SETPOSITION", 79, 6}, {"IF_OPENCHAT", 81, 2}, {"CAM_LOOKAT", 82, 6}, {"LOC_MERGE", 83, 14}, {"MAP_PROJANIM", 87, 15},
        {"LOC_ADD_CHANGE", 90, 4}, {"VARP_LARGE", 97, 6}, {"LOC_ANIM", 106, 4}, {"UPDATE_INV_FULL", 107, -2},
        {"UPDATE_ZONE_PARTIAL_ENCLOSED", 112, -2}, {"HINT_ARROW", 115, 6}, {"OBJ_COUNT", 117, 7}, {"IF_OPENMAIN", 119, 2}, {"UPDATE_PID", 120, 3},
        {"LOGOUT", 121, 0}, {"IF_OPENOVERLAY", 127, 2}, {"CAM_RESET", 133, 0}, {"MINIMAP_TOGGLE", 136, 1}, {"IF_SETHIDE", 138, 3},
        {"UPDATE_ZONE_FULL_FOLLOWS", 144, 2}, {"UPDATE_STAT", 154, 6}, {"UPDATE_ZONE_PARTIAL_FOLLOWS", 155, 2}, {"IF_SETCOLOUR", 160, 4},
        {"UNSET_MAP_FLAG", 164, 0}, {"UPDATE_FRIENDLIST", 168, 9}, {"RESET_CLIENT_VARCACHE", 172, 0}, {"OBJ_REVEAL", 176, 7},
        {"SYNTH_SOUND", 177, 5}, {"TUT_FLASH", 181, 1}, {"IF_SETSCROLLPOS", 184, 4}, {"MIDI_SONG", 187, 2}, {"PLAYER_INFO", 188, -2},
        {"IF_SETTAB_ACTIVE", 189, 1}, {"LOC_DEL", 194, 2}, {"UPDATE_RUNENERGY", 195, 1}, {"MESSAGE_GAME", 196, -1}, {"RESET_ANIMS", 201, 0},
        {"UPDATE_REBOOT_TIMER", 204, 2}, {"CAM_SHAKE", 208, 4}, {"IF_SETANIM", 211, 4}, {"REBUILD_NORMAL", 219, 4}, {"IF_SETMODEL", 222, 4},
        {"MAP_ANIM", 233, 6}, {"FRIENDLIST_LOADED", 235, 1}, {"MESSAGE_PRIVATE", 243, -1}, {"IF_SETNPCHEAD", 244, 4}, {"SET_MULTIWAY", 247, 1},
        {"IF_OPENSIDE", 252, 2}, {"LAST_LOGIN_INFO", 253, 10}
    });

    constexpr auto CLIENT_ROWS_225 = std::to_array<ProtRow_s>({
        {"ANTICHEAT_OPLOGIC8", 2, 2}, {"CLIENT_CHEAT", 4, -1}, {"INV_BUTTON5", 6, 6}, {"ANTICHEAT_OPLOGIC1", 7, 4}, {"OPNPC2", 8, 2},
        {"OPLOCT", 9, 8}, {"FRIENDLIST_DEL", 11, 8}, {"ANTICHEAT_OPLOGIC7", 17, 4}, {"OPNPC3", 27, 2}, {"ANTICHEAT_OPLOGIC3", 30, 3},
        {"INV_BUTTON1", 31, 6}, {"INV_BUTTON4", 38, 6}, {"OPOBJ2", 40, 6}, {"OPHELDT", 48, 8}, {"IDK_SAVEDESIGN", 52, 13}, {"OPPLAYER2", 53, 2},
        {"INV_BUTTON2", 59, 6}, {"ANTICHEAT_OPLOGIC6", 66, 4}, {"IDLE_TIMER", 70, 0}, {"OPHELD2", 71, 6}, {"OPLOCU", 75, 12},
        {"IGNORELIST_ADD", 79, 8}, {"EVENT_TRACKING", 81, -2}, {"ANTICHEAT_CYCLELOGIC5", 85, 0}, {"ANTICHEAT_OPLOGIC2", 88, 4},
        {"MOVE_OPCLICK", 93, -1}, {"OPLOC3", 96, 6}, {"OPLOC4", 97, 6}, {"OPNPC5", 100, 2}, {"NO_TIMEOUT", 108, 0}, {"OPNPC4", 113, 2},
        {"OPLOC5", 116, 6}, {"FRIENDLIST_ADD", 118, 8}, {"OPHELDU", 130, 12}, {"OPHELD3", 133, 6}, {"OPNPCT", 134, 4}, {"OPOBJT", 138, 8},
        {"OPOBJ1", 140, 6}, {"ANTICHEAT_CYCLELOGIC2", 146, -1}, {"MESSAGE_PRIVATE", 148, -1}, {"REBUILD_GETMAPS", 150, -1}, {"IF_BUTTON", 155, 2},
        {"OPHELD4", 157, 6}, {"MESSAGE_PUBLIC", 158, -1}, {"INV_BUTTOND", 159, 6}, {"OPPLAYER1", 164, 2}, {"MOVE_MINIMAPCLICK", 165, -1},
        {"IGNORELIST_DEL", 171, 8}, {"OPLOC2", 172, 6}, {"TUT_CLICKSIDE", 175, 1}, {"ANTICHEAT_OPLOGIC4", 176, 2}, {"OPPLAYERT", 177, 4},
        {"OPOBJ4", 178, 6}, {"MOVE_GAMECLICK", 181, -1}, {"OPPLAYER3", 185, 2}, {"EVENT_CAMERA_POSITION", 189, 6}, {"REPORT_ABUSE", 190, 10},
        {"OPNPC1", 194, 2}, {"OPHELD1", 195, 6}, {"OPOBJ3", 200, 6}, {"OPNPCU", 202, 8}, {"OPPLAYER4", 206, 2}, {"OPHELD5", 211, 6},
        {"INV_BUTTON3", 212, 6}, {"ANTICHEAT_CYCLELOGIC3", 215, 3}, {"ANTICHEAT_CYCLELOGIC6", 219, -1}, {"ANTICHEAT_OPLOGIC5", 220, 0},
        {"CLOSE_MODAL", 231, 0}, {"ANTICHEAT_CYCLELOGIC1", 233, 1}, {"RESUME_PAUSEBUTTON", 235, 2}, {"ANTICHEAT_CYCLELOGIC4", 236, 4},
        {"RESUME_P_COUNTDIALOG", 237, 4}, {"ANTICHEAT_OPLOGIC9", 238, 1}, {"OPOBJU", 239, 12}, {"CHAT_SETMODE", 244, 3}, {"OPLOC1", 245, 6},
        {"OPOBJ5", 247, 6}, {"OPPLAYERU", 248, 8}
    });

    constexpr auto CLIENT_ROWS_289 = std::to_array<ProtRow_s>({
        {"OPOBJ2", 4, 6}, {"OPLOC1", 10, 6}, {"OPPLAYER3", 13, 2}, {"OPPLAYERU", 16, 8}, {"OPNPC2", 21, 2}, {"OPOBJ5", 22, 6},
        {"IDK_SAVEDESIGN", 27, 13}, {"OPNPC4", 30, 2}, {"CLIENT_CHEAT", 34, -1}, {"OPHELD3", 40, 6}, {"INV_BUTTON1", 44, 6}, {"OPLOC2", 45, 6},
        {"ANTICHEAT_OPLOGIC5", 46, 1}, {"ANTICHEAT_OPLOGIC4", 49, 1}, {"OPPLAYER2", 51, 2}, {"OPLOC4", 53, 6}, {"OPOBJU", 55, 12},
        {"MOVE_OPCLICK", 67, -1}, {"OPPLAYER5", 69, 2}, {"ANTICHEAT_OPLOGIC6", 73, 2}, {"OPHELD1", 76, 6}, {"OPHELD5", 79, 6},
        {"ANTICHEAT_OPLOGIC2", 81, 2}, {"ANTICHEAT_CYCLELOGIC5", 85, 0}, {"IF_BUTTON", 86, 2}, {"ANTICHEAT_OPLOGIC9", 88, 3}, {"CLOSE_MODAL", 93, 0},
        {"REPORT_ABUSE", 94, 10}, {"OPOBJ1", 97, 6}, {"MESSAGE_PRIVATE", 107, -1}, {"OPNPCT", 108, 4}, {"OPOBJ3", 110, 6}, {"INV_BUTTON2", 111, 6},
        {"OPHELDT", 112, 8}, {"ANTICHEAT_OPLOGIC3", 122, 4}, {"INV_BUTTON3", 124, 6}, {"ANTICHEAT_CYCLELOGIC3", 125, 1}, {"OPLOC5", 126, 6},
        {"ANTICHEAT_CYCLELOGIC1", 130, -1}, {"ANTICHEAT_OPLOGIC7", 133, 4}, {"ANTICHEAT_CYCLELOGIC4", 137, 1}, {"OPPLAYERT", 138, 4},
        {"IDLE_TIMER", 145, 0}, {"TUT_CLICKSIDE", 146, 1}, {"OPOBJ4", 147, 6}, {"EVENT_APPLET_FOCUS", 149, 1}, {"ANTICHEAT_CYCLELOGIC2", 154, -1},
        {"MESSAGE_PUBLIC", 156, -1}, {"OPNPCU", 160, 8}, {"CHAT_SETMODE", 161, 3}, {"RESUME_PAUSEBUTTON", 166, 2}, {"ANTICHEAT_OPLOGIC8", 168, 1},
        {"OPHELD2", 177, 6}, {"OPNPC3", 178, 2}, {"RESUME_P_COUNTDIALOG", 180, 4}, {"NO_TIMEOUT", 181, 0}, {"OPLOCU", 184, 12},
        {"OPPLAYER4", 189, 2}, {"OPHELD4", 191, 6}, {"IGNORELIST_ADD", 192, 8}, {"EVENT_CAMERA_POSITION", 193, 4}, {"ANTICHEAT_OPLOGIC1", 195, 4},
        {"OPLOC3", 196, 6}, {"OPHELDU", 200, 12}, {"FRIENDLIST_DEL", 203, 8}, {"MAP_BUILD_COMPLETE", 214, 0}, {"OPLOCT", 218, 8},
        {"OPPLAYER1", 220, 2}, {"EVENT_MOUSE_CLICK", 224, 4}, {"INV_BUTTON5", 227, 6}, {"EVENT_MOUSE_MOVE", 229, -1},
        {"ANTICHEAT_CYCLELOGIC7", 232, 0}, {"MOVE_GAMECLICK", 234, -1}, {"FRIENDLIST_ADD", 235, 8}, {"MOVE_MINIMAPCLICK", 236, -1},
        {"OPOBJT", 241, 8}, {"OPNPC5", 247, 2}, {"INV_BUTTON4", 248, 6}, {"IGNORELIST_DEL", 251, 8}, {"OPNPC1", 252, 2}, {"INV_BUTTOND", 253, 7},
        {"ANTICHEAT_CYCLELOGIC6", 255, 1}
    });
    // clang-format on

    constexpr auto ZONE_OPCODES_225 = std::to_array<u8>({23, 42, 49, 50, 59, 69, 76, 151, 191, 223});
    constexpr auto ZONE_OPCODES_289 = std::to_array<u8>({60, 71, 83, 87, 90, 106, 117, 176, 194, 233});

    constexpr auto CLIENT_ONLY_225 = std::to_array({ClientProt_e::EventTracking, ClientProt_e::RebuildGetMaps});
    constexpr auto CLIENT_ONLY_289 = std::to_array({
        ClientProt_e::AnticheatCycleLogic7,
        ClientProt_e::EventAppletFocus,
        ClientProt_e::EventMouseClick,
        ClientProt_e::EventMouseMove,
        ClientProt_e::MapBuildComplete,
        ClientProt_e::OpPlayer5,
    });

    constexpr auto BASE37_LIMIT = u64{6582952005840035281};

    struct RevisionRows_s
    {
        Revision_e revision;
        std::span<const ProtRow_s> serverRows;
        std::span<const ProtRow_s> clientRows;
        std::span<const u8> zoneOpcodes;
        std::span<const ClientProt_e> missingClientProts;
    };

    RevisionRows_s GetRows(Revision_e revision)
    {
        switch (revision)
        {
        case Revision_e::Rev225:
            return {revision, SERVER_ROWS_225, CLIENT_ROWS_225, ZONE_OPCODES_225, CLIENT_ONLY_289};
        case Revision_e::Rev289:
            return {revision, SERVER_ROWS_289, CLIENT_ROWS_289, ZONE_OPCODES_289, CLIENT_ONLY_225};
        }

        assert(false && "Unhandled Revision_e");
        return {};
    }

    const ProtRow_s* FindRow(std::span<const ProtRow_s> rows, u8 opcode)
    {
        const auto found = std::ranges::find(rows, opcode, &ProtRow_s::opcode);
        return found == rows.end() ? nullptr : &*found;
    }

    std::vector<u8> Bytes(std::initializer_list<u8> bytes)
    {
        return bytes;
    }
}

TEST_CASE("Each revision's server table matches the engine's for all 256 opcodes", "[Protocol]")
{
    static_assert(SERVER_ROWS_225.size() == 71);
    static_assert(SERVER_ROWS_289.size() == 69);

    const auto rows = GetRows(GENERATE(Revision_e::Rev225, Revision_e::Rev289));
    const auto protocol = Protocol{rows.revision};
    CAPTURE(static_cast<u16>(rows.revision));

    for (auto opcode = 0; opcode < 256; ++opcode)
    {
        CAPTURE(opcode);

        const auto* const row = FindRow(rows.serverRows, static_cast<u8>(opcode));
        const auto prot = protocol.FindServerProt(static_cast<u8>(opcode));
        REQUIRE(prot.has_value() == (row != nullptr));
        if (!prot)
        {
            continue;
        }

        CHECK(ServerProt::GetName(*prot) == row->name);
        CHECK(protocol.GetSize(*prot) == row->size);
    }
}

TEST_CASE("Each revision's client table matches the engine's", "[Protocol]")
{
    static_assert(CLIENT_ROWS_225.size() == 78);
    static_assert(CLIENT_ROWS_289.size() == 82);

    const auto rows = GetRows(GENERATE(Revision_e::Rev225, Revision_e::Rev289));
    const auto protocol = Protocol{rows.revision};
    CAPTURE(static_cast<u16>(rows.revision));

    auto present = std::size_t{0};
    for (auto index = std::size_t{0}; index < ClientProtTable_s::PROT_COUNT; ++index)
    {
        const auto prot = static_cast<ClientProt_e>(index);
        CAPTURE(ClientProt::GetName(prot));

        if (!protocol.Has(prot))
        {
            continue;
        }

        ++present;
        const auto* const row = FindRow(rows.clientRows, protocol.GetOpcode(prot));
        REQUIRE(row != nullptr);
        CHECK(row->name == ClientProt::GetName(prot));
        CHECK(row->size == protocol.GetSize(prot));
    }

    CHECK(present == rows.clientRows.size());
}

TEST_CASE("Each revision lacks the client packets only the other has", "[Protocol]")
{
    const auto rows = GetRows(GENERATE(Revision_e::Rev225, Revision_e::Rev289));
    const auto protocol = Protocol{rows.revision};
    CAPTURE(static_cast<u16>(rows.revision));

    for (const auto prot : rows.missingClientProts)
    {
        CAPTURE(ClientProt::GetName(prot));
        CHECK_FALSE(protocol.Has(prot));
        CHECK_THROWS_AS(protocol.Require(prot), std::invalid_argument);
        CHECK_THROWS_AS(protocol.GetOpcode(prot), std::invalid_argument);
        CHECK_THROWS_AS(protocol.GetSize(prot), std::invalid_argument);
    }
}

TEST_CASE("Each revision marks exactly the zone sub-packets", "[Protocol]")
{
    const auto rows = GetRows(GENERATE(Revision_e::Rev225, Revision_e::Rev289));
    const auto protocol = Protocol{rows.revision};
    CAPTURE(static_cast<u16>(rows.revision));

    for (auto opcode = 0; opcode < 256; ++opcode)
    {
        CAPTURE(opcode);

        const auto prot = protocol.FindServerProt(static_cast<u8>(opcode));
        const auto isZone = std::ranges::find(rows.zoneOpcodes, static_cast<u8>(opcode)) != rows.zoneOpcodes.end();
        CHECK((prot && ServerProt::IsZoneProt(*prot)) == isZone);
    }
}

TEST_CASE("Every logical packet has a distinct engine name", "[Protocol]")
{
    auto serverNames = std::vector<std::string_view>{};
    for (auto index = std::size_t{0}; index < ServerProtTable_s::PROT_COUNT; ++index)
    {
        serverNames.push_back(ServerProt::GetName(static_cast<ServerProt_e>(index)));
    }

    auto clientNames = std::vector<std::string_view>{};
    for (auto index = std::size_t{0}; index < ClientProtTable_s::PROT_COUNT; ++index)
    {
        clientNames.push_back(ClientProt::GetName(static_cast<ClientProt_e>(index)));
    }

    for (auto* const names : {&serverNames, &clientNames})
    {
        CHECK(std::ranges::none_of(*names, [](std::string_view name)
        {
            return name.empty();
        }));

        std::ranges::sort(*names);
        CHECK(std::ranges::adjacent_find(*names) == names->end());
    }

    CHECK(ServerProt::GetName(ServerProt_e::PlayerInfo) == "PLAYER_INFO");
    CHECK(ClientProt::GetName(ClientProt_e::NoTimeout) == "NO_TIMEOUT");
}

TEST_CASE("Base37 encodes names", "[Base37]")
{
    CHECK(Base37::Encode("a") == 1);
    CHECK(Base37::Encode("z") == 26);
    CHECK(Base37::Encode("0") == 27);
    CHECK(Base37::Encode("9") == 36);
    CHECK(Base37::Encode("ab") == 39);
    CHECK(Base37::Encode("AB") == 39);
    CHECK(Base37::Encode("a b") == 1371);
    CHECK(Base37::Encode("a_b") == 1371);
    CHECK(Base37::Encode("  ab\t") == 39);
    CHECK(Base37::Encode("ab_") == 39);
    CHECK(Base37::Encode("") == 0);
    CHECK(Base37::Encode("abcdefghijklmnop") == Base37::Encode("abcdefghijkl"));
}

TEST_CASE("Base37 decodes names", "[Base37]")
{
    CHECK(Base37::Decode(39) == "ab");
    CHECK(Base37::Decode(1371) == "a_b");
    CHECK(Base37::Decode(Base37::Encode("zezima")) == "zezima");
    CHECK(Base37::Decode(Base37::Encode("bot 123")) == "bot_123");

    SECTION("invalid values decode as invalid_name")
    {
        CHECK(Base37::Decode(0) == Base37::INVALID_NAME);
        CHECK(Base37::Decode(37) == Base37::INVALID_NAME);
        CHECK(Base37::Decode(BASE37_LIMIT) == Base37::INVALID_NAME);
        CHECK(Base37::Decode(BASE37_LIMIT - 1) != Base37::INVALID_NAME);
    }

    SECTION("display names capitalise each word")
    {
        CHECK(Base37::ToDisplayName("hello_world") == "Hello World");
        CHECK(Base37::ToDisplayName("a_1") == "A 1");
        CHECK(Base37::ToDisplayName("") == "");
        CHECK(Base37::DecodeDisplayName(Base37::Encode("Zezima")) == "Zezima");
    }
}

TEST_CASE("WordPack packs text into nibbles", "[WordPack]")
{
    CHECK(WordPack::Pack("hello") == Bytes({0x61, 0xBB, 0x40}));
    CHECK(WordPack::Pack("HELLO") == Bytes({0x61, 0xBB, 0x40}));
    CHECK(WordPack::Pack("m") == Bytes({0xD0}));
    CHECK(WordPack::Pack("am") == Bytes({0x3D, 0x00}));
    CHECK(WordPack::Pack("~") == Bytes({0x00}));
    CHECK(WordPack::Pack("\xA3") == Bytes({0xFA}));
    CHECK(WordPack::Pack("").empty());
    CHECK(WordPack::Pack(std::string(100, 'e')) == std::vector<u8>(40, 0x11));
}

TEST_CASE("WordPack unpacks with sentence case", "[WordPack]")
{
    CHECK(WordPack::Unpack(Bytes({0x61, 0xBB, 0x40})) == "Hello ");
    CHECK(WordPack::Unpack(Bytes({0xD0})) == "M");
    CHECK(WordPack::Unpack(Bytes({0x3D, 0x00})) == "Am ");
    CHECK(WordPack::Unpack(Bytes({0xFA})) == "\xA3");
    CHECK(WordPack::Unpack(WordPack::Pack("hi. there! ok")) == "Hi. There! Ok");
    CHECK(WordPack::Unpack(WordPack::Pack("price: 5$ [x] @y")) == "Price: 5$ [x] @y");

    SECTION("unpacking stops once 100 characters are out")
    {
        CHECK(WordPack::Unpack(std::vector<u8>(60, 0x11)).size() == WordPack::MAX_UNPACK_LENGTH);
    }
}
