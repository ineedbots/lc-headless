#include "pch.hpp"
#include "../Cache/RealCache.hpp"
#include "../Game/FakeGameServer.hpp"
#include "../Game/Fixtures.hpp"
#include "../LogCapture.hpp"
#include "ScriptTestRuntime.hpp"

#include "Cache/GameCache_s.hpp"
#include "Core/ConfigFile.hpp"
#include "Game/GameActions.hpp"
#include "Game/GameClient.hpp"
#include "Game/Map/WorldMap.hpp"
#include "Game/State/GameState_s.hpp"
#include "Script/ScriptApi.hpp"
#include "Script/ScriptBindings.hpp"
#include "Script/ScriptVm.hpp"

#include <catch2/catch_test_macros.hpp>

// The standard library's rules for finding things in the side tabs, run against the 289 cache's interfaces.
namespace
{
    constexpr auto COMBAT_UNARMED = s32{5855};
    constexpr auto COMBAT_STABSWORD = s32{2276};
    constexpr auto STABSWORD_SPECIAL_BAR = u16{7562};
    constexpr auto COMBAT_STAFF = s32{328};
    constexpr auto STAFF_SPELLS = s32{1829};
    constexpr auto QUEST_LIST = s32{638};
    constexpr auto PRAYER = s32{5608};
    constexpr auto MAGIC = s32{1151};
    constexpr auto CONTROLS_TAB = std::size_t{11};

    class RealCacheFixture
    {
    public:
        RealCacheFixture()
            : cache{RealCache::RequireShared()}
            , map{cache}
            , client{std::make_shared<const Config_s>(), cache, FakeGameServer::MakeAccount(), capture.GetLogger()}
            , actions{client}
            , api{state, map, actions}
            , vm{ScriptTestRuntime::Get(), {}, capture.GetLogger()}
        {
            auto& tabs = state.interfaces.tabs;
            tabs[0] = COMBAT_UNARMED;
            tabs[2] = QUEST_LIST;
            tabs[5] = PRAYER;
            tabs[6] = MAGIC;
            for (const auto& [id, component] : cache->components)
            {
                if (component.text == "Auto Retaliate" || component.text == "Auto retaliate")
                {
                    tabs[CONTROLS_TAB] = component.root;
                }
            }

            ScriptBindings::Bind(vm, api);
        }

        ~RealCacheFixture()
        {
            ScriptBindings::Unbind(vm);
        }

        RealCacheFixture(const RealCacheFixture&) = delete;
        RealCacheFixture& operator=(const RealCacheFixture&) = delete;

        LogCapture capture;
        std::shared_ptr<const GameCache_s> cache;
        GameState_s state = Fixtures::PlacedState();
        WorldMap map;
        GameClient client;
        GameActions actions;
        ScriptApi api;
        ScriptVm vm;
    };
}

TEST_CASE("The stdlib finds the real cache's combat styles, prayers, spells and quests", "[RealCache]")
{
    auto fixture = RealCacheFixture{};
    fixture.vm.RunSource(R"python(
assert game.combat_styles() == [(0, '(Accurate)'), (1, '(Aggressive)'), (2, '(Defensive)')], game.combat_styles()
assert game.combat_style_mode('strength') == 1
# Unarmed has no controlled style, so it trains defence instead.
resolution = game.combat_style_resolution('controlled')
assert resolution.effective == 'defence' and resolution.mode == 2

from rs2004.tabs import _select_button, spell_button, teleport_button
assert _select_button(172, 0) is not None and _select_button(172, 1) is not None

toggles = [c for c in interfaces.root(interfaces.tab(5)) if c.button == 'toggle']
assert len(toggles) == len(PRAYER_NAMES)
assert len(set([c.varp for c in toggles])) == len(PRAYER_NAMES)
assert prayer.known('Protect from Melee') and prayer._button('thick skin').id == toggles[0].id

assert spell_button('wind strike') != -1 and spell_button('Superheat item') != -1
assert spell_button('Kamehameha') == -1
assert teleport_button('Varrock') != -1 and teleport_button('Cast @gre@Lumbridge teleport') != -1

all_quests = quests.all()
assert len(all_quests) > 10
assert quests.status("Cook's Assistant") == 'not_started', all_quests
assert special.bar_component() == -1
)python", "real_cache.py");
}

TEST_CASE("The stdlib finds the real cache's special attack bar and autocast spells", "[RealCache]")
{
    auto fixture = RealCacheFixture{};
    auto& tabs = fixture.state.interfaces.tabs;
    tabs[0] = COMBAT_STABSWORD;
    fixture.vm.RunSource(R"python(
assert special.bar_component() == -1
assert not autocast.staff_tab_attached()
)python", "hidden_special.py");

    // The bar's layer starts hidden; the server shows it when a weapon with a special is wielded.
    const auto layer = *fixture.cache->FindComponent(STABSWORD_SPECIAL_BAR)->parent;
    fixture.state.interfaces.components[layer].hidden = false;
    fixture.vm.RunSource(R"python(
assert special.bar_component() == 7562
)python", "special.py");

    tabs[0] = COMBAT_STAFF;
    fixture.vm.RunSource(R"python(
assert autocast.staff_tab_attached()
from rs2004.tabs import _select_button_reading
assert _select_button_reading(108) is not None
)python", "staff.py");

    tabs[0] = STAFF_SPELLS;
    fixture.vm.RunSource(R"python(
choices = [c.id for c in interfaces.root(interfaces.tab(0)) if c.button == 'ok']
assert choices[:len(AUTOCAST_SPELLS)] == list(range(1830, 1830 + len(AUTOCAST_SPELLS))), choices
)python", "spells.py");
}
