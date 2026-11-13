#pragma once

#include "Type/NavEdge_s.hpp"
#include "Type/NavPoint_s.hpp"
#include "Type/NavTeleport_s.hpp"
#include "WorldPathFinder.hpp"

#include <nlohmann/json.hpp>

// Route output uses objects; request tiles remain explicit [x, z, level] arrays.
NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(NavPoint_s, x, z, level)

inline void to_json(nlohmann::json& value, const NavWaypoint_s& waypoint)
{
    auto entry = nlohmann::json(waypoint.point);
    if (const auto* const edge = waypoint.edge)
    {
        auto transport = nlohmann::json{
            {"kind", edge->kind},
            {"loc_name", edge->locName},
            {"action", edge->action},
            {"loc_x", edge->locX},
            {"loc_z", edge->locZ},
            {"accept_any_landing", edge->acceptAnyLanding},
            {"edge_cost", edge->cost},
        };

        if (edge->locId)
        {
            transport["loc_id"] = *edge->locId;
        }

        if (edge->openLocId)
        {
            transport["open_loc_id"] = *edge->openLocId;
        }

        if (edge->toLevel)
        {
            transport["to_level"] = *edge->toLevel;
        }

        if (edge->toTile)
        {
            transport["to_tile"] = {edge->toTile->first, edge->toTile->second};
        }

        entry["transport"] = std::move(transport);
    }
    else if (const auto* const teleport = waypoint.teleport)
    {
        entry["transport"] = nlohmann::json{
            {"kind", "teleport"},
            {"loc_name", teleport->label},
            {"action", teleport->family == "spell" ? "Cast" : "Rub"},
            {"teleport_id", teleport->id},
            {"family", teleport->family},
            {"to_tile", {teleport->to.x, teleport->to.z}},
            {"accept_any_landing", true},
            {"edge_cost", teleport->cost},
        };
    }

    value = std::move(entry);
}

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_ONLY_SERIALIZE(NavPath_s, ok, reason, cost, expanded, waypoints)
