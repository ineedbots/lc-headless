#include "pch.hpp"
#include "NavRect_s.hpp"

bool NavRect_s::Contains(s32 x, s32 z, s32 tileLevel) const
{
    return x >= minX && x <= maxX && z >= minZ && z <= maxZ && (!level || *level == tileLevel);
}
