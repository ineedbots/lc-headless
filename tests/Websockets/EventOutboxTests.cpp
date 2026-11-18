#include "pch.hpp"

#include "Websockets/Events/EventOutbox.hpp"
#include "Websockets/Events/EventLimits.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("Event outboxes reject excess bytes without changing queued frames", "[Events]")
{
    auto outbox = EventOutbox{};
    const auto full = std::make_shared<const std::string>(EventLimits::MAX_OUTBOX_BYTES, 'x');
    REQUIRE(outbox.TryPush(full));
    CHECK_FALSE(outbox.TryPush(std::make_shared<const std::string>("extra")));
    CHECK(outbox.Size() == 1);
    CHECK(outbox.Bytes() == EventLimits::MAX_OUTBOX_BYTES);
    CHECK(outbox.Front() == full);

    outbox.Pop();
    outbox.Pop();
    CHECK(outbox.Size() == 0);
    CHECK(outbox.Bytes() == 0);
    CHECK_FALSE(outbox.Front());
    CHECK(outbox.TryPush(std::make_shared<const std::string>("next")));
}

TEST_CASE("Event outboxes bound item counts and preserve in-flight frame ownership", "[Events]")
{
    auto outbox = EventOutbox{};

    for (std::size_t i = 0; i < EventLimits::MAX_OUTBOX_ITEMS; ++i)
    {
        REQUIRE(outbox.TryPush(std::make_shared<const std::string>(std::to_string(i))));
    }

    const auto bytes = outbox.Bytes();
    CHECK_FALSE(outbox.TryPush(std::make_shared<const std::string>("excess")));
    CHECK(outbox.Bytes() == bytes);

    const auto inFlight = outbox.Front();
    outbox.Pop();
    CHECK(*outbox.Front() == "1");
    CHECK(outbox.TryPush(std::make_shared<const std::string>("replacement")));
    outbox = EventOutbox{};
    CHECK(*inFlight == "0");
    CHECK(outbox.Bytes() == 0);
}
