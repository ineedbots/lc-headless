#include "pch.hpp"

#include "Game/Net/LoginQueue.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    using Clock = LoginQueue::Clock;
}

TEST_CASE("LoginQueue gives the first turn when it's asked for", "[LoginQueue]")
{
    auto queue = LoginQueue{2s};
    const auto now = Clock::now();
    CHECK(queue.Reserve(now) == now);
}

TEST_CASE("LoginQueue spaces turns asked for at once an interval apart, in order", "[LoginQueue]")
{
    auto queue = LoginQueue{2s};
    const auto now = Clock::now();
    CHECK(queue.Reserve(now) == now);
    CHECK(queue.Reserve(now) == now + 2s);
    CHECK(queue.Reserve(now + 1s) == now + 4s);
}

TEST_CASE("LoginQueue gives a turn asked for after the interval when it's asked for", "[LoginQueue]")
{
    auto queue = LoginQueue{2s};
    const auto now = Clock::now();
    static_cast<void>(queue.Reserve(now));
    CHECK(queue.Reserve(now + 5s) == now + 5s);
    CHECK(queue.Reserve(now + 6s) == now + 7s);
}

TEST_CASE("LoginQueue with no interval gives every turn when it's asked for", "[LoginQueue]")
{
    auto queue = LoginQueue{0s};
    const auto now = Clock::now();
    CHECK(queue.Reserve(now) == now);
    CHECK(queue.Reserve(now) == now);
}
