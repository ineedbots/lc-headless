#include "pch.hpp"

#include "Io/ReceiveBuffer.hpp"

#include <catch2/catch_test_macros.hpp>

TEST_CASE("ReceiveBuffer reads, peeks and throws on short reads", "[ReceiveBuffer]")
{
    auto buffer = ReceiveBuffer{};

    SECTION("starts empty")
    {
        CHECK(buffer.Available() == 0);
    }

    SECTION("appended bytes are available")
    {
        buffer.Append(std::array<u8, 3>{1, 2, 3});
        CHECK(buffer.Available() == 3);
    }

    SECTION("reads continue across appends")
    {
        buffer.Append(std::array<u8, 2>{1, 2});
        buffer.Append(std::array<u8, 1>{3});
        buffer.Append(std::span<const u8>{});

        auto destination = std::array<u8, 3>{};
        buffer.Read(destination);
        CHECK(destination == std::array<u8, 3>{1, 2, 3});
        CHECK(buffer.Available() == 0);
    }

    SECTION("read returns the span it was given")
    {
        buffer.Append(std::array<u8, 3>{1, 2, 3});

        auto destination = std::array<u8, 3>{};
        const auto partial = buffer.Read(std::span{destination}.first(2));
        CHECK(partial.data() == destination.data());
        CHECK(partial.size() == 2);

        const auto rest = buffer.Read(std::span{destination}.subspan(2));
        CHECK(rest.data() == destination.data() + 2);
        CHECK(rest.size() == 1);
    }

    SECTION("peek doesn't consume")
    {
        buffer.Append(std::array<u8, 3>{1, 2, 3});

        auto destination = std::array<u8, 2>{};
        buffer.Peek(destination);
        CHECK(destination == std::array<u8, 2>{1, 2});
        CHECK(buffer.Available() == 3);
    }

    SECTION("peek then read give the same bytes")
    {
        buffer.Append(std::array<u8, 3>{1, 2, 3});

        auto peeked = std::array<u8, 2>{};
        auto read = std::array<u8, 2>{};
        buffer.Peek(peeked);
        buffer.Read(read);
        CHECK(peeked == std::array<u8, 2>{1, 2});
        CHECK(read == std::array<u8, 2>{1, 2});
        CHECK(buffer.Available() == 1);
    }

    SECTION("consecutive reads")
    {
        buffer.Append(std::array<u8, 3>{1, 2, 3});

        auto first = std::array<u8, 2>{};
        auto second = std::array<u8, 1>{};
        buffer.Read(first);
        buffer.Read(second);
        CHECK(first == std::array<u8, 2>{1, 2});
        CHECK(second == std::array<u8, 1>{3});
        CHECK(buffer.Available() == 0);
    }

    SECTION("a short read throws and consumes nothing")
    {
        buffer.Append(std::array<u8, 3>{1, 2, 3});

        auto destination = std::array<u8, 4>{9, 9, 9, 9};
        CHECK_THROWS_AS(buffer.Read(destination), std::out_of_range);
        CHECK(destination == std::array<u8, 4>{9, 9, 9, 9});
        CHECK(buffer.Available() == 3);
    }

    SECTION("a short peek throws")
    {
        buffer.Append(std::array<u8, 3>{1, 2, 3});

        auto destination = std::array<u8, 4>{9, 9, 9, 9};
        CHECK_THROWS_AS(buffer.Peek(destination), std::out_of_range);
        CHECK(destination == std::array<u8, 4>{9, 9, 9, 9});
    }

    SECTION("empty reads and peeks are no-ops")
    {
        CHECK_NOTHROW(buffer.Read(std::span<u8>{}));
        CHECK_NOTHROW(buffer.Peek(std::span<u8>{}));
    }
}

TEST_CASE("ReceiveBuffer compacts without losing bytes", "[ReceiveBuffer]")
{
    constexpr auto TOTAL = std::size_t{20'000};
    constexpr auto CHUNK = std::size_t{1000};
    constexpr auto READ_SIZE = std::size_t{7};
    constexpr auto READS_PER_CHUNK = 120;

    auto buffer = ReceiveBuffer{};
    auto nextWritten = std::size_t{0};
    auto nextRead = std::size_t{0};
    auto mismatches = 0;
    const auto readPiece = [&](std::size_t size)
    {
        auto piece = std::vector<u8>(size);
        buffer.Read(piece);

        for (const auto byte : piece)
        {
            if (byte != static_cast<u8>(nextRead & 0xFF))
            {
                ++mismatches;
            }

            ++nextRead;
        }
    };

    while (nextWritten < TOTAL)
    {
        auto chunk = std::vector<u8>(CHUNK);
        for (auto& byte : chunk)
        {
            byte = static_cast<u8>(nextWritten++ & 0xFF);
        }

        buffer.Append(chunk);
        for (auto read = 0; read < READS_PER_CHUNK && buffer.Available() >= READ_SIZE; ++read)
        {
            readPiece(READ_SIZE);
        }
    }

    readPiece(buffer.Available());
    CHECK(nextRead == TOTAL);
    CHECK(mismatches == 0);
    CHECK(buffer.Available() == 0);
}
