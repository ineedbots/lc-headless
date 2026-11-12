#pragma once

#include "Type/GameCache_s.hpp"

class LocTypeResolver
{
public:
    LocTypeResolver() = delete;

    [[nodiscard]] static s32 ResolveId(const GameCache_s& cache, const std::unordered_map<u16, s32>& varps, s32 id);
};
