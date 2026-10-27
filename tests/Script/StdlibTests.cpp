#include "pch.hpp"
#include "../Support/Game/FakeGameServer.hpp"
#include "../Support/LogCapture.hpp"
#include "../Support/Script/Rs2b0tSpecs.hpp"
#include "../Support/Script/ScriptCoverage.hpp"
#include "../Support/Script/ScriptTestRuntime.hpp"

#include "Cache/GameCache_s.hpp"
#include "Config/Config_s.hpp"
#include "Game/GameActions.hpp"
#include "Game/GameClient.hpp"
#include "Game/Map/WorldMap.hpp"
#include "Game/State/GameState_s.hpp"
#include "Script/Bindings/ScriptBindings.hpp"
#include "Script/Error/ScriptError.hpp"
#include "Script/ScriptContext.hpp"
#include "Script/ScriptVm.hpp"
#include "Script/Stdlib.hpp"

#include <catch2/catch_test_macros.hpp>

#include <pocketpy.h>

namespace
{
    const auto TEST_FOLDER = std::filesystem::path{RS2004_SOURCE_DIR} / "tests" / "Stdlib";
    const auto SCRIPTS_FOLDER = std::filesystem::path{RS2004_SOURCE_DIR} / "scripts";

    bool CollectTestName(py_Name name, py_Ref value, void* context) noexcept
    {
        const auto text = py_name2sv(name);
        const auto view = std::string_view{text.data, static_cast<std::size_t>(text.size)};
        if (view.starts_with("test_") && py_callable(value))
        {
            static_cast<std::vector<std::string>*>(context)->emplace_back(view);
        }

        return true;
    }

    // A VM with the API bound over an empty, unplaced state, in which a test module runs. Tests are the
    // module's test_* functions, each a function of plain asserts, since pocketpy has no unittest.
    class StdlibFixture
    {
    public:
        explicit StdlibFixture(const std::filesystem::path& scripts = TEST_FOLDER, std::chrono::milliseconds callTimeout = 1000ms)
            : cache{std::make_shared<const GameCache_s>()}
            , map{cache}
            , client{std::make_shared<const Config_s>(), cache, FakeGameServer::MakeAccount(), capture.GetLogger()}
            , actions{client}
            , api{state, map, actions}
            // Trace callbacks add work to long-running Python tests. Deadline-specific VM tests
            // use ScriptVm directly and keep their original watchdog limits.
            , vm{ScriptTestRuntime::Get(),
                 {.scriptsDirectory = scripts, .callTimeout = ScriptCoverage::AdjustTimeout(callTimeout)},
                 capture.GetLogger()}
        {
            ScriptBindings::Bind(vm, api);
            ScriptBindings::SetSettings(vm, "{}");
        }

        ~StdlibFixture()
        {
            ScriptBindings::Unbind(vm);
        }

        StdlibFixture(const StdlibFixture&) = delete;
        StdlibFixture& operator=(const StdlibFixture&) = delete;

        [[nodiscard]] std::vector<std::string> GetTests()
        {
            auto names = std::vector<std::string>{};
            py_applydict(vm.GetMain(), CollectTestName, &names);
            std::ranges::sort(names);
            return names;
        }

        LogCapture capture;
        std::shared_ptr<const GameCache_s> cache;
        GameState_s state;
        WorldMap map;
        GameClient client;
        GameActions actions;
        ScriptContext api;
        ScriptVm vm;
    };
}

TEST_CASE("The standard library is embedded", "[Stdlib]")
{
    CHECK(Stdlib::Find("rs2004/bot.py").has_value());
    CHECK(Stdlib::Find("rs2004\\bot.py").has_value());
    CHECK_FALSE(Stdlib::Find("rs2004/missing.py").has_value());
}

TEST_CASE("The standard library's Python tests pass", "[Stdlib]")
{
    auto files = std::vector<std::filesystem::path>{};
    for (const auto& entry : std::filesystem::directory_iterator{TEST_FOLDER})
    {
        const auto name = entry.path().filename().string();
        if (name.starts_with("test_") && entry.path().extension() == ".py")
        {
            files.push_back(entry.path().filename());
        }
    }

    std::ranges::sort(files);
    REQUIRE_FALSE(files.empty());

    for (const auto& file : files)
    {
        CAPTURE(file.string());

        auto fixture = StdlibFixture{};
        REQUIRE_NOTHROW(fixture.vm.RunFile(file));

        const auto tests = fixture.GetTests();
        CHECK_FALSE(tests.empty());

        for (const auto& test : tests)
        {
            CAPTURE(test);
            CHECK_NOTHROW(fixture.vm.Call(test));
        }
    }
}

// rs2b0t's own tests keep its describe/test/expect; they import the bots from scripts/, as an account's script does.
// Those that read the walker's data are real-cache tests. The quest engine's and the quests' are in quests/. Each
// file is a section, so one runs alone with -c <file name>.
TEST_CASE("rs2b0t's ported Python tests pass", "[Stdlib]")
{
    auto files = Rs2b0tSpecs::GetFiles(Rs2b0tSpecs::GetFolder());
    REQUIRE_FALSE(files.empty());
    const auto quests = Rs2b0tSpecs::GetFiles(Rs2b0tSpecs::GetFolder() / "quests");
    REQUIRE_FALSE(quests.empty());
    files.insert(files.end(), quests.begin(), quests.end());

    for (const auto& file : files)
    {
        DYNAMIC_SECTION(file.filename().string())
        {
            // A file is one run_specs call, so the watchdog bounds the whole file rather than one test.
            auto fixture = StdlibFixture{SCRIPTS_FOLDER, 60s};
            Rs2b0tSpecs::Run(fixture.vm, file);
        }
    }
}

// Why: some of rs2b0t's tests run at a size pocketpy takes minutes over, such as 10,000 puzzle boxes, so the suite
// runs a sample of each and this hidden case the whole: Rs2004HeadlessTests "[Slow]".
TEST_CASE("rs2b0t's ported Python tests pass at full size", "[.][Slow]")
{
    const auto files = Rs2b0tSpecs::GetFiles(Rs2b0tSpecs::GetFolder() / "slow");
    REQUIRE_FALSE(files.empty());

    for (const auto& file : files)
    {
        CAPTURE(file.filename().string());

        auto fixture = StdlibFixture{SCRIPTS_FOLDER, 1h};
        Rs2b0tSpecs::Run(fixture.vm, file);
    }
}
