#include "pch.hpp"
#include "ClientProt.hpp"

namespace
{
    struct ClientProtInfo_s
    {
        ClientProt_e prot;
        s32 size;
        std::string_view name;
    };

    constexpr auto CLIENT_PROTS = std::to_array<ClientProtInfo_s>({
        {ClientProt_e::OpObj2, 6, "OPOBJ2"},
        {ClientProt_e::OpLoc1, 6, "OPLOC1"},
        {ClientProt_e::OpPlayer3, 2, "OPPLAYER3"},
        {ClientProt_e::OpPlayerU, 8, "OPPLAYERU"},
        {ClientProt_e::OpNpc2, 2, "OPNPC2"},
        {ClientProt_e::OpObj5, 6, "OPOBJ5"},
        {ClientProt_e::IdkSaveDesign, 13, "IDK_SAVEDESIGN"},
        {ClientProt_e::OpNpc4, 2, "OPNPC4"},
        {ClientProt_e::ClientCheat, ClientProt::VAR_BYTE, "CLIENT_CHEAT"},
        {ClientProt_e::OpHeld3, 6, "OPHELD3"},
        {ClientProt_e::InvButton1, 6, "INV_BUTTON1"},
        {ClientProt_e::OpLoc2, 6, "OPLOC2"},
        {ClientProt_e::AnticheatOpLogic5, 1, "ANTICHEAT_OPLOGIC5"},
        {ClientProt_e::AnticheatOpLogic4, 1, "ANTICHEAT_OPLOGIC4"},
        {ClientProt_e::OpPlayer2, 2, "OPPLAYER2"},
        {ClientProt_e::OpLoc4, 6, "OPLOC4"},
        {ClientProt_e::OpObjU, 12, "OPOBJU"},
        {ClientProt_e::MoveOpClick, ClientProt::VAR_BYTE, "MOVE_OPCLICK"},
        {ClientProt_e::OpPlayer5, 2, "OPPLAYER5"},
        {ClientProt_e::AnticheatOpLogic6, 2, "ANTICHEAT_OPLOGIC6"},
        {ClientProt_e::OpHeld1, 6, "OPHELD1"},
        {ClientProt_e::OpHeld5, 6, "OPHELD5"},
        {ClientProt_e::AnticheatOpLogic2, 2, "ANTICHEAT_OPLOGIC2"},
        {ClientProt_e::AnticheatCycleLogic5, 0, "ANTICHEAT_CYCLELOGIC5"},
        {ClientProt_e::IfButton, 2, "IF_BUTTON"},
        {ClientProt_e::AnticheatOpLogic9, 3, "ANTICHEAT_OPLOGIC9"},
        {ClientProt_e::CloseModal, 0, "CLOSE_MODAL"},
        {ClientProt_e::ReportAbuse, 10, "REPORT_ABUSE"},
        {ClientProt_e::OpObj1, 6, "OPOBJ1"},
        {ClientProt_e::MessagePrivate, ClientProt::VAR_BYTE, "MESSAGE_PRIVATE"},
        {ClientProt_e::OpNpcT, 4, "OPNPCT"},
        {ClientProt_e::OpObj3, 6, "OPOBJ3"},
        {ClientProt_e::InvButton2, 6, "INV_BUTTON2"},
        {ClientProt_e::OpHeldT, 8, "OPHELDT"},
        {ClientProt_e::AnticheatOpLogic3, 4, "ANTICHEAT_OPLOGIC3"},
        {ClientProt_e::InvButton3, 6, "INV_BUTTON3"},
        {ClientProt_e::AnticheatCycleLogic3, 1, "ANTICHEAT_CYCLELOGIC3"},
        {ClientProt_e::OpLoc5, 6, "OPLOC5"},
        {ClientProt_e::AnticheatCycleLogic1, ClientProt::VAR_BYTE, "ANTICHEAT_CYCLELOGIC1"},
        {ClientProt_e::AnticheatOpLogic7, 4, "ANTICHEAT_OPLOGIC7"},
        {ClientProt_e::AnticheatCycleLogic4, 1, "ANTICHEAT_CYCLELOGIC4"},
        {ClientProt_e::OpPlayerT, 4, "OPPLAYERT"},
        {ClientProt_e::IdleTimer, 0, "IDLE_TIMER"},
        {ClientProt_e::TutClickSide, 1, "TUT_CLICKSIDE"},
        {ClientProt_e::OpObj4, 6, "OPOBJ4"},
        {ClientProt_e::EventAppletFocus, 1, "EVENT_APPLET_FOCUS"},
        {ClientProt_e::AnticheatCycleLogic2, ClientProt::VAR_BYTE, "ANTICHEAT_CYCLELOGIC2"},
        {ClientProt_e::MessagePublic, ClientProt::VAR_BYTE, "MESSAGE_PUBLIC"},
        {ClientProt_e::OpNpcU, 8, "OPNPCU"},
        {ClientProt_e::ChatSetMode, 3, "CHAT_SETMODE"},
        {ClientProt_e::ResumePauseButton, 2, "RESUME_PAUSEBUTTON"},
        {ClientProt_e::AnticheatOpLogic8, 1, "ANTICHEAT_OPLOGIC8"},
        {ClientProt_e::OpHeld2, 6, "OPHELD2"},
        {ClientProt_e::OpNpc3, 2, "OPNPC3"},
        {ClientProt_e::ResumePCountDialog, 4, "RESUME_P_COUNTDIALOG"},
        {ClientProt_e::NoTimeout, 0, "NO_TIMEOUT"},
        {ClientProt_e::OpLocU, 12, "OPLOCU"},
        {ClientProt_e::OpPlayer4, 2, "OPPLAYER4"},
        {ClientProt_e::OpHeld4, 6, "OPHELD4"},
        {ClientProt_e::IgnoreListAdd, 8, "IGNORELIST_ADD"},
        {ClientProt_e::EventCameraPosition, 4, "EVENT_CAMERA_POSITION"},
        {ClientProt_e::AnticheatOpLogic1, 4, "ANTICHEAT_OPLOGIC1"},
        {ClientProt_e::OpLoc3, 6, "OPLOC3"},
        {ClientProt_e::OpHeldU, 12, "OPHELDU"},
        {ClientProt_e::FriendListDel, 8, "FRIENDLIST_DEL"},
        {ClientProt_e::MapBuildComplete, 0, "MAP_BUILD_COMPLETE"},
        {ClientProt_e::OpLocT, 8, "OPLOCT"},
        {ClientProt_e::OpPlayer1, 2, "OPPLAYER1"},
        {ClientProt_e::EventMouseClick, 4, "EVENT_MOUSE_CLICK"},
        {ClientProt_e::InvButton5, 6, "INV_BUTTON5"},
        {ClientProt_e::EventMouseMove, ClientProt::VAR_BYTE, "EVENT_MOUSE_MOVE"},
        {ClientProt_e::AnticheatCycleLogic7, 0, "ANTICHEAT_CYCLELOGIC7"},
        {ClientProt_e::MoveGameClick, ClientProt::VAR_BYTE, "MOVE_GAMECLICK"},
        {ClientProt_e::FriendListAdd, 8, "FRIENDLIST_ADD"},
        {ClientProt_e::MoveMinimapClick, ClientProt::VAR_BYTE, "MOVE_MINIMAPCLICK"},
        {ClientProt_e::OpObjT, 8, "OPOBJT"},
        {ClientProt_e::OpNpc5, 2, "OPNPC5"},
        {ClientProt_e::InvButton4, 6, "INV_BUTTON4"},
        {ClientProt_e::IgnoreListDel, 8, "IGNORELIST_DEL"},
        {ClientProt_e::OpNpc1, 2, "OPNPC1"},
        {ClientProt_e::InvButtonD, 7, "INV_BUTTOND"},
        {ClientProt_e::AnticheatCycleLogic6, 1, "ANTICHEAT_CYCLELOGIC6"},
    });

    static_assert(CLIENT_PROTS.size() == ClientProt::COUNT, "The client opcode table must list every opcode");

    constexpr auto INFO_BY_OPCODE = []
    {
        auto table = std::array<const ClientProtInfo_s*, 256>{};
        for (const auto& info : CLIENT_PROTS)
        {
            table[static_cast<u8>(info.prot)] = &info;
        }

        return table;
    }();
}

std::optional<s32> ClientProt::GetSize(u8 opcode)
{
    const auto* const info = INFO_BY_OPCODE[opcode];
    if (info == nullptr)
    {
        return std::nullopt;
    }

    return info->size;
}

s32 ClientProt::GetSize(ClientProt_e prot)
{
    const auto* const info = INFO_BY_OPCODE[static_cast<u8>(prot)];
    assert(info != nullptr && "ClientProt_e value missing from the opcode table");
    return info->size;
}

std::string_view ClientProt::GetName(u8 opcode)
{
    const auto* const info = INFO_BY_OPCODE[opcode];
    if (info == nullptr)
    {
        return "UNKNOWN";
    }

    return info->name;
}
