#pragma once

#include "../Tile_s.hpp"
#include "ClientPacket_s.hpp"

enum class MoveKind_e : u8
{
    GameClick,
    MinimapClick,
    OpClick,
};

enum class DragMode_e : u8
{
    Swap,
    Insert,
};

enum class ChatColour_e : u8
{
    Yellow,
    Red,
    Green,
    Cyan,
    Purple,
    White,
    Flash1,
    Flash2,
    Flash3,
    Glow1,
    Glow2,
    Glow3,
};

enum class ChatEffect_e : u8
{
    None,
    Wave,
    Wave2,
    Shake,
    Scroll,
    Slide,
};

// An item in an interface inventory: its object ID, its slot, and the component that shows it.
struct ItemRef_s
{
    u16 obj = 0;
    u16 slot = 0;
    u16 com = 0;
};

struct IdkDesign_s
{
    static constexpr std::size_t KIT_COUNT = 7;
    static constexpr std::size_t COLOUR_COUNT = 5;
    static constexpr u8 NO_KIT = 255;

    bool female = false;
    std::array<u8, KIT_COUNT> kits{};
    std::array<u8, COLOUR_COUNT> colours{};
};

class ClientPackets
{
public:
    static constexpr std::size_t MAX_WAYPOINTS = 25;
    static constexpr u8 MIN_OP = 1;
    static constexpr u8 MAX_OP = 5;
    static constexpr std::size_t MAX_CHEAT_LENGTH = 80;

    ClientPackets() = delete;

    [[nodiscard]] static ClientPacket_s NoTimeout();
    [[nodiscard]] static ClientPacket_s IdleTimer();
    [[nodiscard]] static ClientPacket_s MapBuildComplete();
    [[nodiscard]] static ClientPacket_s EventAppletFocus(bool focused);
    [[nodiscard]] static ClientPacket_s EventCameraPosition(u16 pitch, u16 yaw);

    [[nodiscard]] static ClientPacket_s Move(MoveKind_e kind, std::span<const Tile_s> waypoints, bool run);

    [[nodiscard]] static ClientPacket_s OpObj(u8 op, const Tile_s& tile, u16 obj);
    [[nodiscard]] static ClientPacket_s OpObjT(const Tile_s& tile, u16 obj, u16 spellCom);
    [[nodiscard]] static ClientPacket_s OpObjU(const Tile_s& tile, u16 obj, const ItemRef_s& use);

    [[nodiscard]] static ClientPacket_s OpNpc(u8 op, u16 npcIndex);
    [[nodiscard]] static ClientPacket_s OpNpcT(u16 npcIndex, u16 spellCom);
    [[nodiscard]] static ClientPacket_s OpNpcU(u16 npcIndex, const ItemRef_s& use);

    [[nodiscard]] static ClientPacket_s OpLoc(u8 op, const Tile_s& tile, u16 loc);
    [[nodiscard]] static ClientPacket_s OpLocT(const Tile_s& tile, u16 loc, u16 spellCom);
    [[nodiscard]] static ClientPacket_s OpLocU(const Tile_s& tile, u16 loc, const ItemRef_s& use);

    [[nodiscard]] static ClientPacket_s OpPlayer(u8 op, u16 playerIndex);
    [[nodiscard]] static ClientPacket_s OpPlayerT(u16 playerIndex, u16 spellCom);
    [[nodiscard]] static ClientPacket_s OpPlayerU(u16 playerIndex, const ItemRef_s& use);

    [[nodiscard]] static ClientPacket_s OpHeld(u8 op, const ItemRef_s& item);
    [[nodiscard]] static ClientPacket_s OpHeldT(const ItemRef_s& item, u16 spellCom);
    [[nodiscard]] static ClientPacket_s OpHeldU(const ItemRef_s& item, const ItemRef_s& use);

    [[nodiscard]] static ClientPacket_s InvButton(u8 op, const ItemRef_s& item);
    [[nodiscard]] static ClientPacket_s InvButtonD(u16 com, u16 fromSlot, u16 toSlot, DragMode_e mode);
    [[nodiscard]] static ClientPacket_s IfButton(u16 com);
    [[nodiscard]] static ClientPacket_s ResumePauseButton(u16 com);
    [[nodiscard]] static ClientPacket_s ResumePCountDialog(s32 value);
    [[nodiscard]] static ClientPacket_s CloseModal();
    [[nodiscard]] static ClientPacket_s TutClickSide(u8 tab);
    [[nodiscard]] static ClientPacket_s IdkSaveDesign(const IdkDesign_s& design);

    [[nodiscard]] static ClientPacket_s MessagePublic(std::string_view text, ChatColour_e colour = ChatColour_e::Yellow, ChatEffect_e effect = ChatEffect_e::None);
    [[nodiscard]] static ClientPacket_s MessagePrivate(u64 to, std::string_view text);
    [[nodiscard]] static ClientPacket_s ClientCheat(std::string_view command);
    [[nodiscard]] static ClientPacket_s ChatSetMode(u8 publicMode, u8 privateMode, u8 tradeMode);
    [[nodiscard]] static ClientPacket_s FriendListAdd(u64 name);
    [[nodiscard]] static ClientPacket_s FriendListDel(u64 name);
    [[nodiscard]] static ClientPacket_s IgnoreListAdd(u64 name);
    [[nodiscard]] static ClientPacket_s IgnoreListDel(u64 name);
    [[nodiscard]] static ClientPacket_s ReportAbuse(u64 offender, u8 rule, bool mute);
};
