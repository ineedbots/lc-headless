#include "pch.hpp"
#include "SceneDecoder.hpp"

#include "../../Config/Revision_e.hpp"
#include "../../Io/Packet.hpp"
#include "../Protocol/Protocol.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../State/BuildArea_s.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Zone_s.hpp"
#include "PacketFields.hpp"
#include "StateLog.hpp"

namespace
{
    constexpr auto BUILD_AREA_RADIUS_ZONES = 6;

    // 225 lists each map square in the area, with the CRCs of the server's files for it.
    std::vector<BuildSquare_s> ReadBuildSquares(Packet& packet)
    {
        auto squares = std::vector<BuildSquare_s>{};
        while (packet.GetAvailable() > 0)
        {
            auto& square = squares.emplace_back();
            square.x = packet.G1();
            square.z = packet.G1();
            square.landCrc = packet.G4();
            square.locCrc = packet.G4();
        }

        return squares;
    }

    void DecodeRebuild(Packet& packet, GameState_s& state, const Protocol& protocol)
    {
        const auto zoneX = packet.G2();
        const auto zoneZ = packet.G2();
        state.buildArea = BuildArea_s{
            .loaded = true,
            .centreZoneX = zoneX,
            .centreZoneZ = zoneZ,
            .baseX = (zoneX - BUILD_AREA_RADIUS_ZONES) * Zone_s::SIZE,
            .baseZ = (zoneZ - BUILD_AREA_RADIUS_ZONES) * Zone_s::SIZE,
        };

        if (protocol.GetRevision() < Revision_e::Rev274)
        {
            state.buildArea.squares = ReadBuildSquares(packet);
        }

        // The server resends every zone in view after a rebuild.
        state.groundItems.clear();
        state.locChanges.clear();
        ++state.sceneChangeCount;
    }

    void ResetAnimations(GameState_s& state)
    {
        state.localPlayer.animation.id = -1;
        for (auto& player : state.players)
        {
            player.animation.id = -1;
        }

        for (auto& npc : state.npcs)
        {
            npc.animation.id = -1;
        }
    }

    void SkipCamera(Packet& packet, GameState_s& state)
    {
        state.cinematicCamera = true;
        packet.SetPos(packet.GetLength());
    }
}

// 225 sends a song by name and a jingle as its MIDI bytes, which the state has no id for, so they're read and
// dropped.
void SceneDecoder::Decode(ServerProt_e prot, Packet& packet, GameState_s& state, const Protocol& protocol)
{
    switch (prot)
    {
    case ServerProt_e::RebuildNormal:
        DecodeRebuild(packet, state, protocol);
        return;
    case ServerProt_e::ResetAnims:
        ResetAnimations(state);
        return;

    case ServerProt_e::CamMoveTo:
    case ServerProt_e::CamLookAt:
        SkipCamera(packet, state);
        return;
    case ServerProt_e::CamShake:
        packet.SetPos(packet.GetLength());
        return;
    case ServerProt_e::CamReset:
        state.cinematicCamera = false;
        return;

    case ServerProt_e::MidiSong:
        if (protocol.GetRevision() < Revision_e::Rev274)
        {
            packet.SetPos(packet.GetLength());
            return;
        }

        state.audio.song = PacketFields::ReadId(packet);
        return;
    case ServerProt_e::MidiJingle:
        if (protocol.GetRevision() < Revision_e::Rev274)
        {
            packet.SetPos(packet.GetLength());
            return;
        }

        state.audio.jingle = packet.G2();
        packet.G2();
        return;
    case ServerProt_e::SynthSound:
    {
        auto sound = SoundEffect_s{.tick = state.tick};
        sound.id = packet.G2();
        sound.loops = packet.G1();
        sound.delay = packet.G2();
        StateLog::Push(state.sounds, sound);
        return;
    }

    case ServerProt_e::DataLand:
    case ServerProt_e::DataLandDone:
    case ServerProt_e::DataLoc:
    case ServerProt_e::DataLocDone:
        // TODO: assemble the map files sent over the wire (RevisionDesign 9.1, phase 6).
        packet.SetPos(packet.GetLength());
        return;

    default:
        assert(false && "Not a scene packet");
        return;
    }
}
