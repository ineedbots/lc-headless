#include "pch.hpp"
#include "NavGraph.hpp"

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

    s32 QuestRank(std::string_view status)
    {
        if (status == "complete")
        {
            return 2;
        }

        return status == "started" ? 1 : 0;
    }

    s32 Count(const std::unordered_map<std::string, s32>& counts, std::string_view name)
    {
        const auto found = counts.find(Lower(name));
        return found == counts.end() ? 0 : found->second;
    }

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

        const auto& source = *found;
        auto requirement = NavRequires_s{};
        requirement.members = source.value("members", false);
        if (source.contains("freeSlots"))
        {
            requirement.freeSlots = source.at("freeSlots").get<s32>();
        }

        requirement.skills = ReadAmounts(source, "skills", "level");
        requirement.items = ReadAmounts(source, "items", "count");
        requirement.worn = ReadAmounts(source, "worn", "count");
        if (source.contains("currency"))
        {
            const auto& currency = source.at("currency");
            requirement.currency = NavRequires_s::Amount_s{.name = currency.at("name").get<std::string>(), .count = currency.at("amount").get<s32>()};
        }

        requirement.questWaivesItems = source.value("questWaivesItems", std::string{});
        if (source.contains("quests"))
        {
            for (const auto& quest : source.at("quests"))
            {
                requirement.quests.push_back({
                    .quest = quest.at("quest").get<std::string>(),
                    .minStatus = quest.value("minStatus", std::string{}),
                    .maxStatus = quest.value("maxStatus", std::string{}),
                });
            }
        }

        requirement.forbidEntranaRestricted = source.value("forbidEntranaRestricted", false);
        requirement.slashTool = source.value("slashTool", false);
        return requirement;
    }

    std::string ReadFile(const std::filesystem::path& path)
    {
        auto file = std::ifstream{path, std::ios::binary};
        if (!file)
        {
            throw std::runtime_error{std::format("{}: can't be read", path.string())};
        }

        return {std::istreambuf_iterator<char>{file}, std::istreambuf_iterator<char>{}};
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

bool NavRect_s::Contains(s32 x, s32 z, s32 tileLevel) const
{
    return x >= minX && x <= maxX && z >= minZ && z <= maxZ && (!level || *level == tileLevel);
}

bool NavRequires_s::IsGated() const
{
    return members || freeSlots || !skills.empty() || !items.empty() || !worn.empty() || currency || !questWaivesItems.empty() || !quests.empty() || forbidEntranaRestricted || slashTool;
}

std::optional<std::string> NavRequires_s::Check(const NavState_s& state) const
{
    if (members && !state.members)
    {
        return "members-only";
    }

    if (freeSlots && state.freeSlots < *freeSlots)
    {
        return std::format("need {} free inventory slots (have {})", *freeSlots, state.freeSlots);
    }

    for (const auto& skill : skills)
    {
        const auto have = Count(state.skills, skill.name);
        if (have < skill.count)
        {
            return std::format("need {} {} (have {})", skill.name, skill.count, have);
        }
    }

    const auto waived = !questWaivesItems.empty() && [&]
    {
        const auto found = state.quests.find(Lower(questWaivesItems));
        return found != state.quests.end() && found->second == "complete";
    }();

    if (currency && !waived && Count(state.items, currency->name) < currency->count)
    {
        return std::format("need {} {} (have {})", currency->count, currency->name, Count(state.items, currency->name));
    }

    for (const auto& item : items)
    {
        if (!waived && Count(state.items, item.name) < item.count)
        {
            return std::format("need {} {} (have {})", item.count, item.name, Count(state.items, item.name));
        }
    }

    for (const auto& item : worn)
    {
        if (Count(state.worn, item.name) < item.count)
        {
            return std::format("need to wear {}", item.name);
        }
    }

    if (forbidEntranaRestricted && state.entranaRestrictedGear)
    {
        return "remove weapons and armour before Entrana";
    }

    if (slashTool && state.canSlashWeb == false)
    {
        return "need a knife or a bladed weapon to slash webs";
    }

    for (const auto& quest : quests)
    {
        const auto found = state.quests.find(Lower(quest.quest));
        const auto status = found == state.quests.end() ? std::string{"unknown"} : found->second;
        if (status == "unknown" && !quest.maxStatus.empty())
        {
            return std::format("need to know where {} stands", quest.quest);
        }

        if (!quest.maxStatus.empty() && QuestRank(status) > QuestRank(quest.maxStatus))
        {
            return std::format("need {} at most {} (it's {})", quest.quest, quest.maxStatus, status);
        }

        if (!quest.minStatus.empty() && QuestRank(status) < QuestRank(quest.minStatus))
        {
            return std::format("need {} {} (it's {})", quest.quest, quest.minStatus, status);
        }
    }

    return std::nullopt;
}

NavGraph::NavGraph(const WalkMap& map, const std::filesystem::path& directory)
{
    const auto edges = ReadFile(directory / "edges.json");
    const auto teleports = ReadFile(directory / "teleports.json");
    Load(map, edges, teleports);
}

NavGraph::NavGraph(const WalkMap& map, std::string_view edgesJson, std::string_view teleportsJson)
{
    Load(map, edgesJson, teleportsJson);
}

void NavGraph::Load(const WalkMap& map, std::string_view edgesJson, std::string_view teleportsJson)
{
    WithFile("edges.json", [&]
    {
        for (const auto& entry : Json::parse(edgesJson))
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
            const auto span = std::max(std::abs(edge.to.x - edge.from.x), std::abs(edge.to.z - edge.from.z));
            m_longEdges = m_longEdges || span > edge.cost;
            m_doors += edge.kind == "door" ? 1 : 0;
            m_edges.push_back(std::move(edge));
        }
    });

    for (const auto& edge : m_edges)
    {
        m_from[GetNodeId(edge.from.x, edge.from.z, edge.from.level)].push_back(&edge);
    }

    WithFile("teleports.json", [&]
    {
        for (const auto& entry : Json::parse(teleportsJson))
        {
            auto teleport = NavTeleport_s{
                .id = entry.at("teleportId").get<std::string>(),
                .family = entry.value("family", std::string{"spell"}),
                .label = entry.value("label", std::string{}),
                .to = ReadPoint(entry.at("to")),
                .requirement = ReadRequires(entry),
            };

            const auto jewellery = teleport.family == "jewellery";
            teleport.cost = entry.value("cost", jewellery ? 8 : 10);
            if (entry.contains("origin") && entry.at("origin").contains("maxWildernessLevel"))
            {
                teleport.maxWildernessLevel = entry.at("origin").at("maxWildernessLevel").get<s32>();
            }

            if (entry.contains("itemNameMatch"))
            {
                teleport.itemNameMatch = entry.at("itemNameMatch").get<std::vector<std::string>>();
            }

            m_teleports.push_back(std::move(teleport));
        }
    });
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

Navigation_s::Navigation_s(const GameCache_s& cache, const std::filesystem::path& directory)
    : map{cache}
    , graph{map, directory}
{
    for (const auto name : DATA_FILES)
    {
        data.emplace(std::string{name}, ReadFile(directory / std::format("{}.json", name)));
    }
}

Navigation_s::Navigation_s(const GameCache_s& cache, std::string_view edgesJson, std::string_view teleportsJson)
    : map{cache}
    , graph{map, edgesJson, teleportsJson}
{
}

std::optional<std::string_view> Navigation_s::GetData(std::string_view name) const
{
    const auto found = data.find(std::string{name});
    if (found == data.end())
    {
        return std::nullopt;
    }

    return std::string_view{found->second};
}
