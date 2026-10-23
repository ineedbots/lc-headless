#include "pch.hpp"
#include "GameCache_s.hpp"

#include "../Utils/StringUtils.hpp"
#include "LocType_s.hpp"
#include "MapSquare.hpp"
#include "NpcType_s.hpp"
#include "ObjType_s.hpp"
#include "TextPool.hpp"

namespace
{
    template <typename T>
    const T* FindType(const std::vector<T>& types, s32 id)
    {
        if (id < 0 || static_cast<std::size_t>(id) >= types.size())
        {
            return nullptr;
        }

        return &types[static_cast<std::size_t>(id)];
    }

    template <typename T>
    std::string_view FindName(const std::vector<T>& types, s32 id)
    {
        const auto* const type = FindType(types, id);
        return type == nullptr ? std::string_view{} : type->name;
    }

    template <typename T>
    std::vector<s32> FindIds(const std::vector<T>& types, std::string_view name)
    {
        auto ids = std::vector<s32>{};
        for (const auto& type : types)
        {
            if (!type.name.empty() && StringUtils::EqualsIgnoringCase(type.name, name))
            {
                ids.push_back(type.id);
            }
        }

        return ids;
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

std::optional<u32> GameCache_s::FindSeqLength(s32 id) const
{
    if (id < 0 || static_cast<std::size_t>(id) >= seqLengths.size())
    {
        return std::nullopt;
    }

    return seqLengths[static_cast<std::size_t>(id)];
}

std::string_view GameCache_s::FindLocName(s32 id) const
{
    return FindName(locs, id);
}

std::string_view GameCache_s::FindNpcName(s32 id) const
{
    return FindName(npcs, id);
}

std::string_view GameCache_s::FindObjName(s32 id) const
{
    return FindName(objs, id);
}

std::vector<s32> GameCache_s::FindLocIds(std::string_view name) const
{
    return FindIds(locs, name);
}

std::vector<s32> GameCache_s::FindNpcIds(std::string_view name) const
{
    return FindIds(npcs, name);
}

std::vector<s32> GameCache_s::FindObjIds(std::string_view name) const
{
    return FindIds(objs, name);
}

const IfComponent_s* GameCache_s::FindComponent(s32 id) const
{
    if (id < 0)
    {
        return nullptr;
    }

    const auto found = components.find(static_cast<u16>(id));
    return found == components.end() ? nullptr : &found->second;
}

std::string_view GameCache_s::GetOption(u16 id) const
{
    return text.GetOption(id);
}

const MapSquare* GameCache_s::FindSquare(s32 squareX, s32 squareZ) const
{
    if (squareX < 0 || squareX > MapSquare::MAX_SQUARE || squareZ < 0 || squareZ > MapSquare::MAX_SQUARE)
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
