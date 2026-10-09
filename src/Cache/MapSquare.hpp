#pragma once

// One loc, packed as the loc file packs it, in 6 bytes.
struct MapLoc_s
{
    static constexpr u16 COORD_MASK = 0x3F;
    static constexpr u32 X_SHIFT = 6;
    static constexpr u32 LEVEL_SHIFT = 12;
    static constexpr u32 SHAPE_SHIFT = 2;
    static constexpr u8 ANGLE_MASK = 0x3;

    u16 id = 0;
    // level << 12 | x << 6 | z, with x and z within the square, and the level the one it's seen on.
    u16 position = 0;
    // shape << 2 | angle.
    u8 info = 0;

    [[nodiscard]] static u16 PackPosition(s32 level, s32 x, s32 z)
    {
        return static_cast<u16>((level << LEVEL_SHIFT) | (x << X_SHIFT) | z);
    }

    [[nodiscard]] s32 GetX() const
    {
        return (position >> X_SHIFT) & COORD_MASK;
    }

    [[nodiscard]] s32 GetZ() const
    {
        return position & COORD_MASK;
    }

    [[nodiscard]] s32 GetLevel() const
    {
        return position >> LEVEL_SHIFT;
    }

    [[nodiscard]] u8 GetShape() const
    {
        return static_cast<u8>(info >> SHAPE_SHIFT);
    }

    [[nodiscard]] u8 GetAngle() const
    {
        return static_cast<u8>(info & ANGLE_MASK);
    }
};

static_assert(sizeof(MapLoc_s) == 6);

// One 64x64 square of the map: the tiles that block walking and the locs a bot can use, both on the
// levels they're seen on. Code outside Cache/ reads it only through these functions, so the way it's
// stored can change without touching its readers.
class MapSquare
{
public:
    static constexpr s32 SIZE = 64;
    static constexpr s32 LEVELS = 4;
    static constexpr s32 ID_SHIFT = 8;

    using BlockedTiles = std::bitset<LEVELS * SIZE * SIZE>;

    // Sorts the locs by tile.
    MapSquare(u8 x, u8 z, BlockedTiles blocked, std::vector<MapLoc_s> locs);

    [[nodiscard]] static u16 GetId(s32 squareX, s32 squareZ);
    [[nodiscard]] static std::size_t GetBit(s32 level, s32 x, s32 z);

    [[nodiscard]] u8 GetX() const;
    [[nodiscard]] u8 GetZ() const;
    [[nodiscard]] bool IsBlocked(s32 level, s32 x, s32 z) const;
    [[nodiscard]] std::span<const MapLoc_s> GetLocsAt(s32 level, s32 x, s32 z) const;
    [[nodiscard]] std::span<const MapLoc_s> GetLocs() const;

private:
    u8 m_x;
    u8 m_z;
    // Bit (level * SIZE + x) * SIZE + z.
    BlockedTiles m_blocked;
    // Sorted by position, which sorts by level, then x, then z.
    std::vector<MapLoc_s> m_locs;
};
