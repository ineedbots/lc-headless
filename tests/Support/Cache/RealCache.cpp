#include "pch.hpp"
#include "RealCache.hpp"
#include "../LogCapture.hpp"

#include "Cache/CacheLoader.hpp"
#include "Cache/GameCache_s.hpp"
#include "Config/Revision_e.hpp"

#include <catch2/catch_test_macros.hpp>

namespace
{
    std::string_view GetVariable(Revision_e revision)
    {
        switch (revision)
        {
        case Revision_e::Rev225:
            return "RS2004_CACHE_DIR_225";
        case Revision_e::Rev274:
            return "RS2004_CACHE_DIR_274";
        case Revision_e::Rev289:
            return "RS2004_CACHE_DIR";
        }

        assert(false && "Unhandled Revision_e");
        return "RS2004_CACHE_DIR";
    }

    std::optional<std::filesystem::path> GetCacheDirectory(std::string_view variable)
    {
        // MSVC deprecates getenv in favour of _dupenv_s, which other platforms don't have.
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable : 4996)
#endif
        const auto* const value = std::getenv(std::string{variable}.c_str());
#ifdef _MSC_VER
#pragma warning(pop)
#endif
        if (value == nullptr || *value == '\0')
        {
            return std::nullopt;
        }

        return std::filesystem::path{value};
    }

    std::shared_ptr<const GameCache_s> Load(const std::filesystem::path& directory, Revision_e revision)
    {
        auto capture = LogCapture{};
        auto loaded = std::make_shared<const GameCache_s>(CacheLoader::Load(directory, revision, *capture.GetLogger()));
        for (const auto& entry : capture.GetEntries())
        {
            UNSCOPED_INFO(entry.message);
        }

        return loaded;
    }
}

std::shared_ptr<const GameCache_s> RealCache::RequireShared(Revision_e revision)
{
    const auto variable = GetVariable(revision);
    const auto directory = GetCacheDirectory(variable);
    if (!directory)
    {
        SKIP(std::format("Set {} to a {} cache folder to run this test", variable, static_cast<u16>(revision)));
    }

    static auto caches = std::map<Revision_e, std::shared_ptr<const GameCache_s>>{};
    auto& cache = caches[revision];
    if (!cache)
    {
        cache = Load(*directory, revision);
    }

    return cache;
}

const GameCache_s& RealCache::Require(Revision_e revision)
{
    return *RequireShared(revision);
}
