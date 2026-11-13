#include "pch.hpp"
#include "NavGraphJson.hpp"

#include "../Map/WalkMap.hpp"
#include "Type/NavEdge_s.hpp"
#include "Type/NavPoint_s.hpp"
#include "Type/NavRequires_s.hpp"
#include "Type/NavTeleport_s.hpp"

#include <nlohmann/json.hpp>

void from_json(const nlohmann::json& value, NavRequires_s& requirement);

namespace
{
    using Json = nlohmann::json;

    NavPoint_s ReadPoint(const Json& json)
    {
        return {.x = json.at("x").get<s32>(), .z = json.at("z").get<s32>(), .level = json.value("level", 0)};
    }

    std::vector<NavRequires_s::Amount_s> ReadAmounts(const Json& json, const char* key, const char* countKey)
    {
        auto amounts = std::vector<NavRequires_s::Amount_s>{};
        if (!json.contains(key))
        {
            return amounts;
        }

        for (const auto& entry : json.at(key))
        {
            amounts.push_back({.name = entry.at("name").get<std::string>(), .count = entry.at(countKey).get<s32>()});
        }

        return amounts;
    }

    std::optional<NavRequires_s> ReadRequires(const Json& json)
    {
        const auto found = json.find("requires");
        if (found == json.end() || !found->is_object())
        {
            return std::nullopt;
        }

        return found->get<NavRequires_s>();
    }

    template <typename TRead>
    auto WithFile(std::string_view name, TRead read)
    {
        try
        {
            return read();
        }
        catch (const Json::exception& e)
        {
            throw std::runtime_error{std::format("{}: {}", name, e.what())};
        }
    }
}

void from_json(const nlohmann::json& value, NavRequires_s& requirement)
{
    requirement = NavRequires_s{};
    requirement.members = value.value("members", false);
    if (value.contains("freeSlots"))
    {
        requirement.freeSlots = value.at("freeSlots").get<s32>();
    }

    requirement.skills = ReadAmounts(value, "skills", "level");
    requirement.items = ReadAmounts(value, "items", "count");
    requirement.worn = ReadAmounts(value, "worn", "count");
    if (value.contains("currency"))
    {
        const auto& currency = value.at("currency");
        requirement.currency = NavRequires_s::Amount_s{.name = currency.at("name").get<std::string>(), .count = currency.at("amount").get<s32>()};
    }

    requirement.questWaivesItems = value.value("questWaivesItems", std::string{});
    if (value.contains("quests"))
    {
        for (const auto& quest : value.at("quests"))
        {
            requirement.quests.push_back({
                .quest = quest.at("quest").get<std::string>(),
                .minStatus = quest.value("minStatus", std::string{}),
                .maxStatus = quest.value("maxStatus", std::string{}),
            });
        }
    }

    requirement.forbidEntranaRestricted = value.value("forbidEntranaRestricted", false);
    requirement.slashTool = value.value("slashTool", false);
    requirement.essenceExitReturn = value.value("essenceExitReturn", std::string{});
}

void from_json(const nlohmann::json& value, NavTeleport_s& teleport)
{
    teleport = NavTeleport_s{
        .id = value.at("teleportId").get<std::string>(),
        .family = value.value("family", std::string{"spell"}),
        .label = value.value("label", std::string{}),
        .to = ReadPoint(value.at("to")),
        .requirement = ReadRequires(value),
    };

    const auto jewellery = teleport.family == "jewellery";
    teleport.cost = value.value("cost", jewellery ? 8 : 10);
    if (value.contains("origin") && value.at("origin").contains("maxWildernessLevel"))
    {
        teleport.maxWildernessLevel = value.at("origin").at("maxWildernessLevel").get<s32>();
    }

    if (value.contains("itemNameMatch"))
    {
        teleport.itemNameMatch = value.at("itemNameMatch").get<std::vector<std::string>>();
    }
}

std::vector<NavEdge_s> NavGraphJson::ReadEdges(const WalkMap& map, std::string_view text)
{
    auto edges = std::vector<NavEdge_s>{};
    WithFile("edges.json", [&]
    {
        for (const auto& entry : Json::parse(text))
        {
            auto edge = NavEdge_s{
                .kind = entry.at("kind").get<std::string>(),
                .from = ReadPoint(entry.at("from")),
                .to = ReadPoint(entry.at("to")),
                .cost = entry.at("cost").get<s32>(),
                .locName = entry.value("locName", std::string{}),
                .action = entry.value("action", std::string{}),
                .locX = entry.value("locX", 0),
                .locZ = entry.value("locZ", 0),
            };

            if (!map.IsWalkable(edge.from.x, edge.from.z, edge.from.level) || !map.IsWalkable(edge.to.x, edge.to.z, edge.to.level))
            {
                continue;
            }

            if (entry.contains("locId"))
            {
                edge.locId = entry.at("locId").get<s32>();
            }

            if (entry.contains("openLocId"))
            {
                edge.openLocId = entry.at("openLocId").get<s32>();
            }

            if (entry.contains("toLevel"))
            {
                edge.toLevel = entry.at("toLevel").get<s32>();
            }

            if (entry.contains("toTile"))
            {
                edge.toTile = std::pair{entry.at("toTile").at("x").get<s32>(), entry.at("toTile").at("z").get<s32>()};
            }

            edge.acceptAnyLanding = entry.value("acceptAnyLanding", false);
            edge.requirement = ReadRequires(entry);

            edges.push_back(std::move(edge));
        }
    });
    return edges;
}

std::vector<NavTeleport_s> NavGraphJson::ReadTeleports(std::string_view text)
{
    auto teleports = std::vector<NavTeleport_s>{};
    WithFile("teleports.json", [&]
    {
        for (const auto& entry : Json::parse(text))
        {
            teleports.push_back(entry.get<NavTeleport_s>());
        }
    });
    return teleports;
}
