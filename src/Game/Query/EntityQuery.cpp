#include "pch.hpp"
#include "EntityQuery.hpp"

#include "../../Cache/GameCache_s.hpp"
#include "../Map/InteractionRoutes.hpp"
#include "../Map/WorldMap.hpp"
#include "../State/EntityStatus.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Npc_s.hpp"
#include "../State/Player_s.hpp"
#include "../State/Zone_s.hpp"
#include "../Tile_s.hpp"
#include "SearchFilter_s.hpp"

namespace
{
    // Nearest first, keeping the given order between equal distances.
    template <typename T, typename TTile>
    void SortByDistance(std::vector<T>& candidates, const Tile_s& from, TTile getTile)
    {
        std::ranges::stable_sort(candidates, {}, [&from, &getTile](const T& candidate)
        {
            return from.GetDistance(getTile(candidate));
        });
    }

    // The nearest candidate that accept takes; ties go to the first in the given order.
    template <typename T, typename TTile, typename TAccept>
    std::optional<T> FindNearest(std::vector<T> candidates, const Tile_s& from, TTile getTile, TAccept accept)
    {
        SortByDistance(candidates, from, getTile);

        const auto found = std::ranges::find_if(candidates, accept);
        if (found == candidates.end())
        {
            return std::nullopt;
        }

        return *found;
    }
}

EntityQuery::EntityQuery(const GameState_s& state, const WorldMap& map)
    : m_state{state}
    , m_map{map}
{
}

std::vector<Npc_s> EntityQuery::GetNpcs(const SearchFilter_s& filter) const
{
    const auto& cache = m_map.GetCache();
    auto found = std::vector<Npc_s>{};
    for (const auto& npc : m_state.npcs)
    {
        if (filter.Matches(GetPosition(), npc.tile, npc.type, cache.FindNpcName(npc.type)))
        {
            found.push_back(npc);
        }
    }

    return found;
}

std::optional<Npc_s> EntityQuery::GetNearestNpc(const SearchFilter_s& filter, std::optional<bool> inCombat, bool reachable) const
{
    auto candidates = GetNpcs(filter);
    if (inCombat)
    {
        std::erase_if(candidates, [this, &inCombat](const Npc_s& npc)
        {
            return EntityStatus::InCombat(npc, m_state.tick) != *inCombat;
        });
    }

    const auto here = GetPosition();
    const auto getTile = [](const Npc_s& npc)
    {
        return npc.tile;
    };

    return FindNearest(std::move(candidates), here, getTile, [this, reachable, &here](const Npc_s& npc)
    {
        return !reachable || InteractionRoutes::FindEntityRoute(m_map, here, npc.tile).has_value();
    });
}

std::optional<Npc_s> EntityQuery::GetNpc(u16 index) const
{
    const auto* npc = m_state.FindNpc(index);
    if (npc == nullptr)
    {
        return std::nullopt;
    }

    return *npc;
}

std::vector<Player_s> EntityQuery::GetPlayers(std::optional<s32> radius) const
{
    const auto filter = SearchFilter_s{.radius = radius};
    auto found = std::vector<Player_s>{};
    for (const auto& player : m_state.players)
    {
        if (filter.Matches(GetPosition(), player.tile, 0, {}))
        {
            found.push_back(player);
        }
    }

    return found;
}

std::optional<Player_s> EntityQuery::GetPlayerByName(std::string_view name) const
{
    const auto* player = m_state.FindPlayerByName(name);
    if (player == nullptr)
    {
        return std::nullopt;
    }

    return *player;
}

std::vector<GroundItem_s> EntityQuery::GetGroundItems(const SearchFilter_s& filter) const
{
    const auto& cache = m_map.GetCache();
    auto found = std::vector<GroundItem_s>{};
    for (const auto& item : m_state.groundItems)
    {
        if (filter.Matches(GetPosition(), item.tile, item.id, cache.FindObjName(item.id)))
        {
            found.push_back(item);
        }
    }

    return found;
}

std::optional<GroundItem_s> EntityQuery::GetNearestGroundItem(const SearchFilter_s& filter, bool reachable) const
{
    const auto here = GetPosition();
    const auto getTile = [](const GroundItem_s& item)
    {
        return item.tile;
    };

    return FindNearest(GetGroundItems(filter), here, getTile, [this, reachable, &here](const GroundItem_s& item)
    {
        return !reachable || InteractionRoutes::FindGroundItemRoute(m_map, here, item.tile).has_value();
    });
}

std::optional<SceneLoc_s> EntityQuery::GetLocAt(const Tile_s& tile, std::optional<LocLayer_e> layer) const
{
    if (layer)
    {
        return m_map.GetLoc(tile, *layer);
    }

    auto removed = std::optional<SceneLoc_s>{};
    for (const auto each : WorldMap::LOC_LAYERS)
    {
        const auto loc = m_map.GetLoc(tile, each);
        if (!loc)
        {
            continue;
        }

        if (loc->id >= 0)
        {
            return loc;
        }

        if (!removed)
        {
            removed = loc;
        }
    }

    return removed;
}

std::vector<SceneLoc_s> EntityQuery::GetLocs(const SearchFilter_s& filter, std::optional<LocLayer_e> layer) const
{
    const auto& cache = m_map.GetCache();
    const auto here = GetPosition();
    auto locs = m_map.GetLocs(here.level);
    std::erase_if(locs, [&cache, &here, &filter, &layer](const SceneLoc_s& loc)
    {
        return (layer && loc.layer != *layer) || !filter.Matches(here, loc.tile, loc.id, cache.FindLocName(loc.id));
    });

    SortByDistance(locs, here, [](const SceneLoc_s& loc)
    {
        return loc.tile;
    });

    return locs;
}

std::optional<SceneLoc_s> EntityQuery::GetNearestLoc(const SearchFilter_s& filter, std::optional<LocLayer_e> layer, bool reachable) const
{
    const auto here = GetPosition();
    const auto getTile = [](const SceneLoc_s& loc)
    {
        return loc.tile;
    };

    return FindNearest(GetLocs(filter, layer), here, getTile, [this, reachable, &here](const SceneLoc_s& loc)
    {
        return !reachable || InteractionRoutes::FindLocRoute(m_map, here, loc.tile, static_cast<u16>(loc.id)).has_value();
    });
}

bool EntityQuery::HasGroundItem(u16 obj, const Tile_s& tile) const
{
    return std::ranges::any_of(m_state.groundItems, [obj, &tile](const GroundItem_s& item)
    {
        return item.id == obj && item.tile == tile;
    });
}

const Tile_s& EntityQuery::GetPosition() const
{
    return m_state.localPlayer.tile;
}
