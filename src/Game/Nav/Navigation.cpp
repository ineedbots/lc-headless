#include "pch.hpp"
#include "Navigation.hpp"

#include "../../Cache/GameCache_s.hpp"
#include "../../Utils/FileUtils.hpp"
#include "../Map/WalkMap.hpp"
#include "NavGraph.hpp"

namespace
{
    std::string ReadFile(const std::filesystem::path& path)
    {
        auto text = FileUtils::ReadText(path);
        if (!text)
        {
            throw std::runtime_error{std::format("{}: can't be read", path.string())};
        }

        return std::move(*text);
    }
}

Navigation::Navigation(const GameCache_s& cache, const std::filesystem::path& directory)
    : m_map{cache}
    , m_graph{m_map, ReadFile(directory / "edges.json"), ReadFile(directory / "teleports.json")}
{
    for (const auto name : DATA_FILES)
    {
        m_data.emplace(std::string{name}, ReadFile(directory / std::format("{}.json", name)));
    }
}

Navigation::Navigation(const GameCache_s& cache, std::string_view edgesJson, std::string_view teleportsJson)
    : m_map{cache}
    , m_graph{m_map, edgesJson, teleportsJson}
{
}

const WalkMap& Navigation::GetMap() const
{
    return m_map;
}

const NavGraph& Navigation::GetGraph() const
{
    return m_graph;
}

std::optional<std::string_view> Navigation::GetData(std::string_view name) const
{
    const auto found = m_data.find(std::string{name});
    if (found == m_data.end())
    {
        return std::nullopt;
    }

    return std::string_view{found->second};
}
