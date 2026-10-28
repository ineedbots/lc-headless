#include "pch.hpp"
#include "../Support/Cache/TestCache.hpp"
#include "../Support/Game/FakeGameServer.hpp"
#include "../Support/Game/QueryWorld.hpp"
#include "../Support/LogCapture.hpp"
#include "../Support/Script/ScriptTestRuntime.hpp"

#include "Config/Config_s.hpp"
#include "Game/Decode/StateLog.hpp"
#include "Game/GameActions.hpp"
#include "Game/GameClient.hpp"
#include "Game/State/Stat_e.hpp"
#include "Script/Bindings/ScriptBindings.hpp"
#include "Script/Host/EventDispatcher.hpp"
#include "Script/Host/ScriptHooks.hpp"
#include "Script/ScriptContext.hpp"
#include "Script/ScriptVm.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    // Exercise the real VM, runtime hooks and object conversion against controlled game state.
    // No socket or server timing is needed to reproduce events whose entities have already disappeared.
    class DispatchFixture
    {
    public:
        explicit DispatchFixture(std::string_view source)
            : client{std::make_shared<const Config_s>(), world.cache, FakeGameServer::MakeAccount(), capture.GetLogger()}
            , actions{client}
            , context{world.state, world.map, actions}
            , vm{ScriptTestRuntime::Get(), {}, capture.GetLogger()}
            , hooks{vm, [this] { return running; },
                    [this](std::string_view where, std::string_view message)
                    {
                        errors.emplace_back(std::string{where} + ": " + std::string{message});
                        running = false;
                    },
                    [this]
                    {
                        if (++calls == stopAfter)
                        {
                            running = false;
                        }
                    }}
        {
            ScriptBindings::Bind(vm, context);
            ScriptBindings::SetSettings(vm, "{}");
            vm.RunSource(std::string{"seen = []\ndef loop():\n    pass\n"} + std::string{source}, "events_test.py");
            vm.Activate();
            py_assign(py_r0(), vm.GetMain());
            py_assign(py_r1(), py_getdict(vm.GetBuiltins(), py_name("settings")));
            static_cast<void>(vm.CallBuiltin("_rt_load", std::array{py_r0(), py_r1()}));
            dispatcher.SkipToPresent(world.state, *world.cache);
        }

        ~DispatchFixture()
        {
            ScriptBindings::Unbind(vm);
        }

        void Add(GameEventData event)
        {
            StateLog::AddEvent(world.state, std::move(event));
        }

        void Dispatch()
        {
            dispatcher.DispatchEvents(world.state, *world.cache, hooks, *capture.GetLogger());
        }

        void Check(std::string_view assertions)
        {
            REQUIRE_NOTHROW(vm.RunSource(assertions, "events_assertions.py"));
        }

        LogCapture capture;
        QueryWorld world;
        GameClient client;
        GameActions actions;
        ScriptContext context;
        ScriptVm vm;
        bool running = true;
        std::size_t calls = 0;
        std::size_t stopAfter = std::numeric_limits<std::size_t>::max();
        std::vector<std::string> errors;
        ScriptHooks hooks;
        EventDispatcher dispatcher;
    };
}

TEST_CASE("EventDispatcher uses current NPC state for spawns and saved state for despawns", "[EventDispatcher]")
{
    auto f = DispatchFixture{R"python(
def on_npc_spawned(npc):
    seen.append(('spawn', npc.index, npc.name, npc.tile().x))
def on_npc_despawned(npc):
    seen.append(('despawn', npc.index, npc.name, npc.tile().x))
)python"};
    auto npc = f.world.state.npcs.front();
    f.Add(NpcAdded_s{npc});
    f.world.state.npcs.front().tile.x = 3300;
    f.Add(NpcRemoved_s{npc});
    auto gone = QueryWorld::MakeNpc(900, QueryWorld::COW, {.x = 3400, .z = 3200});
    f.Add(NpcAdded_s{gone});
    f.Dispatch();
    f.Check("assert seen[0] == ('spawn', 10, 'Chicken', 3300)\n"
            "assert seen[1][0:3] == ('despawn', 10, 'Chicken')\n"
            "assert seen[1][3] != 3300\n"
            "assert seen[2] == ('spawn', 900, 'Cow', 3400)\n");
    CHECK(f.errors.empty());
}

TEST_CASE("EventDispatcher delivers NPC hits and speech even after an NPC disappears", "[EventDispatcher]")
{
    auto f = DispatchFixture{R"python(
def on_npc_damaged(npc, damage):
    seen.append(('hit', None if npc is None else npc.index, damage))
def on_npc_say(npc, text):
    seen.append(('say', None if npc is None else npc.index, text))
)python"};
    f.Add(NpcHit_s{.index = 10, .hit = {.damage = 4}});
    f.Add(NpcHit_s{.index = 900, .hit = {.damage = 7}});
    f.Add(NpcSaid_s{.index = 10, .text = "Hello"});
    f.Add(NpcSaid_s{.index = 900, .text = "Gone"});
    f.Dispatch();
    f.Check("assert seen == [('hit', 10, 4), ('hit', None, 7), ('say', 10, 'Hello'), ('say', None, 'Gone')]\n");
    CHECK(f.errors.empty());
}

TEST_CASE("EventDispatcher preserves player snapshots and handles missing damage targets", "[EventDispatcher]")
{
    auto f = DispatchFixture{R"python(
def on_player_spawned(player):
    seen.append(('spawn', player.index, player.name))
def on_player_despawned(player):
    seen.append(('despawn', player.index, player.name))
def on_player_damaged(player, damage):
    seen.append(('hit', None if player is None else player.name, damage))
def on_damaged(damage):
    seen.append(('local', damage))
)python"};
    auto player = Player_s{};
    player.index = 20;
    player.appearance = Appearance_s{.name = "Alice"};
    f.Add(PlayerAdded_s{player});
    auto current = player;
    current.appearance->name = "Bob";
    f.world.state.players.push_back(current);
    f.Add(PlayerRemoved_s{player});
    player.index = 21;
    f.Add(PlayerAdded_s{player});
    f.Add(PlayerHit_s{.index = 20, .hit = {.damage = 2}});
    f.Add(PlayerHit_s{.index = 900, .hit = {.damage = 9}});
    f.Add(LocalHit_s{.hit = {.damage = 3}});
    f.Dispatch();
    f.Check("assert seen == [('spawn', 20, 'Bob'), ('despawn', 20, 'Alice'), ('spawn', 21, 'Alice'), ('hit', 'Bob', 2), ('hit', None, 9), ('local', 3)]\n");
    CHECK(f.errors.empty());
}

TEST_CASE("EventDispatcher converts ground items and scenery changes into script objects", "[EventDispatcher]")
{
    auto f = DispatchFixture{R"python(
def on_ground_item_spawned(item):
    seen.append(('spawn', item.id, item.name, item.count, item.tile().x))
def on_ground_item_changed(item, previous):
    seen.append(('changed', item.count, previous))
def on_ground_item_despawned(item):
    seen.append(('despawn', item.id, item.count))
def on_loc_changed(loc):
    seen.append(('loc', loc.id, loc.name, loc.changed, loc.shape, loc.angle))
)python"};
    const auto item = GroundItem_s{.tile = {.x = 3200, .z = 3201}, .id = 995, .count = 50};
    f.Add(GroundItemAdded_s{item});
    f.Add(GroundItemCountChanged_s{.item = item, .previousCount = 10});
    f.Add(GroundItemRemoved_s{item});
    f.Add(LocChanged_s{.change = {.tile = item.tile, .layer = LocLayer_e::Wall, .id = QueryWorld::DOOR, .shape = 0, .angle = 2}});
    f.Add(LocChanged_s{.change = {.tile = item.tile, .id = -1}});
    f.Dispatch();
    f.Check("assert seen == [('spawn', 995, 'Coins', 50, 3200), ('changed', 50, 10), ('despawn', 995, 50), ('loc', 1530, 'Door', True, 0, 2), ('loc', -1, None, True, 0, 0)]\n");
    CHECK(f.errors.empty());
}

TEST_CASE("EventDispatcher reports death before skill changes and ignores unchanged stats", "[EventDispatcher]")
{
    auto f = DispatchFixture{R"python(
def on_death():
    seen.append('death')
def on_skill_xp(event):
    seen.append(('xp', event.name, event.xp, event.delta))
def on_skill_level(event):
    seen.append(('level', event.name, event.level, event.previous))
)python"};
    const auto hp = static_cast<u8>(Stat_e::Hitpoints);
    f.Add(StatChanged_s{.stat = hp, .previous = {.xp = 100, .level = 5, .baseLevel = 5}, .current = {.xp = 120, .level = 0, .baseLevel = 6}});
    f.Add(StatChanged_s{.stat = hp, .previous = {.level = 0}, .current = {.level = 0}});
    f.Add(StatChanged_s{.stat = 0, .previous = {.level = 5}, .current = {.level = 0}});
    f.Add(StatChanged_s{.stat = hp, .previous = {.level = 5}, .current = {.level = 6}});
    f.Dispatch();
    f.Check("assert seen == ['death', ('xp', 'hitpoints', 120, 20), ('level', 'hitpoints', 6, 5)]\n");
    CHECK(f.errors.empty());
}

TEST_CASE("EventDispatcher converts varps modals and reboot ticks in arrival order", "[EventDispatcher]")
{
    auto f = DispatchFixture{R"python(
def on_varp_changed(event):
    seen.append(('varp', event.index, event.value, event.previous))
def on_interface_changed():
    seen.append('modal')
def on_system_update(seconds):
    seen.append(('update', seconds))
)python"};
    f.Add(VarpChanged_s{.varp = 173, .previous = 0, .value = 1});
    f.Add(ModalChanged_s{.mainModal = 100});
    f.Add(RebootStarted_s{.ticks = 100});
    f.Add(RebootStarted_s{.ticks = 1});
    f.Dispatch();
    f.Dispatch();
    f.Check("assert seen == [('varp', 173, 1, 0), 'modal', ('update', 60), ('update', 0)]\n");
    CHECK(f.errors.empty());
}

TEST_CASE("EventDispatcher reports backpack changes by slot including removed and unknown items", "[EventDispatcher]")
{
    auto f = DispatchFixture{R"python(
def on_inventory_changed(event):
    seen.append((event.slot, event.id, event.name, event.count, event.previous_id, event.previous_count))
)python"};
    auto& slots = f.world.state.inventories[TestCache::INVENTORY].slots;
    // QueryWorld starts with coins, an empty slot and two separate bones.
    slots = {{.id = 995, .count = 125}, {.id = 60000, .count = 2}, {.id = 526, .count = 1}};
    f.Add(InventoryChanged_s{TestCache::INVENTORY});
    f.Dispatch();
    f.Dispatch();
    f.Check("assert seen == [(0, 995, 'Coins', 125, 995, 100), (1, 60000, None, 2, -1, 0), (3, -1, None, 0, 526, 1)]\n");
    slots.clear();
    f.Add(InventoryChanged_s{TestCache::INVENTORY});
    f.Dispatch();
    f.Check("assert seen[3:] == [(0, -1, None, 0, 995, 125), (1, -1, None, 0, 60000, 2), (2, -1, None, 0, 526, 1)]\n");
    CHECK(f.errors.empty());
}

TEST_CASE("EventDispatcher updates backpack snapshots even without subscribers", "[EventDispatcher]")
{
    auto f = DispatchFixture{""};
    auto& inventory = f.world.state.inventories[TestCache::INVENTORY];
    inventory.slots = {{.id = 995, .count = 150}};
    f.Add(InventoryChanged_s{TestCache::INVENTORY});
    f.Dispatch();
    f.Check("events.on('inventory_changed', lambda e: seen.append((e.previous_count, e.count)))\n");
    inventory.slots[0].count = 175;
    f.Add(InventoryChanged_s{TestCache::BANK});
    f.Dispatch();
    f.Check("assert seen == []\n");
    f.Add(InventoryChanged_s{TestCache::INVENTORY});
    f.Dispatch();
    f.Check("assert seen == [(150, 175)]\n");
    f.world.state.inventories.erase(TestCache::INVENTORY);
    f.Add(InventoryChanged_s{TestCache::INVENTORY});
    f.Dispatch();
    f.Check("assert seen == [(150, 175), (175, 0)]\n");
    CHECK(f.errors.empty());
}

TEST_CASE("EventDispatcher stops between changed backpack slots when a callback stops the script", "[EventDispatcher]")
{
    auto f = DispatchFixture{"events.on('inventory_changed', lambda e: seen.append(e.slot))\n"};
    f.world.state.inventories[TestCache::INVENTORY].slots.clear();
    f.stopAfter = 1;
    f.Add(InventoryChanged_s{TestCache::INVENTORY});
    f.Dispatch();
    f.Check("assert seen == [0]\n");
    CHECK_FALSE(f.running);
    CHECK(f.errors.empty());
}

TEST_CASE("EventDispatcher dispatches chat types to generic and specific hooks once", "[EventDispatcher]")
{
    auto f = DispatchFixture{R"python(
def on_chat_message(event):
    seen.append(('chat', event.type, event.username, event.text))
def on_server_message(text):
    seen.append(('game', text))
def on_private_message(sender, text):
    seen.append(('private', sender, text))
def on_trade_request(sender):
    seen.append(('trade', sender))
def on_duel_request(sender):
    seen.append(('duel', sender))
)python"};
    StateLog::AddMessage(f.world.state, MessageType_e::Game, "", 0, 0, "Welcome");
    StateLog::AddMessage(f.world.state, MessageType_e::Public, "Alice", 0, 0, "Hello");
    StateLog::AddMessage(f.world.state, MessageType_e::Private, "Bob", 0, 0, "Secret");
    StateLog::AddMessage(f.world.state, MessageType_e::TradeRequest, "Carol", 0, 0, "");
    StateLog::AddMessage(f.world.state, MessageType_e::DuelRequest, "Dave", 0, 0, "");
    StateLog::AddMessage(f.world.state, MessageType_e::Say, "NPC", 0, 0, "Ignored");
    f.dispatcher.DispatchMessages(f.world.state, f.hooks);
    f.dispatcher.DispatchMessages(f.world.state, f.hooks);
    f.Check(R"python(
assert seen == [('chat', 'game', None, 'Welcome'), ('game', 'Welcome'),
                ('chat', 'public', 'Alice', 'Hello'),
                ('chat', 'private', 'Bob', 'Secret'), ('private', 'Bob', 'Secret'),
                ('chat', 'trade_request', 'Carol', ''), ('trade', 'Carol'),
                ('chat', 'duel_request', 'Dave', ''), ('duel', 'Dave')]
)python");
    CHECK(f.errors.empty());
}

TEST_CASE("EventDispatcher consumes stopped events and messages without replaying them", "[EventDispatcher]")
{
    auto f = DispatchFixture{R"python(
def on_damaged(damage):
    seen.append(damage)
def on_server_message(text):
    seen.append(text)
)python"};
    f.running = false;
    f.Add(LocalHit_s{.hit = {.damage = 4}});
    StateLog::AddMessage(f.world.state, MessageType_e::Game, "", 0, 0, "old");
    f.Dispatch();
    f.dispatcher.DispatchMessages(f.world.state, f.hooks);
    f.running = true;
    f.Add(LocalHit_s{.hit = {.damage = 7}});
    StateLog::AddMessage(f.world.state, MessageType_e::Game, "", 0, 0, "new");
    f.Dispatch();
    f.dispatcher.DispatchMessages(f.world.state, f.hooks);
    f.Check("assert seen == [7, 'new']\n");
    CHECK(f.errors.empty());
}

TEST_CASE("EventDispatcher skips old history and snapshots when starting a script", "[EventDispatcher]")
{
    auto f = DispatchFixture{R"python(
def on_damaged(damage):
    seen.append(damage)
def on_server_message(text):
    seen.append(text)
)python"};
    f.Add(LocalHit_s{.hit = {.damage = 4}});
    StateLog::AddMessage(f.world.state, MessageType_e::Game, "", 0, 0, "old");
    f.dispatcher.SkipToPresent(f.world.state, *f.world.cache);
    f.Dispatch();
    f.dispatcher.DispatchMessages(f.world.state, f.hooks);
    f.Check("assert seen == []\n");
    f.world.state.inventories.clear();
    f.dispatcher.SkipToPresent(f.world.state, *f.world.cache);
    CHECK(f.errors.empty());
}

TEST_CASE("EventDispatcher warns about dropped history once and keeps surviving event order", "[EventDispatcher]")
{
    auto f = DispatchFixture{"events.on('damaged', lambda damage: seen.append(damage))\n"};
    f.world.state.eventCount += 5;
    f.Add(LocalHit_s{.hit = {.damage = 2}});
    f.Add(LocalHit_s{.hit = {.damage = 3}});
    f.Dispatch();
    f.Dispatch();
    f.Check("assert seen == [2, 3]\n");
    CHECK(std::ranges::count_if(f.capture.GetEntries(), [](const CapturedLog_s& entry)
    {
        return entry.message == "5 game events were dropped before the script saw them";
    }) == 1);
    CHECK(f.errors.empty());
}

TEST_CASE("EventDispatcher stops subsequent events after a callback raises", "[EventDispatcher]")
{
    auto f = DispatchFixture{R"python(
def on_damaged(damage):
    seen.append(damage)
    raise ValueError('broken hook')
)python"};
    f.Add(LocalHit_s{.hit = {.damage = 2}});
    f.Add(LocalHit_s{.hit = {.damage = 3}});
    f.Dispatch();
    REQUIRE(f.errors.size() == 1);
    CHECK(f.errors[0].find("on_damaged()") != std::string::npos);
    CHECK(f.errors[0].find("broken hook") != std::string::npos);
    f.running = true;
    f.Dispatch();
    f.Check("assert seen == [2]\n");
}

TEST_CASE("EventDispatcher passes projectile timing tiles and optional targets", "[EventDispatcher]")
{
    auto f = DispatchFixture{R"python(
def on_projectile(projectile):
    seen.append((projectile.spotanim, projectile.source(), projectile.destination(),
                 projectile.target, projectile.start_delay, projectile.end_delay, projectile.tick))
)python"};
    auto projectile = Projectile_s{.source = {.x = 3200, .z = 3201, .level = 1},
                                   .destination = {.x = 3205, .z = 3206, .level = 1},
                                   .target = EntityRef_s{.type = EntityType_e::Npc, .index = 10},
                                   .spotAnim = 91, .startDelay = 3, .endDelay = 20, .tick = 100};
    f.Add(ProjectileLaunched_s{projectile});
    projectile.target = EntityRef_s{.type = EntityType_e::Player, .index = 20};
    f.Add(ProjectileLaunched_s{projectile});
    projectile.target.reset();
    f.Add(ProjectileLaunched_s{projectile});
    f.Dispatch();
    f.Check("assert len(seen) == 3\n"
            "assert seen[0] == (91, Tile(3200, 3201, 1), Tile(3205, 3206, 1), ('npc', 10), 3, 20, 100)\n"
            "assert seen[1][3] == ('player', 20)\n"
            "assert seen[2][3] is None\n");
    CHECK(f.errors.empty());
}

TEST_CASE("EventDispatcher does not call specific chat hooks after a generic hook stops the script", "[EventDispatcher]")
{
    auto f = DispatchFixture{R"python(
def on_chat_message(event):
    seen.append(event.text)
def on_server_message(text):
    seen.append('specific')
)python"};
    f.stopAfter = 1;
    StateLog::AddMessage(f.world.state, MessageType_e::Game, "", 0, 0, "first");
    StateLog::AddMessage(f.world.state, MessageType_e::Game, "", 0, 0, "second");
    f.dispatcher.DispatchMessages(f.world.state, f.hooks);
    f.running = true;
    f.dispatcher.DispatchMessages(f.world.state, f.hooks);
    f.Check("assert seen == ['first']\n");
    CHECK(f.errors.empty());
}
