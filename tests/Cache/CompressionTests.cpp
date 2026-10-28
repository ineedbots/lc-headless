#include "pch.hpp"
#include "../Support/Cache/CacheWriter.hpp"

#include "Cache/CacheStore.hpp"
#include "Cache/Compression.hpp"
#include "Cache/Error/CacheError.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/generators/catch_generators.hpp>
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

TEST_CASE("Compression rejects gzip that still has output after filling the largest buffer", "[Compression][CompressionFailureCoverage]")
{
    const auto data = std::vector<u8>(CacheStore::MAX_FILE_SIZE * 2, 'x');
    CHECK_THROWS_WITH(Compression::Gunzip(GzipWithoutVersion(data)), ContainsSubstring("gzip data unpacks to more than 2000000 bytes"));
    CHECK(Compression::Gunzip(GzipWithoutVersion(std::array<u8, 3>{1, 2, 3})) == std::vector<u8>{1, 2, 3});
}

TEST_CASE("Compression checks gzip payload and size checksums", "[Compression][CompressionFailureCoverage]")
{
    const auto trailerOffset = GENERATE(std::size_t{8}, std::size_t{4});
    const auto data = MakeData(20'000);
    auto packed = GzipWithoutVersion(data);
    packed[packed.size() - trailerOffset] ^= 1;
    CHECK_THROWS_WITH(Compression::Gunzip(packed), ContainsSubstring("gzip data is damaged (Z_DATA_ERROR)"));
    CHECK(Compression::Gunzip(GzipWithoutVersion(data)) == data);
}

TEST_CASE("Compression rejects a damaged bzip2 block checksum and truncated trailer", "[Compression][CompressionFailureCoverage]")
{
    const auto data = MakeData(1000);
    const auto packed = CacheWriter::Bzip2Headerless(data);
    auto damaged = packed;
    // The headerless stream begins with its six-byte block marker, followed by the block CRC.
    damaged[6] ^= 1;
    CHECK_THROWS_WITH(Compression::Bunzip2(damaged, data.size()), ContainsSubstring("bzip2 data is damaged (BZ_DATA_ERROR)"));
    CHECK_THROWS_WITH(Compression::Bunzip2(std::span{packed}.first(packed.size() - 5), data.size()), ContainsSubstring("bzip2 data ends early"));
    CHECK(Compression::Bunzip2(packed, data.size()) == data);
}
