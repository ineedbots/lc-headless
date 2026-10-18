#include "pch.hpp"

#include "Console/ConsoleInput.hpp"

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
