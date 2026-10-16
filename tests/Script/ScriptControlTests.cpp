#include "pch.hpp"

#include "Script/ScriptControl.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("ScriptControl keeps the strongest stop request until it's taken", "[ScriptControl]")
{
    auto control = ScriptControl{};

    CHECK(control.TakeStopRequest() == StopRequest_e::None);
    control.RequestStop(StopRequest_e::Account);
    control.RequestStop(StopRequest_e::Script);
    CHECK(control.TakeStopRequest() == StopRequest_e::Account);
    CHECK(control.TakeStopRequest() == StopRequest_e::None);
}

TEST_CASE("ScriptControl keeps a relog request until it's taken", "[ScriptControl]")
{
    auto control = ScriptControl{};

    CHECK_FALSE(control.TakeRelogRequest().has_value());
    control.RequestRelog(30s);
    CHECK(control.TakeRelogRequest() == 30s);
    CHECK_FALSE(control.TakeRelogRequest().has_value());
}

TEST_CASE("ScriptControl notes progress at the step's time", "[ScriptControl]")
{
    auto control = ScriptControl{};

    CHECK_FALSE(control.GetLastProgress().has_value());
    control.SetStepTime(1200);
    control.NoteProgress();
    control.SetStepTime(1800);
    CHECK(control.GetStepTime() == 1800);
    CHECK(control.GetLastProgress() == 1200);
}
