#include "pch.hpp"

#include "../Support/LogCapture.hpp"
#include "../Support/TempFolder.hpp"
#include "Accounts/AccountDataLog.hpp"
#include "Accounts/AccountReporting.hpp"
#include "Application/Events/ApplicationEventBridge.hpp"
#include "Cache/Type/GameCache_s.hpp"
#include "Config/Type/AccountConfig_s.hpp"
#include "Config/Type/Config_s.hpp"
#include "Game/GameClient.hpp"
#include "Game/State/Type/Entity_s.hpp"
#include "Game/State/Type/GameState_s.hpp"
#include "Game/State/Type/Stat_e.hpp"
#include "Game/Type/Tile_s.hpp"
#include "../Support/FleetDatabaseReader.hpp"

#include <catch2/catch_test_macros.hpp>
#include <nlohmann/json.hpp>

namespace
{
    std::vector<nlohmann::json> Records(const std::filesystem::path& path, std::string_view account = "bot1")
    {
        return ReadFleetRecords(path, "account-data", account);
    }

    GameState_s SettledState()
    {
        auto state = GameState_s{};
        state.placed = true;
        state.tick = 2;
        state.placedTick = 1;
        state.pid = 42;
        state.localPlayer.tile = {.x = 3200, .z = 3201, .level = 2};
        state.stats[static_cast<std::size_t>(Stat_e::Hitpoints)] = {.level = 25, .baseLevel = 30};
        state.stats[static_cast<std::size_t>(Stat_e::Prayer)] = {.level = 12, .baseLevel = 20};
        state.runEnergy = 80;
        return state;
    }
}

TEST_CASE("Account data records settled values and server facing targets", "[AccountDataLog]")
{
    const auto folder = TempFolder{"rs2004-account-data"};
    auto capture = LogCapture{};
    const auto cache = GameCache_s{};
    auto database = std::make_shared<FleetDatabase>(folder.GetPath() / "fleet.sqlite");
    auto log = AccountDataLog{cache, capture.GetLogger(), "bot1", database, 0s};
    auto state = SettledState();
    const auto now = AccountDataLog::Clock::now();
    log.Step(now, state, ClientStatus_e::InGame);
    auto first = Records(log.GetDatabasePath()).back();
    CHECK(first["account"] == "bot1");
    CHECK(first["pid"] == 42);
    CHECK(first["tile"] == nlohmann::json{{"x", 3200}, {"z", 3201}, {"level", 2}});
    CHECK(first["hp"] == nlohmann::json{{"current", 25}, {"base", 30}});
    CHECK(first["prayer"]["current"] == 12);
    CHECK(first["energy"] == 80);
    CHECK(first["target"].is_null());
    CHECK(first["destination"].is_null());
    CHECK(first["specialAttack"].is_null());

    state.localPlayer.faceEntity = EntityRef_s{.type = EntityType_e::Npc, .index = 17};
    state.localPlayer.faceCoord = FineCoord_s{.x = 6403, .z = 6405};
    state.walkDestination = Tile_s{.x = 3210, .z = 3211, .level = 2};
    state.varps[300] = 750;
    state.varps[301] = 1;
    log.Step(now, state, ClientStatus_e::InGame);
    auto record = Records(log.GetDatabasePath()).back();
    CHECK(record["target"] == nlohmann::json{{"kind", "npc"}, {"index", 17}});
    CHECK(record["destination"]["x"] == 3210);
    CHECK(record["moving"] == true);
    CHECK(record["specialAttack"] == nlohmann::json{{"energy", 750}, {"armed", true}});

    state.localPlayer.faceEntity->type = EntityType_e::Player;
    log.Step(now, state, ClientStatus_e::InGame);
    CHECK(Records(log.GetDatabasePath()).back()["target"]["kind"] == "player");
    state.localPlayer.faceEntity.reset();
    log.Step(now, state, ClientStatus_e::InGame);
    CHECK(Records(log.GetDatabasePath()).back()["target"] == nlohmann::json{{"kind", "tile"}, {"tile", {{"x", 3201}, {"z", 3202}, {"level", 2}}}});
    state.localPlayer.faceCoord.reset();
    state.walkDestination.reset();
    log.Step(now, state, ClientStatus_e::InGame);
    CHECK(Records(log.GetDatabasePath()).back()["target"].is_null());
    CHECK(Records(log.GetDatabasePath()).back()["destination"].is_null());
}

TEST_CASE("Account data coalesces changes and clears stale state across sessions", "[AccountDataLog]")
{
    const auto folder = TempFolder{"rs2004-account-data-interval"};
    auto capture = LogCapture{};
    const auto cache = GameCache_s{};
    auto database = std::make_shared<FleetDatabase>(folder.GetPath() / "fleet.sqlite");
    auto log = AccountDataLog{cache, capture.GetLogger(), "bot1", database, 5s};
    auto state = SettledState();
    const auto now = AccountDataLog::Clock::now();
    log.Step(now, state, ClientStatus_e::InGame);
    ++state.tick;
    log.Step(now + 5s, state, ClientStatus_e::InGame);
    REQUIRE(Records(log.GetDatabasePath()).size() == 1);
    state.runEnergy = 70;
    log.Step(now + 6s, state, ClientStatus_e::InGame);
    state.runEnergy = 60;
    log.Step(now + 7s, state, ClientStatus_e::InGame);
    REQUIRE(Records(log.GetDatabasePath()).size() == 2);
    log.Step(now + 11s, state, ClientStatus_e::InGame);
    REQUIRE(Records(log.GetDatabasePath()).size() == 3);
    CHECK(Records(log.GetDatabasePath()).back()["energy"] == 60);
    log.Step(now + 12s, state, ClientStatus_e::Disconnected);
    auto record = Records(log.GetDatabasePath()).back();
    CHECK(record["state"] == "disconnected");
    CHECK(record["tile"].is_null());
    CHECK(record["pid"].is_null());
    CHECK(record["hp"].is_null());
    CHECK(record["settled"] == false);
    state.placedTick = state.tick;
    log.Step(now + 13s, state, ClientStatus_e::InGame);
    CHECK(Records(log.GetDatabasePath()).back()["hp"].is_null());
    ++state.tick;
    state.pid = 99;
    log.Step(now + 14s, state, ClientStatus_e::InGame);
    CHECK(Records(log.GetDatabasePath()).back()["pid"] == 99);
}

TEST_CASE("Account reporting publishes account data only after successful writes and retries failures", "[AccountDataLog][FleetEvents]")
{
    const auto folder = TempFolder{"rs2004-account-data-events"};
    auto capture = LogCapture{};
    const auto cache = GameCache_s{};
    const auto path = folder.GetPath() / "fleet.sqlite";
    folder.WriteFile("fleet.sqlite", "blocked");
    auto config = Config_s{};
    config.scripting.fleetDatabasePath = path.string();
    config.scripting.experienceLogEnabled = false;
    config.scripting.bankLogEnabled = false;
    config.scripting.inventoryLogEnabled = false;
    config.scripting.equipmentLogEnabled = false;
    auto bridge = std::make_shared<ApplicationEventBridge>(std::vector<std::string>{"bot1"});
    const auto client = bridge->Connect();
    bridge->Enqueue(client, R"({"version":1,"type":"subscribe","id":"data","events":["fleet.account-data"],"accounts":["bot1"]})");
    const auto drain = [&]
    {
        while (bridge->HasIncoming())
        {
            bridge->Service();
        }
    };
    drain();
    bridge->Pop(client);
    bridge->Pop(client);
    auto reporting = AccountReporting{config, AccountConfig_s{.name = "bot1"}, cache, capture.GetLogger(), {}, bridge};
    const auto now = AccountDataLog::Clock::now();
    auto state = SettledState();
    reporting.ObserveSession(now, state, ClientStatus_e::InGame);
    drain();
    CHECK_FALSE(bridge->Front(client));
    REQUIRE(std::filesystem::remove(path));
    reporting.ObserveSession(now + 1s, state, ClientStatus_e::InGame);
    CHECK_FALSE(std::filesystem::exists(path));
    reporting.ObserveSession(now + 5s, state, ClientStatus_e::InGame);
    drain();
    REQUIRE(bridge->Front(client));
    const auto event = nlohmann::json::parse(*bridge->Front(client));
    CHECK(event["event"] == "fleet.account-data");
    CHECK(event["account"] == "bot1");
    CHECK(event["payload"] == Records(path).back());
    config.scripting.accountDataLogEnabled = false;
    auto disabled = AccountReporting{config, AccountConfig_s{.name = "bot1"}, cache, capture.GetLogger(), {}, bridge};
    bridge->Pop(client);
    disabled.ObserveSession(now + 10s, state, ClientStatus_e::Disconnected);
    drain();
    CHECK_FALSE(bridge->Front(client));
}
