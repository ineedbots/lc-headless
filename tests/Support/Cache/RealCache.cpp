#include "pch.hpp"
#include "RealCache.hpp"
#include "../LogCapture.hpp"

#include "Cache/CacheLoader.hpp"
#include "Cache/GameCache_s.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    constexpr auto CACHE_DIR_VARIABLE = "RS2004_CACHE_DIR";

    std::optional<std::filesystem::path> GetCacheDirectory()
    {
        // MSVC deprecates getenv in favour of _dupenv_s, which other platforms don't have.
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable : 4996)
#endif
        const auto* const value = std::getenv(CACHE_DIR_VARIABLE);
#ifdef _MSC_VER
#pragma warning(pop)
#endif
        if (value == nullptr || *value == '\0')
        {
            return std::nullopt;
        }

        return std::filesystem::path{value};
    }
}

std::shared_ptr<const GameCache_s> RealCache::RequireShared()
{
    const auto directory = GetCacheDirectory();
    if (!directory)
    {
        SKIP("Set RS2004_CACHE_DIR to a 289 cache folder to run this test");
    }

    static const auto cache = [&directory]
    {
        auto capture = LogCapture{};
        auto loaded = std::make_shared<const GameCache_s>(CacheLoader::Load(*directory, *capture.GetLogger()));
        for (const auto& entry : capture.GetEntries())
        {
            UNSCOPED_INFO(entry.message);
        }

        return loaded;
    }();

    return cache;
}

const GameCache_s& RealCache::Require()
{
    return *RequireShared();
}
