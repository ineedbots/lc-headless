#pragma once

#include "../../Io/Packet.hpp"
#include "../Tile_s.hpp"
#include "ClientPacket_s.hpp"
#include "ClientProt.hpp"
#include "Protocol.hpp"

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

enum class MapFile_e : u8
{
    Land,
    Locs,
};

// One of a map square's files, which a 225 client asks the server for when its own copy is stale.
struct MapRequest_s
{
    MapFile_e file = MapFile_e::Land;
    u8 x = 0;
    u8 z = 0;
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
    static constexpr std::size_t MAX_CHEAT_LENGTH = 80;

    explicit ClientPackets(Protocol protocol);

    [[nodiscard]] ClientPacket_s NoTimeout() const;
    [[nodiscard]] ClientPacket_s IdleTimer() const;
    [[nodiscard]] ClientPacket_s MapBuildComplete() const;
    [[nodiscard]] ClientPacket_s EventAppletFocus(bool focused) const;
    [[nodiscard]] ClientPacket_s EventCameraPosition(u16 pitch, u16 yaw) const;
    [[nodiscard]] ClientPacket_s RebuildGetMaps(std::span<const MapRequest_s> requests) const;

    [[nodiscard]] ClientPacket_s Move(MoveKind_e kind, std::span<const Tile_s> waypoints, bool run) const;

    [[nodiscard]] ClientPacket_s OpObj(u8 op, const Tile_s& tile, u16 obj) const;
    [[nodiscard]] ClientPacket_s OpObjT(const Tile_s& tile, u16 obj, u16 spellCom) const;
    [[nodiscard]] ClientPacket_s OpObjU(const Tile_s& tile, u16 obj, const ItemRef_s& use) const;

    [[nodiscard]] ClientPacket_s OpNpc(u8 op, u16 npcIndex) const;
    [[nodiscard]] ClientPacket_s OpNpcT(u16 npcIndex, u16 spellCom) const;
    [[nodiscard]] ClientPacket_s OpNpcU(u16 npcIndex, const ItemRef_s& use) const;

    [[nodiscard]] ClientPacket_s OpLoc(u8 op, const Tile_s& tile, u16 loc) const;
    [[nodiscard]] ClientPacket_s OpLocT(const Tile_s& tile, u16 loc, u16 spellCom) const;
    [[nodiscard]] ClientPacket_s OpLocU(const Tile_s& tile, u16 loc, const ItemRef_s& use) const;

    [[nodiscard]] ClientPacket_s OpPlayer(u8 op, u16 playerIndex) const;
    [[nodiscard]] ClientPacket_s OpPlayerT(u16 playerIndex, u16 spellCom) const;
    [[nodiscard]] ClientPacket_s OpPlayerU(u16 playerIndex, const ItemRef_s& use) const;

    [[nodiscard]] ClientPacket_s OpHeld(u8 op, const ItemRef_s& item) const;
    [[nodiscard]] ClientPacket_s OpHeldT(const ItemRef_s& item, u16 spellCom) const;
    [[nodiscard]] ClientPacket_s OpHeldU(const ItemRef_s& item, const ItemRef_s& use) const;

    [[nodiscard]] ClientPacket_s InvButton(u8 op, const ItemRef_s& item) const;
    [[nodiscard]] ClientPacket_s InvButtonD(u16 com, u16 fromSlot, u16 toSlot, DragMode_e mode) const;
    [[nodiscard]] ClientPacket_s IfButton(u16 com) const;
    [[nodiscard]] ClientPacket_s ResumePauseButton(u16 com) const;
    [[nodiscard]] ClientPacket_s ResumePCountDialog(s32 value) const;
    [[nodiscard]] ClientPacket_s CloseModal() const;
    [[nodiscard]] ClientPacket_s TutClickSide(u8 tab) const;
    [[nodiscard]] ClientPacket_s IdkSaveDesign(const IdkDesign_s& design) const;

    [[nodiscard]] ClientPacket_s MessagePublic(std::string_view text, ChatColour_e colour = ChatColour_e::Yellow, ChatEffect_e effect = ChatEffect_e::None) const;
    [[nodiscard]] ClientPacket_s MessagePrivate(u64 to, std::string_view text) const;
    [[nodiscard]] ClientPacket_s ClientCheat(std::string_view command) const;
    [[nodiscard]] ClientPacket_s ChatSetMode(u8 publicMode, u8 privateMode, u8 tradeMode) const;
    [[nodiscard]] ClientPacket_s FriendListAdd(u64 name) const;
    [[nodiscard]] ClientPacket_s FriendListDel(u64 name) const;
    [[nodiscard]] ClientPacket_s IgnoreListAdd(u64 name) const;
    [[nodiscard]] ClientPacket_s IgnoreListDel(u64 name) const;
    [[nodiscard]] ClientPacket_s ReportAbuse(u64 offender, u8 rule, bool mute) const;

private:
    // Throws std::invalid_argument for a packet this revision doesn't have, so an action fails before it
    // walks anywhere rather than when its packet is sent.
    [[nodiscard]] ClientPacket_s Make(ClientProt_e prot, const Packet& payload = {}) const;
    [[nodiscard]] ClientPacket_s MakeName(ClientProt_e prot, u64 name) const;

    Protocol m_protocol;
};
