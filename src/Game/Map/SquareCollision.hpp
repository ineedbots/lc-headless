#pragma once

#include "../../Cache/GameCache_s.hpp"
#include "CollisionMap.hpp"

// The collision a map square's tiles and locs add, as ClientBuild adds it, shared by the build area's
// WorldMap and the whole world's WalkMap so the two can't drift apart.
namespace SquareCollision
{
    // A loc of type id at (x, z) in the grid. Only types that block walking add anything.
    void AddLoc(CollisionMap& collision, const GameCache_s& cache, s32 x, s32 z, s32 id, u8 shape, u8 angle);
    // The square's blocked tiles and locs on the level, with its corner at (originX, originZ) in the grid;
    // whatever falls outside the grid is left out.
    void AddSquare(CollisionMap& collision, const GameCache_s& cache, const MapSquare& square, s32 level, s32 originX, s32 originZ);
}
