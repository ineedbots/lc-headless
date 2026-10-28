#include "pch.hpp"
#include "../Support/Cache/TestCache.hpp"
#include "../Support/Game/FakeGameServer.hpp"
#include "../Support/Game/Fixtures.hpp"
#include "../Support/Game/QueryWorld.hpp"
#include "../Support/Game/TestWorld.hpp"
#include "../Support/LogCapture.hpp"

#include "Config/Config_s.hpp"
#include "Game/GameActions.hpp"
#include "Game/GameClient.hpp"
#include "Game/Menu/MenuOp.hpp"
#include "Game/Query/InventoryItem_s.hpp"
#include "Cache/ClientCode_e.hpp"
#include "Game/Protocol/ClientProt.hpp"
#include "Io/Packet.hpp"
#include "Script/ScriptActions.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    // A client that never logs in: actions only get as far as checking their targets, since sending throws
    // without a session.
    class ActionsFixture
    {
    public:
        ActionsFixture()
            : client{std::make_shared<const Config_s>(), world.cache, FakeGameServer::MakeAccount(), capture.GetLogger()}
            , gameActions{client}
            , actions{world.state, world.map, gameActions}
        {
        }

        LogCapture capture;
        QueryWorld world;
        GameClient client;
        GameActions gameActions;
        ScriptActions actions;
    };
}

TEST_CASE("ScriptActions report targets that are gone", "[ScriptActions]")
{
    auto fixture = ActionsFixture{};
    auto& actions = fixture.actions;
    const auto bones = InventoryItem_s{.com = TestCache::INVENTORY, .slot = 2, .id = QueryWorld::BONES, .count = 1};

    CHECK_FALSE(actions.InteractNpc(99, MenuOp::ATTACK));
    CHECK_FALSE(actions.InteractPlayer(99, 1));
    CHECK_FALSE(actions.InteractGroundItem(QueryWorld::BONES, Fixtures::HOME, Fixtures::HOME, MenuOp::TAKE));
    CHECK_FALSE(actions.ItemOp({.com = TestCache::INVENTORY, .slot = 1, .id = QueryWorld::BONES}, MenuOp::DROP));
    CHECK_FALSE(actions.ItemOp({.com = TestCache::INVENTORY, .slot = 40, .id = QueryWorld::BONES}, MenuOp::DROP));
    CHECK_FALSE(actions.UseItemOnNpc(bones, 99));

    // The targets exist, so these get as far as sending, which needs a session.
    CHECK_THROWS_AS(actions.InteractGroundItem(QueryWorld::BONES, Fixtures::HOME + 2, Fixtures::HOME + 2, MenuOp::TAKE), std::runtime_error);
    CHECK_THROWS_AS(actions.ItemOp(bones, MenuOp::DROP), std::runtime_error);
}

TEST_CASE("ScriptActions have nothing to continue or answer without a dialogue", "[ScriptActions]")
{
    auto fixture = ActionsFixture{};
    auto& actions = fixture.actions;

    CHECK_FALSE(actions.FindContinue().has_value());
    CHECK_FALSE(actions.ContinueDialogue());
    CHECK_FALSE(actions.IsCountDialogOpen());
    CHECK_FALSE(actions.AnswerCountDialog(5));
    CHECK_FALSE(actions.IsAppearanceScreenOpen());
}

namespace
{
    constexpr auto PANEL = u16{900};
    constexpr auto ACCEPT = u16{906};

    std::shared_ptr<const GameCache_s> MakeActionCache()
    {
        auto cache = std::make_shared<GameCache_s>();
        TestCache::SetComponents(*cache);
        TestCache::SetChatInterfaces(*cache);
        TestCache::AddNpc(*cache, TestWorld::NPC_TYPE, "Goblin", {"Talk-to", "Attack"});
        TestCache::AddObj(*cache, TestWorld::LOGS, "Logs");
        TestCache::AddObj(*cache, TestWorld::COINS, "Coins");
        TestCache::AddComponents(*cache, {
            {.id = PANEL, .root = PANEL, .width = 300, .height = 300, .children = {{901}, {.id = 902, .y = 40}, {903}, {904}, {905}, {ACCEPT}, {907}}},
            {.id = 901, .root = PANEL, .type = ComponentType_e::Text, .buttonType = ButtonType_e::Ok, .width = 100, .height = 20, .text = "Confirm"},
            {.id = 902, .root = PANEL, .type = ComponentType_e::Text, .width = 100, .height = 20, .text = "Plain label"},
            {.id = 903, .root = PANEL, .buttonType = ButtonType_e::Target},
            {.id = 904, .root = PANEL, .buttonType = ButtonType_e::Continue},
            {.id = 905, .root = PANEL, .buttonType = ButtonType_e::Close},
            {.id = ACCEPT, .root = PANEL, .buttonType = ButtonType_e::Ok, .clientCode = ClientCode_e::AcceptDesign},
            {.id = 907, .root = PANEL, .buttonType = ButtonType_e::Ok, .hidden = true},
            {.id = TestCache::RUN_ON_BUTTON, .root = 950, .buttonType = ButtonType_e::Select},
        });
        return cache;
    }

    class ActionSession
    {
    public:
        ActionSession()
            : server{TestWorld::Send}
            , client{std::make_shared<const Config_s>(server.MakeConfig()), MakeActionCache(), FakeGameServer::MakeAccount(), capture.GetLogger()}
            , gameActions{client}
            , actions{state, client.GetMap(), gameActions}
        {
            client.Login();
            const auto deadline = std::chrono::steady_clock::now() + 5s;
            while (!client.GetState().IsSettled() && std::chrono::steady_clock::now() < deadline)
            {
                client.Pump(20ms);
            }
            REQUIRE(client.GetState().IsSettled());
            state = client.GetState();
        }

        InventoryItem_s Logs() const
        {
            return {.com = TestCache::INVENTORY, .slot = 0, .id = TestWorld::LOGS, .count = TestWorld::LOG_COUNT};
        }

        void ExpectWords(ClientProt_e prot, std::initializer_list<u16> words)
        {
            client.Flush();
            REQUIRE(server.WaitForPacket(prot, ++expectedCounts[prot]));
            const auto packets = server.GetPackets(prot);
            auto expected = Packet{};
            for (const auto word : words)
            {
                expected.P2(word);
            }
            CHECK(packets.back().payload == std::vector<u8>(expected.GetData().begin(), expected.GetData().end()));
        }

        LogCapture capture;
        FakeGameServer server;
        GameClient client;
        GameState_s state;
        GameActions gameActions;
        ScriptActions actions;
        std::map<ClientProt_e, std::size_t> expectedCounts;
    };
}

TEST_CASE("ScriptActions reject stale inventory references for every item action", "[ScriptActions]")
{
    auto f = ActionsFixture{};
    const auto stale = InventoryItem_s{.com = TestCache::INVENTORY, .slot = 0, .id = QueryWorld::BONES};
    const auto bones = InventoryItem_s{.com = TestCache::INVENTORY, .slot = 2, .id = QueryWorld::BONES};
    CHECK_FALSE(f.actions.InventoryButton(stale, 1));
    CHECK_FALSE(f.actions.UseItemOnNpc(stale, 10));
    CHECK_FALSE(f.actions.UseItemOnPlayer(stale, Fixtures::PID));
    CHECK_FALSE(f.actions.UseItemOnLoc(stale, QueryWorld::DOOR, Fixtures::HOME, Fixtures::HOME));
    CHECK_FALSE(f.actions.UseItemOnGroundItem(stale, QueryWorld::COINS, Fixtures::HOME, Fixtures::HOME + 1));
    CHECK_FALSE(f.actions.UseItemOnItem(stale, bones));
    CHECK_FALSE(f.actions.UseItemOnItem(bones, stale));
    CHECK_FALSE(f.actions.CastOnItem(100, stale));
}

TEST_CASE("ScriptActions reject missing entity and ground-item targets", "[ScriptActions]")
{
    auto f = ActionsFixture{};
    const auto bones = InventoryItem_s{.com = TestCache::INVENTORY, .slot = 2, .id = QueryWorld::BONES};
    CHECK_FALSE(f.actions.UseItemOnPlayer(bones, 900));
    CHECK_FALSE(f.actions.UseItemOnGroundItem(bones, QueryWorld::COINS, Fixtures::HOME, Fixtures::HOME));
    CHECK_FALSE(f.actions.CastOnNpc(100, 900));
    CHECK_FALSE(f.actions.CastOnPlayer(100, 900));
    CHECK_FALSE(f.actions.CastOnGroundItem(100, QueryWorld::COINS, Fixtures::HOME, Fixtures::HOME));
    f.world.state.localPlayer.tile.level = 1;
    CHECK_FALSE(f.actions.InteractGroundItem(QueryWorld::COINS, Fixtures::HOME, Fixtures::HOME + 1, 1));
}

TEST_CASE("ScriptActions send NPC and player interactions only while the target exists", "[ScriptActions]")
{
    auto f = ActionSession{};
    CHECK(f.actions.InteractNpc(TestWorld::NPC_INDEX, 2));
    f.ExpectWords(ClientProt_e::OpNpc2, {TestWorld::NPC_INDEX});
    f.state.npcs.clear();
    CHECK_FALSE(f.actions.InteractNpc(TestWorld::NPC_INDEX, 2));
    CHECK(f.actions.InteractPlayer(Fixtures::PID, 1));
    f.ExpectWords(ClientProt_e::OpPlayer1, {Fixtures::PID});
    CHECK(f.server.GetPackets(ClientProt_e::OpNpc2).size() == 1);
}

TEST_CASE("ScriptActions preserve inventory component slot and id in item packets", "[ScriptActions]")
{
    auto f = ActionSession{};
    const auto logs = f.Logs();
    CHECK(f.actions.ItemOp(logs, 1));
    f.ExpectWords(ClientProt_e::OpHeld1, {TestWorld::LOGS, 0, TestCache::INVENTORY});
    CHECK(f.actions.InventoryButton(logs, 2));
    f.ExpectWords(ClientProt_e::InvButton2, {TestWorld::LOGS, 0, TestCache::INVENTORY});
    CHECK(f.actions.CastOnItem(100, logs));
    f.ExpectWords(ClientProt_e::OpHeldT, {TestWorld::LOGS, 0, TestCache::INVENTORY, 100});
    // A count change alone leaves the same item reference usable.
    f.state.inventories[TestCache::INVENTORY].slots[0].count = 1;
    CHECK(f.actions.ItemOp(logs, 1));
    f.ExpectWords(ClientProt_e::OpHeld1, {TestWorld::LOGS, 0, TestCache::INVENTORY});
}

TEST_CASE("ScriptActions send item-on-entity packets with their source item", "[ScriptActions]")
{
    auto f = ActionSession{};
    CHECK(f.actions.UseItemOnNpc(f.Logs(), TestWorld::NPC_INDEX));
    f.ExpectWords(ClientProt_e::OpNpcU, {TestWorld::NPC_INDEX, TestWorld::LOGS, 0, TestCache::INVENTORY});
    CHECK(f.actions.UseItemOnPlayer(f.Logs(), Fixtures::PID));
    f.ExpectWords(ClientProt_e::OpPlayerU, {Fixtures::PID, TestWorld::LOGS, 0, TestCache::INVENTORY});
    CHECK(f.actions.CastOnNpc(100, TestWorld::NPC_INDEX));
    f.ExpectWords(ClientProt_e::OpNpcT, {TestWorld::NPC_INDEX, 100});
    CHECK(f.actions.CastOnPlayer(100, Fixtures::PID));
    f.ExpectWords(ClientProt_e::OpPlayerT, {Fixtures::PID, 100});
}

TEST_CASE("ScriptActions validate ground targets before sending item and spell packets", "[ScriptActions]")
{
    auto f = ActionSession{};
    constexpr auto X = static_cast<u16>(Fixtures::HOME + 1);
    CHECK(f.actions.InteractGroundItem(TestWorld::COINS, X, X, 3));
    f.ExpectWords(ClientProt_e::OpObj3, {X, X, TestWorld::COINS});
    CHECK(f.actions.UseItemOnGroundItem(f.Logs(), TestWorld::COINS, X, X));
    f.ExpectWords(ClientProt_e::OpObjU, {X, X, TestWorld::COINS, TestWorld::LOGS, 0, TestCache::INVENTORY});
    CHECK(f.actions.CastOnGroundItem(100, TestWorld::COINS, X, X));
    f.ExpectWords(ClientProt_e::OpObjT, {X, X, TestWorld::COINS, 100});
    f.state.groundItems.clear();
    CHECK_FALSE(f.actions.InteractGroundItem(TestWorld::COINS, X, X, 3));
    CHECK_FALSE(f.actions.UseItemOnGroundItem(f.Logs(), TestWorld::COINS, X, X));
    CHECK_FALSE(f.actions.CastOnGroundItem(100, TestWorld::COINS, X, X));
    f.actions.ClickButton(901);
    f.ExpectWords(ClientProt_e::IfButton, {901});
    CHECK(f.server.GetPackets(ClientProt_e::OpObj3).size() == 1);
    CHECK(f.server.GetPackets(ClientProt_e::OpObjU).size() == 1);
    CHECK(f.server.GetPackets(ClientProt_e::OpObjT).size() == 1);
}

TEST_CASE("ScriptActions keep source and target slots distinct when using items together", "[ScriptActions]")
{
    auto f = ActionSession{};
    f.state.inventories[TestCache::INVENTORY].slots.push_back({.id = 995, .count = 10});
    const auto target = InventoryItem_s{.com = TestCache::INVENTORY, .slot = 1, .id = 995, .count = 10};
    CHECK(f.actions.UseItemOnItem(f.Logs(), target));
    f.ExpectWords(ClientProt_e::OpHeldU, {995, 1, TestCache::INVENTORY, TestWorld::LOGS, 0, TestCache::INVENTORY});
    f.state.inventories[TestCache::INVENTORY].slots[1].id = -1;
    CHECK_FALSE(f.actions.UseItemOnItem(f.Logs(), target));
    f.actions.ClickButton(901);
    f.ExpectWords(ClientProt_e::IfButton, {901});
    CHECK(f.server.GetPackets(ClientProt_e::OpHeldU).size() == 1);
}

TEST_CASE("ScriptActions retain loc coordinates and source items in scenery actions", "[ScriptActions]")
{
    auto f = ActionSession{};
    constexpr auto X = static_cast<u16>(Fixtures::HOME - 2);
    constexpr auto Z = static_cast<u16>(Fixtures::HOME + 3);
    constexpr auto LOC = u16{1530};
    f.actions.InteractLoc(LOC, X, Z, 1);
    f.ExpectWords(ClientProt_e::OpLoc1, {X, Z, LOC});
    CHECK(f.actions.UseItemOnLoc(f.Logs(), LOC, X, Z));
    f.ExpectWords(ClientProt_e::OpLocU, {X, Z, LOC, TestWorld::LOGS, 0, TestCache::INVENTORY});
    f.actions.CastOnLoc(100, LOC, X, Z);
    f.ExpectWords(ClientProt_e::OpLocT, {X, Z, LOC, 100});
}

TEST_CASE("ScriptActions only click visible components of a supported button type", "[ScriptActions]")
{
    auto f = ActionSession{};
    CHECK_THROWS_AS(f.actions.ClickComponent(65000), std::invalid_argument);
    CHECK_THROWS_AS(f.actions.ClickComponent(902), std::invalid_argument);
    CHECK_THROWS_AS(f.actions.ClickComponent(903), std::invalid_argument);
    CHECK_FALSE(f.actions.ClickComponent(901));
    f.state.interfaces.mainModal = PANEL;
    CHECK_FALSE(f.actions.ClickComponent(907));
    CHECK(f.actions.ClickComponent(901));
    f.ExpectWords(ClientProt_e::IfButton, {901});
    CHECK(f.actions.ClickComponent(904));
    f.ExpectWords(ClientProt_e::ResumePauseButton, {904});
    CHECK(f.actions.ClickComponent(905));
    f.ExpectWords(ClientProt_e::CloseModal, {});
    CHECK(f.server.GetPackets(ClientProt_e::IfButton).size() == 1);
}

TEST_CASE("ScriptActions text clicks respect the requested root and require a button", "[ScriptActions]")
{
    auto f = ActionSession{};
    f.state.interfaces.mainModal = PANEL;
    CHECK_FALSE(f.actions.ClickText("Missing", std::nullopt));
    CHECK_FALSE(f.actions.ClickText("Plain label", PANEL));
    CHECK_FALSE(f.actions.ClickText("Confirm", 950));
    CHECK(f.actions.ClickText("Confirm", PANEL));
    f.ExpectWords(ClientProt_e::IfButton, {901});
    CHECK(f.server.GetPackets(ClientProt_e::IfButton).size() == 1);
}

TEST_CASE("ScriptActions resume each dialogue and answer each count prompt only once", "[ScriptActions]")
{
    auto f = ActionSession{};
    f.state.interfaces.chatModal = TestCache::DIALOGUE;
    ++f.state.interfaces.modalChanges;
    CHECK(f.actions.FindContinue() == TestCache::DIALOGUE_CONTINUE);
    CHECK(f.actions.ContinueDialogue());
    CHECK_FALSE(f.actions.ContinueDialogue());
    f.ExpectWords(ClientProt_e::ResumePauseButton, {TestCache::DIALOGUE_CONTINUE});
    ++f.state.interfaces.modalChanges;
    CHECK(f.actions.ContinueDialogue());
    f.ExpectWords(ClientProt_e::ResumePauseButton, {TestCache::DIALOGUE_CONTINUE});
    CHECK(f.server.GetPackets(ClientProt_e::ResumePauseButton).size() == 2);
    f.state.interfaces.countDialogOpen = true;
    CHECK(f.actions.AnswerCountDialog(7));
    CHECK_FALSE(f.actions.IsCountDialogOpen());
    CHECK_FALSE(f.actions.AnswerCountDialog(8));
    f.ExpectWords(ClientProt_e::ResumePCountDialog, {0, 7});
    CHECK(f.server.GetPackets(ClientProt_e::ResumePCountDialog).size() == 1);
}

TEST_CASE("ScriptActions save a character design only with its accept screen open", "[ScriptActions]")
{
    auto f = ActionSession{};
    const auto design = IdkDesign_s{.female = true, .kits = {1, 2, 3, 4, 5, 6, 7}, .colours = {1, 2, 3, 4, 5}};
    CHECK_FALSE(f.actions.SetAppearance(design));
    CHECK_FALSE(f.actions.IsAppearanceScreenOpen());
    f.state.interfaces.mainModal = TestCache::DIALOGUE;
    CHECK_FALSE(f.actions.SetAppearance(design));
    f.state.interfaces.mainModal = PANEL;
    CHECK(f.actions.IsAppearanceScreenOpen());
    CHECK(f.actions.SetAppearance(design));
    f.ExpectWords(ClientProt_e::IfButton, {ACCEPT});
    REQUIRE(f.server.WaitForPacket(ClientProt_e::IdkSaveDesign));
    const auto packets = f.server.GetPackets(ClientProt_e::IdkSaveDesign);
    REQUIRE(packets.size() == 1);
    CHECK(packets[0].payload == std::vector<u8>{1, 1, 2, 3, 4, 5, 6, 7, 1, 2, 3, 4, 5});
}

TEST_CASE("ScriptActions use the cache run buttons and check whether their interface is open", "[ScriptActions]")
{
    auto f = ActionSession{};
    CHECK_FALSE(f.actions.CanSetRun());
    f.state.interfaces.sideModal = 950;
    CHECK(f.actions.CanSetRun());
    f.actions.SetRun(true);
    f.ExpectWords(ClientProt_e::IfButton, {TestCache::RUN_ON_BUTTON});
    f.actions.SetRun(false);
    f.ExpectWords(ClientProt_e::IfButton, {TestCache::RUN_OFF_BUTTON});
}
