#pragma once
#include "../Game/FakeGameServer.hpp"
#include "../LogCapture.hpp"
#include "../TempFolder.hpp"

#include "Console/LogLevel_e.hpp"
#include "Game/GameClient.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Game/Protocol/ServerProt.hpp"
#include "Io/Packet.hpp"
#include "Script/Host/ScriptHost.hpp"

#include <catch2/catch_test_macros.hpp>

// A logged-in client with a script loaded from a temporary scripts folder, as main.py beside any other
// files given. Steps take explicit times, so the tests control when loop() is due.
class HostFixture
{
public:
    using Clock = ScriptHost::Clock;
    using Files = std::vector<std::pair<std::string, std::string>>;

    static constexpr auto WAIT = 5s;
    static constexpr auto PUMP_STEP = 20ms;

    explicit HostFixture(std::string_view script, std::string settings = "{}");
    HostFixture(std::string_view script, ScriptHostOptions_s options, const Files& otherFiles = {});

    [[nodiscard]] std::vector<std::string> GetScriptLines() const;
    // Sends a PLAYER_INFO, which is a server tick, and pumps until the client has it.
    void SendTick();
    void Send(ServerProt_e prot, const Packet& packet);
    void SendInventory(u16 com, const std::vector<std::pair<u16, u8>>& items);
    void OpenMainSide(u16 main, u16 side);

    template <typename TCondition>
    void PumpUntil(TCondition condition)
    {
        const auto deadline = Clock::now() + WAIT;
        while (Clock::now() < deadline && !condition())
        {
            client.Pump(PUMP_STEP);
        }

        REQUIRE(condition());
    }

    // Runs the script's step now and sends what it queued.
    void Step();
    [[nodiscard]] std::vector<u8> LastPayload(ClientProt_e prot) const;
    [[nodiscard]] bool HasLog(LogLevel_e level, std::string_view text) const;

    LogCapture capture{LogLevel_e::Info};
    FakeGameServer server;
    TempFolder folder;
    GameClient client;
    std::optional<ScriptHost> host;
};
