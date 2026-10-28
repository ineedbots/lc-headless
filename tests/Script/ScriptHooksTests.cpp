#include "pch.hpp"
#include "../Support/LogCapture.hpp"
#include "../Support/Script/ScriptTestRuntime.hpp"

#include "Script/Host/ScriptHooks.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

TEST_CASE("ScriptHooks restores the caller's VM and skips malformed console registrations", "[ScriptHooks][HookBoundaryCoverage]")
{
    auto capture = LogCapture{};
    auto& runtime = ScriptTestRuntime::Get();
    auto owner = ScriptVm{runtime, {}, capture.GetLogger()};
    auto caller = ScriptVm{runtime, {}, capture.GetLogger()};
    owner.RunSource("_listening = {'tick': 1}\n_commands = {'zebra': 'last', 'alpha': 'first', 7: 'invalid name', 'bad_help': 42}\n",
                    "registries.py", owner.GetBuiltins());
    auto hooks = ScriptHooks{owner, [] { return true; }, [](auto, auto) {}, [] {}};
    caller.Activate();
    CHECK(&hooks.GetVm() == &owner);
    CHECK(hooks.Has("tick"));
    CHECK(py_currentvm() == caller.GetSlot());
    CHECK_FALSE(hooks.Has("missing"));
    CHECK(py_currentvm() == caller.GetSlot());
    const auto commands = hooks.GetCommands();
    CHECK(py_currentvm() == caller.GetSlot());
    REQUIRE(commands.size() == 2);
    CHECK(commands[0].name == "alpha");
    CHECK(commands[0].help == "first");
    CHECK(commands[1].name == "zebra");
    CHECK(commands[1].help == "last");
}

TEST_CASE("ScriptHooks accepts absent registries and ignores a non-dictionary command registry", "[ScriptHooks][HookBoundaryCoverage]")
{
    const auto source = GENERATE("pass\n", "_commands = ['not a registry']\n");
    auto capture = LogCapture{};
    auto vm = ScriptVm{ScriptTestRuntime::Get(), {}, capture.GetLogger()};
    vm.RunSource(source, "registries.py", vm.GetBuiltins());
    auto hooks = ScriptHooks{vm, [] { return true; }, [](auto, auto) {}, [] {}};
    CHECK_FALSE(hooks.Has("tick"));
    CHECK(hooks.GetCommands().empty());
    CHECK_NOTHROW(hooks.Call("tick"));
}

TEST_CASE("ScriptHooks passes arguments and reports dispatch errors without running the success callback", "[ScriptHooks][HookBoundaryCoverage]")
{
    auto capture = LogCapture{};
    auto vm = ScriptVm{ScriptTestRuntime::Get(), {}, capture.GetLogger()};
    vm.RunSource(R"python(
_listening = {'tick': 1, 'broken': 1}
calls = 0
def _rt_dispatch(name, value=0):
    global calls
    calls += 1
    if name == 'broken':
        raise ValueError('hook failure')
    return value + 1
)python", "dispatch.py", vm.GetBuiltins());
    auto running = true;
    auto after = 0;
    auto errors = std::vector<std::pair<std::string, std::string>>{};
    auto hooks = ScriptHooks{vm, [&] { return running; }, [&](auto where, auto message)
    {
        errors.emplace_back(where, message);
    }, [&] { ++after; }};
    vm.Activate();
    py_newint(py_r0(), 42);
    const auto answer = hooks.Dispatch("tick", std::array{py_r0()});
    REQUIRE(answer.has_value());
    CHECK(py_toint(*answer) == 43);
    CHECK(after == 1);
    CHECK(errors.empty());
    CHECK_FALSE(hooks.Dispatch("broken").has_value());
    CHECK(after == 1);
    REQUIRE(errors.size() == 1);
    CHECK(errors[0].first == "on_broken()");
    CHECK_THAT(errors[0].second, Catch::Matchers::ContainsSubstring("ValueError: hook failure"));
    hooks.Call("missing");
    running = false;
    hooks.Call("tick");
    CHECK_FALSE(hooks.IsRunning());
    CHECK(after == 1);
    vm.RunSource("assert calls == 2\n", "check.py", vm.GetBuiltins());
    running = true;
    hooks.Call("tick");
    CHECK(after == 2);
}
