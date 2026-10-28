#include "pch.hpp"
#include "../Support/LogCapture.hpp"
#include "../Support/Script/ScriptTestRuntime.hpp"
#include "../Support/TempFolder.hpp"

#include "Console/LogLevel_e.hpp"
#include "Console/Logger.hpp"
#include "Script/Error/ScriptError.hpp"
#include "Script/ScriptVm.hpp"
#include "Script/Stdlib.hpp"
#include "Utils/FileUtils.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>
#include <pocketpy.h>
#include <nlohmann/json.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    nlohmann::json ReadProfile(const std::filesystem::path& directory)
    {
        const auto text = FileUtils::ReadText(directory / "profiler_report.json");
        REQUIRE(text.has_value());
        return nlohmann::json::parse(*text);
    }

    s64 ProfileHits(const nlohmann::json& report, std::string_view file)
    {
        s64 hits = 0;
        for (const auto& line : report.at("records").at(std::string{file}))
        {
            hits += line.at(1).get<s64>();
        }
        return hits;
    }
}

TEST_CASE("Script profiling accumulates calls and generator resumes with matching sources", "[ScriptVm][Profiling]")
{
    const auto folder = TempFolder{"rs2004-profile-tests"};
    const auto output = folder.GetPath() / "profile";
    folder.WriteFile("helper.py", "def answer():\n    return 42\n");
    auto capture = LogCapture{};
    auto vm = ScriptVm{ScriptTestRuntime::Get(), {.scriptsDirectory = folder.GetPath(), .profileDirectory = output}, capture.GetLogger()};
    const auto source = "import helper\nimport rs2004.geometry\n\ndef steps():\n    yield helper.answer()\n    yield 2\n\ngen = steps()\n\ndef step():\n    return next(gen)\n";
    vm.RunSource(source, "main.py");
    CHECK(py_toint(vm.Call("step")) == 42);
    vm.SaveProfile();
    const auto first = ReadProfile(output);
    CHECK(first.at("CLOCKS_PER_SEC").get<s64>() > 0);
    CHECK(ProfileHits(first, "helper.py") > 0);
    CHECK(py_toint(vm.Call("step")) == 2);
    vm.SaveProfile();
    CHECK(ProfileHits(ReadProfile(output), "main.py") > ProfileHits(first, "main.py"));
    CHECK(FileUtils::ReadText(output / "sources/main.py") == source);
    CHECK(FileUtils::ReadText(output / "sources/helper.py") == "def answer():\n    return 42\n");
    REQUIRE(Stdlib::Find("rs2004/geometry.py").has_value());
    CHECK(FileUtils::ReadText(output / "sources/rs2004/geometry.py") == Stdlib::Find("rs2004/geometry.py"));
    CHECK_THROWS_WITH(vm.WaitForDebugger(), ContainsSubstring("can't share"));
}

TEST_CASE("Script profiling balances suspended generators before an empty hook", "[ScriptVm][Profiling]")
{
    const auto folder = TempFolder{"rs2004-profile-yields"};
    auto capture = LogCapture{};
    auto vm = ScriptVm{ScriptTestRuntime::Get(), {.profileDirectory = folder.GetPath()}, capture.GetLogger()};
    vm.RunSource("def child():\n    yield 1\n    yield 2\n\ndef parent():\n    yield from child()\n\ngen = parent()\n\ndef step():\n    return next(gen)\n\ndef hook():\n    pass\n", "yielding.py");
    CHECK(py_toint(vm.Call("step")) == 1);
    // While the tutorial guardian is suspended, tick dispatch can return without any more Python work.
    CHECK_NOTHROW(vm.Call("hook"));
    CHECK(py_toint(vm.Call("step")) == 2);
    CHECK_NOTHROW(vm.Call("hook"));
    CHECK_THROWS_WITH(vm.Call("step"), ContainsSubstring("StopIteration"));
    CHECK_NOTHROW(vm.Call("hook"));
    vm.SaveProfile();
    CHECK(ProfileHits(ReadProfile(folder.GetPath()), "yielding.py") > 0);
}

TEST_CASE("Script profiling saves errors and recovers after watchdog timeouts", "[ScriptVm][Profiling]")
{
    const auto folder = TempFolder{"rs2004-profile-errors"};
    auto capture = LogCapture{};
    auto vm = ScriptVm{ScriptTestRuntime::Get(), {.callTimeout = 50ms, .profileDirectory = folder.GetPath()}, capture.GetLogger()};
    vm.RunSource("def fail():\n    raise ValueError('failure')\n\ndef spin():\n    while True:\n        pass\n\ndef answer():\n    return 42\n", "errors.py");
    CHECK_THROWS_WITH(vm.Call("fail"), ContainsSubstring("ValueError"));
    CHECK(ProfileHits(ReadProfile(folder.GetPath()), "errors.py") > 0);
    CHECK_THROWS_WITH(vm.Call("spin"), ContainsSubstring("TimeoutError"));
    CHECK(py_toint(vm.Call("answer")) == 42);
    vm.SaveProfile();
    CHECK(ProfileHits(ReadProfile(folder.GetPath()), "errors.py") > 0);
}

TEST_CASE("Script profiling keeps VMs isolated and writes before releasing a slot", "[ScriptVm][Profiling]")
{
    const auto folder = TempFolder{"rs2004-profile-vms"};
    auto capture = LogCapture{};
    auto& runtime = ScriptTestRuntime::Get();
    {
        auto first = ScriptVm{runtime, {.profileDirectory = folder.GetPath() / "first"}, capture.GetLogger()};
        auto second = ScriptVm{runtime, {.profileDirectory = folder.GetPath() / "second"}, capture.GetLogger()};
        first.RunSource("def answer():\n    return 1\n", "first.py");
        second.RunSource("def answer():\n    return 2\n", "second.py");
        CHECK(py_toint(first.Call("answer")) == 1);
        CHECK(py_toint(second.Call("answer")) == 2);
    }
    const auto first = ReadProfile(folder.GetPath() / "first");
    const auto second = ReadProfile(folder.GetPath() / "second");
    CHECK(first.at("records").contains("first.py"));
    CHECK_FALSE(first.at("records").contains("second.py"));
    CHECK(second.at("records").contains("second.py"));
    CHECK_FALSE(second.at("records").contains("first.py"));
    {
        auto disabled = ScriptVm{runtime, {}, capture.GetLogger()};
        disabled.RunSource("pass\n", "disabled.py");
        disabled.SaveProfile();
    }
    CHECK(ReadProfile(folder.GetPath() / "first") == first);
}

TEST_CASE("Script profiling checkpoints without resetting and tolerates write failures", "[ScriptVm][Profiling]")
{
    const auto folder = TempFolder{"rs2004-profile-save"};
    const auto output = folder.GetPath() / "output";
    auto capture = LogCapture{};
    auto vm = ScriptVm{ScriptTestRuntime::Get(), {.profileDirectory = output}, capture.GetLogger()};
    vm.RunSource("def answer():\n    return 42\n", "checkpoint.py");
    CHECK_FALSE(std::filesystem::exists(output));
    const auto now = std::chrono::steady_clock::now();
    vm.CheckpointProfile(now + 61s);
    const auto first = ReadProfile(output);
    CHECK(py_toint(vm.Call("answer")) == 42);
    vm.CheckpointProfile(now + 62s);
    CHECK(ReadProfile(output) == first);
    vm.CheckpointProfile(now + 122s);
    CHECK(ProfileHits(ReadProfile(output), "checkpoint.py") > ProfileHits(first, "checkpoint.py"));

    folder.WriteFile("blocked", "a file, not a directory");
    auto blocked = ScriptVm{ScriptTestRuntime::Get(), {.profileDirectory = folder.GetPath() / "blocked"}, capture.GetLogger()};
    blocked.RunSource("def answer():\n    return 7\n", "blocked.py");
    CHECK_NOTHROW(blocked.SaveProfile());
    CHECK(py_toint(blocked.Call("answer")) == 7);
    CHECK(std::ranges::any_of(capture.GetEntries(), [](const auto& entry)
    {
        return entry.message.find("Couldn't save script profile") != std::string::npos;
    }));
}

namespace
{
    using LogLine = std::pair<LogLevel_e, std::string>;

    std::vector<LogLine> GetLines(const LogCapture& capture)
    {
        auto lines = std::vector<LogLine>{};
        for (const auto& entry : capture.GetEntries())
        {
            lines.emplace_back(entry.level, entry.message);
        }

        return lines;
    }

    std::string ToString(py_Ref value)
    {
        return py_tostr(value);
    }

    // Stand-ins for the walker's route search: a native call that takes as many milliseconds as it's given,
    // run as the search is, or as any other binding.
    bool SlowSearch(int, py_StackRef argv) noexcept
    {
        const auto ms = std::chrono::milliseconds{py_toint(py_arg(0))};
        const auto found = ScriptVm::GetCurrent().RunRouteSearch([ms]
        {
            std::this_thread::sleep_for(ms);
            return true;
        });
        py_newbool(py_retval(), found);
        return true;
    }

    bool SlowBinding(int, py_StackRef argv) noexcept
    {
        std::this_thread::sleep_for(std::chrono::milliseconds{py_toint(py_arg(0))});
        py_newnone(py_retval());
        return true;
    }
}

TEST_CASE("ScriptVm runs source and calls the functions it defines", "[ScriptVm]")
{
    auto capture = LogCapture{};
    auto vm = ScriptVm{ScriptTestRuntime::Get(), {}, capture.GetLogger()};
    vm.RunSource("LIMIT = 10\n\ndef add(a, b):\n    return a + b\n\ndef answer():\n    return 42\n", "adder.py");

    CHECK(vm.HasFunction("add"));
    CHECK_FALSE(vm.HasFunction("LIMIT"));
    CHECK_FALSE(vm.HasFunction("missing"));
    CHECK(py_toint(vm.Call("answer")) == 42);

    vm.Activate();
    py_newint(py_r0(), 2);
    py_newint(py_r1(), 3);

    const auto args = std::array{py_r0(), py_r1()};
    CHECK(py_toint(vm.Call("add", args)) == 5);

    CHECK_THROWS_WITH(vm.Call("missing"), ContainsSubstring("no function missing()"));
}

TEST_CASE("ScriptVm sends print, log and debug to its logger", "[ScriptVm]")
{
    auto capture = LogCapture{};
    {
        auto vm = ScriptVm{ScriptTestRuntime::Get(), {}, capture.GetLogger()};
        // clang-format off
        vm.RunSource("log('hello', 42, None)\n"
                     "debug('detail')\n"
                     "print('a', 'b')\n"
                     "print('first\\nsecond')\n"
                     "print('partial', end='')\n",
            "output.py");
        // clang-format on

        // clang-format off
        CHECK(GetLines(capture) == std::vector<LogLine>{
            {LogLevel_e::Info, "hello 42 None"},
            {LogLevel_e::Verbose, "detail"},
            {LogLevel_e::Info, "a b"},
            {LogLevel_e::Info, "first"},
            {LogLevel_e::Info, "second"},
        });
        // clang-format on
    }

    REQUIRE_FALSE(capture.GetEntries().empty());
    CHECK(capture.GetEntries().back().message == "partial");
}

TEST_CASE("ScriptVm keeps each script's globals to itself", "[ScriptVm]")
{
    auto capture = LogCapture{};
    auto& runtime = ScriptTestRuntime::Get();
    auto first = ScriptVm{runtime, {}, capture.GetLogger()};
    auto second = ScriptVm{runtime, {}, capture.GetLogger()};
    auto third = ScriptVm{runtime, {}, capture.GetLogger()};

    first.RunSource("owner = 'first'\n\ndef get():\n    return owner\n", "first.py");
    second.RunSource("owner = 'second'\n\ndef get():\n    return owner\n", "second.py");
    third.RunSource("def get():\n    return owner\n", "third.py");

    CHECK(ToString(first.Call("get")) == "first");
    CHECK(ToString(second.Call("get")) == "second");
    CHECK_THROWS_WITH(third.Call("get"), ContainsSubstring("NameError"));
}

TEST_CASE("ScriptVm imports from the scripts folder, then its lib folder", "[ScriptVm]")
{
    auto capture = LogCapture{};
    const auto folder = TempFolder{"rs2004-script-tests"};
    folder.WriteFile("helper.py", "SOURCE = 'scripts'\n");
    folder.WriteFile("lib/helper.py", "SOURCE = 'lib'\n");
    folder.WriteFile("lib/shared.py", "def greet(name):\n    log('hello from lib', name)\n    return 'lib'\n");
    folder.WriteFile("lib/tools/__init__.py", "");
    folder.WriteFile("lib/tools/walking.py", "NAME = 'walking'\n");
    // clang-format off
    folder.WriteFile("main.py",
        "import helper\n"
        "import shared\n"
        "import tools.walking\n"
        "\n"
        "def sources():\n"
        "    return helper.SOURCE + ',' + shared.greet('bot') + ',' + tools.walking.NAME\n");
    // clang-format on

    auto vm = ScriptVm{ScriptTestRuntime::Get(), ScriptVmOptions_s{.scriptsDirectory = folder.GetPath()}, capture.GetLogger()};
    vm.RunFile("main.py");

    CHECK(ToString(vm.Call("sources")) == "scripts,lib,walking");
    REQUIRE_FALSE(capture.GetEntries().empty());
    CHECK(capture.GetEntries().back().message == "hello from lib bot");

    SECTION("it remembers every file it ran or imported")
    {
        const auto& root = folder.GetPath();
        const auto expected = std::vector<std::filesystem::path>{root / "main.py", root / "helper.py", root / "lib/shared.py", root / "lib/tools/__init__.py", root / "lib/tools/walking.py"};
        const auto& files = vm.GetFiles();
        REQUIRE_FALSE(files.empty());
        CHECK(files.front() == root / "main.py");
        CHECK(std::ranges::is_permutation(files, expected));
    }

    SECTION("a missing module raises ImportError")
    {
        CHECK_THROWS_WITH(vm.RunSource("import missing_module\n", "missing.py"), ContainsSubstring("ImportError") && ContainsSubstring("missing_module"));
    }

    SECTION("pocketpy's own modules still import")
    {
        CHECK_NOTHROW(vm.RunSource("import math\nimport json\nimport random\nimport collections\n", "stdlib.py"));
    }
}

TEST_CASE("ScriptVm runs a script file relative to the scripts folder", "[ScriptVm]")
{
    auto capture = LogCapture{};
    const auto folder = TempFolder{"rs2004-script-tests"};
    folder.WriteFile("examples/walker.py", "def loop():\n    return 600\n");
    folder.WriteFile("broken.py", "def loop(:\n    return 600\n");

    auto vm = ScriptVm{ScriptTestRuntime::Get(), ScriptVmOptions_s{.scriptsDirectory = folder.GetPath()}, capture.GetLogger()};
    vm.RunFile("examples/walker.py");
    CHECK(py_toint(vm.Call("loop")) == 600);

    CHECK_THROWS_WITH(vm.RunFile("examples/missing.py"), ContainsSubstring("Can't read script"));
    CHECK_THROWS_WITH(vm.RunFile("../outside.py"), ContainsSubstring("must be relative to the scripts directory"));
    CHECK_THROWS_WITH(vm.RunFile(folder.GetPath() / "examples/walker.py"), ContainsSubstring("must be relative to the scripts directory"));
    CHECK_THROWS_WITH(vm.RunFile("broken.py"), ContainsSubstring("broken.py") && ContainsSubstring("line 1") && ContainsSubstring("SyntaxError"));
}

TEST_CASE("ScriptVm turns a Python exception into a ScriptError with its traceback", "[ScriptVm]")
{
    auto capture = LogCapture{};
    auto vm = ScriptVm{ScriptTestRuntime::Get(), {}, capture.GetLogger()};
    vm.RunSource("def fail():\n    raise ValueError('boom')\n\ndef ok():\n    return 1\n", "failing.py");

    CHECK_THROWS_WITH(vm.Call("fail"), ContainsSubstring("ValueError: boom") && ContainsSubstring("failing.py") && ContainsSubstring("line 2"));
    CHECK(py_toint(vm.Call("ok")) == 1);
    CHECK_THROWS_WITH(vm.RunSource("raise KeyError('at load')\n", "load.py"), ContainsSubstring("KeyError"));

    SECTION("failed calls leave nothing on the stack")
    {
        constexpr auto CALLS = 20'000;
        auto failures = 0;
        for (auto i = 0; i < CALLS; ++i)
        {
            try
            {
                vm.Call("fail");
            }
            catch (const ScriptError&)
            {
                ++failures;
            }
        }

        CHECK(failures == CALLS);
        CHECK(py_toint(vm.Call("ok")) == 1);
    }
}

TEST_CASE("ScriptVm's watchdog stops a script that runs too long", "[ScriptVm]")
{
    auto capture = LogCapture{};
    auto vm = ScriptVm{ScriptTestRuntime::Get(), ScriptVmOptions_s{.callTimeout = 100ms}, capture.GetLogger()};
    vm.RunSource("def spin():\n    while True:\n        pass\n\ndef ok():\n    return 1\n", "spin.py");

    const auto start = std::chrono::steady_clock::now();
    CHECK_THROWS_WITH(vm.Call("spin"), ContainsSubstring("TimeoutError"));
    CHECK(std::chrono::steady_clock::now() - start < 2s);
    CHECK(py_toint(vm.Call("ok")) == 1);

    CHECK_THROWS_WITH(vm.RunSource("while True:\n    pass\n", "top.py"), ContainsSubstring("TimeoutError"));
}

TEST_CASE("ScriptVm gives the walker's route search more than a call's timeout", "[ScriptVm]")
{
    auto capture = LogCapture{};
    auto vm = ScriptVm{ScriptTestRuntime::Get(), ScriptVmOptions_s{.callTimeout = 100ms}, capture.GetLogger()};
    vm.Activate();
    py_bind(vm.GetMain(), "search(ms)", SlowSearch);
    py_bind(vm.GetMain(), "slow(ms)", SlowBinding);
    // clang-format off
    vm.RunSource("import time\n"
                 "\n"
                 "def busy(ms):\n"
                 "    end = time.time() + ms / 1000\n"
                 "    while time.time() < end:\n"
                 "        pass\n"
                 "\n"
                 "def search_then(ms, busy_ms):\n"
                 "    found = search(ms)\n"
                 "    busy(busy_ms)\n"
                 "    return found\n"
                 "\n"
                 "def slow_then(ms, busy_ms):\n"
                 "    slow(ms)\n"
                 "    busy(busy_ms)\n",
        "route.py");
    // clang-format on

    const auto call = [&vm](std::string_view function, s32 ms, s32 busyMs)
    {
        vm.Activate();
        py_newint(py_r0(), ms);
        py_newint(py_r1(), busyMs);

        const auto args = std::array{py_r0(), py_r1()};
        return vm.Call(function, args);
    };

    // Here a search may take 500 ms, and the Python after it 100 ms more. So a 250 ms search passes, a 700 ms
    // one doesn't, and neither does a minute of Python after a short one.
    CHECK(py_tobool(call("search_then", 250, 60)));
    CHECK_THROWS_WITH(call("search_then", 700, 0), ContainsSubstring("TimeoutError"));

    const auto start = std::chrono::steady_clock::now();
    CHECK_THROWS_WITH(call("search_then", 10, 60000), ContainsSubstring("TimeoutError"));
    CHECK(std::chrono::steady_clock::now() - start < 2s);

    // Any other binding counts against the call's own timeout.
    CHECK_THROWS_WITH(call("slow_then", 250, 0), ContainsSubstring("TimeoutError"));
}

TEST_CASE("ScriptVm makes time.sleep raise instead of stalling every account", "[ScriptVm]")
{
    auto capture = LogCapture{};
    auto vm = ScriptVm{ScriptTestRuntime::Get(), {}, capture.GetLogger()};
    // clang-format off
    vm.RunSource("import time\n"
                 "from time import sleep\n"
                 "\n"
                 "def nap():\n"
                 "    time.sleep(0.01)\n"
                 "\n"
                 "def nap_imported():\n"
                 "    sleep(0.01)\n"
                 "\n"
                 "def now():\n"
                 "    return time.time()\n",
        "sleepy.py");
    // clang-format on

    CHECK_THROWS_WITH(vm.Call("nap"), ContainsSubstring("return a delay from loop()"));
    CHECK_THROWS_WITH(vm.Call("nap_imported"), ContainsSubstring("return a delay from loop()"));
    CHECK_NOTHROW(vm.Call("now"));
}
