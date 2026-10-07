#include "pch.hpp"
#include "ClientPackets.hpp"

#include "../../Io/Packet.hpp"
#include "../Tile_s.hpp"
#include "ClientPacket_s.hpp"
#include "ClientProt.hpp"
#include "WordPack.hpp"

namespace
{
    constexpr auto OPOBJ = std::to_array({ClientProt_e::OpObj1, ClientProt_e::OpObj2, ClientProt_e::OpObj3, ClientProt_e::OpObj4, ClientProt_e::OpObj5});
    constexpr auto OPNPC = std::to_array({ClientProt_e::OpNpc1, ClientProt_e::OpNpc2, ClientProt_e::OpNpc3, ClientProt_e::OpNpc4, ClientProt_e::OpNpc5});
    constexpr auto OPLOC = std::to_array({ClientProt_e::OpLoc1, ClientProt_e::OpLoc2, ClientProt_e::OpLoc3, ClientProt_e::OpLoc4, ClientProt_e::OpLoc5});
    constexpr auto OPPLAYER = std::to_array({ClientProt_e::OpPlayer1, ClientProt_e::OpPlayer2, ClientProt_e::OpPlayer3, ClientProt_e::OpPlayer4, ClientProt_e::OpPlayer5});
    constexpr auto OPHELD = std::to_array({ClientProt_e::OpHeld1, ClientProt_e::OpHeld2, ClientProt_e::OpHeld3, ClientProt_e::OpHeld4, ClientProt_e::OpHeld5});
    constexpr auto INV_BUTTON = std::to_array({ClientProt_e::InvButton1, ClientProt_e::InvButton2, ClientProt_e::InvButton3, ClientProt_e::InvButton4, ClientProt_e::InvButton5});

    constexpr auto MAX_COORD = 0xFFFF;
    constexpr auto MAX_CHAT_COLOUR = static_cast<u8>(ChatColour_e::Glow3);
    constexpr auto MAX_CHAT_EFFECT = static_cast<u8>(ChatEffect_e::Slide);
    constexpr auto MAX_PUBLIC_CHAT_MODE = 3;
    constexpr auto MAX_PRIVATE_CHAT_MODE = 2;
    constexpr auto MAX_REPORT_RULE = 11;

    // Any 14 bytes are accepted. These are the webclient's constant fields, with its mouse,
    // camera and scene fields left at zero.
    constexpr auto MINIMAP_TRAILER = std::to_array<u8>({0, 0, 0, 0, 57, 0, 0, 89, 0, 0, 0, 0, 0, 63});

    ClientPacket_s Make(ClientProt_e prot, const Packet& payload)
    {
        const auto data = payload.GetData();
        return {.prot = prot, .payload = {data.begin(), data.end()}};
    }

    ClientProt_e SelectOp(u8 op, const std::array<ClientProt_e, ClientPackets::MAX_OP>& prots, std::string_view kind)
    {
        if (op < ClientPackets::MIN_OP || op > ClientPackets::MAX_OP)
        {
            throw std::invalid_argument{std::format("{} option must be from {} to {}, not {}", kind, ClientPackets::MIN_OP, ClientPackets::MAX_OP, op)};
        }

        return prots[op - ClientPackets::MIN_OP];
    }

    void PutCoord(Packet& packet, s32 coord)
    {
        if (coord < 0 || coord > MAX_COORD)
        {
            throw std::invalid_argument{std::format("Coordinate {} is outside 0 to {}", coord, MAX_COORD)};
        }

        packet.P2(coord);
    }

    void PutTile(Packet& packet, const Tile_s& tile)
    {
        PutCoord(packet, tile.x);
        PutCoord(packet, tile.z);
    }

    void PutItem(Packet& packet, const ItemRef_s& item)
    {
        packet.P2(item.obj);
        packet.P2(item.slot);
        packet.P2(item.com);
    }

    void PutWaypointOffset(Packet& packet, s32 offset)
    {
        if (offset < std::numeric_limits<s8>::min() || offset > std::numeric_limits<s8>::max())
        {
            throw std::invalid_argument{std::format("Waypoint offset {} doesn't fit in a signed byte", offset)};
        }

        packet.P1(offset);
    }

    ClientPacket_s MakeName(ClientProt_e prot, u64 name)
    {
        auto packet = Packet{};
        packet.P8(std::bit_cast<s64>(name));
        return Make(prot, packet);
    }

    ClientProt_e GetMoveProt(MoveKind_e kind)
    {
        switch (kind)
        {
        case MoveKind_e::GameClick:
            return ClientProt_e::MoveGameClick;
        case MoveKind_e::MinimapClick:
            return ClientProt_e::MoveMinimapClick;
        case MoveKind_e::OpClick:
            return ClientProt_e::MoveOpClick;
        }

        assert(false && "Unhandled MoveKind_e");
        return ClientProt_e::MoveGameClick;
    }
}

ClientPacket_s ClientPackets::NoTimeout()
{
    return {.prot = ClientProt_e::NoTimeout};
}

ClientPacket_s ClientPackets::IdleTimer()
{
    return {.prot = ClientProt_e::IdleTimer};
}

ClientPacket_s ClientPackets::MapBuildComplete()
{
    return {.prot = ClientProt_e::MapBuildComplete};
}

ClientPacket_s ClientPackets::EventAppletFocus(bool focused)
{
    auto packet = Packet{};
    packet.P1(focused ? 1 : 0);
    return Make(ClientProt_e::EventAppletFocus, packet);
}

ClientPacket_s ClientPackets::EventCameraPosition(u16 pitch, u16 yaw)
{
    auto packet = Packet{};
    packet.P2(pitch);
    packet.P2(yaw);
    return Make(ClientProt_e::EventCameraPosition, packet);
}

ClientPacket_s ClientPackets::Move(MoveKind_e kind, std::span<const Tile_s> waypoints, bool run)
{
    if (waypoints.empty() || waypoints.size() > MAX_WAYPOINTS)
    {
        throw std::invalid_argument{std::format("A move needs 1 to {} waypoints, not {}", MAX_WAYPOINTS, waypoints.size())};
    }

    const auto& start = waypoints.front();
    auto packet = Packet{};
    packet.P1(run ? 1 : 0);
    PutTile(packet, start);
    for (const auto& waypoint : waypoints.subspan(1))
    {
        PutWaypointOffset(packet, waypoint.x - start.x);
        PutWaypointOffset(packet, waypoint.z - start.z);
    }

    if (kind == MoveKind_e::MinimapClick)
    {
        packet.PData(MINIMAP_TRAILER);
    }

    return Make(GetMoveProt(kind), packet);
}

ClientPacket_s ClientPackets::OpObj(u8 op, const Tile_s& tile, u16 obj)
{
    const auto prot = SelectOp(op, OPOBJ, "OPOBJ");
    auto packet = Packet{};
    PutTile(packet, tile);
    packet.P2(obj);
    return Make(prot, packet);
}

ClientPacket_s ClientPackets::OpObjT(const Tile_s& tile, u16 obj, u16 spellCom)
{
    auto packet = Packet{};
    PutTile(packet, tile);
    packet.P2(obj);
    packet.P2(spellCom);
    return Make(ClientProt_e::OpObjT, packet);
}

ClientPacket_s ClientPackets::OpObjU(const Tile_s& tile, u16 obj, const ItemRef_s& use)
{
    auto packet = Packet{};
    PutTile(packet, tile);
    packet.P2(obj);
    PutItem(packet, use);
    return Make(ClientProt_e::OpObjU, packet);
}

ClientPacket_s ClientPackets::OpNpc(u8 op, u16 npcIndex)
{
    const auto prot = SelectOp(op, OPNPC, "OPNPC");
    auto packet = Packet{};
    packet.P2(npcIndex);
    return Make(prot, packet);
}

ClientPacket_s ClientPackets::OpNpcT(u16 npcIndex, u16 spellCom)
{
    auto packet = Packet{};
    packet.P2(npcIndex);
    packet.P2(spellCom);
    return Make(ClientProt_e::OpNpcT, packet);
}

ClientPacket_s ClientPackets::OpNpcU(u16 npcIndex, const ItemRef_s& use)
{
    auto packet = Packet{};
    packet.P2(npcIndex);
    PutItem(packet, use);
    return Make(ClientProt_e::OpNpcU, packet);
}

ClientPacket_s ClientPackets::OpLoc(u8 op, const Tile_s& tile, u16 loc)
{
    const auto prot = SelectOp(op, OPLOC, "OPLOC");
    auto packet = Packet{};
    PutTile(packet, tile);
    packet.P2(loc);
    return Make(prot, packet);
}

ClientPacket_s ClientPackets::OpLocT(const Tile_s& tile, u16 loc, u16 spellCom)
{
    auto packet = Packet{};
    PutTile(packet, tile);
    packet.P2(loc);
    packet.P2(spellCom);
    return Make(ClientProt_e::OpLocT, packet);
}

ClientPacket_s ClientPackets::OpLocU(const Tile_s& tile, u16 loc, const ItemRef_s& use)
{
    auto packet = Packet{};
    PutTile(packet, tile);
    packet.P2(loc);
    PutItem(packet, use);
    return Make(ClientProt_e::OpLocU, packet);
}

ClientPacket_s ClientPackets::OpPlayer(u8 op, u16 playerIndex)
{
    const auto prot = SelectOp(op, OPPLAYER, "OPPLAYER");
    auto packet = Packet{};
    packet.P2(playerIndex);
    return Make(prot, packet);
}

ClientPacket_s ClientPackets::OpPlayerT(u16 playerIndex, u16 spellCom)
{
    auto packet = Packet{};
    packet.P2(playerIndex);
    packet.P2(spellCom);
    return Make(ClientProt_e::OpPlayerT, packet);
}

ClientPacket_s ClientPackets::OpPlayerU(u16 playerIndex, const ItemRef_s& use)
{
    auto packet = Packet{};
    packet.P2(playerIndex);
    PutItem(packet, use);
    return Make(ClientProt_e::OpPlayerU, packet);
}

ClientPacket_s ClientPackets::OpHeld(u8 op, const ItemRef_s& item)
{
    const auto prot = SelectOp(op, OPHELD, "OPHELD");
    auto packet = Packet{};
    PutItem(packet, item);
    return Make(prot, packet);
}

ClientPacket_s ClientPackets::OpHeldT(const ItemRef_s& item, u16 spellCom)
{
    auto packet = Packet{};
    PutItem(packet, item);
    packet.P2(spellCom);
    return Make(ClientProt_e::OpHeldT, packet);
}

ClientPacket_s ClientPackets::OpHeldU(const ItemRef_s& item, const ItemRef_s& use)
{
    auto packet = Packet{};
    PutItem(packet, item);
    PutItem(packet, use);
    return Make(ClientProt_e::OpHeldU, packet);
}

ClientPacket_s ClientPackets::InvButton(u8 op, const ItemRef_s& item)
{
    const auto prot = SelectOp(op, INV_BUTTON, "INV_BUTTON");
    auto packet = Packet{};
    PutItem(packet, item);
    return Make(prot, packet);
}

ClientPacket_s ClientPackets::InvButtonD(u16 com, u16 fromSlot, u16 toSlot, DragMode_e mode)
{
    auto packet = Packet{};
    packet.P2(com);
    packet.P2(fromSlot);
    packet.P2(toSlot);
    packet.P1(static_cast<u8>(mode));
    return Make(ClientProt_e::InvButtonD, packet);
}

ClientPacket_s ClientPackets::IfButton(u16 com)
{
    auto packet = Packet{};
    packet.P2(com);
    return Make(ClientProt_e::IfButton, packet);
}

ClientPacket_s ClientPackets::ResumePauseButton(u16 com)
{
    auto packet = Packet{};
    packet.P2(com);
    return Make(ClientProt_e::ResumePauseButton, packet);
}

ClientPacket_s ClientPackets::ResumePCountDialog(s32 value)
{
    auto packet = Packet{};
    packet.P4(value);
    return Make(ClientProt_e::ResumePCountDialog, packet);
}

ClientPacket_s ClientPackets::CloseModal()
{
    return {.prot = ClientProt_e::CloseModal};
}

ClientPacket_s ClientPackets::TutClickSide(u8 tab)
{
    auto packet = Packet{};
    packet.P1(tab);
    return Make(ClientProt_e::TutClickSide, packet);
}

ClientPacket_s ClientPackets::IdkSaveDesign(const IdkDesign_s& design)
{
    auto packet = Packet{};
    packet.P1(design.female ? 1 : 0);
    packet.PData(design.kits);
    packet.PData(design.colours);
    return Make(ClientProt_e::IdkSaveDesign, packet);
}

ClientPacket_s ClientPackets::MessagePublic(std::string_view text, ChatColour_e colour, ChatEffect_e effect)
{
    if (static_cast<u8>(colour) > MAX_CHAT_COLOUR || static_cast<u8>(effect) > MAX_CHAT_EFFECT)
    {
        throw std::invalid_argument{"Public chat colour or effect is out of range"};
    }

    auto packet = Packet{};
    packet.P1(static_cast<u8>(colour));
    packet.P1(static_cast<u8>(effect));
    packet.PData(WordPack::Pack(text));
    return Make(ClientProt_e::MessagePublic, packet);
}

ClientPacket_s ClientPackets::MessagePrivate(u64 to, std::string_view text)
{
    auto packet = Packet{};
    packet.P8(std::bit_cast<s64>(to));
    packet.PData(WordPack::Pack(text));
    return Make(ClientProt_e::MessagePrivate, packet);
}

ClientPacket_s ClientPackets::ClientCheat(std::string_view command)
{
    if (command.size() > MAX_CHEAT_LENGTH || command.find('\n') != std::string_view::npos)
    {
        throw std::invalid_argument{std::format("A cheat command must be at most {} characters on one line", MAX_CHEAT_LENGTH)};
    }

    auto packet = Packet{};
    packet.PJStr(command);
    return Make(ClientProt_e::ClientCheat, packet);
}

ClientPacket_s ClientPackets::ChatSetMode(u8 publicMode, u8 privateMode, u8 tradeMode)
{
    if (publicMode > MAX_PUBLIC_CHAT_MODE || privateMode > MAX_PRIVATE_CHAT_MODE || tradeMode > MAX_PRIVATE_CHAT_MODE)
    {
        throw std::invalid_argument{"Chat modes are public 0 to 3, private and trade 0 to 2"};
    }

    auto packet = Packet{};
    packet.P1(publicMode);
    packet.P1(privateMode);
    packet.P1(tradeMode);
    return Make(ClientProt_e::ChatSetMode, packet);
}

ClientPacket_s ClientPackets::FriendListAdd(u64 name)
{
    return MakeName(ClientProt_e::FriendListAdd, name);
}

ClientPacket_s ClientPackets::FriendListDel(u64 name)
{
    return MakeName(ClientProt_e::FriendListDel, name);
}

ClientPacket_s ClientPackets::IgnoreListAdd(u64 name)
{
    return MakeName(ClientProt_e::IgnoreListAdd, name);
}

ClientPacket_s ClientPackets::IgnoreListDel(u64 name)
{
    return MakeName(ClientProt_e::IgnoreListDel, name);
}

ClientPacket_s ClientPackets::ReportAbuse(u64 offender, u8 rule, bool mute)
{
    if (rule > MAX_REPORT_RULE)
    {
        throw std::invalid_argument{std::format("Report rule must be from 0 to {}", MAX_REPORT_RULE)};
    }

    auto packet = Packet{};
    packet.P8(std::bit_cast<s64>(offender));
    packet.P1(rule);
    packet.P1(mute ? 1 : 0);
    return Make(ClientProt_e::ReportAbuse, packet);
}
