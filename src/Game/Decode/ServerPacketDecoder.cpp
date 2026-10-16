#include "pch.hpp"
#include "ServerPacketDecoder.hpp"

#include "../../Console/Logger.hpp"
#include "../../Io/Packet.hpp"
#include "../Error/ProtocolError.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../State/GameState_s.hpp"
#include "../Tile_s.hpp"
#include "InterfacePacketDecoder.hpp"
#include "InventoryDecoder.hpp"
#include "NpcInfoDecoder.hpp"
#include "PlayerInfoDecoder.hpp"
#include "PlayerStateDecoder.hpp"
#include "SceneDecoder.hpp"
#include "SocialDecoder.hpp"
#include "ZoneDecoder.hpp"

namespace
{
    // A walk requested during a tick starts on the next one; a third tick allows for a slow connection.
    // A player that still isn't moving after that isn't going to.
    constexpr auto WALK_START_TICKS = u64{3};
}

ServerPacketDecoder::ServerPacketDecoder(std::shared_ptr<Logger> logger)
    : m_logger{std::move(logger)}
{
    assert(m_logger && "ServerPacketDecoder needs a logger");
}

void ServerPacketDecoder::Decode(ServerProt_e prot, std::span<const u8> payload, GameState_s& state)
{
    const auto name = ServerProt::GetName(static_cast<u8>(prot));
    auto packet = Packet{payload};
    try
    {
        DecodePacket(prot, packet, state);
    }
    catch (const std::out_of_range& e)
    {
        throw ProtocolError{std::format("{} payload of {} bytes is too short: {}", name, payload.size(), e.what())};
    }

    if (packet.GetAvailable() != 0)
    {
        throw ProtocolError{std::format("{} payload has {} bytes left over", name, packet.GetAvailable())};
    }
}

void ServerPacketDecoder::Reset()
{
    m_playerInfo.Reset();
    m_social.Reset();
}

// Every opcode is listed with no default, so GCC and Clang (-Wswitch) warn about one with no decoder.
void ServerPacketDecoder::DecodePacket(ServerProt_e prot, Packet& packet, GameState_s& state)
{
    switch (prot)
    {
    case ServerProt_e::PlayerInfo:
        DecodePlayerInfo(packet, state);
        return;
    case ServerProt_e::NpcInfo:
        NpcInfoDecoder::Decode(packet.GetData(), state);
        packet.SetPos(packet.GetLength());
        return;

    case ServerProt_e::UpdateZoneFullFollows:
        m_zone.SetZone(packet);
        m_zone.ResetZone(state);
        return;
    case ServerProt_e::UpdateZonePartialFollows:
        m_zone.SetZone(packet);
        return;
    case ServerProt_e::UpdateZonePartialEnclosed:
        m_zone.SetZone(packet);
        m_zone.DecodeEnclosed(packet, state);
        return;
    case ServerProt_e::ObjAdd:
    case ServerProt_e::ObjDel:
    case ServerProt_e::ObjCount:
    case ServerProt_e::ObjReveal:
    case ServerProt_e::LocAddChange:
    case ServerProt_e::LocDel:
    case ServerProt_e::LocAnim:
    case ServerProt_e::LocMerge:
    case ServerProt_e::MapAnim:
    case ServerProt_e::MapProjAnim:
        m_zone.DecodeSubPacket(static_cast<u8>(prot), packet, state);
        return;

    case ServerProt_e::RebuildNormal:
    case ServerProt_e::ResetAnims:
    case ServerProt_e::CamMoveTo:
    case ServerProt_e::CamLookAt:
    case ServerProt_e::CamShake:
    case ServerProt_e::CamReset:
    case ServerProt_e::MidiSong:
    case ServerProt_e::MidiJingle:
    case ServerProt_e::SynthSound:
        SceneDecoder::Decode(prot, packet, state);
        return;

    case ServerProt_e::IfOpenMain:
    case ServerProt_e::IfOpenSide:
    case ServerProt_e::IfOpenChat:
    case ServerProt_e::IfOpenMainSide:
    case ServerProt_e::IfClose:
    case ServerProt_e::IfOpenOverlay:
    case ServerProt_e::IfSetTab:
    case ServerProt_e::IfSetTabActive:
    case ServerProt_e::PCountDialog:
    case ServerProt_e::TutOpen:
    case ServerProt_e::TutFlash:
    case ServerProt_e::IfSetText:
    case ServerProt_e::IfSetHide:
    case ServerProt_e::IfSetColour:
    case ServerProt_e::IfSetAnim:
    case ServerProt_e::IfSetPosition:
    case ServerProt_e::IfSetScrollPos:
    case ServerProt_e::IfSetObject:
    case ServerProt_e::IfSetModel:
    case ServerProt_e::IfSetNpcHead:
    case ServerProt_e::IfSetPlayerHead:
        InterfacePacketDecoder::Decode(prot, packet, state, *m_logger);
        return;

    case ServerProt_e::UpdateInvFull:
    case ServerProt_e::UpdateInvPartial:
    case ServerProt_e::UpdateInvStopTransmit:
        InventoryDecoder::Decode(prot, packet, state);
        return;

    case ServerProt_e::VarpSmall:
    case ServerProt_e::VarpLarge:
    case ServerProt_e::UpdateStat:
    case ServerProt_e::UpdateRunEnergy:
    case ServerProt_e::UpdateRunWeight:
    case ServerProt_e::UpdatePid:
    case ServerProt_e::UpdateRebootTimer:
    case ServerProt_e::LastLoginInfo:
    case ServerProt_e::HintArrow:
    case ServerProt_e::SetPlayerOp:
    case ServerProt_e::SetMultiway:
    case ServerProt_e::MinimapToggle:
    case ServerProt_e::UnsetMapFlag:
        PlayerStateDecoder::Decode(prot, packet, state, *m_logger);
        return;

    case ServerProt_e::MessageGame:
    case ServerProt_e::MessagePrivate:
    case ServerProt_e::UpdateFriendList:
    case ServerProt_e::UpdateIgnoreList:
    case ServerProt_e::FriendListLoaded:
    case ServerProt_e::ChatFilterSettings:
        m_social.Decode(prot, packet, state);
        return;

    case ServerProt_e::ResetClientVarCache:
    case ServerProt_e::Logout:
        return;
    }

    throw ProtocolError{std::format("No decoder for server opcode {}", static_cast<u8>(prot))};
}

void ServerPacketDecoder::DecodePlayerInfo(Packet& packet, GameState_s& state)
{
    m_playerInfo.Decode(packet.GetData(), state);
    packet.SetPos(packet.GetLength());

    ZoneDecoder::PruneInactive(state);

    if (!state.walkDestination || !state.placed)
    {
        return;
    }

    // UNSET_MAP_FLAG ends a walk that moved, but a walk blocked from its first step gets nothing, so
    // standing still once the server has had time to start the walk ends it too.
    const auto arrived = state.localPlayer.tile == *state.walkDestination;
    const auto stalled = state.localPlayer.movedTick != state.tick && state.tick >= state.walkRequestTick + WALK_START_TICKS;
    if (arrived || stalled)
    {
        state.walkDestination.reset();
    }
}
