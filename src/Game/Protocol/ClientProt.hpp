#pragma once

#include "../../Config/Revision_e.hpp"
#include "WireProt_s.hpp"

// Every client packet any supported revision accepts, named as the engine names them. The values aren't
// opcodes: each revision's table (ClientProt::GetTable) maps them to its own.
enum class ClientProt_e : u8
{
    AnticheatCycleLogic1,
    AnticheatCycleLogic2,
    AnticheatCycleLogic3,
    AnticheatCycleLogic4,
    AnticheatCycleLogic5,
    AnticheatCycleLogic6,
    AnticheatCycleLogic7,
    AnticheatOpLogic1,
    AnticheatOpLogic2,
    AnticheatOpLogic3,
    AnticheatOpLogic4,
    AnticheatOpLogic5,
    AnticheatOpLogic6,
    AnticheatOpLogic7,
    AnticheatOpLogic8,
    AnticheatOpLogic9,
    ChatSetMode,
    ClientCheat,
    CloseModal,
    EventAppletFocus,
    EventCameraPosition,
    EventMouseClick,
    EventMouseMove,
    EventTracking,
    FriendListAdd,
    FriendListDel,
    IdkSaveDesign,
    IdleTimer,
    IfButton,
    IgnoreListAdd,
    IgnoreListDel,
    InvButton1,
    InvButton2,
    InvButton3,
    InvButton4,
    InvButton5,
    InvButtonD,
    MapBuildComplete,
    MessagePrivate,
    MessagePublic,
    MoveGameClick,
    MoveMinimapClick,
    MoveOpClick,
    NoTimeout,
    OpHeld1,
    OpHeld2,
    OpHeld3,
    OpHeld4,
    OpHeld5,
    OpHeldT,
    OpHeldU,
    OpLoc1,
    OpLoc2,
    OpLoc3,
    OpLoc4,
    OpLoc5,
    OpLocT,
    OpLocU,
    OpNpc1,
    OpNpc2,
    OpNpc3,
    OpNpc4,
    OpNpc5,
    OpNpcT,
    OpNpcU,
    OpObj1,
    OpObj2,
    OpObj3,
    OpObj4,
    OpObj5,
    OpObjT,
    OpObjU,
    OpPlayer1,
    OpPlayer2,
    OpPlayer3,
    OpPlayer4,
    OpPlayer5,
    OpPlayerT,
    OpPlayerU,
    RebuildGetMaps,
    ReportAbuse,
    ResumePauseButton,
    ResumePCountDialog,
    TutClickSide,
};

// One revision's client packets, indexed both by opcode and by packet. A packet the revision doesn't
// accept has no entry.
struct ClientProtTable_s
{
    static constexpr std::size_t PROT_COUNT = 84;
    static constexpr std::size_t OPCODE_COUNT = 256;

    std::array<std::optional<ClientProt_e>, OPCODE_COUNT> byOpcode{};
    std::array<std::optional<WireProt_s>, PROT_COUNT> byProt{};
};

class ClientProt
{
public:
    static constexpr s32 VAR_BYTE = -1;
    static constexpr s32 VAR_SHORT = -2;

    ClientProt() = delete;

    [[nodiscard]] static std::string_view GetName(ClientProt_e prot);
    [[nodiscard]] static const ClientProtTable_s& GetTable(Revision_e revision);
};
