#pragma once

#include "../Map/WorldMap.hpp"
#include "../State/GameState_s.hpp"
#include "../Tile_s.hpp"

// Routes from the local player across the build area, by the rule each kind of target is walked to.
class ReachQuery
{
public:
    ReachQuery(const GameState_s& state, const WorldMap& map);

    [[nodiscard]] bool CanReachEntity(const Tile_s& tile) const;
    [[nodiscard]] bool CanReachGroundItem(const Tile_s& tile) const;
    [[nodiscard]] bool CanReachLoc(const Tile_s& tile, u16 loc) const;
    // Whether a walk can end on the tile.
    [[nodiscard]] bool IsReachable(const Tile_s& tile) const;
    // Whether one step between neighbouring tiles is open.
    [[nodiscard]] bool CanStep(const Tile_s& from, const Tile_s& to) const;
    // The waypoints a walk to the tile would send, or nullopt without a route.
    [[nodiscard]] std::optional<std::vector<Tile_s>> FindPath(const Tile_s& tile) const;
    // Whether the server's sight ray from one tile reaches a body of size whose south-west tile is to. False
    // across levels, or for a tile outside the loaded area.
    [[nodiscard]] bool HasLineOfSight(const Tile_s& from, const Tile_s& to, s32 size) const;
    // A loaded tile's collision flags, as CollisionFlag has them, or nullopt outside the loaded area.
    [[nodiscard]] std::optional<u32> GetFlags(const Tile_s& tile) const;

private:
    [[nodiscard]] const Tile_s& GetPosition() const;

    const GameState_s& m_state;
    const WorldMap& m_map;
};
