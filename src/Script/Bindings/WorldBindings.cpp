#include "pch.hpp"
#include "WorldBindings.hpp"

#include "../../Cache/GameCache_s.hpp"
#include "../../Cache/MapSquare.hpp"
#include "../../Game/Map/WorldMap.hpp"
#include "../../Game/Query/EntityQuery.hpp"
#include "../../Game/Tile_s.hpp"
#include "../Convert/PyArgs.hpp"
#include "../Convert/PyObjects.hpp"
#include "../Convert/PyValue.hpp"
#include "../ScriptContext.hpp"
#include "BindingSupport.hpp"

#include <pocketpy.h>

namespace
{
    constexpr auto MAX_LEVEL = s64{MapSquare::LEVELS - 1};

    constexpr auto MAX_SQUARE = s64{MapSquare::MAX_SQUARE};

    bool GetNpcs(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            PyValue::FromList(py_retval(), BindingSupport::GetContext().GetEntities().GetNpcs(PyArgs::ToSearch(py_arg(0), py_arg(1), py_arg(2))), BindingSupport::FromNpc);
            return true;
        });
    }

    bool GetNearestNpcById(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto inCombat = PyValue::ToOptionalBool(py_arg(2), "in_combat");
            const auto reachable = PyValue::ToBool(py_arg(3), "reachable");
            PyValue::FromOptional(py_retval(), BindingSupport::GetContext().GetEntities().GetNearestNpc(PyArgs::ToFilter(py_arg(0), py_arg(1)), inCombat, reachable), BindingSupport::FromNpc);
            return true;
        });
    }

    bool GetNearestNpcByName(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto inCombat = PyValue::ToOptionalBool(py_arg(2), "in_combat");
            const auto reachable = PyValue::ToBool(py_arg(3), "reachable");
            PyValue::FromOptional(py_retval(), BindingSupport::GetContext().GetEntities().GetNearestNpc(PyArgs::ToNameFilter(py_arg(0), py_arg(1)), inCombat, reachable), BindingSupport::FromNpc);
            return true;
        });
    }

    bool GetNpc(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            PyValue::FromOptional(py_retval(), BindingSupport::GetContext().GetEntities().GetNpc(PyValue::ToU16(py_arg(0), "index")), BindingSupport::FromNpc);
            return true;
        });
    }

    bool GetPlayers(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            PyValue::FromList(py_retval(), BindingSupport::GetContext().GetEntities().GetPlayers(PyArgs::ToRadius(py_arg(0))), BindingSupport::FromPlayer);
            return true;
        });
    }

    bool GetPlayerByName(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            PyValue::FromOptional(py_retval(), BindingSupport::GetContext().GetEntities().GetPlayerByName(PyValue::ToString(py_arg(0), "name")), BindingSupport::FromPlayer);
            return true;
        });
    }

    bool GetGroundItems(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            PyValue::FromList(py_retval(), BindingSupport::GetContext().GetEntities().GetGroundItems(PyArgs::ToSearch(py_arg(0), py_arg(1), py_arg(2))), BindingSupport::FromGroundItem);
            return true;
        });
    }

    bool GetNearestGroundItemById(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto reachable = PyValue::ToBool(py_arg(2), "reachable");
            PyValue::FromOptional(py_retval(), BindingSupport::GetContext().GetEntities().GetNearestGroundItem(PyArgs::ToFilter(py_arg(0), py_arg(1)), reachable), BindingSupport::FromGroundItem);
            return true;
        });
    }

    bool GetNearestGroundItemByName(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto reachable = PyValue::ToBool(py_arg(2), "reachable");
            PyValue::FromOptional(py_retval(), BindingSupport::GetContext().GetEntities().GetNearestGroundItem(PyArgs::ToNameFilter(py_arg(0), py_arg(1)), reachable), BindingSupport::FromGroundItem);
            return true;
        });
    }

    bool GetLocAt(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
            const auto loc = context.GetEntities().GetLocAt(context.ToTile(PyArgs::ToCoord(py_arg(0), "x"), PyArgs::ToCoord(py_arg(1), "z")), PyArgs::ToLayer(py_arg(2)));
            PyValue::FromOptional(py_retval(), loc, BindingSupport::FromLoc);
            return true;
        });
    }

    bool GetLocs(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            PyValue::FromList(py_retval(), BindingSupport::GetContext().GetEntities().GetLocs(PyArgs::ToSearch(py_arg(0), py_arg(1), py_arg(3)), PyArgs::ToLayer(py_arg(2))), BindingSupport::FromLoc);
            return true;
        });
    }

    bool GetNearestLocById(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto reachable = PyValue::ToBool(py_arg(3), "reachable");
            const auto loc = BindingSupport::GetContext().GetEntities().GetNearestLoc(PyArgs::ToFilter(py_arg(0), py_arg(1)), PyArgs::ToLayer(py_arg(2)), reachable);
            PyValue::FromOptional(py_retval(), loc, BindingSupport::FromLoc);
            return true;
        });
    }

    bool GetNearestLocByName(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto reachable = PyValue::ToBool(py_arg(3), "reachable");
            const auto loc = BindingSupport::GetContext().GetEntities().GetNearestLoc(PyArgs::ToNameFilter(py_arg(0), py_arg(1)), PyArgs::ToLayer(py_arg(2)), reachable);
            PyValue::FromOptional(py_retval(), loc, BindingSupport::FromLoc);
            return true;
        });
    }

    bool GetNpcType(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto& cache = BindingSupport::GetContext().GetCache();
            const auto* const type = cache.FindNpc(static_cast<s32>(PyValue::ToInt(py_arg(0), "id")));
            if (type == nullptr)
            {
                return BindingSupport::ReturnNone();
            }

            PyObjects::FromNpcType(py_retval(), *type, cache);
            return true;
        });
    }

    // The ids of the cache's types of that kind ('item', 'npc' or 'loc') with the name, matched without regard to case.
    bool FindTypeIds(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto& cache = BindingSupport::GetContext().GetCache();
            const auto kind = PyValue::ToString(py_arg(0), "kind");
            const auto name = PyValue::ToString(py_arg(1), "name");
            auto ids = std::vector<s32>{};
            if (kind == "item")
            {
                ids = cache.FindObjIds(name);
            }
            else if (kind == "npc")
            {
                ids = cache.FindNpcIds(name);
            }
            else if (kind == "loc")
            {
                ids = cache.FindLocIds(name);
            }
            else
            {
                throw std::invalid_argument{std::format("kind must be 'item', 'npc' or 'loc', not '{}'", kind)};
            }

            PyValue::FromList(py_retval(), ids, [](py_OutRef out, s32 id)
            {
                py_newint(out, id);
            });
            return true;
        });
    }

    bool GetItemType(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto& cache = BindingSupport::GetContext().GetCache();
            const auto* const type = cache.FindObj(static_cast<s32>(PyValue::ToInt(py_arg(0), "id")));
            if (type == nullptr)
            {
                return BindingSupport::ReturnNone();
            }

            PyObjects::FromItemType(py_retval(), *type, cache);
            return true;
        });
    }

    // Every named obj, as (id, name, value, stackable, members, equippable, note_of, stack_variant) with note_of
    // -1 for an obj that isn't a note: the market's catalog, built once, without an ItemType for each.
    bool GetItemCatalog(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            const auto& cache = BindingSupport::GetContext().GetCache();
            auto named = std::vector<const ObjType_s*>{};
            for (const auto& type : cache.objs)
            {
                if (!type.name.empty())
                {
                    named.push_back(&type);
                }
            }

            PyValue::FromList(py_retval(), named, [](py_OutRef out, const ObjType_s* type)
            {
                constexpr auto FIELDS = 8;
                py_newtuple(out, FIELDS);
                py_newint(py_tuple_getitem(out, 0), type->id);
                PyValue::FromString(py_tuple_getitem(out, 1), type->name);
                py_newint(py_tuple_getitem(out, 2), type->cost);
                py_newbool(py_tuple_getitem(out, 3), type->stackable);
                py_newbool(py_tuple_getitem(out, 4), type->members);
                py_newbool(py_tuple_getitem(out, 5), type->equippable);
                py_newint(py_tuple_getitem(out, 6), type->noteOf ? s32{*type->noteOf} : -1);
                py_newbool(py_tuple_getitem(out, 7), type->stackVariant);
            });
            return true;
        });
    }

    bool GetLocType(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto& cache = BindingSupport::GetContext().GetCache();
            const auto* const type = cache.FindLoc(static_cast<s32>(PyValue::ToInt(py_arg(0), "id")));
            if (type == nullptr)
            {
                return BindingSupport::ReturnNone();
            }

            PyObjects::FromLocType(py_retval(), *type, cache);
            return true;
        });
    }

    // Whether the tile, on your level, is in the area the server has loaded.
    bool InScene(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
            const auto x = static_cast<s32>(PyValue::ToInt(py_arg(0), "x", 0, Tile_s::MAX_COORD));
            const auto z = static_cast<s32>(PyValue::ToInt(py_arg(1), "z", 0, Tile_s::MAX_COORD));
            return BindingSupport::ReturnBool(context.GetMap().Contains(context.ToTile(x, z)));
        });
    }

    // (lx, lz, id, shape, angle) for each of a map square's locs on a level, as the cache has them.
    bool GetSquareLocs(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto& cache = BindingSupport::GetContext().GetCache();
            const auto* const square = cache.FindSquare(static_cast<s32>(PyValue::ToInt(py_arg(0), "x", 0, MAX_SQUARE)), static_cast<s32>(PyValue::ToInt(py_arg(1), "z", 0, MAX_SQUARE)));
            const auto level = static_cast<s32>(PyValue::ToInt(py_arg(2), "level", 0, MAX_LEVEL));
            auto locs = std::vector<MapLoc_s>{};
            if (square != nullptr)
            {
                for (const auto& loc : square->GetLocs())
                {
                    if (loc.GetLevel() == level)
                    {
                        locs.push_back(loc);
                    }
                }
            }

            PyValue::FromList(py_retval(), locs, [](py_OutRef out, const MapLoc_s& loc)
            {
                constexpr auto FIELDS = 5;
                py_newtuple(out, FIELDS);
                py_newint(py_tuple_getitem(out, 0), loc.GetX());
                py_newint(py_tuple_getitem(out, 1), loc.GetZ());
                py_newint(py_tuple_getitem(out, 2), loc.id);
                py_newint(py_tuple_getitem(out, 3), loc.GetShape());
                py_newint(py_tuple_getitem(out, 4), loc.GetAngle());
            });
            return true;
        });
    }
}

void WorldBindings::Add(std::vector<BoundFunction_s>& functions)
{
    functions.insert(functions.end(), {
                                          {"get_npcs(ids=None, radius=None, names=None)", GetNpcs},
                                          {"get_nearest_npc_by_id(ids=None, radius=None, in_combat=None, reachable=False)", GetNearestNpcById},
                                          {"get_nearest_npc_by_name(names, radius=None, in_combat=None, reachable=False)", GetNearestNpcByName},
                                          {"get_npc(index)", GetNpc},
                                          {"get_players(radius=None)", GetPlayers},
                                          {"get_player_by_name(name)", GetPlayerByName},
                                          {"get_ground_items(ids=None, radius=None, names=None)", GetGroundItems},
                                          {"get_nearest_ground_item_by_id(ids=None, radius=None, reachable=False)", GetNearestGroundItemById},
                                          {"get_nearest_ground_item_by_name(names, radius=None, reachable=False)", GetNearestGroundItemByName},
                                          {"get_loc_at(x, z, layer=None)", GetLocAt},
                                          {"get_locs(ids=None, radius=None, layer=None, names=None)", GetLocs},
                                          {"get_nearest_loc_by_id(ids=None, radius=None, layer=None, reachable=False)", GetNearestLocById},
                                          {"get_nearest_loc_by_name(names, radius=None, layer=None, reachable=False)", GetNearestLocByName},
                                          {"get_npc_type(id)", GetNpcType},
                                          {"get_item_type(id)", GetItemType},
                                          {"get_item_catalog()", GetItemCatalog},
                                          {"get_loc_type(id)", GetLocType},
                                          {"find_type_ids(kind, name)", FindTypeIds},
                                          {"square_locs(x, z, level)", GetSquareLocs},
                                          {"in_scene(x, z)", InScene},
                                      });
}
