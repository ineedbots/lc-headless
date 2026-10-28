#include "pch.hpp"
#include "../Support/TempFolder.hpp"

#include "Utils/FileUtils.hpp"

#include <catch2/catch_test_macros.hpp>

#ifdef __linux__
TEST_CASE("FileUtils handles a file that opens but fails during reading", "[FileUtils][HostResilienceCoverage]")
{
    // procfs exposes this as a regular file; reading offset zero produces EIO rather than EOF.
    REQUIRE(std::filesystem::is_regular_file("/proc/self/mem"));
    CHECK_FALSE(FileUtils::ReadText("/proc/self/mem").has_value());
    CHECK_FALSE(FileUtils::ReadBytes("/proc/self/mem").has_value());
    const auto folder = TempFolder{"rs2004-read-after-error"};
    folder.WriteFile("healthy.txt", "healthy");
    CHECK(FileUtils::ReadText(folder.GetPath() / "healthy.txt") == "healthy");
}
#endif

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

TEST_CASE("FileUtils::ReadBytes preserves every byte and distinguishes empty from missing", "[FileUtils][FileUtilsCoverage]")
{
    const auto folder = TempFolder{"rs2004-file-utils-tests"};
    auto content = std::string{};
    auto expected = std::vector<u8>{};
    for (auto value = 0; value < 256; ++value)
    {
        content.push_back(static_cast<char>(value));
        expected.push_back(static_cast<u8>(value));
    }
    folder.WriteFile("binary.dat", content);
    folder.WriteFile("empty.dat", "");

    CHECK(FileUtils::ReadBytes(folder.GetPath() / "binary.dat") == expected);
    CHECK(FileUtils::ReadBytes(folder.GetPath() / "empty.dat") == std::vector<u8>{});
    CHECK_FALSE(FileUtils::ReadBytes(folder.GetPath() / "missing.dat"));
    CHECK_FALSE(FileUtils::ReadBytes(folder.GetPath()));
}

TEST_CASE("FileUtils::ReplaceFile cleans up when the destination is a directory", "[FileUtils][FileUtilsCoverage]")
{
    const auto folder = TempFolder{"rs2004-file-utils-tests"};
    const auto destination = folder.GetPath() / "destination";
    std::filesystem::create_directory(destination);
    folder.WriteFile("destination/keep.txt", "keep me");

    CHECK_THROWS_AS(FileUtils::ReplaceFile(destination, "replacement"), std::runtime_error);
    CHECK(std::filesystem::is_directory(destination));
    CHECK(FileUtils::ReadText(destination / "keep.txt") == "keep me");
    CHECK_FALSE(std::filesystem::exists(folder.GetPath() / "destination.tmp"));
}

TEST_CASE("FileUtils::ReplaceFile creates new files and truncates stale temporary content", "[FileUtils][FileUtilsCoverage]")
{
    const auto folder = TempFolder{"rs2004-file-utils-tests"};
    const auto path = folder.GetPath() / "new.dat";
    folder.WriteFile("new.dat.tmp", "stale temporary content");

    FileUtils::ReplaceFile(path, "\0\xff\n"sv);

    CHECK(FileUtils::ReadBytes(path) == std::vector<u8>{0, 255, 10});
    CHECK_FALSE(std::filesystem::exists(folder.GetPath() / "new.dat.tmp"));
    FileUtils::ReplaceFile(path, "");
    CHECK(FileUtils::ReadBytes(path) == std::vector<u8>{});
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
