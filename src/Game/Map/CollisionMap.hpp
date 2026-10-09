#pragma once

// One level of the 104x104 build area, indexed by local tile: absolute minus the build area's base.
// Angles are the webclient's: 0 west, 1 north, 2 east, 3 south.
class CollisionMap
{
public:
    static constexpr s32 SIZE = 104;

    CollisionMap();

    // Open tiles inside, and BOUNDS on the outermost ring.
    void Reset();
    void BlockGround(s32 x, s32 z);
    void AddLoc(s32 x, s32 z, s32 width, s32 length, u8 angle, bool blockRange);
    void AddWall(s32 x, s32 z, u8 shape, u8 angle, bool blockRange);

    [[nodiscard]] static bool Contains(s32 x, s32 z);
    [[nodiscard]] u32 GetFlags(s32 x, s32 z) const;
    // Whether a player on (srcX, srcZ) can use the wall or wall decor on (dstX, dstZ).
    [[nodiscard]] bool CanReachWall(s32 srcX, s32 srcZ, s32 dstX, s32 dstZ, u8 shape, u8 angle) const;
    [[nodiscard]] bool CanReachWallDecor(s32 srcX, s32 srcZ, s32 dstX, s32 dstZ, u8 shape, u8 angle) const;
    // Whether a player on (srcX, srcZ) is on the width x length area at (dstX, dstZ), or beside it on a
    // side that forceApproach allows and no wall closes.
    [[nodiscard]] bool CanReachArea(s32 srcX, s32 srcZ, s32 dstX, s32 dstZ, s32 width, s32 length, u8 forceApproach) const;

private:
    // Tiles outside the area are ignored, so a large loc on the edge is cut off.
    void Add(s32 x, s32 z, u32 flags);

    std::vector<u32> m_flags;
};
