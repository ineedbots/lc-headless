#include "pch.hpp"
#include "SquareCollision.hpp"

#include "../../Cache/LocType_s.hpp"
#include "../../Cache/MapSquare.hpp"
#include "LocShape.hpp"

void SquareCollision::AddLoc(CollisionMap& collision, const GameCache_s& cache, s32 x, s32 z, s32 id, u8 shape, u8 angle)
{
    const auto* const type = cache.FindLoc(id);
    if (type == nullptr || !type->blockWalk)
    {
        return;
    }

    switch (LocShape::GetLayer(shape))
    {
    case LocLayer_e::Wall:
        collision.AddWall(x, z, shape, angle, type->blockRange);
        return;
    case LocLayer_e::Ground:
        collision.AddLoc(x, z, type->width, type->length, angle, type->blockRange);
        return;
    case LocLayer_e::GroundDecor:
        if (type->active)
        {
            collision.BlockGround(x, z);
        }
        return;
    case LocLayer_e::WallDecor:
        return;
    }
}

void SquareCollision::AddSquare(CollisionMap& collision, const GameCache_s& cache, const MapSquare& square, s32 level, s32 originX, s32 originZ)
{
    for (auto x = 0; x < MapSquare::SIZE; ++x)
    {
        for (auto z = 0; z < MapSquare::SIZE; ++z)
        {
            if (square.IsBlocked(level, x, z) && collision.InBounds(originX + x, originZ + z))
            {
                collision.BlockGround(originX + x, originZ + z);
            }
        }
    }

    for (const auto& loc : square.GetLocs())
    {
        if (loc.GetLevel() == level)
        {
            AddLoc(collision, cache, originX + loc.GetX(), originZ + loc.GetZ(), loc.id, loc.GetShape(), loc.GetAngle());
        }
    }
}
