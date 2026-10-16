#include "pch.hpp"
#include "../Support/TempFolder.hpp"

#include "Utils/FileUtils.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("FileUtils::ReadText reads a whole file as it is", "[FileUtils]")
{
    const auto folder = TempFolder{"rs2004-file-utils-tests"};
    folder.WriteFile("text.txt", "line one\r\nline two\n\0end"s);

    CHECK(FileUtils::ReadText(folder.GetPath() / "text.txt") == "line one\r\nline two\n\0end"s);
    CHECK_FALSE(FileUtils::ReadText(folder.GetPath() / "missing.txt"));
    CHECK_FALSE(FileUtils::ReadText(folder.GetPath()));
}

TEST_CASE("FileUtils::ReplaceFile replaces a file and leaves no temporary behind", "[FileUtils]")
{
    const auto folder = TempFolder{"rs2004-file-utils-tests"};
    folder.WriteFile("account.jsonc", "old");
    const auto path = folder.GetPath() / "account.jsonc";

    FileUtils::ReplaceFile(path, "new text");

    CHECK(FileUtils::ReadText(path) == "new text");
    CHECK_FALSE(std::filesystem::exists(folder.GetPath() / "account.jsonc.tmp"));
}

TEST_CASE("FileUtils::ReplaceFile throws when it can't write", "[FileUtils]")
{
    const auto folder = TempFolder{"rs2004-file-utils-tests"};

    CHECK_THROWS_AS(FileUtils::ReplaceFile(folder.GetPath() / "missing" / "account.jsonc", "text"), std::runtime_error);
}

TEST_CASE("FileUtils::IsInsideFolder", "[FileUtils]")
{
    CHECK(FileUtils::IsInsideFolder("main.py"));
    CHECK(FileUtils::IsInsideFolder("lib/helpers.py"));
    CHECK(FileUtils::IsInsideFolder("lib/./helpers.py"));
    CHECK_FALSE(FileUtils::IsInsideFolder(""));
    CHECK_FALSE(FileUtils::IsInsideFolder("../main.py"));
    CHECK_FALSE(FileUtils::IsInsideFolder("lib/../../main.py"));
    CHECK_FALSE(FileUtils::IsInsideFolder("/etc/passwd"));
#ifdef _WIN32
    CHECK_FALSE(FileUtils::IsInsideFolder("C:/scripts/main.py"));
    CHECK_FALSE(FileUtils::IsInsideFolder("C:main.py"));
#endif
}
