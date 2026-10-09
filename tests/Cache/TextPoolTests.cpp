#include "pch.hpp"

#include "Cache/TextPool.hpp"

#include <catch2/catch_test_macros.hpp>

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
