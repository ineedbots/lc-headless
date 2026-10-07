#include "pch.hpp"
#include "../LogCapture.hpp"
#include "ScriptTestRuntime.hpp"

#include "Core/Logger.hpp"
#include "Script/ScriptError.hpp"
#include "Script/ScriptRuntime.hpp"
#include "Script/ScriptVm.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>
#include <pocketpy.h>

using Catch::Matchers::ContainsSubstring;

TEST_CASE("ScriptRuntime hands out at most 16 isolated VMs", "[ScriptRuntime]")
{
    auto capture = LogCapture{};
    auto& runtime = ScriptTestRuntime::Get();
    REQUIRE(runtime.GetFreeSlotCount() == ScriptRuntime::MAX_VMS);

    auto vms = std::vector<std::unique_ptr<ScriptVm>>{};
    for (auto i = 0; i < ScriptRuntime::MAX_VMS; ++i)
    {
        vms.push_back(std::make_unique<ScriptVm>(runtime, ScriptVmOptions_s{}, capture.GetLogger()));
        vms.back()->RunSource(std::format("NUMBER = {}\n\ndef number():\n    return NUMBER\n", i), "numbered.py");
    }

    CHECK(runtime.GetFreeSlotCount() == 0);
    for (auto i = 0; i < ScriptRuntime::MAX_VMS; ++i)
    {
        CHECK(py_toint(vms[static_cast<std::size_t>(i)]->Call("number")) == i);
    }

    const auto createExtra = [&runtime, &capture]
    {
        auto extra = ScriptVm{runtime, {}, capture.GetLogger()};
    };
    CHECK_THROWS_WITH(createExtra(), ContainsSubstring("All 16 script VMs are in use"));

    const auto releasedSlot = vms.back()->GetSlot();
    vms.pop_back();
    CHECK(runtime.GetFreeSlotCount() == 1);

    auto replacement = ScriptVm{runtime, {}, capture.GetLogger()};
    CHECK(replacement.GetSlot() == releasedSlot);
}

TEST_CASE("ScriptRuntime resets a released slot", "[ScriptRuntime]")
{
    auto capture = LogCapture{};
    auto& runtime = ScriptTestRuntime::Get();

    auto slot = -1;
    {
        auto first = ScriptVm{runtime, {}, capture.GetLogger()};
        slot = first.GetSlot();
        first.RunSource("def secret():\n    return 1\n", "first.py");
    }

    auto second = ScriptVm{runtime, {}, capture.GetLogger()};
    REQUIRE(second.GetSlot() == slot);
    CHECK_FALSE(second.HasFunction("secret"));

    second.RunSource("log('builtins are back')\n", "second.py");
    REQUIRE_FALSE(capture.GetEntries().empty());
    CHECK(capture.GetEntries().back().message == "builtins are back");
}

TEST_CASE("ScriptRuntime keeps types registered in one VM out of the others", "[ScriptRuntime]")
{
    auto capture = LogCapture{};
    auto& runtime = ScriptTestRuntime::Get();
    auto first = ScriptVm{runtime, {}, capture.GetLogger()};
    auto second = ScriptVm{runtime, {}, capture.GetLogger()};

    first.Activate();
    static_cast<void>(py_newtype("Thing", tp_object, first.GetMain(), nullptr));

    CHECK(first.HasFunction("Thing"));
    CHECK_FALSE(second.HasFunction("Thing"));
}
