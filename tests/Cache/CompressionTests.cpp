#include "pch.hpp"
#include "CacheWriter.hpp"

#include "Cache/CacheError.hpp"
#include "Cache/CacheStore.hpp"
#include "Cache/Compression.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    constexpr auto MAP_VERSION_SIZE = std::size_t{2};

    // Text-like bytes, so the data compresses but not to nothing.
    std::vector<u8> MakeData(std::size_t size)
    {
        auto data = std::vector<u8>(size);
        auto state = u32{12345};
        for (auto& byte : data)
        {
            state = state * 1103515245 + 12345;
            byte = static_cast<u8>('a' + (state >> 16) % 16);
        }

        return data;
    }

    std::vector<u8> GzipWithoutVersion(std::span<const u8> data)
    {
        auto packed = CacheWriter::Gzip(data);
        packed.resize(packed.size() - MAP_VERSION_SIZE);
        return packed;
    }
}

TEST_CASE("Compression unpacks headerless bzip2", "[Compression]")
{
    SECTION("small data")
    {
        const auto data = MakeData(100);
        CHECK(Compression::Bunzip2(CacheWriter::Bzip2Headerless(data), data.size()) == data);
    }

    SECTION("300 KB, which spans several blocks")
    {
        const auto data = MakeData(300 * 1024);
        CHECK(Compression::Bunzip2(CacheWriter::Bzip2Headerless(data), data.size()) == data);
    }

    SECTION("nothing")
    {
        CHECK(Compression::Bunzip2(CacheWriter::Bzip2Headerless({}), 0).empty());
    }
}

TEST_CASE("Compression rejects bzip2 data that doesn't unpack to its size", "[Compression]")
{
    const auto data = MakeData(1000);
    const auto packed = CacheWriter::Bzip2Headerless(data);

    CHECK_THROWS_AS(Compression::Bunzip2(packed, data.size() - 1), CacheError);
    CHECK_THROWS_WITH(Compression::Bunzip2(packed, data.size() - 1), ContainsSubstring("unpacks to 1000 bytes, not 999"));
    CHECK_THROWS_WITH(Compression::Bunzip2(packed, data.size() - 10), ContainsSubstring("unpacks to more than 990 bytes"));
    CHECK_THROWS_WITH(Compression::Bunzip2(packed, data.size() + 1), ContainsSubstring("unpacks to 1000 bytes, not 1001"));

    const auto truncated = std::span{packed}.first(packed.size() / 2);
    CHECK_THROWS_AS(Compression::Bunzip2(truncated, data.size()), CacheError);

    const auto garbage = MakeData(200);
    CHECK_THROWS_WITH(Compression::Bunzip2(garbage, data.size()), ContainsSubstring("bzip2 data is damaged"));
}

TEST_CASE("Compression unpacks gzip", "[Compression]")
{
    const auto data = MakeData(50'000);
    CHECK(Compression::Gunzip(GzipWithoutVersion(data)) == data);
    CHECK(Compression::Gunzip(GzipWithoutVersion({})).empty());
}

TEST_CASE("Compression rejects damaged gzip and output over the limit", "[Compression]")
{
    const auto packed = GzipWithoutVersion(MakeData(10'000));
    CHECK_THROWS_WITH(Compression::Gunzip(std::span{packed}.first(packed.size() / 2)), ContainsSubstring("gzip data ends early"));

    auto damaged = packed;
    damaged[0] ^= 0xFF;
    CHECK_THROWS_WITH(Compression::Gunzip(damaged), ContainsSubstring("gzip data is damaged"));

    const auto huge = std::vector<u8>(CacheStore::MAX_FILE_SIZE + 1);
    CHECK_THROWS_WITH(Compression::Gunzip(GzipWithoutVersion(huge)), ContainsSubstring("more than 2000000 bytes"));

    const auto atLimit = std::vector<u8>(CacheStore::MAX_FILE_SIZE);
    CHECK(Compression::Gunzip(GzipWithoutVersion(atLimit)).size() == CacheStore::MAX_FILE_SIZE);
}
