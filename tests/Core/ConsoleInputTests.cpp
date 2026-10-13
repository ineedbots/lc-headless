#include "pch.hpp"

#include "Core/ConsoleInput.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    using Clock = ConsoleInput::Clock;
}

TEST_CASE("ConsoleInput hands each line over once, in order", "[ConsoleInput]")
{
    auto input = ConsoleInput{};
    CHECK(input.TakeLines().empty());

    input.Push("help");
    input.Push("@bot1 status");
    CHECK(input.TakeLines() == std::vector<std::string>{"help", "@bot1 status"});
    CHECK(input.TakeLines().empty());
}

TEST_CASE("ConsoleInput wakes a wait when a line arrives", "[ConsoleInput]")
{
    auto input = ConsoleInput{};
    auto start = Clock::now();
    input.WaitUntil(start + 20ms);
    CHECK(Clock::now() - start >= 20ms);

    auto typist = std::thread{[&input]
    {
        std::this_thread::sleep_for(20ms);
        input.Push("quit");
    }};

    start = Clock::now();
    input.WaitUntil(start + 10s);
    CHECK(Clock::now() - start < 5s);
    typist.join();
    CHECK(input.TakeLines() == std::vector<std::string>{"quit"});

    // A line not yet taken ends a wait at once.
    input.Push("status");
    start = Clock::now();
    input.WaitUntil(start + 10s);
    CHECK(Clock::now() - start < 5s);
}
