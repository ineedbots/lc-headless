#include "pch.hpp"
#include "TestWorld.hpp"

#include "FakeGameServer.hpp"
#include "Fixtures.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Io/Packet.hpp"

namespace
{
    constexpr auto COINS_POS = u8{0x11};
}

void TestWorld::Send(FakeGameServer& server, bool reconnect)
{
    server.Send(ServerProt_e::RebuildNormal, Fixtures::Rebuild());
    if (!reconnect)
    {
        server.Send(ServerProt_e::UpdatePid, Fixtures::UpdatePid());
    }

    server.Send(ServerProt_e::PlayerInfo, Fixtures::PlaceLocalPlayer(Fixtures::HOME_LOCAL, Fixtures::HOME_LOCAL, 0, Fixtures::Appearance(FakeGameServer::USERNAME)));
    if (reconnect)
    {
        return;
    }

    server.Send(ServerProt_e::NpcInfo, Fixtures::AddNpc(NPC_INDEX, NPC_TYPE, 2, 0));
    server.Send(ServerProt_e::UpdateZoneFullFollows, Fixtures::Zone(Fixtures::HOME_LOCAL, Fixtures::HOME_LOCAL));
    server.Send(ServerProt_e::ObjAdd, Fixtures::ObjAdd(COINS_POS, COINS, COIN_COUNT));

    auto inventory = Packet{};
    inventory.P2(INVENTORY);
    inventory.P2(1);
    inventory.P2(LOGS + 1);
    inventory.P1(LOG_COUNT);
    server.Send(ServerProt_e::UpdateInvFull, Fixtures::ToBytes(inventory));
    server.Send(ServerProt_e::MessageGame, Fixtures::MessageGame(WELCOME));
}
