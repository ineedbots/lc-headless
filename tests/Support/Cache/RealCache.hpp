#pragma once

#include "Cache/GameCache_s.hpp"
#include "Config/Revision_e.hpp"

// A real cache, loaded once per revision for every test that reads it; the load's log goes to the test output.
// The 289 cache is the folder in RS2004_CACHE_DIR, such as ../289server/engine/data/pack, the 274 cache the one
// in RS2004_CACHE_DIR_274, such as ../274server/engine/data/pack, and the 225 cache the one in
// RS2004_CACHE_DIR_225, such as ../225server/engine/data/pack/client.
class RealCache
{
public:
    RealCache() = delete;

    // Skips the test when the revision's variable isn't set.
    [[nodiscard]] static const GameCache_s& Require(Revision_e revision);
    [[nodiscard]] static std::shared_ptr<const GameCache_s> RequireShared(Revision_e revision);
};
