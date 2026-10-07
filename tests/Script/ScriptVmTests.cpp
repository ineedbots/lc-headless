#include "pch.hpp"
#include "../LogCapture.hpp"
#include "../TempFolder.hpp"
#include "ScriptTestRuntime.hpp"

#include "Core/Logger.hpp"
#include "Script/ScriptError.hpp"
#include "Script/ScriptVm.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>
#include <pocketpy.h>

using Catch::Matchers::ContainsSubstring;

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
        vm.RunSource("log('hello', 42, None)\n"
                     "debug('detail')\n"
                     "print('a', 'b')\n"
                     "print('first\\nsecond')\n"
                     "print('partial', end='')\n",
            "output.py");

        CHECK(GetLines(capture) == std::vector<LogLine>{
            {LogLevel_e::Info, "hello 42 None"},
            {LogLevel_e::Verbose, "detail"},
            {LogLevel_e::Info, "a b"},
            {LogLevel_e::Info, "first"},
            {LogLevel_e::Info, "second"},
        });
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
    folder.WriteFile("main.py",
        "import helper\n"
        "import shared\n"
        "import tools.walking\n"
        "\n"
        "def sources():\n"
        "    return helper.SOURCE + ',' + shared.greet('bot') + ',' + tools.walking.NAME\n");

    auto vm = ScriptVm{ScriptTestRuntime::Get(), ScriptVmOptions_s{.scriptsDirectory = folder.GetPath()}, capture.GetLogger()};
    vm.RunFile("main.py");

    CHECK(ToString(vm.Call("sources")) == "scripts,lib,walking");
    REQUIRE_FALSE(capture.GetEntries().empty());
    CHECK(capture.GetEntries().back().message == "hello from lib bot");

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

TEST_CASE("ScriptVm makes time.sleep raise instead of stalling every account", "[ScriptVm]")
{
    auto capture = LogCapture{};
    auto vm = ScriptVm{ScriptTestRuntime::Get(), {}, capture.GetLogger()};
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

    CHECK_THROWS_WITH(vm.Call("nap"), ContainsSubstring("return a delay from loop()"));
    CHECK_THROWS_WITH(vm.Call("nap_imported"), ContainsSubstring("return a delay from loop()"));
    CHECK_NOTHROW(vm.Call("now"));
}
