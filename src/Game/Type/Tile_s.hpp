#pragma once

struct Tile_s
{
    // The largest coordinate a script may name.
    static constexpr s32 MAX_COORD = 32767;

    s32 x = 0;
    s32 z = 0;
    s32 level = 0;

    [[nodiscard]] bool operator==(const Tile_s& other) const = default;

    [[nodiscard]] s32 GetDistance(const Tile_s& other) const
    {
        return std::max(std::abs(x - other.x), std::abs(z - other.z));
    }

    // In the rectangle whose south-west corner is (minX, minZ), on any level.
    [[nodiscard]] bool IsInRect(s32 minX, s32 minZ, s64 width, s64 height) const
    {
        return x >= minX && x < minX + width && z >= minZ && z < minZ + height;
    }
};
