#pragma once

#include "CollisionMap.hpp"

// A body on a collision map: its south-west tile, in the map's coordinates, and its size.
struct Footprint_s
{
    s32 x = 0;
    s32 z = 0;
    s32 size = 1;
};

// The engine's sight ray, its rayCastLine with line of sight on, as rs2b0t's lineOfSight.ts ports it. What it
// says the server can see is what a ranged or magic attack fires at without walking.
class LineOfSight
{
public:
    LineOfSight() = delete;

    // A tile outside the map reads as opaque, since nothing is known of ground that isn't loaded.
    [[nodiscard]] static bool Has(const CollisionMap& collision, const Footprint_s& source, const Footprint_s& target);
};
