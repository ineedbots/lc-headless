#include "pch.hpp"
#include "SceneDecoder.hpp"

#include "../../Io/Packet.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../State/BuildArea_s.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Zone_s.hpp"
#include "PacketFields.hpp"
#include "StateLog.hpp"

namespace
{
    constexpr auto BUILD_AREA_RADIUS_ZONES = 6;

    void DecodeRebuild(Packet& packet, GameState_s& state)
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

void SceneDecoder::Decode(ServerProt_e prot, Packet& packet, GameState_s& state)
{
    switch (prot)
    {
    case ServerProt_e::RebuildNormal:
        DecodeRebuild(packet, state);
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
        state.audio.song = PacketFields::ReadId(packet);
        return;
    case ServerProt_e::MidiJingle:
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

    default:
        assert(false && "Not a scene packet");
        return;
    }
}
