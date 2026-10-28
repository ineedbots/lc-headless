#include "pch.hpp"
#include "Game/Nav/NavRequires_s.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>

TEST_CASE("Every navigation restriction marks an edge as gated", "[NavRequirements]")
{
    auto requirement = NavRequires_s{};
    CHECK_FALSE(requirement.IsGated());
    CHECK_FALSE(requirement.Check(NavState_s{}).has_value());
    SECTION("membership") { requirement.members = true; }
    SECTION("free slots, even zero") { requirement.freeSlots = 0; }
    SECTION("skills") { requirement.skills = {{"Agility", 10}}; }
    SECTION("items") { requirement.items = {{"Rope", 1}}; }
    SECTION("worn items") { requirement.worn = {{"Boots of lightness", 1}}; }
    SECTION("currency") { requirement.currency = NavRequires_s::Amount_s{"Coins", 10}; }
    SECTION("quest waiver") { requirement.questWaivesItems = "Prince Ali Rescue"; }
    SECTION("quest status") { requirement.quests = {{"Cook's Assistant", "complete", {}}}; }
    SECTION("Entrana gear") { requirement.forbidEntranaRestricted = true; }
    SECTION("slash tool") { requirement.slashTool = true; }
    SECTION("essence return") { requirement.essenceExitReturn = "aubury"; }
    CHECK(requirement.IsGated());
}

TEST_CASE("Navigation checks membership and free slot thresholds", "[NavRequirements]")
{
    const auto requirement = NavRequires_s{.members = true, .freeSlots = 2};
    auto state = NavState_s{};
    CHECK(requirement.Check(state) == "members-only");
    state.members = true;
    CHECK(requirement.Check(state) == "need 2 free inventory slots (have 0)");
    state.freeSlots = 1;
    CHECK(requirement.Check(state) == "need 2 free inventory slots (have 1)");
    state.freeSlots = 2;
    CHECK_FALSE(requirement.Check(state).has_value());
}

TEST_CASE("Navigation skills and supplies use case insensitive names and exact thresholds", "[NavRequirements]")
{
    auto requirement = NavRequires_s{};
    auto state = NavState_s{};
    SECTION("skills")
    {
        requirement.skills = {{"Agility", 20}};
        CHECK(requirement.Check(state) == "need Agility 20 (have 0)");
        state.skills["agility"] = 19;
        CHECK(requirement.Check(state) == "need Agility 20 (have 19)");
        state.skills["agility"] = 20;
    }
    SECTION("items")
    {
        requirement.items = {{"Rope", 2}};
        CHECK(requirement.Check(state) == "need 2 Rope (have 0)");
        state.items["rope"] = 1;
        CHECK(requirement.Check(state) == "need 2 Rope (have 1)");
        state.items["rope"] = 2;
    }
    SECTION("currency")
    {
        requirement.currency = NavRequires_s::Amount_s{"Coins", 30};
        CHECK(requirement.Check(state) == "need 30 Coins (have 0)");
        state.items["coins"] = 29;
        CHECK(requirement.Check(state) == "need 30 Coins (have 29)");
        state.items["coins"] = 30;
    }
    CHECK_FALSE(requirement.Check(state).has_value());
}

TEST_CASE("Quest completion waives supplies but preserves equipment and skill requirements", "[NavRequirements]")
{
    const auto requirement = NavRequires_s{
        .skills = {{"Agility", 10}}, .items = {{"Rope", 1}}, .worn = {{"Boots", 1}},
        .currency = NavRequires_s::Amount_s{"Coins", 30}, .questWaivesItems = "Prince Ali Rescue"};
    auto state = NavState_s{};
    state.skills["agility"] = 10;
    CHECK(requirement.Check(state) == "need 30 Coins (have 0)");
    state.quests["prince ali rescue"] = "started";
    CHECK(requirement.Check(state) == "need 30 Coins (have 0)");
    state.quests["prince ali rescue"] = "complete";
    state.items["boots"] = 1;
    CHECK(requirement.Check(state) == "need to wear Boots");
    state.worn["boots"] = 1;
    CHECK_FALSE(requirement.Check(state).has_value());
    state.skills.clear();
    CHECK(requirement.Check(state) == "need Agility 10 (have 0)");
}

TEST_CASE("Navigation quest bounds distinguish unknown, unstarted, started and complete", "[NavRequirements]")
{
    auto requirement = NavRequires_s{};
    auto state = NavState_s{};
    SECTION("minimum status")
    {
        requirement.quests = {{"Cook's Assistant", "started", {}}};
        CHECK(requirement.Check(state) == "need Cook's Assistant started (it's unknown)");
        state.quests["cook's assistant"] = "not_started";
        CHECK(requirement.Check(state) == "need Cook's Assistant started (it's not_started)");
        state.quests["cook's assistant"] = "started";
        CHECK_FALSE(requirement.Check(state).has_value());
        state.quests["cook's assistant"] = "complete";
        CHECK_FALSE(requirement.Check(state).has_value());
    }
    SECTION("maximum status requires known state")
    {
        requirement.quests = {{"Cook's Assistant", {}, "started"}};
        CHECK(requirement.Check(state) == "need to know where Cook's Assistant stands");
        state.quests["cook's assistant"] = "unknown";
        CHECK(requirement.Check(state) == "need to know where Cook's Assistant stands");
        state.quests["cook's assistant"] = "complete";
        CHECK(requirement.Check(state) == "need Cook's Assistant at most started (it's complete)");
        state.quests["cook's assistant"] = "started";
        CHECK_FALSE(requirement.Check(state).has_value());
        state.quests["cook's assistant"] = "not_started";
        CHECK_FALSE(requirement.Check(state).has_value());
    }
    SECTION("both bounds")
    {
        requirement.quests = {{"Cook's Assistant", "started", "started"}};
        state.quests["cook's assistant"] = "started";
        CHECK_FALSE(requirement.Check(state).has_value());
        state.quests["cook's assistant"] = "complete";
        CHECK(requirement.Check(state).has_value());
        state.quests["cook's assistant"] = "not_started";
        CHECK(requirement.Check(state).has_value());
    }
}

TEST_CASE("Navigation checks Entrana gear independently from slash tools", "[NavRequirements]")
{
    const auto requirement = NavRequires_s{.forbidEntranaRestricted = true, .slashTool = true};
    auto state = NavState_s{.entranaRestrictedGear = true, .canSlashWeb = true};
    CHECK(requirement.Check(state) == "remove weapons and armour before Entrana");
    state.entranaRestrictedGear = false;
    state.canSlashWeb = false;
    CHECK(requirement.Check(state) == "need a knife or a bladed weapon to slash webs");
    state.canSlashWeb = true;
    CHECK_FALSE(requirement.Check(state).has_value());
    state.canSlashWeb.reset();
    CHECK_FALSE(requirement.Check(state).has_value());
}
