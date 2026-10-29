#include "pch.hpp"
#include "../Support/TempFile.hpp"

#include "Console/ConsoleInput.hpp"
#include "Console/ConsoleLogScope.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("ConsoleInput hands each line over once, in order", "[ConsoleInput]")
{
    auto input = ConsoleInput{};
    CHECK(input.TakeLines().empty());

    input.Push("help");
    input.Push("@bot1 status");
    CHECK(input.TakeLines() == std::vector<std::string>{"help", "@bot1 status"});
    CHECK(input.TakeLines().empty());
}

TEST_CASE("ConsoleInput calls its arrival callback for each line", "[ConsoleInput]")
{
    auto input = ConsoleInput{};
    auto arrivals = 0;
    input.SetOnArrived([&arrivals]
    {
        ++arrivals;
    });

    input.Push("help");
    input.Push("status");
    CHECK(arrivals == 2);

    input.SetOnArrived({});
    input.Push("quit");
    CHECK(arrivals == 2);
    CHECK(input.TakeLines() == std::vector<std::string>{"help", "status", "quit"});
}

TEST_CASE("ConsoleInput callbacks can drain queued lines and replace themselves", "[ConsoleInput][ConsoleCoverage]")
{
    auto input = ConsoleInput{};
    auto received = std::vector<std::string>{};
    auto second = 0;
    input.SetOnArrived([&]
    {
        received = input.TakeLines();
        input.SetOnArrived([&] { ++second; });
    });
    input.Push("first");
    CHECK(received == std::vector<std::string>{"first"});
    CHECK(input.TakeLines().empty());
    input.Push("second");
    CHECK(second == 1);
    CHECK(input.TakeLines() == std::vector<std::string>{"second"});
}

TEST_CASE("ConsoleInput prints a complete line to a supplied stream", "[ConsoleInput][ConsoleCoverage]")
{
    auto input = ConsoleInput{};
    CHECK_FALSE(input.IsInteractive());
    const auto file = MakeTempFile();
    REQUIRE(file != nullptr);
    input.Print(file.get(), "hello");
    input.Print(file.get(), "");
    std::rewind(file.get());
    auto bytes = std::array<char, 32>{};
    const auto read = std::fread(bytes.data(), 1, bytes.size(), file.get());
    CHECK(std::string(bytes.data(), read) == "hello\n\n");
    input.Close();
    input.Close();
    CHECK_FALSE(input.IsInteractive());
}

TEST_CASE("ConsoleLogScope installs and removes its console while preserving queued input", "[ConsoleInput][ConsoleCoverage]")
{
    const auto input = std::make_shared<ConsoleInput>();
    input->Push("status");
    auto installed = std::vector<std::shared_ptr<ConsoleInput>>{};
    {
        auto scope = ConsoleLogScope{[&](std::shared_ptr<ConsoleInput> console)
        {
            installed.push_back(std::move(console));
        }, input};
        REQUIRE(installed.size() == 1);
        CHECK(installed.front() == input);
    }
    REQUIRE(installed.size() == 2);
    CHECK(installed.back() == nullptr);
    CHECK(input->TakeLines() == std::vector<std::string>{"status"});
}

TEST_CASE("ConsoleLogScope restores logging when no console was supplied", "[ConsoleInput][ConsoleCoverage]")
{
    auto calls = 0;
    {
        auto scope = ConsoleLogScope{[&](std::shared_ptr<ConsoleInput> console)
        {
            CHECK(console == nullptr);
            ++calls;
        }, nullptr};
        CHECK(calls == 1);
    }
    CHECK(calls == 2);
}
