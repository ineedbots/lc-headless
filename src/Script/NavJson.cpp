#include "pch.hpp"
#include "NavJson.hpp"

#include <nlohmann/json.hpp>

namespace
{
    using Json = nlohmann::json;

    std::string Lower(std::string_view text)
    {
        auto result = std::string{text};
        std::ranges::transform(result, result.begin(), [](char c) { return static_cast<char>(std::tolower(static_cast<unsigned char>(c))); });
        return result;
    }

    NavPoint_s ReadPoint(const Json& json)
    {
        if (!json.is_array() || json.size() != 3)
        {
            throw std::invalid_argument{"a tile must be [x, z, level]"};
        }

        return {.x = json[0].get<s32>(), .z = json[1].get<s32>(), .level = json[2].get<s32>()};
    }

    std::unordered_map<std::string, s32> ReadCounts(const Json& json, const char* key)
    {
        auto counts = std::unordered_map<std::string, s32>{};
        if (const auto found = json.find(key); found != json.end() && found->is_object())
        {
            for (const auto& [name, count] : found->items())
            {
                counts[Lower(name)] += count.get<s32>();
            }
        }

        return counts;
    }

    template <typename T>
    std::optional<T> ReadOptional(const Json& json, const char* key)
    {
        const auto found = json.find(key);
        if (found == json.end() || found->is_null())
        {
            return std::nullopt;
        }

        return found->get<T>();
    }

    NavState_s ReadState(const Json& json)
    {
        auto state = NavState_s{
            .members = json.value("members", false),
            .skills = ReadCounts(json, "skills"),
            .items = ReadCounts(json, "items"),
            .worn = ReadCounts(json, "worn"),
            .freeSlots = json.value("free_slots", 0),
            .entranaRestrictedGear = json.value("entrana_restricted_gear", false),
            .canSlashWeb = ReadOptional<bool>(json, "can_slash_web"),
        };

        if (const auto quests = json.find("quests"); quests != json.end() && quests->is_object())
        {
            for (const auto& [name, status] : quests->items())
            {
                state.quests[Lower(name)] = status.get<std::string>();
            }
        }

        return state;
    }

    NavPolicy_s ReadPolicy(const Json& json)
    {
        return {
            .useTeleports = ReadOptional<bool>(json, "use_teleports"),
            .useShips = ReadOptional<bool>(json, "use_ships"),
            .useShortcuts = ReadOptional<bool>(json, "use_shortcuts"),
            .distanceBeforeTeleport = json.value("distance_before_teleport", 0),
            .allowTeleportIds = json.value("allow_teleport_ids", std::vector<std::string>{}),
            .denyTeleportIds = json.value("deny_teleport_ids", std::vector<std::string>{}),
        };
    }
}

NavRequest_s NavJson::ParseRequest(std::string_view text)
{
    try
    {
        const auto json = Json::parse(text);
        auto request = NavRequest_s{.from = ReadPoint(json.at("from")), .to = ReadPoint(json.at("to"))};
        auto& options = request.options;
        options.maxExpansions = json.value("max_expansions", NavFindOptions_s::MAX_EXPANSIONS);
        options.useTeleportCatalog = ReadOptional<bool>(json, "use_teleport_catalog");
        if (const auto doors = json.find("avoid_doors"); doors != json.end() && doors->is_array())
        {
            for (const auto& door : *doors)
            {
                options.avoidDoors.emplace_back(door.at(0).get<s32>(), door.at(1).get<s32>());
            }
        }

        if (const auto zones = json.find("avoid_zones"); zones != json.end() && zones->is_array())
        {
            for (const auto& zone : *zones)
            {
                options.avoidZones.push_back({
                    .minX = zone.at("min_x").get<s32>(),
                    .maxX = zone.at("max_x").get<s32>(),
                    .minZ = zone.at("min_z").get<s32>(),
                    .maxZ = zone.at("max_z").get<s32>(),
                    .level = ReadOptional<s32>(zone, "level"),
                });
            }
        }

        if (const auto policy = json.find("policy"); policy != json.end() && policy->is_object())
        {
            options.policy = ReadPolicy(*policy);
        }

        if (const auto state = json.find("state"); state != json.end() && state->is_object())
        {
            options.state = ReadState(*state);
        }

        return request;
    }
    catch (const Json::exception& e)
    {
        throw std::invalid_argument{std::format("a route request is malformed: {}", e.what())};
    }
}

std::string NavJson::ToJson(const NavPath_s& path)
{
    auto json = Json{{"ok", path.ok}, {"reason", path.reason}, {"cost", path.cost}, {"expanded", path.expanded}};
    auto waypoints = Json::array();
    for (const auto& waypoint : path.waypoints)
    {
        auto entry = Json{{"x", waypoint.point.x}, {"z", waypoint.point.z}, {"level", waypoint.point.level}};
        if (const auto* const edge = waypoint.edge)
        {
            auto transport = Json{
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
            entry["transport"] = Json{
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

        waypoints.push_back(std::move(entry));
    }

    json["waypoints"] = std::move(waypoints);
    return json.dump();
}
