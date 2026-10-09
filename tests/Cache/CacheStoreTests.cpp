#include "pch.hpp"
#include "../TempFolder.hpp"
#include "CacheWriter.hpp"

#include "Cache/CacheError.hpp"
#include "Cache/CacheStore.hpp"

#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_string.hpp>

using Catch::Matchers::ContainsSubstring;

namespace
{
    constexpr auto FILE_ID_OFFSET = std::size_t{0};
    constexpr auto PART_OFFSET = std::size_t{2};
    constexpr auto NEXT_SECTOR_OFFSET = std::size_t{4};
    constexpr auto STORE_OFFSET = std::size_t{7};

    std::vector<u8> MakeBytes(std::size_t size, u8 seed)
    {
        auto bytes = std::vector<u8>(size);
        for (std::size_t i = 0; i < size; ++i)
        {
            bytes[i] = static_cast<u8>(seed + i * 7);
        }

        return bytes;
    }

    void PutU24(std::vector<u8>& bytes, std::size_t offset, u32 value)
    {
        bytes[offset] = static_cast<u8>(value >> 16);
        bytes[offset + 1] = static_cast<u8>(value >> 8);
        bytes[offset + 2] = static_cast<u8>(value);
    }

    std::size_t GetSectorStart(std::size_t sector)
    {
        return sector * CacheStore::SECTOR_SIZE;
    }

    // Store 0 file 1 is 1,300 bytes in sectors 1 to 3.
    class DamageFixture
    {
    public:
        DamageFixture()
            : folder{"rs2004-cache-store-tests"}
        {
            writer.Put(0, 1, MakeBytes(1300, 3));
            written = writer.Build();
        }

        std::string ReadError()
        {
            CacheWriter::WriteStore(folder.GetPath(), written);
            auto store = CacheStore{folder.GetPath()};
            try
            {
                static_cast<void>(store.Read(0, 1));
            }
            catch (const CacheError& e)
            {
                return e.what();
            }

            return "no error";
        }

        TempFolder folder;
        CacheWriter writer;
        WrittenStore_s written;
    };
}

TEST_CASE("CacheStore reads files of one and several sectors", "[CacheStore]")
{
    const auto folder = TempFolder{"rs2004-cache-store-tests"};
    auto writer = CacheWriter{};
    const auto small = MakeBytes(100, 1);
    const auto exact = MakeBytes(512, 2);
    const auto large = MakeBytes(1300, 3);
    const auto map = MakeBytes(700, 4);
    writer.Put(0, 1, small);
    writer.Put(0, 2, exact);
    writer.Put(0, 3, large);
    writer.Put(0, 5, {});
    writer.Put(4, 9, map);
    static_cast<void>(writer.Write(folder.GetPath()));

    auto store = CacheStore{folder.GetPath()};
    CHECK(store.GetFileCount(0) == 6);
    CHECK(store.GetFileCount(4) == 10);
    CHECK(store.GetFileCount(1) == 0);
    CHECK(store.Read(0, 1) == small);
    CHECK(store.Read(0, 2) == exact);
    CHECK(store.Read(0, 3) == large);
    CHECK(store.Read(4, 9) == map);

    SECTION("absent entries give nothing")
    {
        CHECK_FALSE(store.Read(0, 0).has_value());
        CHECK_FALSE(store.Read(0, 4).has_value());
        CHECK_FALSE(store.Read(0, 5).has_value());
        CHECK_FALSE(store.Read(0, 6).has_value());
        CHECK_FALSE(store.Read(4, 100).has_value());
    }
}

TEST_CASE("CacheStore needs its .dat, and an index for each store it reads", "[CacheStore]")
{
    const auto folder = TempFolder{"rs2004-cache-store-tests"};
    CHECK_THROWS_WITH(CacheStore{folder.GetPath()}, ContainsSubstring("main_file_cache.dat not found"));

    auto writer = CacheWriter{};
    writer.Put(0, 1, MakeBytes(10, 1));
    static_cast<void>(writer.Write(folder.GetPath()));
    std::filesystem::remove(folder.GetPath() / "main_file_cache.idx4");

    auto store = CacheStore{folder.GetPath()};
    CHECK(store.Read(0, 1).has_value());
    CHECK(store.GetFileCount(4) == 0);
    CHECK_THROWS_WITH(store.Read(4, 0), ContainsSubstring("main_file_cache.idx4 not found"));
}

TEST_CASE("CacheStore rejects damaged sector chains, naming the store and file", "[CacheStore]")
{
    auto fixture = DamageFixture{};
    auto& dat = fixture.written.dat;

    SECTION("a sector of another file")
    {
        dat[GetSectorStart(1) + FILE_ID_OFFSET + 1] = 7;
        CHECK(fixture.ReadError() == "store 0 file 1: sector 1 belongs to file 7");
    }

    SECTION("a sector out of order")
    {
        dat[GetSectorStart(2) + PART_OFFSET + 1] = 5;
        CHECK(fixture.ReadError() == "store 0 file 1: sector 2 is part 5, not 1");
    }

    SECTION("a sector of another store")
    {
        dat[GetSectorStart(1) + STORE_OFFSET] = 3;
        CHECK(fixture.ReadError() == "store 0 file 1: sector 1 belongs to store 2");
    }

    SECTION("a next sector past the end of the .dat")
    {
        PutU24(dat, GetSectorStart(1) + NEXT_SECTOR_OFFSET, 80);
        CHECK(fixture.ReadError() == "store 0 file 1: sector 80 is past the end of main_file_cache.dat");
    }

    SECTION("a chain that ends early")
    {
        PutU24(dat, GetSectorStart(2) + NEXT_SECTOR_OFFSET, 0);
        CHECK(fixture.ReadError() == "store 0 file 1: the sector chain ends after 1024 of 1300 bytes");
    }

    SECTION("a size over the limit")
    {
        PutU24(fixture.written.indexes[0], CacheStore::INDEX_ENTRY_SIZE, static_cast<u32>(CacheStore::MAX_FILE_SIZE + 1));
        CHECK(fixture.ReadError() == "store 0 file 1: size 2000001 is over the limit of 2000000");
    }

    SECTION("a first sector past the end of the .dat")
    {
        PutU24(fixture.written.indexes[0], CacheStore::INDEX_ENTRY_SIZE + 3, 999);
        CHECK(fixture.ReadError() == "store 0 file 1: sector 999 is past the end of main_file_cache.dat");
    }
}
