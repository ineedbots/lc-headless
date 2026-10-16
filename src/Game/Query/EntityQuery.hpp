#pragma once

#include "../Map/WorldMap.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Npc_s.hpp"
#include "../State/Player_s.hpp"
#include "../State/Zone_s.hpp"
#include "../Tile_s.hpp"
#include "SearchFilter_s.hpp"

// The NPCs, players, ground items and locs around the local player, read in place, so it's cheap to make and
// can't go stale. A filter's radius counts from the local player. Reachable means the path finder reaches the
// target by the rule the matching interaction walks by.
class EntityQuery
{
public:
    EntityQuery(const GameState_s& state, const WorldMap& map);

    [[nodiscard]] std::vector<Npc_s> GetNpcs(const SearchFilter_s& filter) const;
    [[nodiscard]] std::optional<Npc_s> GetNearestNpc(const SearchFilter_s& filter, std::optional<bool> inCombat, bool reachable = false) const;
    [[nodiscard]] std::optional<Npc_s> GetNpc(u16 index) const;
    [[nodiscard]] std::vector<Player_s> GetPlayers(std::optional<s32> radius) const;
    [[nodiscard]] std::optional<Player_s> GetPlayerByName(std::string_view name) const;
    [[nodiscard]] std::vector<GroundItem_s> GetGroundItems(const SearchFilter_s& filter) const;
    [[nodiscard]] std::optional<GroundItem_s> GetNearestGroundItem(const SearchFilter_s& filter, bool reachable = false) const;
    // Without a layer, the first loc on the tile in layer order, preferring one that's there to one the
    // server removed.
    [[nodiscard]] std::optional<SceneLoc_s> GetLocAt(const Tile_s& tile, std::optional<LocLayer_e> layer) const;
    // Nearest first, leaving out locs the server removed.
    [[nodiscard]] std::vector<SceneLoc_s> GetLocs(const SearchFilter_s& filter, std::optional<LocLayer_e> layer) const;
    [[nodiscard]] std::optional<SceneLoc_s> GetNearestLoc(const SearchFilter_s& filter, std::optional<LocLayer_e> layer, bool reachable = false) const;
    [[nodiscard]] bool HasGroundItem(u16 obj, const Tile_s& tile) const;

private:
    [[nodiscard]] const Tile_s& GetPosition() const;

    const GameState_s& m_state;
    const WorldMap& m_map;
};
