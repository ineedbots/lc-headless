#include "pch.hpp"
#include "PlayerBindings.hpp"

#include "../../Game/Query/PlayerQuery.hpp"
#include "../../Game/State/EntityStatus.hpp"
#include "../../Game/State/GameState_s.hpp"
#include "../../Game/State/Player_s.hpp"
#include "../../Game/State/Stat_e.hpp"
#include "../../Game/State/Stat_s.hpp"
#include "../../Game/Tile_s.hpp"
#include "../Convert/PyArgs.hpp"
#include "../Convert/PyValue.hpp"
#include "../ScriptContext.hpp"
#include "BindingSupport.hpp"

#include <pocketpy.h>

namespace
{
    constexpr auto MAX_DAMAGE_TICKS = 1000;

    bool GetTick(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(static_cast<s64>(BindingSupport::GetContext().GetState().tick));
        });
    }

    bool IsPlaced(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetState().placed);
        });
    }

    bool IsMembers(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetState().members);
        });
    }

    bool GetX(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetPosition().x);
        });
    }

    bool GetZ(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetPosition().z);
        });
    }

    bool GetLevel(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetPosition().level);
        });
    }

    bool GetPosition(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            const auto position = BindingSupport::GetContext().GetPosition();
            PyValue::FromPoint(py_retval(), position.x, position.z);
            return true;
        });
    }

    bool DistanceTo(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
            return BindingSupport::ReturnInt(context.GetPosition().GetDistance(context.ToTile(PyArgs::ToCoord(py_arg(0), "x"), PyArgs::ToCoord(py_arg(1), "z"))));
        });
    }

    bool Distance(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto from = Tile_s{.x = PyArgs::ToCoord(py_arg(0), "x1"), .z = PyArgs::ToCoord(py_arg(1), "z1")};
            const auto to = Tile_s{.x = PyArgs::ToCoord(py_arg(2), "x2"), .z = PyArgs::ToCoord(py_arg(3), "z2")};
            return BindingSupport::ReturnInt(from.GetDistance(to));
        });
    }

    bool InRadiusOf(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
            const auto centre = context.ToTile(PyArgs::ToCoord(py_arg(0), "x"), PyArgs::ToCoord(py_arg(1), "z"));
            return BindingSupport::ReturnBool(context.GetPosition().GetDistance(centre) <= PyValue::ToInt(py_arg(2), "radius"));
        });
    }

    bool InRect(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto x = PyArgs::ToCoord(py_arg(0), "x");
            const auto z = PyArgs::ToCoord(py_arg(1), "z");
            const auto width = PyValue::ToInt(py_arg(2), "width");
            const auto height = PyValue::ToInt(py_arg(3), "height");
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetPosition().IsInRect(x, z, width, height));
        });
    }

    bool At(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
            return BindingSupport::ReturnBool(context.GetPosition() == context.ToTile(PyArgs::ToCoord(py_arg(0), "x"), PyArgs::ToCoord(py_arg(1), "z")));
        });
    }

    bool GetPid(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetState().pid);
        });
    }

    bool GetName(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            const auto& appearance = BindingSupport::GetContext().GetLocalPlayer().appearance;
            return appearance ? BindingSupport::ReturnString(appearance->name) : BindingSupport::ReturnNone();
        });
    }

    bool GetCombatLevel(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            const auto& appearance = BindingSupport::GetContext().GetLocalPlayer().appearance;
            return BindingSupport::ReturnInt(appearance ? appearance->combatLevel : 0);
        });
    }

    bool GetRunEnergy(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetState().runEnergy);
        });
    }

    bool GetWeight(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetState().runWeight);
        });
    }

    bool IsMoving(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetPlayer().IsMoving());
        });
    }

    bool GetWalkDestination(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            PyValue::FromOptional(py_retval(), BindingSupport::GetContext().GetState().walkDestination, [](py_OutRef out, const Tile_s& tile)
            {
                PyValue::FromPoint(out, tile.x, tile.z);
            });
            return true;
        });
    }

    bool InCombat(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetPlayer().InCombat());
        });
    }

    bool IsRunning(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetPlayer().IsRunning());
        });
    }

    // Whether a hit that did damage landed on you within the last ticks.
    bool TookDamage(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
            const auto ticks = static_cast<u64>(PyValue::ToInt(py_arg(0), "ticks", 0, MAX_DAMAGE_TICKS));
            return BindingSupport::ReturnBool(EntityStatus::TookDamage(context.GetLocalPlayer(), context.GetState().tick, ticks));
        });
    }

    bool GetLocalPlayer(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            BindingSupport::FromPlayer(py_retval(), BindingSupport::GetContext().GetLocalPlayer());
            return true;
        });
    }

    const Stat_s& GetStatArgument(py_StackRef argv)
    {
        return BindingSupport::GetContext().GetPlayer().GetStat(static_cast<s32>(PyValue::ToInt(py_arg(0), "stat")));
    }

    bool GetCurrentStat(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            return BindingSupport::ReturnInt(GetStatArgument(argv).level);
        });
    }

    bool GetMaxStat(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            return BindingSupport::ReturnInt(GetStatArgument(argv).baseLevel);
        });
    }

    bool GetExperience(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            return BindingSupport::ReturnInt(GetStatArgument(argv).xp);
        });
    }

    bool GetHp(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetState().GetStat(Stat_e::Hitpoints).level);
        });
    }

    bool GetMaxHp(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetState().GetStat(Stat_e::Hitpoints).baseLevel);
        });
    }

    bool GetHpPercent(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetState().GetStat(Stat_e::Hitpoints).GetPercent());
        });
    }

    bool GetVarp(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetState().GetVarp(PyValue::ToU16(py_arg(0), "id")));
        });
    }
}

void PlayerBindings::Add(std::vector<BoundFunction_s>& functions)
{
    functions.insert(functions.end(), {
                                          {"is_placed()", IsPlaced},
                                          {"tick()", GetTick},
                                          {"get_tick()", GetTick},
                                          {"get_x()", GetX},
                                          {"get_z()", GetZ},
                                          {"get_level()", GetLevel},
                                          {"get_position()", GetPosition},
                                          {"get_pid()", GetPid},
                                          {"get_name()", GetName},
                                          {"get_combat_level()", GetCombatLevel},
                                          {"get_run_energy()", GetRunEnergy},
                                          {"get_weight()", GetWeight},
                                          {"is_moving()", IsMoving},
                                          {"get_walk_destination()", GetWalkDestination},
                                          {"in_combat()", InCombat},
                                          {"is_running()", IsRunning},
                                          {"get_local_player()", GetLocalPlayer},
                                          {"get_current_stat(stat)", GetCurrentStat},
                                          {"get_max_stat(stat)", GetMaxStat},
                                          {"get_experience(stat)", GetExperience},
                                          {"get_hp()", GetHp},
                                          {"get_max_hp()", GetMaxHp},
                                          {"get_hp_percent()", GetHpPercent},
                                          {"distance_to(x, z)", DistanceTo},
                                          {"distance(x1, z1, x2, z2)", Distance},
                                          {"in_radius_of(x, z, radius)", InRadiusOf},
                                          {"in_rect(x, z, width, height)", InRect},
                                          {"at(x, z)", At},
                                          {"get_varp(id)", GetVarp},
                                          {"is_members()", IsMembers},
                                          {"took_damage(ticks=4)", TookDamage},
                                      });
}
