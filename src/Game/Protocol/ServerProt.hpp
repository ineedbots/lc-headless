#pragma once

#include "../../Config/Revision_e.hpp"
#include "WireProt_s.hpp"

// Every server packet any supported revision sends, named as the engine names them. The values aren't
// opcodes: each revision's table (ServerProt::GetTable) maps them to its own.
enum class ServerProt_e : u8
{
    CamLookAt,
    CamMoveTo,
    CamReset,
    CamShake,
    ChatFilterSettings,
    DataLand,
    DataLandDone,
    DataLoc,
    DataLocDone,
    EnableTracking,
    FinishTracking,
    FriendListLoaded,
    HintArrow,
    IfClose,
    IfOpenChat,
    IfOpenMain,
    IfOpenMainSide,
    IfOpenOverlay,
    IfOpenSide,
    IfSetAnim,
    IfSetColour,
    IfSetHide,
    IfSetModel,
    IfSetNpcHead,
    IfSetObject,
    IfSetPlayerHead,
    IfSetPosition,
    IfSetRecol,
    IfSetScrollPos,
    IfSetTab,
    IfSetTabActive,
    IfSetText,
    LastLoginInfo,
    LocAddChange,
    LocAnim,
    LocDel,
    LocMerge,
    Logout,
    MapAnim,
    MapProjAnim,
    MessageGame,
    MessagePrivate,
    MidiJingle,
    MidiSong,
    MinimapToggle,
    NpcInfo,
    ObjAdd,
    ObjCount,
    ObjDel,
    ObjReveal,
    PlayerInfo,
    PCountDialog,
    RebuildNormal,
    ResetAnims,
    ResetClientVarCache,
    SetMultiway,
    SetPlayerOp,
    SynthSound,
    TutFlash,
    TutOpen,
    UnsetMapFlag,
    UpdateFriendList,
    UpdateIgnoreList,
    UpdateInvFull,
    UpdateInvPartial,
    UpdateInvStopTransmit,
    UpdatePid,
    UpdateRebootTimer,
    UpdateRunEnergy,
    UpdateRunWeight,
    UpdateStat,
    UpdateZoneFullFollows,
    UpdateZonePartialEnclosed,
    UpdateZonePartialFollows,
    VarpLarge,
    VarpSmall,
};

// One revision's server packets, indexed both by opcode and by packet. A packet the revision doesn't
// send has no entry.
struct ServerProtTable_s
{
    static constexpr std::size_t PROT_COUNT = 76;
    static constexpr std::size_t OPCODE_COUNT = 256;

    std::array<std::optional<ServerProt_e>, OPCODE_COUNT> byOpcode{};
    std::array<std::optional<WireProt_s>, PROT_COUNT> byProt{};
};

class ServerProt
{
public:
    static constexpr s32 VAR_BYTE = -1;
    static constexpr s32 VAR_SHORT = -2;

    ServerProt() = delete;

    [[nodiscard]] static std::string_view GetName(ServerProt_e prot);
    [[nodiscard]] static bool IsZoneProt(ServerProt_e prot);
    [[nodiscard]] static const ServerProtTable_s& GetTable(Revision_e revision);
};
