#include "pch.hpp"
#include "MapSquare.hpp"

MapSquare::MapSquare(u8 x, u8 z, BlockedTiles blocked, std::vector<MapLoc_s> locs)
    : m_x{x}
    , m_z{z}
    , m_blocked{blocked}
    , m_locs{std::move(locs)}
{
    std::ranges::stable_sort(m_locs, {}, &MapLoc_s::position);
}

u16 MapSquare::GetId(s32 squareX, s32 squareZ)
{
    assert(squareX >= 0 && squareX <= 0xFF && squareZ >= 0 && squareZ <= 0xFF && "Square coordinates out of range");
    return static_cast<u16>((squareX << ID_SHIFT) | squareZ);
}

std::size_t MapSquare::GetBit(s32 level, s32 x, s32 z)
{
    assert(level >= 0 && level < LEVELS && x >= 0 && x < SIZE && z >= 0 && z < SIZE && "Tile outside the square");
    return static_cast<std::size_t>((level * SIZE + x) * SIZE + z);
}

u8 MapSquare::GetX() const
{
    return m_x;
}

u8 MapSquare::GetZ() const
{
    return m_z;
}

bool MapSquare::IsBlocked(s32 level, s32 x, s32 z) const
{
    return m_blocked.test(GetBit(level, x, z));
}

std::span<const MapLoc_s> MapSquare::GetLocsAt(s32 level, s32 x, s32 z) const
{
    assert(level >= 0 && level < LEVELS && x >= 0 && x < SIZE && z >= 0 && z < SIZE && "Tile outside the square");
    const auto [first, last] = std::ranges::equal_range(m_locs, MapLoc_s::PackPosition(level, x, z), {}, &MapLoc_s::position);
    return {first, last};
}

std::span<const MapLoc_s> MapSquare::GetLocs() const
{
    return m_locs;
}
