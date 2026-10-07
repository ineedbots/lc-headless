#include "pch.hpp"

#include "Io/Isaac.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    constexpr auto INT32_MIN_VALUE = std::numeric_limits<s32>::min();
    constexpr auto INT32_MAX_VALUE = std::numeric_limits<s32>::max();

    std::map<int, s32> GetOutputs(std::span<const s32> seed, std::span<const int> outputNumbers)
    {
        auto isaac = Isaac{seed};
        const auto last = std::ranges::max(outputNumbers);
        auto outputs = std::map<int, s32>{};
        for (auto number = 1; number <= last; ++number)
        {
            const auto value = isaac.NextInt();
            if (std::ranges::find(outputNumbers, number) != outputNumbers.end())
            {
                outputs.emplace(number, value);
            }
        }

        return outputs;
    }

    std::vector<s32> Draw(Isaac& isaac, std::size_t count)
    {
        auto values = std::vector<s32>{};
        values.reserve(count);
        for (std::size_t i = 0; i < count; ++i)
        {
            values.push_back(isaac.NextInt());
        }

        return values;
    }
}

TEST_CASE("Isaac matches the TS anchor values", "[Isaac]")
{
    const auto counting = std::array<s32, 4>{1, 2, 3, 4};
    CHECK(GetOutputs(counting, std::array{1, 2, 3}) == std::map<int, s32>{{1, -621246914}, {2, 1957022519}, {3, -1345000077}});
    CHECK(GetOutputs(counting, std::array{256, 257}) == std::map<int, s32>{{256, 681500538}, {257, 1010642953}});
    CHECK(GetOutputs(counting, std::array{512, 1024}) == std::map<int, s32>{{512, -962902924}, {1024, 392795429}});

    const auto zeros = std::array<s32, 4>{};
    CHECK(GetOutputs(zeros, std::array{1, 256, 257}) == std::map<int, s32>{{1, 405143795}, {256, -412232903}, {257, 2053665039}});

    const auto extremes = std::array<s32, 4>{INT32_MIN_VALUE, -1, INT32_MAX_VALUE, 0x12345678};
    CHECK(GetOutputs(extremes, std::array{1, 257}) == std::map<int, s32>{{1, -528844012}, {257, -343157757}});
}

TEST_CASE("Isaac with an empty seed matches an all-zero seed", "[Isaac]")
{
    auto empty = Isaac{std::span<const s32>{}};
    auto zeros = Isaac{std::array<s32, 4>{}};

    CHECK(Draw(empty, 1024) == Draw(zeros, 1024));
}

TEST_CASE("Isaac instances share no state", "[Isaac]")
{
    const auto firstSeed = std::array<s32, 4>{1, 2, 3, 4};
    const auto secondSeed = std::array<s32, 4>{5, 6, 7, 8};
    constexpr auto COUNT = std::size_t{600};

    SECTION("the same seed gives the same stream")
    {
        auto first = Isaac{firstSeed};
        auto second = Isaac{firstSeed};
        CHECK(Draw(first, COUNT) == Draw(second, COUNT));
    }

    SECTION("interleaved draws match each instance's solo stream")
    {
        auto soloFirst = Isaac{firstSeed};
        auto soloSecond = Isaac{secondSeed};
        const auto expectedFirst = Draw(soloFirst, COUNT);
        const auto expectedSecond = Draw(soloSecond, COUNT);

        auto first = Isaac{firstSeed};
        auto second = Isaac{secondSeed};
        auto interleavedFirst = std::vector<s32>{};
        auto interleavedSecond = std::vector<s32>{};
        for (std::size_t i = 0; i < COUNT; ++i)
        {
            interleavedFirst.push_back(first.NextInt());
            interleavedSecond.push_back(second.NextInt());
        }

        CHECK(interleavedFirst == expectedFirst);
        CHECK(interleavedSecond == expectedSecond);
    }
}
