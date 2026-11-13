#pragma once

#include "../Map/WalkMap.hpp"
#include "Type/NavEdge_s.hpp"
#include "Type/NavTeleport_s.hpp"

class NavGraphJson
{
public:
    NavGraphJson() = delete;

    [[nodiscard]] static std::vector<NavEdge_s> ReadEdges(const WalkMap& map, std::string_view text);
    [[nodiscard]] static std::vector<NavTeleport_s> ReadTeleports(std::string_view text);
};
