#pragma once

struct Tile_s
{
    s32 x = 0;
    s32 z = 0;
    s32 level = 0;

    [[nodiscard]] bool operator==(const Tile_s& other) const = default;

    [[nodiscard]] s32 GetDistance(const Tile_s& other) const
    {
        return std::max(std::abs(x - other.x), std::abs(z - other.z));
    }
};
