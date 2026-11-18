#include "pch.hpp"

#include "Accounts/Reporting/ReportWriteCompletion.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    struct PendingWrite_s
    {
        int value;
        std::future<void> completion;
    };
}

TEST_CASE("Reporting completion waits for a commit and consumes it exactly once", "[Reporting]")
{
    auto promise = std::promise<void>{};
    auto pending = std::optional{PendingWrite_s{7, promise.get_future()}};
    auto committed = 0;
    auto failed = 0;
    const auto poll = [&]
    {
        ReportWriteCompletion::Poll(pending, [&](const auto& write)
        {
            CHECK_FALSE(pending);
            committed += write.value;
        }, [&](const auto&, const std::exception&)
        {
            ++failed;
        });
    };
    poll();
    CHECK(pending.has_value());
    CHECK(committed == 0);

    promise.set_value();
    poll();
    poll();
    CHECK(committed == 7);
    CHECK(failed == 0);
}

TEST_CASE("Reporting completion distinguishes write failure from committed callback failure", "[Reporting]")
{
    auto promise = std::promise<void>{};
    auto pending = std::optional{PendingWrite_s{7, promise.get_future()}};
    auto failed = 0;
    const auto onFailure = [&](const auto& write, const std::exception& error)
    {
        CHECK(write.value == 7);
        CHECK(std::string_view{error.what()} == "write failed");
        ++failed;
    };

    SECTION("database failure")
    {
        promise.set_exception(std::make_exception_ptr(std::runtime_error{"write failed"}));
        ReportWriteCompletion::Poll(pending, [](const auto&)
        {
            FAIL("A failed write must not be treated as committed");
        }, onFailure);
        CHECK(failed == 1);
    }

    SECTION("committed callback failure")
    {
        promise.set_value();
        CHECK_THROWS_AS(ReportWriteCompletion::Poll(pending, [](const auto&)
        {
            throw std::runtime_error{"callback failed"};
        }, onFailure),
                        std::runtime_error);
        CHECK(failed == 0);
    }

    CHECK_FALSE(pending);
}
