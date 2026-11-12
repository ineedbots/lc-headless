#include "pch.hpp"
#include "LocTypeResolver.hpp"

#include "Type/GameCache_s.hpp"
#include "Type/LocType_s.hpp"
#include "Type/VarbitType_s.hpp"

s32 LocTypeResolver::ResolveId(const GameCache_s& cache, const std::unordered_map<u16, s32>& varps, s32 id)
{
    const auto* const type = cache.FindLoc(id);
    if (type == nullptr || type->multiloc.empty())
    {
        return id;
    }

    if (type->multivarbit >= cache.varbits.size())
    {
        return -1;
    }

    const auto& varbit = cache.varbits[type->multivarbit];
    assert(varbit.startBit <= varbit.endBit && varbit.endBit < 32 && "Invalid varbit range");

    const auto value = varps.find(varbit.baseVar);
    const auto bits = value == varps.end() ? u32{0} : static_cast<u32>(value->second);
    const auto width = varbit.endBit - varbit.startBit + 1;
    const auto mask = width == 32 ? std::numeric_limits<u32>::max() : (u32{1} << width) - 1;
    const auto index = (bits >> varbit.startBit) & mask;
    if (index >= type->multiloc.size() || cache.FindLoc(type->multiloc[index]) == nullptr)
    {
        return -1;
    }

    return type->multiloc[index];
}
