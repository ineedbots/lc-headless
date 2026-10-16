#include "pch.hpp"
#include "SearchFilter_s.hpp"

#include "../../Utils/StringUtils.hpp"
#include "../Tile_s.hpp"

bool SearchFilter_s::MatchesType(s32 id, std::string_view name) const
{
    if (!ids.empty() && std::ranges::find(ids, id) == ids.end())
    {
        return false;
    }

    if (names.empty())
    {
        return true;
    }

    return !name.empty() && std::ranges::any_of(names, [name](const std::string& wanted)
    {
        return StringUtils::EqualsIgnoringCase(wanted, name);
    });
}

bool SearchFilter_s::MatchesTile(const Tile_s& centre, const Tile_s& tile) const
{
    return !radius || (tile.level == centre.level && centre.GetDistance(tile) <= *radius);
}

bool SearchFilter_s::Matches(const Tile_s& centre, const Tile_s& tile, s32 id, std::string_view name) const
{
    return MatchesType(id, name) && MatchesTile(centre, tile);
}
