#pragma once

#include "../../Cache/GameCache_s.hpp"
#include "../../Cache/MapSquare.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Zone_s.hpp"
#include "../Tile_s.hpp"
#include "CollisionMap.hpp"

// A loc in the build area as it is now: as the server changed it, or else as the cache has it.
struct SceneLoc_s
{
    Tile_s tile;
    LocLayer_e layer = LocLayer_e::Ground;
    // -1 when the server removed it.
    s32 id = -1;
    u8 shape = 0;
    u8 angle = 0;
    bool changed = false;
};

// One account's view of the map: collision for the build area's four levels, and the scenery in it.
// Update rebuilds both from the shared cache and the state whenever the state's build area or loc
// changes have moved on, so they always agree with what the server sent.
class WorldMap
{
public:
    static constexpr s32 LEVELS = 4;

    explicit WorldMap(std::shared_ptr<const GameCache_s> cache);

    void Update(const GameState_s& state);
    // Forgets the area, for a fresh login, which starts the state over.
    void Clear();

    [[nodiscard]] const GameCache_s& GetCache() const;
    [[nodiscard]] bool IsLoaded() const;
    [[nodiscard]] const BuildArea_s& GetBuildArea() const;
    [[nodiscard]] bool Contains(const Tile_s& tile) const;
    [[nodiscard]] const CollisionMap& GetCollision(s32 level) const;
    // nullopt when the tile has nothing in that layer, or is outside the build area.
    [[nodiscard]] std::optional<SceneLoc_s> GetLoc(const Tile_s& tile, LocLayer_e layer) const;
    // Every loc on the level, except ones the server removed.
    [[nodiscard]] std::vector<SceneLoc_s> GetLocs(s32 level) const;

private:
    void Rebuild(const GameState_s& state);
    void AddCollision(s32 level, s32 x, s32 z, s32 id, u8 shape, u8 angle);
    [[nodiscard]] const LocChange_s* FindChange(const Tile_s& tile, LocLayer_e layer) const;
    [[nodiscard]] std::vector<const MapSquare*> GetSquares() const;
    // Calls visit with each of the cache's locs in the area as the webclient's scene holds them: not on
    // the outer ring, and not where a change replaced them.
    template <typename TVisit>
    void VisitCachedLocs(TVisit visit) const;

    std::shared_ptr<const GameCache_s> m_cache;
    BuildArea_s m_area;
    std::optional<u64> m_builtAt;
    std::array<CollisionMap, LEVELS> m_collision;
    std::vector<LocChange_s> m_changes;
};
