#pragma once

#include "../../Cache/GameCache_s.hpp"

// The whole world's walking, for routes beyond the build area: for every tile of every map square on every
// level with a floor, the directions a player can step out of it, whether it can be stood on, and which of
// its sides have walls. It's built once from the cache by the webclient's rules (SquareCollision and
// PathFinder::CanStep), and shared read-only by every account. The doors the cache places shut are walls in
// it; NavGraph's door edges cross them.
class WalkMap
{
public:
    static constexpr s32 LEVELS = 4;
    static constexpr s32 DIRECTIONS = 8;
    // Each direction's step, as rs2b0t orders them: north, east, south, west, then the diagonals clockwise
    // from north-east. Bit d of a tile's exits is direction d.
    static constexpr std::array<s32, DIRECTIONS> DX = {0, 1, 0, -1, 1, 1, -1, -1};
    static constexpr std::array<s32, DIRECTIONS> DZ = {1, 0, -1, 0, 1, -1, -1, 1};
    static constexpr u8 WALL_NORTH = 0x1;
    static constexpr u8 WALL_EAST = 0x2;
    static constexpr u8 WALL_SOUTH = 0x4;
    static constexpr u8 WALL_WEST = 0x8;

    explicit WalkMap(const GameCache_s& cache);

    [[nodiscard]] bool IsWalkable(s32 x, s32 z, s32 level) const;
    [[nodiscard]] u8 GetExits(s32 x, s32 z, s32 level) const;
    [[nodiscard]] u8 GetWalls(s32 x, s32 z, s32 level) const;
    // Squares times the levels with a floor that it holds, and their size in bytes.
    [[nodiscard]] std::size_t GetLevelSquareCount() const;
    [[nodiscard]] std::size_t GetMemoryBytes() const;

private:
    static constexpr s32 TILES = 64 * 64;

    struct LevelSquare_s
    {
        std::array<u8, TILES> exits{};
        std::array<u8, TILES> walls{};
        std::bitset<TILES> walkable;
    };

    [[nodiscard]] static u32 GetKey(s32 x, s32 z, s32 level);
    [[nodiscard]] const LevelSquare_s* Find(s32 x, s32 z, s32 level) const;
    void BuildSquare(const GameCache_s& cache, const MapSquare& square, s32 level);

    std::unordered_map<u32, std::unique_ptr<LevelSquare_s>> m_squares;
};
