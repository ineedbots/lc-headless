#pragma once

#include "../Tile_s.hpp"

// Empty id and name lists match anything. Names match a type's name without regard to case, and a type
// with no name never matches one. A radius counts tiles from the centre, on its level.
struct SearchFilter_s
{
    std::vector<s32> ids;
    std::vector<std::string> names;
    std::optional<s32> radius;

    [[nodiscard]] bool MatchesType(s32 id, std::string_view name) const;
    [[nodiscard]] bool MatchesTile(const Tile_s& centre, const Tile_s& tile) const;
    [[nodiscard]] bool Matches(const Tile_s& centre, const Tile_s& tile, s32 id, std::string_view name) const;
};
