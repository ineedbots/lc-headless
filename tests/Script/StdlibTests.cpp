#include "pch.hpp"
#include "../Game/FakeGameServer.hpp"
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
#include "Script/ScriptError.hpp"
#include "Script/ScriptVm.hpp"
#include "Script/Stdlib.hpp"

#include <catch2/catch_test_macros.hpp>

#include <pocketpy.h>

namespace
{
    const auto TEST_FOLDER = std::filesystem::path{RS2004_SOURCE_DIR} / "tests" / "Stdlib";

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
        StdlibFixture()
            : cache{std::make_shared<const GameCache_s>()}
            , map{cache}
            , client{std::make_shared<const Config_s>(), cache, FakeGameServer::MakeAccount(), capture.GetLogger()}
            , actions{client}
            , api{state, map, actions}
            , vm{ScriptTestRuntime::Get(), {.scriptsDirectory = TEST_FOLDER}, capture.GetLogger()}
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
        ScriptApi api;
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
