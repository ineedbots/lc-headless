#pragma once

#include "../Game/Nav/WorldPathFinder.hpp"

struct NavRequest_s
{
    NavPoint_s from;
    NavPoint_s to;
    NavFindOptions_s options;
};

// The stdlib's walker asks for routes and reads them as JSON, which keeps the options' many optional fields
// out of the bindings. Names are snake_case:
//
//     {"from": [x, z, level], "to": [x, z, level], "max_expansions": 1200000, "avoid_doors": [[x, z]],
//      "use_teleport_catalog": true, "avoid_zones": [{"min_x", "max_x", "min_z", "max_z", "level"}],
//      "policy": {"use_teleports", "use_ships", "use_shortcuts", "distance_before_teleport",
//                 "allow_teleport_ids", "deny_teleport_ids"},
//      "state": {"members", "skills": {name: level}, "items": {name: count}, "worn": {name: count},
//                "quests": {name: status}, "free_slots", "entrana_restricted_gear", "can_slash_web"}}
//
// A route comes back as {"ok", "reason", "cost", "expanded", "waypoints": [{"x", "z", "level",
// "transport": {"kind", "loc_name", "action", "loc_x", "loc_z", "loc_id", "open_loc_id", "to_level",
// "to_tile": [x, z], "accept_any_landing", "teleport_id", "edge_cost"}}]}, a waypoint's transport being the
// hop that arrives there.
namespace NavJson
{
    // Throws std::invalid_argument naming what's wrong.
    [[nodiscard]] NavRequest_s ParseRequest(std::string_view json);
    [[nodiscard]] std::string ToJson(const NavPath_s& path);
}
