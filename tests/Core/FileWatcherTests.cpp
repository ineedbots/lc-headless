#include "pch.hpp"
#include "../TempFolder.hpp"

#include "Core/FileWatcher.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    // Moves a file's modification time on, as a save would, without depending on the clock's resolution.
    void Touch(const std::filesystem::path& path, std::chrono::seconds offset)
    {
        std::filesystem::last_write_time(path, std::filesystem::last_write_time(path) + offset);
    }
}

TEST_CASE("FileWatcher reports a change once it has held still for a check", "[FileWatcher]")
{
    const auto folder = TempFolder{"rs2004-watcher-tests"};
    folder.WriteFile("main.py", "a");
    folder.WriteFile("helper.py", "b");
    const auto main = folder.GetPath() / "main.py";
    const auto helper = folder.GetPath() / "helper.py";
    auto watcher = FileWatcher{{main, helper}};

    CHECK(watcher.GetFiles() == std::vector{main, helper});
    CHECK_FALSE(watcher.Check());

    SECTION("a saved file counts on the check after the one that saw it")
    {
        Touch(helper, 1s);
        CHECK_FALSE(watcher.Check());
        CHECK(watcher.Check());
        CHECK_FALSE(watcher.Check());
    }

    SECTION("a file still being written waits until it stops")
    {
        Touch(main, 1s);
        CHECK_FALSE(watcher.Check());
        Touch(main, 1s);
        CHECK_FALSE(watcher.Check());
        CHECK(watcher.Check());
    }

    SECTION("a file put back before the change settles isn't a change")
    {
        Touch(main, 1s);
        CHECK_FALSE(watcher.Check());
        Touch(main, -1s);
        CHECK_FALSE(watcher.Check());
        CHECK_FALSE(watcher.Check());
    }

    SECTION("deleting a file and creating it again are changes")
    {
        std::filesystem::remove(helper);
        CHECK_FALSE(watcher.Check());
        CHECK(watcher.Check());

        folder.WriteFile("helper.py", "c");
        CHECK_FALSE(watcher.Check());
        CHECK(watcher.Check());
    }
}

TEST_CASE("FileWatcher watches a file that doesn't exist yet", "[FileWatcher]")
{
    const auto folder = TempFolder{"rs2004-watcher-tests"};
    auto watcher = FileWatcher{{folder.GetPath() / "main.py"}};
    CHECK_FALSE(watcher.Check());

    folder.WriteFile("main.py", "a");
    CHECK_FALSE(watcher.Check());
    CHECK(watcher.Check());
}
