#include "pch.hpp"
#include "Application/InterruptSignal.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("InterruptSignal counts successive interrupts across handler installation", "[Application][InterruptCoverage]")
{
    const auto previous = std::signal(SIGINT, SIG_IGN);
    struct RestoreSignal
    {
        decltype(previous) handler;
        ~RestoreSignal() { std::signal(SIGINT, handler); }
    } restore{previous};
    const auto before = InterruptSignal::GetCount();
    InterruptSignal::Install();
    CHECK(std::raise(SIGINT) == 0);
    CHECK(InterruptSignal::GetCount() == before + 1);
    // Windows resets the C signal handler after delivery; reinstall before the second signal.
    InterruptSignal::Install();
    CHECK(std::raise(SIGINT) == 0);
    CHECK(InterruptSignal::GetCount() == before + 2);
}
