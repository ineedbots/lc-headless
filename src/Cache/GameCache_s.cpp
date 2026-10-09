#include "pch.hpp"
#include "GameCache_s.hpp"

#include "LocType_s.hpp"
#include "MapSquare.hpp"
#include "NpcType_s.hpp"
#include "ObjType_s.hpp"
#include "TextPool.hpp"

namespace
{
    constexpr auto MAX_SQUARE_COORD = 0xFF;

    template <typename T>
    const T* FindType(const std::vector<T>& types, s32 id)
    {
        if (id < 0 || static_cast<std::size_t>(id) >= types.size())
        {
            return nullptr;
        }

        return &types[static_cast<std::size_t>(id)];
    }
}

const LocType_s* GameCache_s::FindLoc(s32 id) const
{
    return FindType(locs, id);
}

const NpcType_s* GameCache_s::FindNpc(s32 id) const
{
    return FindType(npcs, id);
}

const ObjType_s* GameCache_s::FindObj(s32 id) const
{
    return FindType(objs, id);
}

std::string_view GameCache_s::GetOption(u16 id) const
{
    return text.GetOption(id);
}

const MapSquare* GameCache_s::FindSquare(s32 squareX, s32 squareZ) const
{
    if (squareX < 0 || squareX > MAX_SQUARE_COORD || squareZ < 0 || squareZ > MAX_SQUARE_COORD)
    {
        return nullptr;
    }

    const auto found = squares.find(MapSquare::GetId(squareX, squareZ));
    if (found == squares.end())
    {
        return nullptr;
    }

    return &found->second;
}
