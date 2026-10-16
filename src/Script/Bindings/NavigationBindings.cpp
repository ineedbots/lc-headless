#include "pch.hpp"
#include "NavigationBindings.hpp"

#include "../../Cache/MapSquare.hpp"
#include "../../Game/Nav/NavJson.hpp"
#include "../../Game/Nav/Navigation.hpp"
#include "../../Game/Nav/WorldPathFinder.hpp"
#include "../../Game/Query/ReachQuery.hpp"
#include "../../Game/Tile_s.hpp"
#include "../Convert/PyArgs.hpp"
#include "../Convert/PyValue.hpp"
#include "../ScriptContext.hpp"
#include "../ScriptVm.hpp"
#include "BindingSupport.hpp"

#include <pocketpy.h>

namespace
{
    constexpr auto MAX_LEVEL = s64{MapSquare::LEVELS - 1};

    bool CanReachEntity(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
            return BindingSupport::ReturnBool(context.GetReach().CanReachEntity(context.ToTile(PyArgs::ToCoord(py_arg(0), "x"), PyArgs::ToCoord(py_arg(1), "z"))));
        });
    }

    bool CanReachGroundItem(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
            return BindingSupport::ReturnBool(context.GetReach().CanReachGroundItem(context.ToTile(PyArgs::ToCoord(py_arg(0), "x"), PyArgs::ToCoord(py_arg(1), "z"))));
        });
    }

    bool CanReachLoc(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
            return BindingSupport::ReturnBool(context.GetReach().CanReachLoc(context.ToTile(PyArgs::ToCoord(py_arg(1), "x"), PyArgs::ToCoord(py_arg(2), "z")), PyValue::ToU16(py_arg(0), "id")));
        });
    }

    bool IsReachable(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto& context = BindingSupport::GetContext();
            return BindingSupport::ReturnBool(context.GetReach().IsReachable(context.ToTile(PyArgs::ToCoord(py_arg(0), "x"), PyArgs::ToCoord(py_arg(1), "z"))));
        });
    }

    bool FindPath(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto& context = BindingSupport::GetContext();
            const auto path = context.GetReach().FindPath(context.ToTile(PyArgs::ToCoord(py_arg(0), "x"), PyArgs::ToCoord(py_arg(1), "z")));
            PyValue::FromOptional(py_retval(), path, [](py_OutRef out, const std::vector<Tile_s>& waypoints)
            {
                PyValue::FromList(out, waypoints, BindingSupport::FromTile);
            });
            return true;
        });
    }

    bool CanStep(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto coord = [argv](int index, std::string_view name)
            {
                return static_cast<s32>(PyValue::ToInt(py_arg(index), name, 0, Tile_s::MAX_COORD));
            };

            const auto& context = BindingSupport::GetContext();
            return BindingSupport::ReturnBool(context.GetReach().CanStep(context.ToTile(coord(0, "from_x"), coord(1, "from_z")), context.ToTile(coord(2, "to_x"), coord(3, "to_z"))));
        });
    }

    // A route across the world, as NavJson describes the request and the answer; None without navigation.
    bool FindWorldPath(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto request = NavJson::ParseRequest(PyValue::ToString(py_arg(0), "request"));
            const auto path = ScriptVm::GetCurrent().RunRouteSearch([&request]
            {
                const auto* const navigation = BindingSupport::GetContext().GetNavigation();
                return navigation == nullptr ? std::nullopt : std::optional{WorldPathFinder::FindPath(*navigation, request.from, request.to, request.options)};
            });
            if (!path)
            {
                return BindingSupport::ReturnNone();
            }

            PyValue::FromString(py_retval(), NavJson::ToJson(*path));
            return true;
        });
    }

    // One of the walker's data files as JSON text, or None without navigation.
    bool GetNavData(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto* const navigation = BindingSupport::GetContext().GetNavigation();
            const auto name = PyValue::ToString(py_arg(0), "name");
            const auto text = navigation != nullptr ? navigation->GetData(name) : std::nullopt;
            if (!text)
            {
                return BindingSupport::ReturnNone();
            }

            PyValue::FromString(py_retval(), *text);
            return true;
        });
    }

    // (walkable, exits) for a tile of the world map, or None without navigation.
    bool GetWalkTile(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto* const navigation = BindingSupport::GetContext().GetNavigation();
            const auto x = static_cast<s32>(PyValue::ToInt(py_arg(0), "x", 0, Tile_s::MAX_COORD));
            const auto z = static_cast<s32>(PyValue::ToInt(py_arg(1), "z", 0, Tile_s::MAX_COORD));
            const auto level = static_cast<s32>(PyValue::ToInt(py_arg(2), "level", 0, MAX_LEVEL));
            if (navigation == nullptr)
            {
                return BindingSupport::ReturnNone();
            }

            PyValue::FromPoint(py_retval(), navigation->GetMap().IsWalkable(x, z, level) ? 1 : 0, navigation->GetMap().GetExits(x, z, level));
            return true;
        });
    }
}

void NavigationBindings::Add(std::vector<BoundFunction_s>& functions)
{
    functions.insert(functions.end(), {
                                          {"can_reach_entity(x, z)", CanReachEntity},
                                          {"can_reach_ground_item(x, z)", CanReachGroundItem},
                                          {"can_reach_loc(id, x, z)", CanReachLoc},
                                          {"is_reachable(x, z)", IsReachable},
                                          {"find_path(x, z)", FindPath},
                                          {"find_world_path(request)", FindWorldPath},
                                          {"nav_data(name)", GetNavData},
                                          {"walk_tile(x, z, level)", GetWalkTile},
                                          {"can_step(from_x, from_z, to_x, to_z)", CanStep},
                                      });
}
