#pragma once

#include "../Map/WalkMap.hpp"
#include "NavEdge_s.hpp"
#include "NavTeleport_s.hpp"

// Edges whose ends WalkMap can't stand on are left out, as rs2b0t's PathFinder leaves them out.
class NavGraph
{
public:
    // edges.json's and teleports.json's text.
    NavGraph(const WalkMap& map, std::string_view edgesJson, std::string_view teleportsJson);

    [[nodiscard]] static u32 GetNodeId(s32 x, s32 z, s32 level);
    [[nodiscard]] std::span<const NavEdge_s* const> GetEdgesFrom(u32 node) const;
    [[nodiscard]] std::span<const NavTeleport_s> GetTeleports() const;
    // Whether any edge spans more tiles than it costs, which makes the straight-line distance an
    // overestimate.
    [[nodiscard]] bool HasLongEdges() const;
    [[nodiscard]] std::size_t GetEdgeCount() const;
    [[nodiscard]] std::size_t GetDoorCount() const;

private:
    std::vector<NavEdge_s> m_edges;
    std::unordered_map<u32, std::vector<const NavEdge_s*>> m_from;
    std::vector<NavTeleport_s> m_teleports;
    bool m_longEdges = false;
    std::size_t m_doors = 0;
};
