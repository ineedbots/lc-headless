#include "pch.hpp"

#include "Cache/TextPool.hpp"
#include "Cache/Error/CacheError.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

TEST_CASE("TextPool rejects option id overflow while keeping existing options usable", "[TextPool][CompletionCoverage]")
{
    auto pool = TextPool{};
    for (auto id = u32{1}; id <= std::numeric_limits<u16>::max(); ++id)
    {
        REQUIRE(pool.InternOption(std::format("option {}", id)) == id);
    }
    CHECK(pool.GetOptionCount() == 65536);
    CHECK_THROWS_AS(pool.InternOption("overflow"), CacheError);
    CHECK_THROWS_WITH(pool.InternOption("overflow"), "the types have more than 65535 distinct options");
    CHECK(pool.GetOptionCount() == 65536);
    CHECK(pool.InternOption("option 65535") == 65535);
    CHECK(pool.GetOption(1) == "option 1");
    CHECK(pool.GetOption(65535) == "option 65535");
    CHECK(pool.InternOption("") == TextPool::NO_OPTION);
    pool.FinishInterning();
    CHECK(pool.GetOption(65535) == "option 65535");
}

TEST_CASE("TextPool stores each distinct string once", "[TextPool]")
{
    auto pool = TextPool{};
    const auto attack = pool.Intern(std::string{"Attack"});
    const auto again = pool.Intern(std::string{"Attack"});
    CHECK(attack == "Attack");
    CHECK(attack.data() == again.data());
    CHECK(pool.Intern("Talk-to").data() != attack.data());
    CHECK(pool.Intern("").empty());
}

TEST_CASE("TextPool numbers options from 1 in the order first seen", "[TextPool]")
{
    auto pool = TextPool{};
    CHECK(pool.GetOptionCount() == 1);
    CHECK(pool.InternOption("") == TextPool::NO_OPTION);
    CHECK(pool.InternOption("Chop down") == 1);
    CHECK(pool.InternOption("Open") == 2);
    CHECK(pool.InternOption("Chop down") == 1);
    CHECK(pool.GetOptionCount() == 3);
    CHECK(pool.GetOption(TextPool::NO_OPTION).empty());
    CHECK(pool.GetOption(2) == "Open");
    CHECK(pool.Intern("Open").data() == pool.GetOption(2).data());
}

TEST_CASE("TextPool's views outlive a move and FinishInterning", "[TextPool]")
{
    auto pool = TextPool{};
    const auto name = pool.Intern("Chicken");
    const auto option = pool.InternOption("Attack");
    pool.FinishInterning();

    const auto moved = std::move(pool);
    CHECK(name == "Chicken");
    CHECK(moved.GetOption(option) == "Attack");
}

TEST_CASE("TextPool gives text longer than a chunk a chunk of its own", "[TextPool]")
{
    auto pool = TextPool{};
    const auto before = pool.Intern("before");
    const auto longText = std::string(TextPool::CHUNK_SIZE + 10, 'x');
    const auto interned = pool.Intern(longText);
    const auto after = pool.Intern("after");
    CHECK(interned == longText);
    CHECK(before == "before");
    CHECK(after == "after");
    CHECK(pool.Intern(longText).data() == interned.data());
}
