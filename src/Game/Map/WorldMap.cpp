#include "pch.hpp"
#include "WorldMap.hpp"

#include "../../Cache/GameCache_s.hpp"
#include "../../Cache/LocType_s.hpp"
#include "../../Cache/MapSquare.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Zone_s.hpp"
#include "../Tile_s.hpp"
#include "CollisionMap.hpp"
#include "LocShape.hpp"

namespace
{
    constexpr auto BUILD_AREA_RADIUS_ZONES = 6;
    constexpr auto ZONES_PER_SQUARE = MapSquare::SIZE / Zone_s::SIZE;
    // loadLocations leaves the outer ring of the area, which is all BOUNDS, without locs.
    constexpr auto FIRST_SCENE_TILE = 1;
    constexpr auto LAST_SCENE_TILE = BuildArea_s::SIZE - 2;

    bool IsInScene(s32 localX, s32 localZ)
    {
        return localX >= FIRST_SCENE_TILE && localZ >= FIRST_SCENE_TILE && localX <= LAST_SCENE_TILE && localZ <= LAST_SCENE_TILE;
    }

    bool IsLevel(s32 level)
    {
        return level >= 0 && level < WorldMap::LEVELS;
    }
}

WorldMap::WorldMap(std::shared_ptr<const GameCache_s> cache)
    : m_cache{std::move(cache)}
{
    assert(m_cache && "WorldMap needs a cache");
}

void WorldMap::Update(const GameState_s& state)
{
    if (!state.buildArea.loaded || m_builtAt == state.sceneChangeCount)
    {
        return;
    }

    Rebuild(state);
}

void WorldMap::Clear()
{
    m_area = BuildArea_s{};
    m_builtAt.reset();
    m_changes.clear();
}

const GameCache_s& WorldMap::GetCache() const
{
    return *m_cache;
}

bool WorldMap::IsLoaded() const
{
    return m_builtAt.has_value();
}

const BuildArea_s& WorldMap::GetBuildArea() const
{
    return m_area;
}

bool WorldMap::Contains(const Tile_s& tile) const
{
    return IsLoaded() && IsLevel(tile.level) && CollisionMap::Contains(tile.x - m_area.baseX, tile.z - m_area.baseZ);
}

const CollisionMap& WorldMap::GetCollision(s32 level) const
{
    assert(IsLevel(level) && "Level out of range");
    return m_collision[static_cast<std::size_t>(level)];
}

template <typename TVisit>
void WorldMap::VisitCachedLocs(TVisit visit) const
{
    for (const auto* const square : GetSquares())
    {
        const auto originX = square->GetX() * MapSquare::SIZE;
        const auto originZ = square->GetZ() * MapSquare::SIZE;
        for (const auto loc : square->GetLocs())
        {
            const auto tile = Tile_s{.x = originX + loc.GetX(), .z = originZ + loc.GetZ(), .level = loc.GetLevel()};
            const auto localX = tile.x - m_area.baseX;
            const auto localZ = tile.z - m_area.baseZ;
            const auto layer = LocShape::GetLayer(loc.GetShape());
            if (!IsInScene(localX, localZ) || FindChange(tile, layer) != nullptr)
            {
                continue;
            }

            visit(SceneLoc_s{.tile = tile, .layer = layer, .id = loc.id, .shape = loc.GetShape(), .angle = loc.GetAngle()}, localX, localZ);
        }
    }
}

std::optional<SceneLoc_s> WorldMap::GetLoc(const Tile_s& tile, LocLayer_e layer) const
{
    if (!Contains(tile))
    {
        return std::nullopt;
    }

    if (const auto* const change = FindChange(tile, layer))
    {
        return SceneLoc_s{.tile = tile, .layer = layer, .id = change->id, .shape = change->shape, .angle = change->angle, .changed = true};
    }

    if (!IsInScene(tile.x - m_area.baseX, tile.z - m_area.baseZ))
    {
        return std::nullopt;
    }

    const auto* const square = m_cache->FindSquare(tile.x / MapSquare::SIZE, tile.z / MapSquare::SIZE);
    if (square == nullptr)
    {
        return std::nullopt;
    }

    for (const auto loc : square->GetLocsAt(tile.level, tile.x % MapSquare::SIZE, tile.z % MapSquare::SIZE))
    {
        if (LocShape::GetLayer(loc.GetShape()) == layer)
        {
            return SceneLoc_s{.tile = tile, .layer = layer, .id = loc.id, .shape = loc.GetShape(), .angle = loc.GetAngle()};
        }
    }

    return std::nullopt;
}

std::vector<SceneLoc_s> WorldMap::GetLocs(s32 level) const
{
    auto locs = std::vector<SceneLoc_s>{};
    if (!IsLoaded())
    {
        return locs;
    }

    VisitCachedLocs([level, &locs](const SceneLoc_s& loc, s32, s32)
    {
        if (loc.tile.level == level)
        {
            locs.push_back(loc);
        }
    });

    for (const auto& change : m_changes)
    {
        if (change.tile.level != level || change.id < 0)
        {
            continue;
        }

        locs.push_back({.tile = change.tile, .layer = change.layer, .id = change.id, .shape = change.shape, .angle = change.angle, .changed = true});
    }

    return locs;
}

// Follows ClientBuild, which blocks the squares' tiles and adds their locs, and locChangeUnchecked, which
// puts each change in place of what the cache has in its layer on its tile.
void WorldMap::Rebuild(const GameState_s& state)
{
    m_area = state.buildArea;
    m_changes = state.locChanges;
    for (auto& collision : m_collision)
    {
        collision.Reset();
    }

    for (const auto* const square : GetSquares())
    {
        const auto originX = square->GetX() * MapSquare::SIZE - m_area.baseX;
        const auto originZ = square->GetZ() * MapSquare::SIZE - m_area.baseZ;
        for (auto level = 0; level < LEVELS; ++level)
        {
            for (auto x = 0; x < MapSquare::SIZE; ++x)
            {
                for (auto z = 0; z < MapSquare::SIZE; ++z)
                {
                    if (square->IsBlocked(level, x, z))
                    {
                        m_collision[static_cast<std::size_t>(level)].BlockGround(originX + x, originZ + z);
                    }
                }
            }
        }
    }

    VisitCachedLocs([this](const SceneLoc_s& loc, s32 localX, s32 localZ)
    {
        AddCollision(loc.tile.level, localX, localZ, loc.id, loc.shape, loc.angle);
    });

    for (const auto& change : m_changes)
    {
        const auto localX = change.tile.x - m_area.baseX;
        const auto localZ = change.tile.z - m_area.baseZ;
        if (change.id < 0 || !IsLevel(change.tile.level) || !IsInScene(localX, localZ))
        {
            continue;
        }

        AddCollision(change.tile.level, localX, localZ, change.id, change.shape, change.angle);
    }

    m_builtAt = state.sceneChangeCount;
}

// ClientBuild.addLoc's collision: only types that block walking touch it.
void WorldMap::AddCollision(s32 level, s32 x, s32 z, s32 id, u8 shape, u8 angle)
{
    const auto* const type = m_cache->FindLoc(id);
    if (type == nullptr || !type->blockWalk)
    {
        return;
    }

    auto& collision = m_collision[static_cast<std::size_t>(level)];
    switch (LocShape::GetLayer(shape))
    {
    case LocLayer_e::Wall:
        collision.AddWall(x, z, shape, angle, type->blockRange);
        return;
    case LocLayer_e::Ground:
        collision.AddLoc(x, z, type->width, type->length, angle, type->blockRange);
        return;
    case LocLayer_e::GroundDecor:
        if (type->active)
        {
            collision.BlockGround(x, z);
        }
        return;
    case LocLayer_e::WallDecor:
        return;
    }
}

const LocChange_s* WorldMap::FindChange(const Tile_s& tile, LocLayer_e layer) const
{
    const auto found = std::ranges::find_if(m_changes, [&tile, layer](const LocChange_s& change)
    {
        return change.tile == tile && change.layer == layer;
    });

    return found == m_changes.end() ? nullptr : &*found;
}

std::vector<const MapSquare*> WorldMap::GetSquares() const
{
    auto squares = std::vector<const MapSquare*>{};
    const auto firstX = (m_area.centreZoneX - BUILD_AREA_RADIUS_ZONES) / ZONES_PER_SQUARE;
    const auto lastX = (m_area.centreZoneX + BUILD_AREA_RADIUS_ZONES) / ZONES_PER_SQUARE;
    const auto firstZ = (m_area.centreZoneZ - BUILD_AREA_RADIUS_ZONES) / ZONES_PER_SQUARE;
    const auto lastZ = (m_area.centreZoneZ + BUILD_AREA_RADIUS_ZONES) / ZONES_PER_SQUARE;
    for (auto squareX = firstX; squareX <= lastX; ++squareX)
    {
        for (auto squareZ = firstZ; squareZ <= lastZ; ++squareZ)
        {
            if (const auto* const square = m_cache->FindSquare(squareX, squareZ))
            {
                squares.push_back(square);
            }
        }
    }

    return squares;
}
