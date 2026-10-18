#include "pch.hpp"
#include "ServerProt.hpp"

#include "../../Config/Revision_e.hpp"
#include "ProtTableBuilder.hpp"
#include "WireProt_s.hpp"

namespace
{
    struct ServerProtInfo_s
    {
        ServerProt_e prot;
        std::string_view name;
        bool isZone = false;
    };

    struct ServerProtRow_s
    {
        ServerProt_e prot;
        u8 opcode;
        s32 size;
    };

    constexpr auto SERVER_PROT_INFOS = std::to_array<ServerProtInfo_s>({
        {ServerProt_e::CamLookAt, "CAM_LOOKAT"},
        {ServerProt_e::CamMoveTo, "CAM_MOVETO"},
        {ServerProt_e::CamReset, "CAM_RESET"},
        {ServerProt_e::CamShake, "CAM_SHAKE"},
        {ServerProt_e::ChatFilterSettings, "CHAT_FILTER_SETTINGS"},
        {ServerProt_e::DataLand, "DATA_LAND"},
        {ServerProt_e::DataLandDone, "DATA_LAND_DONE"},
        {ServerProt_e::DataLoc, "DATA_LOC"},
        {ServerProt_e::DataLocDone, "DATA_LOC_DONE"},
        {ServerProt_e::EnableTracking, "ENABLE_TRACKING"},
        {ServerProt_e::FinishTracking, "FINISH_TRACKING"},
        {ServerProt_e::FriendListLoaded, "FRIENDLIST_LOADED"},
        {ServerProt_e::HintArrow, "HINT_ARROW"},
        {ServerProt_e::IfClose, "IF_CLOSE"},
        {ServerProt_e::IfOpenChat, "IF_OPENCHAT"},
        {ServerProt_e::IfOpenMain, "IF_OPENMAIN"},
        {ServerProt_e::IfOpenMainSide, "IF_OPENMAIN_SIDE"},
        {ServerProt_e::IfOpenOverlay, "IF_OPENOVERLAY"},
        {ServerProt_e::IfOpenSide, "IF_OPENSIDE"},
        {ServerProt_e::IfSetAnim, "IF_SETANIM"},
        {ServerProt_e::IfSetColour, "IF_SETCOLOUR"},
        {ServerProt_e::IfSetHide, "IF_SETHIDE"},
        {ServerProt_e::IfSetModel, "IF_SETMODEL"},
        {ServerProt_e::IfSetNpcHead, "IF_SETNPCHEAD"},
        {ServerProt_e::IfSetObject, "IF_SETOBJECT"},
        {ServerProt_e::IfSetPlayerHead, "IF_SETPLAYERHEAD"},
        {ServerProt_e::IfSetPosition, "IF_SETPOSITION"},
        {ServerProt_e::IfSetRecol, "IF_SETRECOL"},
        {ServerProt_e::IfSetScrollPos, "IF_SETSCROLLPOS"},
        {ServerProt_e::IfSetTab, "IF_SETTAB"},
        {ServerProt_e::IfSetTabActive, "IF_SETTAB_ACTIVE"},
        {ServerProt_e::IfSetText, "IF_SETTEXT"},
        {ServerProt_e::LastLoginInfo, "LAST_LOGIN_INFO"},
        {ServerProt_e::LocAddChange, "LOC_ADD_CHANGE", true},
        {ServerProt_e::LocAnim, "LOC_ANIM", true},
        {ServerProt_e::LocDel, "LOC_DEL", true},
        {ServerProt_e::LocMerge, "LOC_MERGE", true},
        {ServerProt_e::Logout, "LOGOUT"},
        {ServerProt_e::MapAnim, "MAP_ANIM", true},
        {ServerProt_e::MapProjAnim, "MAP_PROJANIM", true},
        {ServerProt_e::MessageGame, "MESSAGE_GAME"},
        {ServerProt_e::MessagePrivate, "MESSAGE_PRIVATE"},
        {ServerProt_e::MidiJingle, "MIDI_JINGLE"},
        {ServerProt_e::MidiSong, "MIDI_SONG"},
        {ServerProt_e::MinimapToggle, "MINIMAP_TOGGLE"},
        {ServerProt_e::NpcInfo, "NPC_INFO"},
        {ServerProt_e::ObjAdd, "OBJ_ADD", true},
        {ServerProt_e::ObjCount, "OBJ_COUNT", true},
        {ServerProt_e::ObjDel, "OBJ_DEL", true},
        {ServerProt_e::ObjReveal, "OBJ_REVEAL", true},
        {ServerProt_e::PlayerInfo, "PLAYER_INFO"},
        {ServerProt_e::PCountDialog, "P_COUNTDIALOG"},
        {ServerProt_e::RebuildNormal, "REBUILD_NORMAL"},
        {ServerProt_e::ResetAnims, "RESET_ANIMS"},
        {ServerProt_e::ResetClientVarCache, "RESET_CLIENT_VARCACHE"},
        {ServerProt_e::SetMultiway, "SET_MULTIWAY"},
        {ServerProt_e::SetPlayerOp, "SET_PLAYER_OP"},
        {ServerProt_e::SynthSound, "SYNTH_SOUND"},
        {ServerProt_e::TutFlash, "TUT_FLASH"},
        {ServerProt_e::TutOpen, "TUT_OPEN"},
        {ServerProt_e::UnsetMapFlag, "UNSET_MAP_FLAG"},
        {ServerProt_e::UpdateFriendList, "UPDATE_FRIENDLIST"},
        {ServerProt_e::UpdateIgnoreList, "UPDATE_IGNORELIST"},
        {ServerProt_e::UpdateInvFull, "UPDATE_INV_FULL"},
        {ServerProt_e::UpdateInvPartial, "UPDATE_INV_PARTIAL"},
        {ServerProt_e::UpdateInvStopTransmit, "UPDATE_INV_STOP_TRANSMIT"},
        {ServerProt_e::UpdatePid, "UPDATE_PID"},
        {ServerProt_e::UpdateRebootTimer, "UPDATE_REBOOT_TIMER"},
        {ServerProt_e::UpdateRunEnergy, "UPDATE_RUNENERGY"},
        {ServerProt_e::UpdateRunWeight, "UPDATE_RUNWEIGHT"},
        {ServerProt_e::UpdateStat, "UPDATE_STAT"},
        {ServerProt_e::UpdateZoneFullFollows, "UPDATE_ZONE_FULL_FOLLOWS"},
        {ServerProt_e::UpdateZonePartialEnclosed, "UPDATE_ZONE_PARTIAL_ENCLOSED"},
        {ServerProt_e::UpdateZonePartialFollows, "UPDATE_ZONE_PARTIAL_FOLLOWS"},
        {ServerProt_e::VarpLarge, "VARP_LARGE"},
        {ServerProt_e::VarpSmall, "VARP_SMALL"},
    });

    static_assert(SERVER_PROT_INFOS.size() == ServerProtTable_s::PROT_COUNT, "Every server packet needs a name");
    static_assert(ProtTableBuilder::IsInProtOrder(SERVER_PROT_INFOS), "Server packet names must be in ServerProt_e's order");

    constexpr auto SERVER_PROTS_225 = std::to_array<ServerProtRow_s>({
        {ServerProt_e::CamLookAt, 74, 6},
        {ServerProt_e::CamMoveTo, 3, 6},
        {ServerProt_e::CamReset, 239, 0},
        {ServerProt_e::CamShake, 13, 4},
        {ServerProt_e::ChatFilterSettings, 32, 3},
        {ServerProt_e::DataLand, 132, ServerProt::VAR_SHORT},
        {ServerProt_e::DataLandDone, 80, 2},
        {ServerProt_e::DataLoc, 220, ServerProt::VAR_SHORT},
        {ServerProt_e::DataLocDone, 20, 2},
        {ServerProt_e::EnableTracking, 226, 0},
        {ServerProt_e::FinishTracking, 133, 0},
        {ServerProt_e::HintArrow, 25, 6},
        {ServerProt_e::IfClose, 129, 0},
        {ServerProt_e::IfOpenChat, 14, 2},
        {ServerProt_e::IfOpenMain, 168, 2},
        {ServerProt_e::IfOpenMainSide, 28, 4},
        {ServerProt_e::IfOpenSide, 195, 2},
        {ServerProt_e::IfSetAnim, 146, 4},
        {ServerProt_e::IfSetColour, 2, 4},
        {ServerProt_e::IfSetHide, 26, 3},
        {ServerProt_e::IfSetModel, 87, 4},
        {ServerProt_e::IfSetNpcHead, 204, 4},
        {ServerProt_e::IfSetObject, 46, 6},
        {ServerProt_e::IfSetPlayerHead, 197, 2},
        {ServerProt_e::IfSetPosition, 209, 6},
        {ServerProt_e::IfSetRecol, 103, 6},
        {ServerProt_e::IfSetTab, 167, 3},
        {ServerProt_e::IfSetTabActive, 84, 1},
        {ServerProt_e::IfSetText, 201, ServerProt::VAR_SHORT},
        {ServerProt_e::LastLoginInfo, 140, 9},
        {ServerProt_e::LocAddChange, 59, 4},
        {ServerProt_e::LocAnim, 42, 4},
        {ServerProt_e::LocDel, 76, 2},
        {ServerProt_e::LocMerge, 23, 14},
        {ServerProt_e::Logout, 142, 0},
        {ServerProt_e::MapAnim, 191, 6},
        {ServerProt_e::MapProjAnim, 69, 15},
        {ServerProt_e::MessageGame, 4, ServerProt::VAR_BYTE},
        {ServerProt_e::MessagePrivate, 41, ServerProt::VAR_BYTE},
        {ServerProt_e::MidiJingle, 212, ServerProt::VAR_SHORT},
        {ServerProt_e::MidiSong, 54, ServerProt::VAR_BYTE},
        {ServerProt_e::NpcInfo, 1, ServerProt::VAR_SHORT},
        {ServerProt_e::ObjAdd, 223, 5},
        {ServerProt_e::ObjCount, 151, 7},
        {ServerProt_e::ObjDel, 49, 3},
        {ServerProt_e::ObjReveal, 50, 7},
        {ServerProt_e::PlayerInfo, 184, ServerProt::VAR_SHORT},
        {ServerProt_e::PCountDialog, 243, 0},
        {ServerProt_e::RebuildNormal, 237, ServerProt::VAR_SHORT},
        {ServerProt_e::ResetAnims, 136, 0},
        {ServerProt_e::ResetClientVarCache, 193, 0},
        {ServerProt_e::SetMultiway, 254, 1},
        {ServerProt_e::SynthSound, 12, 5},
        {ServerProt_e::TutFlash, 126, 1},
        {ServerProt_e::TutOpen, 185, 2},
        {ServerProt_e::UnsetMapFlag, 19, 0},
        {ServerProt_e::UpdateFriendList, 152, 9},
        {ServerProt_e::UpdateIgnoreList, 21, ServerProt::VAR_SHORT},
        {ServerProt_e::UpdateInvFull, 98, ServerProt::VAR_SHORT},
        {ServerProt_e::UpdateInvPartial, 213, ServerProt::VAR_SHORT},
        {ServerProt_e::UpdateInvStopTransmit, 15, 2},
        {ServerProt_e::UpdatePid, 139, 2},
        {ServerProt_e::UpdateRebootTimer, 43, 2},
        {ServerProt_e::UpdateRunEnergy, 68, 1},
        {ServerProt_e::UpdateRunWeight, 22, 2},
        {ServerProt_e::UpdateStat, 44, 6},
        {ServerProt_e::UpdateZoneFullFollows, 135, 2},
        {ServerProt_e::UpdateZonePartialEnclosed, 162, ServerProt::VAR_SHORT},
        {ServerProt_e::UpdateZonePartialFollows, 7, 2},
        {ServerProt_e::VarpLarge, 175, 6},
        {ServerProt_e::VarpSmall, 150, 3},
    });

    constexpr auto SERVER_PROTS_274 = std::to_array<ServerProtRow_s>({
        {ServerProt_e::CamLookAt, 233, 6},
        {ServerProt_e::CamMoveTo, 200, 6},
        {ServerProt_e::CamReset, 101, 0},
        {ServerProt_e::CamShake, 64, 4},
        {ServerProt_e::ChatFilterSettings, 114, 3},
        {ServerProt_e::FriendListLoaded, 185, 1},
        {ServerProt_e::HintArrow, 156, 6},
        {ServerProt_e::IfClose, 171, 0},
        {ServerProt_e::IfOpenChat, 166, 2},
        {ServerProt_e::IfOpenMain, 211, 2},
        {ServerProt_e::IfOpenMainSide, 158, 4},
        {ServerProt_e::IfOpenOverlay, 240, 2},
        {ServerProt_e::IfOpenSide, 16, 2},
        {ServerProt_e::IfSetAnim, 134, 4},
        {ServerProt_e::IfSetColour, 183, 4},
        {ServerProt_e::IfSetHide, 10, 3},
        {ServerProt_e::IfSetModel, 129, 4},
        {ServerProt_e::IfSetNpcHead, 142, 4},
        {ServerProt_e::IfSetObject, 28, 6},
        {ServerProt_e::IfSetPlayerHead, 192, 2},
        {ServerProt_e::IfSetPosition, 77, 6},
        {ServerProt_e::IfSetScrollPos, 54, 4},
        {ServerProt_e::IfSetTab, 215, 3},
        {ServerProt_e::IfSetTabActive, 241, 1},
        {ServerProt_e::IfSetText, 44, ServerProt::VAR_SHORT},
        {ServerProt_e::LastLoginInfo, 91, 10},
        {ServerProt_e::LocAddChange, 138, 4},
        {ServerProt_e::LocAnim, 48, 4},
        {ServerProt_e::LocDel, 173, 2},
        {ServerProt_e::LocMerge, 176, 14},
        {ServerProt_e::Logout, 88, 0},
        {ServerProt_e::MapAnim, 85, 6},
        {ServerProt_e::MapProjAnim, 107, 15},
        {ServerProt_e::MessageGame, 161, ServerProt::VAR_BYTE},
        {ServerProt_e::MessagePrivate, 235, ServerProt::VAR_BYTE},
        {ServerProt_e::MidiJingle, 15, 4},
        {ServerProt_e::MidiSong, 23, 2},
        {ServerProt_e::MinimapToggle, 194, 1},
        {ServerProt_e::NpcInfo, 197, ServerProt::VAR_SHORT},
        {ServerProt_e::ObjAdd, 81, 5},
        {ServerProt_e::ObjCount, 95, 7},
        {ServerProt_e::ObjDel, 52, 3},
        {ServerProt_e::ObjReveal, 219, 7},
        {ServerProt_e::PlayerInfo, 167, ServerProt::VAR_SHORT},
        {ServerProt_e::PCountDialog, 210, 0},
        {ServerProt_e::RebuildNormal, 231, 4},
        {ServerProt_e::ResetAnims, 47, 0},
        {ServerProt_e::ResetClientVarCache, 190, 0},
        {ServerProt_e::SetMultiway, 207, 1},
        {ServerProt_e::SetPlayerOp, 17, ServerProt::VAR_BYTE},
        {ServerProt_e::SynthSound, 34, 5},
        {ServerProt_e::TutFlash, 90, 1},
        {ServerProt_e::TutOpen, 130, 2},
        {ServerProt_e::UnsetMapFlag, 115, 0},
        {ServerProt_e::UpdateFriendList, 247, 9},
        {ServerProt_e::UpdateIgnoreList, 3, ServerProt::VAR_SHORT},
        {ServerProt_e::UpdateInvFull, 106, ServerProt::VAR_SHORT},
        {ServerProt_e::UpdateInvPartial, 172, ServerProt::VAR_SHORT},
        {ServerProt_e::UpdateInvStopTransmit, 227, 2},
        {ServerProt_e::UpdatePid, 133, 3},
        {ServerProt_e::UpdateRebootTimer, 89, 2},
        {ServerProt_e::UpdateRunEnergy, 83, 1},
        {ServerProt_e::UpdateRunWeight, 67, 2},
        {ServerProt_e::UpdateStat, 105, 6},
        {ServerProt_e::UpdateZoneFullFollows, 153, 2},
        {ServerProt_e::UpdateZonePartialEnclosed, 195, ServerProt::VAR_SHORT},
        {ServerProt_e::UpdateZonePartialFollows, 32, 2},
        {ServerProt_e::VarpLarge, 245, 6},
        {ServerProt_e::VarpSmall, 203, 3},
    });

    constexpr auto SERVER_PROTS_289 = std::to_array<ServerProtRow_s>({
        {ServerProt_e::CamLookAt, 82, 6},
        {ServerProt_e::CamMoveTo, 73, 6},
        {ServerProt_e::CamReset, 133, 0},
        {ServerProt_e::CamShake, 208, 4},
        {ServerProt_e::ChatFilterSettings, 13, 3},
        {ServerProt_e::FriendListLoaded, 235, 1},
        {ServerProt_e::HintArrow, 115, 6},
        {ServerProt_e::IfClose, 23, 0},
        {ServerProt_e::IfOpenChat, 81, 2},
        {ServerProt_e::IfOpenMain, 119, 2},
        {ServerProt_e::IfOpenMainSide, 55, 4},
        {ServerProt_e::IfOpenOverlay, 127, 2},
        {ServerProt_e::IfOpenSide, 252, 2},
        {ServerProt_e::IfSetAnim, 211, 4},
        {ServerProt_e::IfSetColour, 160, 4},
        {ServerProt_e::IfSetHide, 138, 3},
        {ServerProt_e::IfSetModel, 222, 4},
        {ServerProt_e::IfSetNpcHead, 244, 4},
        {ServerProt_e::IfSetObject, 18, 6},
        {ServerProt_e::IfSetPlayerHead, 30, 2},
        {ServerProt_e::IfSetPosition, 79, 6},
        {ServerProt_e::IfSetScrollPos, 184, 4},
        {ServerProt_e::IfSetTab, 63, 3},
        {ServerProt_e::IfSetTabActive, 189, 1},
        {ServerProt_e::IfSetText, 59, ServerProt::VAR_SHORT},
        {ServerProt_e::LastLoginInfo, 253, 10},
        {ServerProt_e::LocAddChange, 90, 4},
        {ServerProt_e::LocAnim, 106, 4},
        {ServerProt_e::LocDel, 194, 2},
        {ServerProt_e::LocMerge, 83, 14},
        {ServerProt_e::Logout, 121, 0},
        {ServerProt_e::MapAnim, 233, 6},
        {ServerProt_e::MapProjAnim, 87, 15},
        {ServerProt_e::MessageGame, 196, ServerProt::VAR_BYTE},
        {ServerProt_e::MessagePrivate, 243, ServerProt::VAR_BYTE},
        {ServerProt_e::MidiJingle, 29, 4},
        {ServerProt_e::MidiSong, 187, 2},
        {ServerProt_e::MinimapToggle, 136, 1},
        {ServerProt_e::NpcInfo, 65, ServerProt::VAR_SHORT},
        {ServerProt_e::ObjAdd, 60, 5},
        {ServerProt_e::ObjCount, 117, 7},
        {ServerProt_e::ObjDel, 71, 3},
        {ServerProt_e::ObjReveal, 176, 7},
        {ServerProt_e::PlayerInfo, 188, ServerProt::VAR_SHORT},
        {ServerProt_e::PCountDialog, 35, 0},
        {ServerProt_e::RebuildNormal, 219, 4},
        {ServerProt_e::ResetAnims, 201, 0},
        {ServerProt_e::ResetClientVarCache, 172, 0},
        {ServerProt_e::SetMultiway, 247, 1},
        {ServerProt_e::SetPlayerOp, 21, ServerProt::VAR_BYTE},
        {ServerProt_e::SynthSound, 177, 5},
        {ServerProt_e::TutFlash, 181, 1},
        {ServerProt_e::TutOpen, 12, 2},
        {ServerProt_e::UnsetMapFlag, 164, 0},
        {ServerProt_e::UpdateFriendList, 168, 9},
        {ServerProt_e::UpdateIgnoreList, 47, ServerProt::VAR_SHORT},
        {ServerProt_e::UpdateInvFull, 107, ServerProt::VAR_SHORT},
        {ServerProt_e::UpdateInvPartial, 76, ServerProt::VAR_SHORT},
        {ServerProt_e::UpdateInvStopTransmit, 28, 2},
        {ServerProt_e::UpdatePid, 120, 3},
        {ServerProt_e::UpdateRebootTimer, 204, 2},
        {ServerProt_e::UpdateRunEnergy, 195, 1},
        {ServerProt_e::UpdateRunWeight, 46, 2},
        {ServerProt_e::UpdateStat, 154, 6},
        {ServerProt_e::UpdateZoneFullFollows, 144, 2},
        {ServerProt_e::UpdateZonePartialEnclosed, 112, ServerProt::VAR_SHORT},
        {ServerProt_e::UpdateZonePartialFollows, 155, 2},
        {ServerProt_e::VarpLarge, 97, 6},
        {ServerProt_e::VarpSmall, 75, 3},
    });

    static_assert(SERVER_PROTS_225.size() == 71, "Revision 225 has 71 server packets");
    static_assert(SERVER_PROTS_274.size() == 69, "Revision 274 has 69 server packets");
    static_assert(SERVER_PROTS_289.size() == 69, "Revision 289 has 69 server packets");
    static_assert(ProtTableBuilder::HasUniqueRows(SERVER_PROTS_225), "A 225 server opcode or packet is listed twice");
    static_assert(ProtTableBuilder::HasUniqueRows(SERVER_PROTS_274), "A 274 server opcode or packet is listed twice");
    static_assert(ProtTableBuilder::HasUniqueRows(SERVER_PROTS_289), "A 289 server opcode or packet is listed twice");

    constexpr auto TABLE_225 = ProtTableBuilder::Build<ServerProtTable_s>(SERVER_PROTS_225);
    constexpr auto TABLE_274 = ProtTableBuilder::Build<ServerProtTable_s>(SERVER_PROTS_274);
    constexpr auto TABLE_289 = ProtTableBuilder::Build<ServerProtTable_s>(SERVER_PROTS_289);

    const ServerProtInfo_s& GetInfo(ServerProt_e prot)
    {
        const auto index = static_cast<std::size_t>(prot);
        assert(index < SERVER_PROT_INFOS.size() && "ServerProt_e value out of range");
        return SERVER_PROT_INFOS[index];
    }
}

std::string_view ServerProt::GetName(ServerProt_e prot)
{
    return GetInfo(prot).name;
}

bool ServerProt::IsZoneProt(ServerProt_e prot)
{
    return GetInfo(prot).isZone;
}

const ServerProtTable_s& ServerProt::GetTable(Revision_e revision)
{
    switch (revision)
    {
    case Revision_e::Rev225:
        return TABLE_225;
    case Revision_e::Rev274:
        return TABLE_274;
    case Revision_e::Rev289:
        return TABLE_289;
    }

    assert(false && "Unhandled Revision_e");
    return TABLE_225;
}
