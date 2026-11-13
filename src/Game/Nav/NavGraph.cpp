#include "pch.hpp"
#include "NavGraph.hpp"

#include "Type/NavEdge_s.hpp"
#include "Type/NavPoint_s.hpp"
#include "Type/NavTeleport_s.hpp"
#include "NavGraphJson.hpp"
#include "../Map/WalkMap.hpp"

NavGraph::NavGraph(const WalkMap& map, std::string_view edgesJson, std::string_view teleportsJson)
    : m_edges{NavGraphJson::ReadEdges(map, edgesJson)}
    , m_teleports{NavGraphJson::ReadTeleports(teleportsJson)}
{
    for (const auto& edge : m_edges)
    {
        const auto span = std::max(std::abs(edge.to.x - edge.from.x), std::abs(edge.to.z - edge.from.z));
        m_longEdges = m_longEdges || span > edge.cost;
        m_doors += edge.kind == "door" ? 1 : 0;
        m_from[GetNodeId(edge.from.x, edge.from.z, edge.from.level)].push_back(&edge);
    }
}

u32 NavGraph::GetNodeId(s32 x, s32 z, s32 level)
{
    return static_cast<u32>((level << 28) | (x << 14) | z);
}

std::span<const NavEdge_s* const> NavGraph::GetEdgesFrom(u32 node) const
{
    const auto found = m_from.find(node);
    if (found == m_from.end())
    {
        return {};
    }

    return found->second;
}

std::span<const NavTeleport_s> NavGraph::GetTeleports() const
{
    return m_teleports;
}

bool NavGraph::HasLongEdges() const
{
    return m_longEdges;
}

std::size_t NavGraph::GetEdgeCount() const
{
    return m_edges.size();
}

std::size_t NavGraph::GetDoorCount() const
{
    return m_doors;
}
