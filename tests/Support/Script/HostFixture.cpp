#include "pch.hpp"
#include "HostFixture.hpp"
#include "../Game/FakeGameServer.hpp"
#include "../Game/Fixtures.hpp"
#include "../Game/TestWorld.hpp"
#include "../LogCapture.hpp"
#include "../TempFolder.hpp"
#include "ScriptTestRuntime.hpp"
#include "ScriptCoverage.hpp"

#include "Config/Config_s.hpp"
#include "Console/LogLevel_e.hpp"
#include "Game/GameClient.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Io/Packet.hpp"
#include "Script/Host/ScriptHost.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    GameClientOptions_s FastOptions()
    {
        return {.retryDelay = 50ms, .loginTimeout = 5s, .keepaliveInterval = 50ms};
    }
}

HostFixture::HostFixture(std::string_view script, std::string settings)
    : HostFixture{script, ScriptHostOptions_s{.settings = std::move(settings)}}
{
}

HostFixture::HostFixture(std::string_view script, ScriptHostOptions_s options, const Files& otherFiles)
    : server{TestWorld::Send}
    , folder{"rs2004-script-host-tests"}
    , client{std::make_shared<const Config_s>(server.MakeConfig()), FakeGameServer::MakeCache(), FakeGameServer::MakeAccount(), capture.GetLogger(), FastOptions()}
{
    folder.WriteFile("main.py", script);
    for (const auto& [name, text] : otherFiles)
    {
        folder.WriteFile(name, text);
    }

    options.scriptsDirectory = folder.GetPath();
    options.file = "main.py";
    options.callTimeout = ScriptCoverage::AdjustTimeout(options.callTimeout);
    host.emplace(ScriptTestRuntime::Get(), client, std::move(options), capture.GetLogger());
    client.Login();

    const auto deadline = Clock::now() + WAIT;
    while (Clock::now() < deadline && !client.GetState().IsSettled())
    {
        client.Pump(PUMP_STEP);
    }

    REQUIRE(client.GetState().IsSettled());
}

std::vector<std::string> HostFixture::GetScriptLines() const
{
    auto lines = std::vector<std::string>{};
    for (const auto& entry : capture.GetEntries())
    {
        if (entry.message.starts_with("> "))
        {
            lines.push_back(entry.message.substr(2));
        }
    }

    return lines;
}

void HostFixture::SendTick()
{
    const auto tick = client.GetState().tick;
    server.Send(ServerProt_e::PlayerInfo, Fixtures::PlaceLocalPlayer());

    const auto deadline = Clock::now() + WAIT;
    while (Clock::now() < deadline && client.GetState().tick == tick)
    {
        client.Pump(PUMP_STEP);
    }

    REQUIRE(client.GetState().tick == tick + 1);
}

void HostFixture::Send(ServerProt_e prot, const Packet& packet)
{
    server.Send(prot, Fixtures::ToBytes(packet));
}

void HostFixture::SendInventory(u16 com, const std::vector<std::pair<u16, u8>>& items)
{
    auto packet = Packet{};
    packet.P2(com);
    packet.P2(static_cast<s32>(items.size()));
    for (const auto& [id, count] : items)
    {
        packet.P2(id + 1);
        packet.P1(count);
    }

    Send(ServerProt_e::UpdateInvFull, packet);
}

void HostFixture::OpenMainSide(u16 main, u16 side)
{
    auto packet = Packet{};
    packet.P2(main);
    packet.P2(side);
    Send(ServerProt_e::IfOpenMainSide, packet);
    PumpUntil([this, main]
    {
        return client.GetState().interfaces.mainModal == main;
    });
}

void HostFixture::Step()
{
    host->Step(Clock::now());
    client.Flush();
}

std::vector<u8> HostFixture::LastPayload(ClientProt_e prot) const
{
    return server.GetPackets(prot).back().payload;
}

bool HostFixture::HasLog(LogLevel_e level, std::string_view text) const
{
    return std::ranges::any_of(capture.GetEntries(), [level, text](const CapturedLog_s& entry)
    {
        return entry.level == level && entry.message.find(text) != std::string::npos;
    });
}
