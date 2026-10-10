#include "pch.hpp"
#include "WorldPathFinder.hpp"

#include <queue>

namespace
{
    // A* keys put the estimate above the cost so far, which breaks ties toward the route further along.
    constexpr auto KEY_SCALE = s64{1} << 20;
    constexpr auto START_SNAP_RADIUS = 2;
    constexpr auto GOAL_RADIUS = 5;
    constexpr auto FOOTPRINT_RADIUS = 2;

    constexpr auto WILDERNESS_WEST = 2944;
    constexpr auto WILDERNESS_EAST = 3391;
    constexpr auto WILDERNESS_SOUTH = 3520;
    constexpr auto WILDERNESS_NORTH = 6399;
    constexpr auto UNDERGROUND_SOUTH = 9920;
    constexpr auto UNDERGROUND_NORTH = 12799;
    constexpr auto WILDERNESS_BAND = 8;

    // Each cardinal neighbour, with the wall on its side that faces back the other way.
    struct Side_s
    {
        s32 dx;
        s32 dz;
        u8 facing;
    };

    constexpr auto CARDINAL_SIDES = std::to_array<Side_s>({
        {0, 1, WalkMap::WALL_SOUTH},
        {1, 0, WalkMap::WALL_WEST},
        {0, -1, WalkMap::WALL_NORTH},
        {-1, 0, WalkMap::WALL_EAST},
    });

    s32 Chebyshev(s32 ax, s32 az, s32 bx, s32 bz)
    {
        return std::max(std::abs(ax - bx), std::abs(az - bz));
    }

    s32 NodeX(u32 node)
    {
        return static_cast<s32>((node >> 14) & 0x3FFF);
    }

    s32 NodeZ(u32 node)
    {
        return static_cast<s32>(node & 0x3FFF);
    }

    s32 NodeLevel(u32 node)
    {
        return static_cast<s32>((node >> 28) & 0x3);
    }

    NavPoint_s ToPoint(u32 node)
    {
        return {.x = NodeX(node), .z = NodeZ(node), .level = NodeLevel(node)};
    }

    u32 ToNode(s32 x, s32 z, s32 level)
    {
        return NavGraph::GetNodeId(x, z, level);
    }

    bool Contains(const std::vector<std::string>& values, std::string_view value)
    {
        return std::ranges::find(values, value) != values.end();
    }

    std::string Lower(std::string_view text)
    {
        auto result = std::string{text};
        std::ranges::transform(result, result.begin(), [](char c) { return static_cast<char>(std::tolower(static_cast<unsigned char>(c))); });
        return result;
    }

    bool KindAllowed(std::string_view kind, const NavPolicy_s& policy)
    {
        if (kind == "teleport" && policy.useTeleports == false)
        {
            return false;
        }

        if ((kind == "ship" || kind == "gangplank") && policy.useShips == false)
        {
            return false;
        }

        return kind != "shortcut" || policy.useShortcuts != false;
    }

    bool InZones(const std::vector<NavRect_s>& zones, s32 x, s32 z, s32 level)
    {
        return std::ranges::any_of(zones, [x, z, level](const NavRect_s& zone) { return zone.Contains(x, z, level); });
    }

    // One move the search can make besides a step.
    struct Hop_s
    {
        u32 to = 0;
        s32 cost = 0;
        const NavEdge_s* edge = nullptr;
        const NavTeleport_s* teleport = nullptr;
    };

    class Search
    {
    public:
        Search(const Navigation_s& navigation, const NavFindOptions_s& options)
            : m_map{navigation.map}
            , m_graph{navigation.graph}
            , m_options{options}
        {
        }

        NavPath_s Run(NavPoint_s fromRaw, NavPoint_s to)
        {
            const auto from = SnapWalkable(fromRaw, START_SNAP_RADIUS);
            if (!from)
            {
                return Fail(std::format("start ({},{},{}) not walkable", fromRaw.x, fromRaw.z, fromRaw.level), 0);
            }

            m_start = ToNode(from->x, from->z, from->level);
            AddTeleports(*from, to);

            const auto cardinal = GetCardinalGoals(to);
            if (!cardinal.empty())
            {
                auto direct = Find(to, cardinal, 1);
                if (direct.ok)
                {
                    return direct;
                }
            }

            const auto goals = GetGoalCandidates(to, GOAL_RADIUS);
            if (goals.empty())
            {
                return Fail(std::format("target ({},{},{}) not walkable within {} tiles", to.x, to.z, to.level, GOAL_RADIUS), 0);
            }

            const auto exact = goals.size() == 1 && goals.contains(ToNode(to.x, to.z, to.level));
            return Find(to, goals, exact ? 0 : GOAL_RADIUS);
        }

    private:
        static NavPath_s Fail(std::string reason, s32 expanded)
        {
            return {.ok = false, .reason = std::move(reason), .expanded = expanded};
        }

        [[nodiscard]] bool IsWalkable(s32 x, s32 z, s32 level) const
        {
            return m_map.IsWalkable(x, z, level);
        }

        // A walkable tile with a way out, the nearest within radius; else a stranded walkable one.
        [[nodiscard]] std::optional<NavPoint_s> SnapWalkable(NavPoint_s point, s32 radius) const
        {
            auto stranded = std::optional<NavPoint_s>{};
            const auto usable = [&](s32 x, s32 z) -> bool
            {
                if (!IsWalkable(x, z, point.level))
                {
                    return false;
                }

                if (m_map.GetExits(x, z, point.level) != 0 || !m_graph.GetEdgesFrom(ToNode(x, z, point.level)).empty())
                {
                    return true;
                }

                if (!stranded)
                {
                    stranded = NavPoint_s{.x = x, .z = z, .level = point.level};
                }

                return false;
            };

            if (usable(point.x, point.z))
            {
                return point;
            }

            for (auto r = 1; r <= radius; ++r)
            {
                for (auto dx = -r; dx <= r; ++dx)
                {
                    for (auto dz = -r; dz <= r; ++dz)
                    {
                        if (std::max(std::abs(dx), std::abs(dz)) == r && usable(point.x + dx, point.z + dz))
                        {
                            return NavPoint_s{.x = point.x + dx, .z = point.z + dz, .level = point.level};
                        }
                    }
                }
            }

            return stranded;
        }

        // The walkable tiles beside any of tiles, on a side no wall closes, within reach of at.
        [[nodiscard]] std::unordered_set<u32> GetBeside(const std::vector<NavPoint_s>& tiles, NavPoint_s at) const
        {
            auto goals = std::unordered_set<u32>{};
            for (const auto& tile : tiles)
            {
                for (const auto& side : CARDINAL_SIDES)
                {
                    const auto x = tile.x + side.dx;
                    const auto z = tile.z + side.dz;
                    if (Chebyshev(x, z, at.x, at.z) > FOOTPRINT_RADIUS)
                    {
                        continue;
                    }

                    if (IsWalkable(x, z, at.level) && (m_map.GetWalls(x, z, at.level) & side.facing) == 0)
                    {
                        goals.insert(ToNode(x, z, at.level));
                    }
                }
            }

            return goals;
        }

        // The solid tiles a loc covers, read back off the walkable ones around one of them.
        [[nodiscard]] std::vector<NavPoint_s> GetBlockedFootprint(NavPoint_s point) const
        {
            auto solid = std::vector<NavPoint_s>{point};
            auto seen = std::unordered_set<u32>{ToNode(point.x, point.z, point.level)};
            auto stack = std::vector<NavPoint_s>{point};
            while (!stack.empty())
            {
                const auto current = stack.back();
                stack.pop_back();
                for (const auto& side : CARDINAL_SIDES)
                {
                    const auto next = NavPoint_s{.x = current.x + side.dx, .z = current.z + side.dz, .level = point.level};
                    if (Chebyshev(next.x, next.z, point.x, point.z) > FOOTPRINT_RADIUS || IsWalkable(next.x, next.z, next.level))
                    {
                        continue;
                    }

                    if (seen.insert(ToNode(next.x, next.z, next.level)).second)
                    {
                        solid.push_back(next);
                        stack.push_back(next);
                    }
                }
            }

            return solid;
        }

        // For a goal that can't be stood on, such as a booth: the tiles beside it, or beside the whole loc.
        [[nodiscard]] std::unordered_set<u32> GetCardinalGoals(NavPoint_s point) const
        {
            if (IsWalkable(point.x, point.z, point.level))
            {
                return {};
            }

            auto beside = GetBeside({point}, point);
            return beside.empty() ? GetBeside(GetBlockedFootprint(point), point) : beside;
        }

        [[nodiscard]] std::unordered_set<u32> GetGoalCandidates(NavPoint_s point, s32 radius) const
        {
            auto goals = std::unordered_set<u32>{};
            if (IsWalkable(point.x, point.z, point.level))
            {
                goals.insert(ToNode(point.x, point.z, point.level));
                return goals;
            }

            auto queue = std::deque<u32>{};
            auto seen = std::unordered_set<u32>{};
            for (const auto node : GetCardinalGoals(point))
            {
                queue.push_back(node);
                seen.insert(node);
            }

            while (!queue.empty())
            {
                const auto node = queue.front();
                queue.pop_front();
                goals.insert(node);
                const auto x = NodeX(node);
                const auto z = NodeZ(node);
                const auto exits = m_map.GetExits(x, z, point.level);
                for (auto direction = 0; direction < WalkMap::DIRECTIONS; ++direction)
                {
                    const auto nx = x + WalkMap::DX[static_cast<std::size_t>(direction)];
                    const auto nz = z + WalkMap::DZ[static_cast<std::size_t>(direction)];
                    const auto next = ToNode(nx, nz, point.level);
                    if ((exits & (1 << direction)) == 0 || Chebyshev(nx, nz, point.x, point.z) > radius || !IsWalkable(nx, nz, point.level) || !seen.insert(next).second)
                    {
                        continue;
                    }

                    queue.push_back(next);
                }
            }

            if (!goals.empty())
            {
                return goals;
            }

            for (auto dx = -radius; dx <= radius; ++dx)
            {
                for (auto dz = -radius; dz <= radius; ++dz)
                {
                    if (IsWalkable(point.x + dx, point.z + dz, point.level))
                    {
                        goals.insert(ToNode(point.x + dx, point.z + dz, point.level));
                    }
                }
            }

            return goals;
        }

        // Teleports leave from the start, when the policy, the wilderness and the account allow them.
        void AddTeleports(NavPoint_s from, NavPoint_s to)
        {
            const auto& policy = m_options.policy;
            const auto inject = m_options.useTeleportCatalog.value_or(policy.useTeleports != false);
            if (!inject || policy.useTeleports == false)
            {
                return;
            }

            const auto span = Chebyshev(from.x, from.z, to.x, to.z);
            const auto wilderness = WorldPathFinder::GetWildernessLevel(from);
            for (const auto& teleport : m_graph.GetTeleports())
            {
                if (!IsWalkable(teleport.to.x, teleport.to.z, teleport.to.level))
                {
                    continue;
                }

                if (!policy.allowTeleportIds.empty() && !Contains(policy.allowTeleportIds, teleport.id))
                {
                    continue;
                }

                if (Contains(policy.denyTeleportIds, teleport.id) || (policy.distanceBeforeTeleport > 0 && span < policy.distanceBeforeTeleport))
                {
                    continue;
                }

                if (teleport.maxWildernessLevel && wilderness > *teleport.maxWildernessLevel)
                {
                    continue;
                }

                // A teleport's runes, levels and quests need the account's state: without one, there's no teleport.
                if (teleport.requirement && (!m_options.state || teleport.requirement->Check(*m_options.state)))
                {
                    continue;
                }

                if (teleport.family == "jewellery" && !HasJewellery(teleport))
                {
                    continue;
                }

                m_teleports.push_back({.to = ToNode(teleport.to.x, teleport.to.z, teleport.to.level), .cost = teleport.cost, .teleport = &teleport});
            }
        }

        [[nodiscard]] bool HasJewellery(const NavTeleport_s& teleport) const
        {
            if (m_options.useTeleportCatalog != true || !m_options.state)
            {
                return false;
            }

            for (const auto& [name, count] : m_options.state->items)
            {
                for (const auto& part : teleport.itemNameMatch)
                {
                    if (count > 0 && name.find(Lower(part)) != std::string::npos)
                    {
                        return true;
                    }
                }
            }

            return false;
        }

        [[nodiscard]] bool EdgeAllowed(const NavEdge_s& edge) const
        {
            if (!KindAllowed(edge.kind, m_options.policy))
            {
                return false;
            }

            const auto avoided = std::ranges::any_of(m_options.avoidDoors, [&edge](const std::pair<s32, s32>& door)
            {
                return door.first == edge.locX && door.second == edge.locZ;
            });

            if (avoided)
            {
                return false;
            }

            // Without a state, gated edges are planned, as rs2b0t plans offline; the walker always gives one.
            return !edge.requirement || !edge.requirement->IsGated() || !m_options.state || !edge.requirement->Check(*m_options.state);
        }

        NavPath_s Find(NavPoint_s goal, const std::unordered_set<u32>& goals, s32 goalSlack)
        {
            m_cost.clear();
            m_cameFrom.clear();
            m_via.clear();
            auto closed = std::unordered_set<u32>{};
            using Entry = std::pair<s64, u32>;
            auto open = std::priority_queue<Entry, std::vector<Entry>, std::greater<>>{};

            const auto distance = [goal, goalSlack](s32 x, s32 z)
            {
                return std::max(0, Chebyshev(x, z, goal.x, goal.z) - goalSlack);
            };

            // The cheapest teleport and the walk from its landing is a lower bound from anywhere, since a
            // teleport works from any tile; without one, long hops make the walking distance an overestimate.
            auto teleportFloor = std::optional<s32>{};
            for (const auto& hop : m_teleports)
            {
                const auto bound = hop.cost + distance(NodeX(hop.to), NodeZ(hop.to));
                teleportFloor = std::min(teleportFloor.value_or(bound), bound);
            }

            const auto heuristic = [&](s32 x, s32 z)
            {
                const auto walk = distance(x, z);
                if (teleportFloor)
                {
                    return std::min(walk, *teleportFloor);
                }

                return m_graph.HasLongEdges() ? 0 : walk;
            };

            const auto push = [&](u32 node, s32 cost)
            {
                open.emplace((static_cast<s64>(cost) + heuristic(NodeX(node), NodeZ(node))) * KEY_SCALE - cost, node);
            };

            m_cost[m_start] = 0;
            push(m_start, 0);
            auto expanded = 0;
            while (!open.empty())
            {
                const auto current = open.top().second;
                open.pop();
                if (!closed.insert(current).second)
                {
                    continue;
                }

                if (goals.contains(current))
                {
                    return Reconstruct(current, expanded);
                }

                if (++expanded > m_options.maxExpansions)
                {
                    return Fail(std::format("expansion budget exceeded ({})", m_options.maxExpansions), expanded);
                }

                const auto x = NodeX(current);
                const auto z = NodeZ(current);
                const auto level = NodeLevel(current);
                const auto cost = m_cost.at(current);
                const auto& zones = m_options.avoidZones;
                const auto escaping = !zones.empty() && InZones(zones, x, z, level);
                const auto relax = [&](u32 next, s32 nextCost, const Hop_s* hop)
                {
                    if (closed.contains(next))
                    {
                        return;
                    }

                    const auto known = m_cost.find(next);
                    if (known != m_cost.end() && known->second <= nextCost)
                    {
                        return;
                    }

                    m_cost[next] = nextCost;
                    m_cameFrom[next] = current;
                    if (hop != nullptr)
                    {
                        m_via[next] = *hop;
                    }
                    else
                    {
                        m_via.erase(next);
                    }

                    push(next, nextCost);
                };

                const auto exits = m_map.GetExits(x, z, level);
                for (auto direction = 0; direction < WalkMap::DIRECTIONS; ++direction)
                {
                    const auto nx = x + WalkMap::DX[static_cast<std::size_t>(direction)];
                    const auto nz = z + WalkMap::DZ[static_cast<std::size_t>(direction)];
                    if ((exits & (1 << direction)) == 0 || (!escaping && !zones.empty() && InZones(zones, nx, nz, level)))
                    {
                        continue;
                    }

                    relax(ToNode(nx, nz, level), cost + 1, nullptr);
                }

                // A staircase with two stands on one floor is two edges, and up then straight back down would
                // pass through the wall between them; the server lands you on one side only.
                const auto arrivedBy = m_via.find(current);
                const auto cameUpStairs = arrivedBy != m_via.end() && arrivedBy->second.edge != nullptr && arrivedBy->second.edge->kind == "stair";
                const auto cameFromLevel = cameUpStairs ? std::optional{NodeLevel(m_cameFrom.at(current))} : std::nullopt;
                const auto hops = GetHops(current);
                for (const auto& hop : hops)
                {
                    if (hop.edge != nullptr && (!EdgeAllowed(*hop.edge) || (cameFromLevel && hop.edge->kind == "stair" && NodeLevel(hop.to) == *cameFromLevel)))
                    {
                        continue;
                    }

                    if (!escaping && !zones.empty() && InZones(zones, NodeX(hop.to), NodeZ(hop.to), NodeLevel(hop.to)))
                    {
                        continue;
                    }

                    relax(hop.to, cost + hop.cost, &hop);
                }
            }

            return Fail("unreachable", expanded);
        }

        [[nodiscard]] std::vector<Hop_s> GetHops(u32 node) const
        {
            auto hops = std::vector<Hop_s>{};
            for (const auto* const edge : m_graph.GetEdgesFrom(node))
            {
                hops.push_back({.to = ToNode(edge->to.x, edge->to.z, edge->to.level), .cost = edge->cost, .edge = edge});
            }

            if (node == m_start)
            {
                hops.insert(hops.end(), m_teleports.begin(), m_teleports.end());
            }

            return hops;
        }

        NavPath_s Reconstruct(u32 goal, s32 expanded)
        {
            auto chain = std::vector<u32>{};
            for (auto node = goal;;)
            {
                chain.push_back(node);
                if (node == m_start)
                {
                    break;
                }

                node = m_cameFrom.at(node);
            }

            std::ranges::reverse(chain);
            const auto direction = [](u32 a, u32 b)
            {
                const auto dx = (NodeX(b) > NodeX(a)) - (NodeX(b) < NodeX(a));
                const auto dz = (NodeZ(b) > NodeZ(a)) - (NodeZ(b) < NodeZ(a));
                return (dx + 1) * 3 + (dz + 1);
            };

            auto path = NavPath_s{.ok = true, .cost = m_cost.at(goal), .expanded = expanded};
            path.waypoints.push_back({.point = ToPoint(chain.front())});
            for (std::size_t i = 1; i < chain.size(); ++i)
            {
                const auto via = m_via.find(chain[i]);
                const auto hop = via == m_via.end() ? nullptr : &via->second;
                const auto last = i + 1 == chain.size();
                const auto nextHop = !last && m_via.contains(chain[i + 1]);
                const auto turns = !last && hop == nullptr && !nextHop && direction(chain[i - 1], chain[i]) != direction(chain[i], chain[i + 1]);
                if (hop != nullptr || nextHop || turns || last)
                {
                    path.waypoints.push_back({
                        .point = ToPoint(chain[i]),
                        .edge = hop != nullptr ? hop->edge : nullptr,
                        .teleport = hop != nullptr ? hop->teleport : nullptr,
                    });
                }
            }

            return path;
        }

        const WalkMap& m_map;
        const NavGraph& m_graph;
        const NavFindOptions_s& m_options;
        u32 m_start = 0;
        std::vector<Hop_s> m_teleports;
        std::unordered_map<u32, s32> m_cost;
        std::unordered_map<u32, u32> m_cameFrom;
        std::unordered_map<u32, Hop_s> m_via;
    };
}

NavPath_s WorldPathFinder::FindPath(const Navigation_s& navigation, NavPoint_s from, NavPoint_s to, const NavFindOptions_s& options)
{
    auto search = Search{navigation, options};
    return search.Run(from, to);
}

s32 WorldPathFinder::GetWildernessLevel(NavPoint_s tile)
{
    if (tile.x < WILDERNESS_WEST || tile.x > WILDERNESS_EAST)
    {
        return 0;
    }

    if (tile.level >= 0 && tile.level <= 3 && tile.z >= WILDERNESS_SOUTH && tile.z <= WILDERNESS_NORTH)
    {
        return (tile.z - WILDERNESS_SOUTH) / WILDERNESS_BAND + 1;
    }

    if (tile.level == 0 && tile.z >= UNDERGROUND_SOUTH && tile.z <= UNDERGROUND_NORTH)
    {
        return (tile.z - UNDERGROUND_SOUTH) / WILDERNESS_BAND + 1;
    }

    return 0;
}
