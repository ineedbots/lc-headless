#pragma once

enum class ServerProt_e : u8
{
    TutOpen = 12,
    ChatFilterSettings = 13,
    IfSetObject = 18,
    SetPlayerOp = 21,
    IfClose = 23,
    UpdateInvStopTransmit = 28,
    MidiJingle = 29,
    IfSetPlayerHead = 30,
    PCountDialog = 35,
    UpdateRunWeight = 46,
    UpdateIgnoreList = 47,
    IfOpenMainSide = 55,
    IfSetText = 59,
    ObjAdd = 60,
    IfSetTab = 63,
    NpcInfo = 65,
    ObjDel = 71,
    CamMoveTo = 73,
    VarpSmall = 75,
    UpdateInvPartial = 76,
    IfSetPosition = 79,
    IfOpenChat = 81,
    CamLookAt = 82,
    LocMerge = 83,
    MapProjAnim = 87,
    LocAddChange = 90,
    VarpLarge = 97,
    LocAnim = 106,
    UpdateInvFull = 107,
    UpdateZonePartialEnclosed = 112,
    HintArrow = 115,
    ObjCount = 117,
    IfOpenMain = 119,
    UpdatePid = 120,
    Logout = 121,
    IfOpenOverlay = 127,
    CamReset = 133,
    MinimapToggle = 136,
    IfSetHide = 138,
    UpdateZoneFullFollows = 144,
    UpdateStat = 154,
    UpdateZonePartialFollows = 155,
    IfSetColour = 160,
    UnsetMapFlag = 164,
    UpdateFriendList = 168,
    ResetClientVarCache = 172,
    ObjReveal = 176,
    SynthSound = 177,
    TutFlash = 181,
    IfSetScrollPos = 184,
    MidiSong = 187,
    PlayerInfo = 188,
    IfSetTabActive = 189,
    LocDel = 194,
    UpdateRunEnergy = 195,
    MessageGame = 196,
    ResetAnims = 201,
    UpdateRebootTimer = 204,
    CamShake = 208,
    IfSetAnim = 211,
    RebuildNormal = 219,
    IfSetModel = 222,
    MapAnim = 233,
    FriendListLoaded = 235,
    MessagePrivate = 243,
    IfSetNpcHead = 244,
    SetMultiway = 247,
    IfOpenSide = 252,
    LastLoginInfo = 253,
};

class ServerProt
{
public:
    static constexpr s32 VAR_BYTE = -1;
    static constexpr s32 VAR_SHORT = -2;
    static constexpr std::size_t COUNT = 69;

    ServerProt() = delete;

    [[nodiscard]] static std::optional<s32> GetSize(u8 opcode);
    [[nodiscard]] static std::string_view GetName(u8 opcode);
    [[nodiscard]] static bool IsZoneProt(u8 opcode);
};
