#include "pch.hpp"
#include "TestWorld.hpp"

#include "FakeGameServer.hpp"
#include "Config/Revision_e.hpp"
#include "Fixtures.hpp"
#include "Game/State/BuildArea_s.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Io/Packet.hpp"

namespace
{
    constexpr auto COINS_POS = u8{0x11};
}

void TestWorld::Send(FakeGameServer& server, bool reconnect)
{
    const auto revision = server.GetRevision();
    const auto rebuild = revision >= Revision_e::Rev274 ? Fixtures::Rebuild() : Fixtures::Rebuild225(std::span{&SQUARE_225, 1});
    server.Send(ServerProt_e::RebuildNormal, rebuild);
    if (!reconnect)
    {
        server.Send(ServerProt_e::UpdatePid, Fixtures::UpdatePid(Fixtures::PID, true, revision));
    }

    const auto appearance = Fixtures::Appearance(FakeGameServer::USERNAME, std::nullopt, revision);
    server.Send(ServerProt_e::PlayerInfo, Fixtures::PlaceLocalPlayer(Fixtures::HOME_LOCAL, Fixtures::HOME_LOCAL, 0, appearance));
    if (reconnect)
    {
        server.Send(ServerProt_e::PlayerInfo, Fixtures::PlaceLocalPlayer());
        return;
    }

    server.Send(ServerProt_e::NpcInfo, Fixtures::AddNpc(NPC_INDEX, NPC_TYPE, 2, 0, revision));
    server.Send(ServerProt_e::UpdateZoneFullFollows, Fixtures::Zone(Fixtures::HOME_LOCAL, Fixtures::HOME_LOCAL));
    server.Send(ServerProt_e::ObjAdd, Fixtures::ObjAdd(COINS_POS, COINS, COIN_COUNT));

    const auto items = std::to_array<std::pair<u16, s32>>({{LOGS, LOG_COUNT}});
    server.Send(ServerProt_e::UpdateInvFull, Fixtures::UpdateInvFull(INVENTORY, items, revision));
    server.Send(ServerProt_e::MessageGame, Fixtures::MessageGame(WELCOME));

    // The next tick, which tells the client the login tick has been read whole.
    server.Send(ServerProt_e::PlayerInfo, Fixtures::PlaceLocalPlayer());
}
