#include "pch.hpp"
#include "NavJson.hpp"

#include "../../Utils/StringUtils.hpp"
#include "Type/NavPoint_s.hpp"
#include "Type/NavState_s.hpp"
#include "NavPayloadJson.hpp"

#include <nlohmann/json.hpp>

namespace
{
    using Json = nlohmann::json;

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
                counts[StringUtils::ToLower(name)] += count.get<s32>();
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
            .essenceExitReturn = ReadOptional<std::string>(json, "essence_exit_return"),
        };

        if (const auto quests = json.find("quests"); quests != json.end() && quests->is_object())
        {
            for (const auto& [name, status] : quests->items())
            {
                state.quests[StringUtils::ToLower(name)] = status.get<std::string>();
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
    return Json(path).dump();
}
