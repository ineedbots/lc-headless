#pragma once

#include "../../Cache/GameCache_s.hpp"
#include "../Map/WalkMap.hpp"
#include "NavGraph.hpp"

// The world's walking and the graph over it, built once at startup, with the data the stdlib's walker reads
// as JSON: crossings.json (tolls, ships and other special crossings), banks.json and danger_zones.json.
class Navigation
{
public:
    // teleports.json is the graph's too; the stdlib reads its jewellery items and dialogue.
    static constexpr std::array<std::string_view, 4> DATA_FILES = {"crossings", "banks", "danger_zones", "teleports"};

    Navigation(const GameCache_s& cache, const std::filesystem::path& directory);
    // Without the data files, for tests.
    Navigation(const GameCache_s& cache, std::string_view edgesJson, std::string_view teleportsJson);

    [[nodiscard]] const WalkMap& GetMap() const;
    [[nodiscard]] const NavGraph& GetGraph() const;
    // By name without ".json".
    [[nodiscard]] std::optional<std::string_view> GetData(std::string_view name) const;

private:
    WalkMap m_map;
    NavGraph m_graph;
    std::unordered_map<std::string, std::string> m_data;
};
