#pragma once

struct GameCache_s;

// The 289 cache from the folder in RS2004_CACHE_DIR, such as ../289server/engine/data/pack, loaded once for
// every test that reads it; the load's log goes to the test output.
class RealCache
{
public:
    RealCache() = delete;

    // The cache, or a SKIP of the test when RS2004_CACHE_DIR isn't set.
    [[nodiscard]] static const GameCache_s& Require();
    [[nodiscard]] static std::shared_ptr<const GameCache_s> RequireShared();
};
