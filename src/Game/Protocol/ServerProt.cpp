#include "pch.hpp"
#include "ServerProt.hpp"

namespace
{
    struct ServerProtInfo_s
    {
        ServerProt_e prot;
        s32 size;
        std::string_view name;
        bool isZone = false;
    };

    constexpr auto SERVER_PROTS = std::to_array<ServerProtInfo_s>({
        {ServerProt_e::TutOpen, 2, "TUT_OPEN"},
        {ServerProt_e::ChatFilterSettings, 3, "CHAT_FILTER_SETTINGS"},
        {ServerProt_e::IfSetObject, 6, "IF_SETOBJECT"},
        {ServerProt_e::SetPlayerOp, ServerProt::VAR_BYTE, "SET_PLAYER_OP"},
        {ServerProt_e::IfClose, 0, "IF_CLOSE"},
        {ServerProt_e::UpdateInvStopTransmit, 2, "UPDATE_INV_STOP_TRANSMIT"},
        {ServerProt_e::MidiJingle, 4, "MIDI_JINGLE"},
        {ServerProt_e::IfSetPlayerHead, 2, "IF_SETPLAYERHEAD"},
        {ServerProt_e::PCountDialog, 0, "P_COUNTDIALOG"},
        {ServerProt_e::UpdateRunWeight, 2, "UPDATE_RUNWEIGHT"},
        {ServerProt_e::UpdateIgnoreList, ServerProt::VAR_SHORT, "UPDATE_IGNORELIST"},
        {ServerProt_e::IfOpenMainSide, 4, "IF_OPENMAIN_SIDE"},
        {ServerProt_e::IfSetText, ServerProt::VAR_SHORT, "IF_SETTEXT"},
        {ServerProt_e::ObjAdd, 5, "OBJ_ADD", true},
        {ServerProt_e::IfSetTab, 3, "IF_SETTAB"},
        {ServerProt_e::NpcInfo, ServerProt::VAR_SHORT, "NPC_INFO"},
        {ServerProt_e::ObjDel, 3, "OBJ_DEL", true},
        {ServerProt_e::CamMoveTo, 6, "CAM_MOVETO"},
        {ServerProt_e::VarpSmall, 3, "VARP_SMALL"},
        {ServerProt_e::UpdateInvPartial, ServerProt::VAR_SHORT, "UPDATE_INV_PARTIAL"},
        {ServerProt_e::IfSetPosition, 6, "IF_SETPOSITION"},
        {ServerProt_e::IfOpenChat, 2, "IF_OPENCHAT"},
        {ServerProt_e::CamLookAt, 6, "CAM_LOOKAT"},
        {ServerProt_e::LocMerge, 14, "LOC_MERGE", true},
        {ServerProt_e::MapProjAnim, 15, "MAP_PROJANIM", true},
        {ServerProt_e::LocAddChange, 4, "LOC_ADD_CHANGE", true},
        {ServerProt_e::VarpLarge, 6, "VARP_LARGE"},
        {ServerProt_e::LocAnim, 4, "LOC_ANIM", true},
        {ServerProt_e::UpdateInvFull, ServerProt::VAR_SHORT, "UPDATE_INV_FULL"},
        {ServerProt_e::UpdateZonePartialEnclosed, ServerProt::VAR_SHORT, "UPDATE_ZONE_PARTIAL_ENCLOSED"},
        {ServerProt_e::HintArrow, 6, "HINT_ARROW"},
        {ServerProt_e::ObjCount, 7, "OBJ_COUNT", true},
        {ServerProt_e::IfOpenMain, 2, "IF_OPENMAIN"},
        {ServerProt_e::UpdatePid, 3, "UPDATE_PID"},
        {ServerProt_e::Logout, 0, "LOGOUT"},
        {ServerProt_e::IfOpenOverlay, 2, "IF_OPENOVERLAY"},
        {ServerProt_e::CamReset, 0, "CAM_RESET"},
        {ServerProt_e::MinimapToggle, 1, "MINIMAP_TOGGLE"},
        {ServerProt_e::IfSetHide, 3, "IF_SETHIDE"},
        {ServerProt_e::UpdateZoneFullFollows, 2, "UPDATE_ZONE_FULL_FOLLOWS"},
        {ServerProt_e::UpdateStat, 6, "UPDATE_STAT"},
        {ServerProt_e::UpdateZonePartialFollows, 2, "UPDATE_ZONE_PARTIAL_FOLLOWS"},
        {ServerProt_e::IfSetColour, 4, "IF_SETCOLOUR"},
        {ServerProt_e::UnsetMapFlag, 0, "UNSET_MAP_FLAG"},
        {ServerProt_e::UpdateFriendList, 9, "UPDATE_FRIENDLIST"},
        {ServerProt_e::ResetClientVarCache, 0, "RESET_CLIENT_VARCACHE"},
        {ServerProt_e::ObjReveal, 7, "OBJ_REVEAL", true},
        {ServerProt_e::SynthSound, 5, "SYNTH_SOUND"},
        {ServerProt_e::TutFlash, 1, "TUT_FLASH"},
        {ServerProt_e::IfSetScrollPos, 4, "IF_SETSCROLLPOS"},
        {ServerProt_e::MidiSong, 2, "MIDI_SONG"},
        {ServerProt_e::PlayerInfo, ServerProt::VAR_SHORT, "PLAYER_INFO"},
        {ServerProt_e::IfSetTabActive, 1, "IF_SETTAB_ACTIVE"},
        {ServerProt_e::LocDel, 2, "LOC_DEL", true},
        {ServerProt_e::UpdateRunEnergy, 1, "UPDATE_RUNENERGY"},
        {ServerProt_e::MessageGame, ServerProt::VAR_BYTE, "MESSAGE_GAME"},
        {ServerProt_e::ResetAnims, 0, "RESET_ANIMS"},
        {ServerProt_e::UpdateRebootTimer, 2, "UPDATE_REBOOT_TIMER"},
        {ServerProt_e::CamShake, 4, "CAM_SHAKE"},
        {ServerProt_e::IfSetAnim, 4, "IF_SETANIM"},
        {ServerProt_e::RebuildNormal, 4, "REBUILD_NORMAL"},
        {ServerProt_e::IfSetModel, 4, "IF_SETMODEL"},
        {ServerProt_e::MapAnim, 6, "MAP_ANIM", true},
        {ServerProt_e::FriendListLoaded, 1, "FRIENDLIST_LOADED"},
        {ServerProt_e::MessagePrivate, ServerProt::VAR_BYTE, "MESSAGE_PRIVATE"},
        {ServerProt_e::IfSetNpcHead, 4, "IF_SETNPCHEAD"},
        {ServerProt_e::SetMultiway, 1, "SET_MULTIWAY"},
        {ServerProt_e::IfOpenSide, 2, "IF_OPENSIDE"},
        {ServerProt_e::LastLoginInfo, 10, "LAST_LOGIN_INFO"},
    });

    static_assert(SERVER_PROTS.size() == ServerProt::COUNT, "The server opcode table must list every opcode");

    constexpr auto INFO_BY_OPCODE = []
    {
        auto table = std::array<const ServerProtInfo_s*, 256>{};
        for (const auto& info : SERVER_PROTS)
        {
            table[static_cast<u8>(info.prot)] = &info;
        }

        return table;
    }();
}

std::optional<s32> ServerProt::GetSize(u8 opcode)
{
    const auto* const info = INFO_BY_OPCODE[opcode];
    if (info == nullptr)
    {
        return std::nullopt;
    }

    return info->size;
}

std::string_view ServerProt::GetName(u8 opcode)
{
    const auto* const info = INFO_BY_OPCODE[opcode];
    if (info == nullptr)
    {
        return "UNKNOWN";
    }

    return info->name;
}

bool ServerProt::IsZoneProt(u8 opcode)
{
    const auto* const info = INFO_BY_OPCODE[opcode];
    return info != nullptr && info->isZone;
}
