#include "pch.hpp"
#include "ScriptBindings.hpp"

#include "../../Cache/GameCache_s.hpp"
#include "../../Cache/MapSquare.hpp"
#include "../../Game/Interface/ChatDialog.hpp"
#include "../../Game/Map/WalkMap.hpp"
#include "../../Game/Map/WorldMap.hpp"
#include "../../Game/Menu/MenuOp.hpp"
#include "../../Game/Menu/Menus.hpp"
#include "../../Game/Nav/NavJson.hpp"
#include "../../Game/Nav/Navigation.hpp"
#include "../../Game/Nav/WorldPathFinder.hpp"
#include "../../Game/Protocol/Base37.hpp"
#include "../../Game/Query/EntityQuery.hpp"
#include "../../Game/Query/InventoryItem_s.hpp"
#include "../../Game/Query/InventoryQuery.hpp"
#include "../../Game/Query/PlayerQuery.hpp"
#include "../../Game/Query/ReachQuery.hpp"
#include "../../Game/Query/SearchFilter_s.hpp"
#include "../../Game/State/EntityStatus.hpp"
#include "../../Game/State/GameState_s.hpp"
#include "../../Game/State/Npc_s.hpp"
#include "../../Game/State/Player_s.hpp"
#include "../../Game/State/Social_s.hpp"
#include "../../Game/State/Stat_e.hpp"
#include "../../Game/State/Stat_s.hpp"
#include "../../Game/State/Zone_s.hpp"
#include "../../Game/Tile_s.hpp"
#include "../../Utils/StringUtils.hpp"
#include "../Convert/PyArgs.hpp"
#include "../Convert/PyObjects.hpp"
#include "../Convert/PyValue.hpp"
#include "../Error/ScriptRaisedError.hpp"
#include "../Error/ScriptTypeError.hpp"
#include "../ScriptActions.hpp"
#include "../ScriptContext.hpp"
#include "../ScriptControl.hpp"
#include "../ScriptRuntime.hpp"
#include "../ScriptVm.hpp"
#include "../Stdlib.hpp"

#include <pocketpy.h>

namespace
{
    // Run into builtins when the API is bound: helpers the host calls, then the standard library's public
    // names and the runtime's entry points, which CallBuiltin finds there.
    constexpr auto PRELUDE_FILE = "rs2004/_prelude.py"sv;
    constexpr auto LOAD_STDLIB_FILE = "rs2004/_load_stdlib.py"sv;

    constexpr auto LOAD_SETTINGS = "settings = _rt_make_settings(_settings_json)\ndel _settings_json\n"sv;
    constexpr auto CORE_MODULE = "_core";

    // Functions that scripts call directly: the script's own control.
    constexpr auto BUILTIN_FUNCTIONS = std::to_array<std::string_view>({
        "stop_script",
        "stop_account",
        "relog",
        "send_bot_message",
    });
    constexpr auto MAX_RELOG_SECONDS = s64{ScriptControl::MAX_RELOG.count()};
    constexpr auto SETTINGS_JSON = "_settings_json";
    constexpr auto MAX_COORD = s64{Tile_s::MAX_COORD};
    constexpr auto MAX_LEVEL = s64{MapSquare::LEVELS - 1};
    constexpr auto MAX_SQUARE = s64{MapSquare::MAX_SQUARE};
    constexpr auto MAX_DAMAGE_TICKS = 1000;

    struct Constant_s
    {
        const char* name;
        s64 value;
    };

    constexpr s64 StatValue(Stat_e stat)
    {
        return static_cast<s64>(stat);
    }

    constexpr auto CONSTANTS = std::to_array<Constant_s>({
        {"COMBAT_TICKS", static_cast<s64>(EntityStatus::COMBAT_TICKS)},
        {"ATTACK", StatValue(Stat_e::Attack)},
        {"DEFENCE", StatValue(Stat_e::Defence)},
        {"STRENGTH", StatValue(Stat_e::Strength)},
        {"HITPOINTS", StatValue(Stat_e::Hitpoints)},
        {"RANGED", StatValue(Stat_e::Ranged)},
        {"PRAYER", StatValue(Stat_e::Prayer)},
        {"MAGIC", StatValue(Stat_e::Magic)},
        {"COOKING", StatValue(Stat_e::Cooking)},
        {"WOODCUTTING", StatValue(Stat_e::Woodcutting)},
        {"FLETCHING", StatValue(Stat_e::Fletching)},
        {"FISHING", StatValue(Stat_e::Fishing)},
        {"FIREMAKING", StatValue(Stat_e::Firemaking)},
        {"CRAFTING", StatValue(Stat_e::Crafting)},
        {"SMITHING", StatValue(Stat_e::Smithing)},
        {"MINING", StatValue(Stat_e::Mining)},
        {"HERBLORE", StatValue(Stat_e::Herblore)},
        {"AGILITY", StatValue(Stat_e::Agility)},
        {"THIEVING", StatValue(Stat_e::Thieving)},
        {"RUNECRAFT", StatValue(Stat_e::Runecraft)},
        {"LAYER_WALL", static_cast<s64>(LocLayer_e::Wall)},
        {"LAYER_WALL_DECOR", static_cast<s64>(LocLayer_e::WallDecor)},
        {"LAYER_GROUND", static_cast<s64>(LocLayer_e::Ground)},
        {"LAYER_GROUND_DECOR", static_cast<s64>(LocLayer_e::GroundDecor)},
    });

    std::array<Constant_s, 5> GetCacheConstants(const GameCache_s& cache)
    {
        return {{
            {"INVENTORY", cache.inventoryComponent},
            {"EQUIPMENT", cache.equipmentComponent},
            {"BANK", cache.bankComponent},
            {"BANK_INVENTORY", cache.bankInventoryComponent},
            {"INVENTORY_SIZE", cache.inventorySize},
        }};
    }

    void SetConstant(py_Ref builtins, const Constant_s& constant)
    {
        auto value = py_TValue{};
        py_newint(&value, constant.value);
        py_setdict(builtins, py_name(constant.name), &value);
    }

    void RunStdlibFile(ScriptVm& vm, std::string_view path, py_GlobalRef module)
    {
        const auto source = Stdlib::Find(path);
        assert(source && "The bindings run a file the standard library doesn't have");
        vm.RunSource(*source, path, module);
    }

    std::array<ScriptContext*, ScriptRuntime::MAX_VMS> boundContexts{};

    ScriptContext& GetContext()
    {
        auto* context = boundContexts[static_cast<std::size_t>(py_currentvm())];
        assert(context != nullptr && "A script function ran in a VM with no ScriptContext bound");
        return *context;
    }

    // Script functions are called from pocketpy's C code, so every C++ exception becomes a Python one here.
    template <typename TBody>
    bool Guard(TBody body) noexcept
    {
        try
        {
            return body();
        }
        catch (const ScriptRaisedError&)
        {
            return false;
        }
        catch (const ScriptTypeError& e)
        {
            return py_exception(tp_TypeError, "%s", e.what());
        }
        catch (const std::invalid_argument& e)
        {
            return py_exception(tp_ValueError, "%s", e.what());
        }
        catch (const std::exception& e)
        {
            return py_exception(tp_RuntimeError, "%s", e.what());
        }
    }

    bool ReturnNone()
    {
        py_newnone(py_retval());
        return true;
    }

    bool ReturnInt(s64 value)
    {
        py_newint(py_retval(), value);
        return true;
    }

    bool ReturnBool(bool value)
    {
        py_newbool(py_retval(), value);
        return true;
    }

    bool ReturnString(std::string_view text)
    {
        PyValue::FromString(py_retval(), text);
        return true;
    }

    s32 ToCoord(py_Ref value, std::string_view name)
    {
        return static_cast<s32>(PyValue::ToInt(value, name, 0, MAX_COORD));
    }

    std::optional<s32> ToRadius(py_Ref value)
    {
        const auto radius = PyValue::ToOptionalInt(value, "radius");
        if (!radius)
        {
            return std::nullopt;
        }

        return static_cast<s32>(PyValue::ToInt(value, "radius", 0, MAX_COORD));
    }

    SearchFilter_s ToFilter(py_Ref ids, py_Ref radius)
    {
        return {.ids = PyArgs::ToIds(ids, "ids"), .radius = ToRadius(radius)};
    }

    SearchFilter_s ToSearch(py_Ref ids, py_Ref radius, py_Ref names)
    {
        auto filter = ToFilter(ids, radius);
        if (!py_isnone(names))
        {
            filter.names = PyArgs::ToNames(names, "names");
        }

        return filter;
    }

    SearchFilter_s ToNameFilter(py_Ref names, py_Ref radius)
    {
        return {.names = PyArgs::ToNames(names, "names"), .radius = ToRadius(radius)};
    }

    std::optional<LocLayer_e> ToLayer(py_Ref value)
    {
        if (py_isnone(value))
        {
            return std::nullopt;
        }

        return static_cast<LocLayer_e>(PyValue::ToInt(value, "layer", 0, static_cast<s64>(LocLayer_e::GroundDecor)));
    }

    // A number is used as it is, and text is looked up in the target's menu by find.
    template <typename TFind>
    auto ResolveOp(py_Ref value, TFind find) -> decltype(find(std::string_view{}))
    {
        const auto choice = PyArgs::ToOpChoice(value);
        if (const auto* const number = std::get_if<u8>(&choice))
        {
            return *number;
        }

        return find(std::get<std::string>(choice));
    }

    void FromNpc(py_OutRef out, const Npc_s& npc)
    {
        auto& context = GetContext();
        PyObjects::FromNpc(out, npc, context.GetState().tick, context.GetCache());
    }

    void FromGroundItem(py_OutRef out, const GroundItem_s& item)
    {
        PyObjects::FromGroundItem(out, item, GetContext().GetCache());
    }

    void FromItem(py_OutRef out, const InventoryItem_s& item)
    {
        PyObjects::FromItem(out, item, GetContext().GetCache());
    }

    void FromLoc(py_OutRef out, const SceneLoc_s& loc)
    {
        PyObjects::FromLoc(out, loc, GetContext().GetCache());
    }

    void FromTile(py_OutRef out, const Tile_s& tile)
    {
        PyValue::FromPoint(out, tile.x, tile.z);
    }

    void FromPlayer(py_OutRef out, const Player_s& player)
    {
        PyObjects::FromPlayer(out, player, GetContext().GetState().tick);
    }

    void FromFriend(py_OutRef out, const Friend_s& entry)
    {
        py_newtuple(out, 2);
        py_newnone(py_tuple_getitem(out, 0));
        py_newint(py_tuple_getitem(out, 1), entry.world);
        PyValue::FromString(py_tuple_getitem(out, 0), entry.name);
    }

    void FromName(py_OutRef out, u64 name37)
    {
        PyValue::FromString(out, Base37::DecodeDisplayName(name37));
    }

    bool GetTick(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(static_cast<s64>(GetContext().GetState().tick));
        });
    }

    bool IsPlaced(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnBool(GetContext().GetState().placed);
        });
    }

    bool GetStepTime(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(GetContext().GetControl().GetStepTime());
        });
    }

    bool NoteProgress(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            GetContext().GetControl().NoteProgress();
            return ReturnNone();
        });
    }

    // When note_progress() was last called, in step time, or None.
    bool GetLastProgress(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            const auto last = GetContext().GetControl().GetLastProgress();
            return last ? ReturnInt(*last) : ReturnNone();
        });
    }

    bool Relog(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto delay = PyValue::ToInt(py_arg(0), "delay_seconds", 0, MAX_RELOG_SECONDS);
            GetContext().GetControl().RequestRelog(std::chrono::seconds{delay});
            return ReturnNone();
        });
    }

    bool CanSetRun(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnBool(GetContext().GetActions().CanSetRun());
        });
    }

    bool IsAppearanceScreenOpen(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnBool(GetContext().GetActions().IsAppearanceScreenOpen());
        });
    }

    // Reads exactly N small numbers from a list or tuple.
    template <std::size_t N>
    std::array<u8, N> ToBytes(py_Ref value, std::string_view name)
    {
        const auto isList = py_islist(value);
        if (!isList && !py_istuple(value))
        {
            throw ScriptTypeError{std::format("{} must be a list of {} numbers", name, N)};
        }

        const auto count = isList ? py_list_len(value) : py_tuple_len(value);
        if (count != static_cast<int>(N))
        {
            throw std::invalid_argument{std::format("{} must hold {} numbers, not {}", name, N, count)};
        }

        auto bytes = std::array<u8, N>{};
        for (auto i = 0; i < count; ++i)
        {
            const auto item = isList ? py_list_getitem(value, i) : py_tuple_getitem(value, i);
            bytes[static_cast<std::size_t>(i)] = static_cast<u8>(PyValue::ToInt(item, name, 0, std::numeric_limits<u8>::max()));
        }

        return bytes;
    }

    bool SetAppearance(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto design = IdkDesign_s{
                .female = PyValue::ToBool(py_arg(0), "female"),
                .kits = ToBytes<IdkDesign_s::KIT_COUNT>(py_arg(1), "kits"),
                .colours = ToBytes<IdkDesign_s::COLOUR_COUNT>(py_arg(2), "colours"),
            };
            return ReturnBool(GetContext().GetActions().SetAppearance(design));
        });
    }

    bool StopScript(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            GetContext().GetControl().RequestStop(StopRequest_e::Script);
            return ReturnNone();
        });
    }

    bool StopAccount(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            GetContext().GetControl().RequestStop(StopRequest_e::Account);
            return ReturnNone();
        });
    }

    bool GetX(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(GetContext().GetPosition().x);
        });
    }

    bool GetZ(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(GetContext().GetPosition().z);
        });
    }

    bool GetLevel(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(GetContext().GetPosition().level);
        });
    }

    bool GetPosition(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            const auto position = GetContext().GetPosition();
            PyValue::FromPoint(py_retval(), position.x, position.z);
            return true;
        });
    }

    bool GetPid(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(GetContext().GetState().pid);
        });
    }

    bool GetName(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            const auto& appearance = GetContext().GetLocalPlayer().appearance;
            return appearance ? ReturnString(appearance->name) : ReturnNone();
        });
    }

    bool GetCombatLevel(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            const auto& appearance = GetContext().GetLocalPlayer().appearance;
            return ReturnInt(appearance ? appearance->combatLevel : 0);
        });
    }

    bool GetRunEnergy(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(GetContext().GetState().runEnergy);
        });
    }

    bool GetWeight(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(GetContext().GetState().runWeight);
        });
    }

    bool IsMoving(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnBool(GetContext().GetPlayer().IsMoving());
        });
    }

    bool GetWalkDestination(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            PyValue::FromOptional(py_retval(), GetContext().GetState().walkDestination, [](py_OutRef out, const Tile_s& tile)
            {
                PyValue::FromPoint(out, tile.x, tile.z);
            });
            return true;
        });
    }

    bool InCombat(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnBool(GetContext().GetPlayer().InCombat());
        });
    }

    bool IsRunning(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnBool(GetContext().GetPlayer().IsRunning());
        });
    }

    bool GetLocalPlayer(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            FromPlayer(py_retval(), GetContext().GetLocalPlayer());
            return true;
        });
    }

    const Stat_s& GetStatArgument(py_StackRef argv)
    {
        return GetContext().GetPlayer().GetStat(static_cast<s32>(PyValue::ToInt(py_arg(0), "stat")));
    }

    bool GetCurrentStat(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            return ReturnInt(GetStatArgument(argv).level);
        });
    }

    bool GetMaxStat(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            return ReturnInt(GetStatArgument(argv).baseLevel);
        });
    }

    bool GetExperience(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            return ReturnInt(GetStatArgument(argv).xp);
        });
    }

    bool GetHp(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(GetContext().GetState().GetStat(Stat_e::Hitpoints).level);
        });
    }

    bool GetMaxHp(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(GetContext().GetState().GetStat(Stat_e::Hitpoints).baseLevel);
        });
    }

    bool GetHpPercent(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(GetContext().GetState().GetStat(Stat_e::Hitpoints).GetPercent());
        });
    }

    bool DistanceTo(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            return ReturnInt(context.GetPosition().GetDistance(context.ToTile(ToCoord(py_arg(0), "x"), ToCoord(py_arg(1), "z"))));
        });
    }

    bool Distance(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto from = Tile_s{.x = ToCoord(py_arg(0), "x1"), .z = ToCoord(py_arg(1), "z1")};
            const auto to = Tile_s{.x = ToCoord(py_arg(2), "x2"), .z = ToCoord(py_arg(3), "z2")};
            return ReturnInt(from.GetDistance(to));
        });
    }

    bool InRadiusOf(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            const auto centre = context.ToTile(ToCoord(py_arg(0), "x"), ToCoord(py_arg(1), "z"));
            return ReturnBool(context.GetPosition().GetDistance(centre) <= PyValue::ToInt(py_arg(2), "radius"));
        });
    }

    bool InRect(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto x = ToCoord(py_arg(0), "x");
            const auto z = ToCoord(py_arg(1), "z");
            const auto width = PyValue::ToInt(py_arg(2), "width");
            const auto height = PyValue::ToInt(py_arg(3), "height");
            const auto here = GetContext().GetPosition();
            return ReturnBool(here.x >= x && here.x < x + width && here.z >= z && here.z < z + height);
        });
    }

    bool At(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            return ReturnBool(context.GetPosition() == context.ToTile(ToCoord(py_arg(0), "x"), ToCoord(py_arg(1), "z")));
        });
    }

    bool GetNpcs(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            PyValue::FromList(py_retval(), GetContext().GetEntities().GetNpcs(ToSearch(py_arg(0), py_arg(1), py_arg(2))), FromNpc);
            return true;
        });
    }

    bool GetNearestNpcById(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto inCombat = PyValue::ToOptionalBool(py_arg(2), "in_combat");
            const auto reachable = PyValue::ToBool(py_arg(3), "reachable");
            PyValue::FromOptional(py_retval(), GetContext().GetEntities().GetNearestNpc(ToFilter(py_arg(0), py_arg(1)), inCombat, reachable), FromNpc);
            return true;
        });
    }

    bool GetNearestNpcByName(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto inCombat = PyValue::ToOptionalBool(py_arg(2), "in_combat");
            const auto reachable = PyValue::ToBool(py_arg(3), "reachable");
            PyValue::FromOptional(py_retval(), GetContext().GetEntities().GetNearestNpc(ToNameFilter(py_arg(0), py_arg(1)), inCombat, reachable), FromNpc);
            return true;
        });
    }

    bool GetNpc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            PyValue::FromOptional(py_retval(), GetContext().GetEntities().GetNpc(PyValue::ToU16(py_arg(0), "index")), FromNpc);
            return true;
        });
    }

    bool GetPlayers(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            PyValue::FromList(py_retval(), GetContext().GetEntities().GetPlayers(ToRadius(py_arg(0))), FromPlayer);
            return true;
        });
    }

    bool GetPlayerByName(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            PyValue::FromOptional(py_retval(), GetContext().GetEntities().GetPlayerByName(PyValue::ToString(py_arg(0), "name")), FromPlayer);
            return true;
        });
    }

    bool GetGroundItems(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            PyValue::FromList(py_retval(), GetContext().GetEntities().GetGroundItems(ToSearch(py_arg(0), py_arg(1), py_arg(2))), FromGroundItem);
            return true;
        });
    }

    bool GetNearestGroundItemById(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto reachable = PyValue::ToBool(py_arg(2), "reachable");
            PyValue::FromOptional(py_retval(), GetContext().GetEntities().GetNearestGroundItem(ToFilter(py_arg(0), py_arg(1)), reachable), FromGroundItem);
            return true;
        });
    }

    bool GetNearestGroundItemByName(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto reachable = PyValue::ToBool(py_arg(2), "reachable");
            PyValue::FromOptional(py_retval(), GetContext().GetEntities().GetNearestGroundItem(ToNameFilter(py_arg(0), py_arg(1)), reachable), FromGroundItem);
            return true;
        });
    }

    bool GetLocAt(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            const auto loc = context.GetEntities().GetLocAt(context.ToTile(ToCoord(py_arg(0), "x"), ToCoord(py_arg(1), "z")), ToLayer(py_arg(2)));
            PyValue::FromOptional(py_retval(), loc, FromLoc);
            return true;
        });
    }

    bool GetLocs(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            PyValue::FromList(py_retval(), GetContext().GetEntities().GetLocs(ToSearch(py_arg(0), py_arg(1), py_arg(3)), ToLayer(py_arg(2))), FromLoc);
            return true;
        });
    }

    bool GetNearestLocById(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto reachable = PyValue::ToBool(py_arg(3), "reachable");
            const auto loc = GetContext().GetEntities().GetNearestLoc(ToFilter(py_arg(0), py_arg(1)), ToLayer(py_arg(2)), reachable);
            PyValue::FromOptional(py_retval(), loc, FromLoc);
            return true;
        });
    }

    bool GetNearestLocByName(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto reachable = PyValue::ToBool(py_arg(3), "reachable");
            const auto loc = GetContext().GetEntities().GetNearestLoc(ToNameFilter(py_arg(0), py_arg(1)), ToLayer(py_arg(2)), reachable);
            PyValue::FromOptional(py_retval(), loc, FromLoc);
            return true;
        });
    }

    bool GetNpcType(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto& cache = GetContext().GetCache();
            const auto* const type = cache.FindNpc(static_cast<s32>(PyValue::ToInt(py_arg(0), "id")));
            if (type == nullptr)
            {
                return ReturnNone();
            }

            PyObjects::FromNpcType(py_retval(), *type, cache);
            return true;
        });
    }

    // The ids of the cache's types of that kind ('item', 'npc' or 'loc') with the name, matched without regard to case.
    bool FindTypeIds(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto& cache = GetContext().GetCache();
            const auto kind = PyValue::ToString(py_arg(0), "kind");
            const auto name = PyValue::ToString(py_arg(1), "name");
            auto ids = std::vector<s64>{};
            const auto collect = [&ids, &name](const auto& types)
            {
                for (const auto& type : types)
                {
                    if (!type.name.empty() && StringUtils::EqualsIgnoringCase(type.name, name))
                    {
                        ids.push_back(type.id);
                    }
                }
            };

            if (kind == "item")
            {
                collect(cache.objs);
            }
            else if (kind == "npc")
            {
                collect(cache.npcs);
            }
            else if (kind == "loc")
            {
                collect(cache.locs);
            }
            else
            {
                throw std::invalid_argument{std::format("kind must be 'item', 'npc' or 'loc', not '{}'", kind)};
            }

            PyValue::FromList(py_retval(), ids, [](py_OutRef out, s64 id)
            {
                py_newint(out, id);
            });
            return true;
        });
    }

    bool GetItemType(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto& cache = GetContext().GetCache();
            const auto* const type = cache.FindObj(static_cast<s32>(PyValue::ToInt(py_arg(0), "id")));
            if (type == nullptr)
            {
                return ReturnNone();
            }

            PyObjects::FromItemType(py_retval(), *type, cache);
            return true;
        });
    }

    bool GetLocType(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto& cache = GetContext().GetCache();
            const auto* const type = cache.FindLoc(static_cast<s32>(PyValue::ToInt(py_arg(0), "id")));
            if (type == nullptr)
            {
                return ReturnNone();
            }

            PyObjects::FromLocType(py_retval(), *type, cache);
            return true;
        });
    }

    bool GetInventory(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            PyValue::FromList(py_retval(), GetContext().GetInventories().GetInventory(PyValue::ToU16(py_arg(0), "com")), FromItem);
            return true;
        });
    }

    bool GetEquipment(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            PyValue::FromList(py_retval(), GetContext().GetInventories().GetInventory(GetContext().GetCache().equipmentComponent), FromItem);
            return true;
        });
    }

    bool GetInventoryCountById(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto filter = SearchFilter_s{.ids = PyArgs::ToIds(py_arg(0), "ids")};
            return ReturnInt(GetContext().GetInventories().CountItems(filter, PyValue::ToU16(py_arg(1), "com")));
        });
    }

    bool GetInventoryItemById(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto filter = SearchFilter_s{.ids = PyArgs::ToIds(py_arg(0), "ids")};
            PyValue::FromOptional(py_retval(), GetContext().GetInventories().FindItem(filter, PyValue::ToU16(py_arg(1), "com")), FromItem);
            return true;
        });
    }

    bool GetInventoryCountByName(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto filter = SearchFilter_s{.names = PyArgs::ToNames(py_arg(0), "names")};
            return ReturnInt(GetContext().GetInventories().CountItems(filter, PyValue::ToU16(py_arg(1), "com")));
        });
    }

    bool GetInventoryItemByName(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto filter = SearchFilter_s{.names = PyArgs::ToNames(py_arg(0), "names")};
            PyValue::FromOptional(py_retval(), GetContext().GetInventories().FindItem(filter, PyValue::ToU16(py_arg(1), "com")), FromItem);
            return true;
        });
    }

    bool GetEmptySlots(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(GetContext().GetInventories().GetEmptySlots());
        });
    }

    bool IsInventoryFull(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnBool(GetContext().GetInventories().GetEmptySlots() == 0);
        });
    }

    bool GetMainModal(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(GetContext().GetState().interfaces.mainModal);
        });
    }

    bool GetSideModal(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(GetContext().GetState().interfaces.sideModal);
        });
    }

    bool GetChatModal(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(GetContext().GetState().interfaces.chatModal);
        });
    }

    bool IsInterfaceOpen(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            return ReturnBool(GetContext().GetPlayer().IsInterfaceOpen(static_cast<s32>(PyValue::ToInt(py_arg(0), "id"))));
        });
    }

    bool GetComponentText(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto text = GetContext().GetPlayer().GetComponentText(PyValue::ToU16(py_arg(0), "com"));
            return text ? ReturnString(*text) : ReturnNone();
        });
    }

    bool IsCountDialogOpen(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnBool(GetContext().GetActions().IsCountDialogOpen());
        });
    }

    bool GetVarp(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            return ReturnInt(GetContext().GetState().GetVarp(PyValue::ToU16(py_arg(0), "id")));
        });
    }

    bool GetFriends(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            PyValue::FromList(py_retval(), GetContext().GetState().social.friends, FromFriend);
            return true;
        });
    }

    bool GetIgnores(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            PyValue::FromList(py_retval(), GetContext().GetState().social.ignores, FromName);
            return true;
        });
    }

    bool HasInventory(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            return ReturnBool(GetContext().GetState().inventories.contains(PyValue::ToU16(py_arg(0), "com")));
        });
    }

    bool GetTexts(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto texts = ChatDialog::GetTexts(GetContext().GetInterfaces(), PyValue::ToU16(py_arg(0), "root"));
            PyValue::FromList(py_retval(), texts, [](py_OutRef out, const std::string& text)
            {
                PyValue::FromString(out, text);
            });
            return true;
        });
    }

    // (com, type, x, options) for the inventories in an interface, x from its corner and options with None
    // where empty, so the stdlib can find the shop's and the trade's by what they offer.
    bool GetInventories(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto view = GetContext().GetInterfaces();
            auto inventories = std::vector<const IfComponent_s*>{};
            for (const auto* const component : view.GetTree(PyValue::ToU16(py_arg(0), "root")))
            {
                if (component->type == ComponentType_e::Inv || component->type == ComponentType_e::InvText)
                {
                    inventories.push_back(component);
                }
            }

            PyValue::FromList(py_retval(), inventories, [&view](py_OutRef out, const IfComponent_s* component)
            {
                constexpr auto FIELDS = 4;
                py_newtuple(out, FIELDS);
                py_newint(py_tuple_getitem(out, 0), component->id);
                py_newnone(py_tuple_getitem(out, 1));
                py_newint(py_tuple_getitem(out, 2), view.GetPosition(*component).x);
                py_newnone(py_tuple_getitem(out, 3));
                PyValue::FromString(py_tuple_getitem(out, 1), PyObjects::GetTypeName(component->type));

                const auto options = std::vector<std::string>{component->options.begin(), component->options.end()};
                PyValue::FromList(py_tuple_getitem(out, 3), options, [](py_OutRef option, const std::string& text)
                {
                    if (text.empty())
                    {
                        py_newnone(option);
                        return;
                    }

                    PyValue::FromString(option, text);
                });
            });
            return true;
        });
    }

    bool CanStep(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto coord = [argv](int index, std::string_view name)
            {
                return static_cast<s32>(PyValue::ToInt(py_arg(index), name, 0, MAX_COORD));
            };

            const auto& context = GetContext();
            return ReturnBool(context.GetReach().CanStep(context.ToTile(coord(0, "from_x"), coord(1, "from_z")), context.ToTile(coord(2, "to_x"), coord(3, "to_z"))));
        });
    }

    // The newest message's sequence number, or 0 before any: a mark to read later messages from.
    bool GetMessageMark(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(static_cast<s64>(GetContext().GetState().messageCount));
        });
    }

    // (sequence, text) for each game message after the mark, oldest first, of the 100 the state keeps.
    bool GetGameMessagesSince(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto mark = PyValue::ToInt(py_arg(0), "mark");
            auto found = std::vector<const ChatMessage_s*>{};
            for (const auto& message : GetContext().GetState().messages)
            {
                if (message.type == MessageType_e::Game && static_cast<s64>(message.sequence) > mark)
                {
                    found.push_back(&message);
                }
            }

            PyValue::FromList(py_retval(), found, [](py_OutRef out, const ChatMessage_s* message)
            {
                py_newtuple(out, 2);
                py_newint(py_tuple_getitem(out, 0), static_cast<s64>(message->sequence));
                py_newnone(py_tuple_getitem(out, 1));
                PyValue::FromString(py_tuple_getitem(out, 1), message->text);
            });
            return true;
        });
    }

    // A route across the world, as NavJson describes the request and the answer; None without navigation.
    bool FindWorldPath(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto request = NavJson::ParseRequest(PyValue::ToString(py_arg(0), "request"));
            const auto path = ScriptVm::GetCurrent().RunRouteSearch([&request]
            {
                const auto* const navigation = GetContext().GetNavigation();
                return navigation == nullptr ? std::nullopt : std::optional{WorldPathFinder::FindPath(*navigation, request.from, request.to, request.options)};
            });
            if (!path)
            {
                return ReturnNone();
            }

            PyValue::FromString(py_retval(), NavJson::ToJson(*path));
            return true;
        });
    }

    // One of the walker's data files as JSON text, or None without navigation.
    bool GetNavData(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto* const navigation = GetContext().GetNavigation();
            const auto name = PyValue::ToString(py_arg(0), "name");
            const auto text = navigation != nullptr ? navigation->GetData(name) : std::nullopt;
            if (!text)
            {
                return ReturnNone();
            }

            PyValue::FromString(py_retval(), *text);
            return true;
        });
    }

    // (walkable, exits) for a tile of the world map, or None without navigation.
    bool GetWalkTile(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto* const navigation = GetContext().GetNavigation();
            const auto x = static_cast<s32>(PyValue::ToInt(py_arg(0), "x", 0, MAX_COORD));
            const auto z = static_cast<s32>(PyValue::ToInt(py_arg(1), "z", 0, MAX_COORD));
            const auto level = static_cast<s32>(PyValue::ToInt(py_arg(2), "level", 0, MAX_LEVEL));
            if (navigation == nullptr)
            {
                return ReturnNone();
            }

            PyValue::FromPoint(py_retval(), navigation->GetMap().IsWalkable(x, z, level) ? 1 : 0, navigation->GetMap().GetExits(x, z, level));
            return true;
        });
    }

    // (lx, lz, id, shape, angle) for each of a map square's locs on a level, as the cache has them.
    bool GetSquareLocs(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto& cache = GetContext().GetCache();
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

    // Whether a hit that did damage landed on you within the last ticks.
    bool TookDamage(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            const auto ticks = static_cast<u64>(PyValue::ToInt(py_arg(0), "ticks", 0, MAX_DAMAGE_TICKS));
            return ReturnBool(EntityStatus::TookDamage(context.GetLocalPlayer(), context.GetState().tick, ticks));
        });
    }

    bool IsMembers(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnBool(GetContext().GetState().members);
        });
    }

    // Whether the tile, on your level, is in the area the server has loaded.
    bool InScene(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            const auto x = static_cast<s32>(PyValue::ToInt(py_arg(0), "x", 0, MAX_COORD));
            const auto z = static_cast<s32>(PyValue::ToInt(py_arg(1), "z", 0, MAX_COORD));
            return ReturnBool(context.GetMap().Contains(context.ToTile(x, z)));
        });
    }

    bool GetModalChanges(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnInt(GetContext().GetState().interfaces.modalChanges);
        });
    }

    bool FindContinue(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            PyValue::FromOptional(py_retval(), GetContext().GetActions().FindContinue(), [](py_OutRef out, u16 com)
            {
                py_newint(out, com);
            });
            return true;
        });
    }

    bool GetChatOptions(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            PyValue::FromList(py_retval(), ChatDialog::GetOptions(GetContext().GetInterfaces()), [](py_OutRef out, const ChatOption_s& option)
            {
                py_newtuple(out, 2);
                py_newint(py_tuple_getitem(out, 0), option.com);
                py_newnone(py_tuple_getitem(out, 1));
                PyValue::FromString(py_tuple_getitem(out, 1), option.text);
            });
            return true;
        });
    }

    bool GetChatTexts(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            PyValue::FromList(py_retval(), ChatDialog::GetTexts(GetContext().GetInterfaces()), [](py_OutRef out, const std::string& text)
            {
                PyValue::FromString(out, text);
            });
            return true;
        });
    }

    // (name, item or -1, [(amount, com)]), with MakeButton_s's amounts.
    bool GetMakeProducts(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            PyValue::FromList(py_retval(), ChatDialog::GetMakeProducts(GetContext().GetInterfaces()), [](py_OutRef out, const MakeProduct_s& product)
            {
                py_newtuple(out, 3);
                py_newnone(py_tuple_getitem(out, 0));
                py_newint(py_tuple_getitem(out, 1), product.item);
                py_newnone(py_tuple_getitem(out, 2));
                PyValue::FromString(py_tuple_getitem(out, 0), product.name);
                PyValue::FromList(py_tuple_getitem(out, 2), product.buttons, [](py_OutRef button, const MakeButton_s& value)
                {
                    PyValue::FromPoint(button, value.amount, value.com);
                });
            });
            return true;
        });
    }

    // (InvItem, product id) for each slot of the main modal's make inventories.
    bool GetMakePanel(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            auto& context = GetContext();
            const auto& state = context.GetState();
            PyValue::FromList(py_retval(), ChatDialog::GetMakePanel(context.GetInterfaces(), state), [&context, &state](py_OutRef out, const MakeSlot_s& slot)
            {
                const auto& items = state.inventories.at(slot.com).slots;
                const auto item = InventoryItem_s{.com = slot.com, .slot = slot.slot, .id = slot.id, .count = items[slot.slot].count};
                py_newtuple(out, 2);
                py_newnone(py_tuple_getitem(out, 0));
                py_newint(py_tuple_getitem(out, 1), slot.product);
                PyObjects::FromItem(py_tuple_getitem(out, 0), item, context.GetCache());
            });
            return true;
        });
    }

    std::optional<u16> ToRoot(py_Ref value)
    {
        if (py_isnone(value))
        {
            return std::nullopt;
        }

        return PyValue::ToU16(value, "root");
    }

    void FromComponents(py_OutRef out, const std::vector<const IfComponent_s*>& components, const InterfaceView& view)
    {
        PyValue::FromList(out, components, [&view](py_OutRef item, const IfComponent_s* component)
        {
            PyObjects::FromComponent(item, *component, view);
        });
    }

    bool GetComponent(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto view = GetContext().GetInterfaces();
            const auto* const component = view.Find(static_cast<s32>(PyValue::ToInt(py_arg(0), "id")));
            if (component == nullptr)
            {
                return ReturnNone();
            }

            PyObjects::FromComponent(py_retval(), *component, view);
            return true;
        });
    }

    bool GetInterface(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto view = GetContext().GetInterfaces();
            FromComponents(py_retval(), view.GetTree(PyValue::ToU16(py_arg(0), "root")), view);
            return true;
        });
    }

    // Visible components, in the open interfaces or one root's, with that text (without regard to case)
    // and that button type, where each is given.
    bool FindComponents(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto view = GetContext().GetInterfaces();
            const auto text = py_isnone(py_arg(0)) ? std::nullopt : std::optional{PyValue::ToString(py_arg(0), "text")};
            const auto button = py_isnone(py_arg(1)) ? std::nullopt : std::optional{PyValue::ToString(py_arg(1), "button")};
            const auto root = ToRoot(py_arg(2));
            const auto roots = root ? std::vector<u16>{*root} : view.GetOpenRoots();
            auto found = std::vector<const IfComponent_s*>{};

            for (const auto id : roots)
            {
                for (const auto* const component : view.GetTree(id))
                {
                    if (text && !StringUtils::EqualsIgnoringCase(view.GetText(*component), *text))
                    {
                        continue;
                    }

                    if (button && PyObjects::GetButtonName(component->buttonType).value_or("") != *button)
                    {
                        continue;
                    }

                    if (view.IsVisible(*component))
                    {
                        found.push_back(component);
                    }
                }
            }

            FromComponents(py_retval(), found, view);
            return true;
        });
    }

    bool GetOpenInterfaces(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            PyValue::FromList(py_retval(), GetContext().GetInterfaces().GetOpenRoots(), [](py_OutRef item, u16 root)
            {
                py_newint(item, root);
            });
            return true;
        });
    }

    bool GetTabInterface(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto& tabs = GetContext().GetState().interfaces.tabs;
            const auto tab = PyValue::ToInt(py_arg(0), "tab", 0, static_cast<s64>(tabs.size()) - 1);
            return ReturnInt(tabs[static_cast<std::size_t>(tab)]);
        });
    }

    bool ClickComponent(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            return ReturnBool(GetContext().GetActions().ClickComponent(PyValue::ToU16(py_arg(0), "id")));
        });
    }

    bool ClickText(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            return ReturnBool(GetContext().GetActions().ClickText(PyValue::ToString(py_arg(0), "text"), ToRoot(py_arg(1))));
        });
    }

    bool GetPlayerMenu(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            const auto menu = Menus::GetPlayerMenu(GetContext().GetState());
            py_newlist(py_retval());

            for (const auto option : menu)
            {
                const auto item = py_list_emplace(py_retval());
                py_newnone(item);

                if (!option.empty())
                {
                    PyValue::FromString(item, option);
                }
            }

            return true;
        });
    }

    bool CanReachEntity(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            return ReturnBool(context.GetReach().CanReachEntity(context.ToTile(ToCoord(py_arg(0), "x"), ToCoord(py_arg(1), "z"))));
        });
    }

    bool CanReachGroundItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            return ReturnBool(context.GetReach().CanReachGroundItem(context.ToTile(ToCoord(py_arg(0), "x"), ToCoord(py_arg(1), "z"))));
        });
    }

    bool CanReachLoc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            return ReturnBool(context.GetReach().CanReachLoc(context.ToTile(ToCoord(py_arg(1), "x"), ToCoord(py_arg(2), "z")), PyValue::ToU16(py_arg(0), "id")));
        });
    }

    bool WalkTo(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            return ReturnBool(GetContext().GetActions().WalkTo(ToCoord(py_arg(0), "x"), ToCoord(py_arg(1), "z"), PyValue::ToBool(py_arg(2), "run")));
        });
    }

    bool IsReachable(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto& context = GetContext();
            return ReturnBool(context.GetReach().IsReachable(context.ToTile(ToCoord(py_arg(0), "x"), ToCoord(py_arg(1), "z"))));
        });
    }

    bool FindPath(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto& context = GetContext();
            const auto path = context.GetReach().FindPath(context.ToTile(ToCoord(py_arg(0), "x"), ToCoord(py_arg(1), "z")));
            PyValue::FromOptional(py_retval(), path, [](py_OutRef out, const std::vector<Tile_s>& waypoints)
            {
                PyValue::FromList(out, waypoints, FromTile);
            });
            return true;
        });
    }

    bool WalkPath(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            const auto points = PyArgs::ToPoints(py_arg(0), context.GetPosition().level, "points");
            context.GetActions().WalkPath(points, PyValue::ToBool(py_arg(1), "run"));
            return ReturnNone();
        });
    }

    bool InteractNpc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            const auto index = PyArgs::ToIndex(py_arg(0), "npc", PyObjects::NPC_CLASS);
            const auto op = ResolveOp(py_arg(1), [&context, index](std::string_view text)
            {
                return Menus::FindNpcOp(context.GetState(), context.GetCache(), index, text);
            });

            return ReturnBool(op && context.GetActions().InteractNpc(index, *op));
        });
    }

    bool TalkToNpc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            return ReturnBool(GetContext().GetActions().InteractNpc(PyArgs::ToIndex(py_arg(0), "npc", PyObjects::NPC_CLASS), MenuOp::TALK));
        });
    }

    bool AttackNpc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            return ReturnBool(GetContext().GetActions().InteractNpc(PyArgs::ToIndex(py_arg(0), "npc", PyObjects::NPC_CLASS), MenuOp::ATTACK));
        });
    }

    bool InteractPlayer(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            const auto index = PyArgs::ToIndex(py_arg(0), "player", PyObjects::PLAYER_CLASS);
            const auto op = ResolveOp(py_arg(1), [&context](std::string_view text)
            {
                return Menus::FindPlayerOp(context.GetState(), text);
            });

            return ReturnBool(context.GetActions().InteractPlayer(index, op));
        });
    }

    // interact_loc(loc, op) or interact_loc(id, x, z, op); a Loc stands in for the first three.
    bool InteractLoc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            auto loc = LocRef_s{};
            auto opArgument = py_arg(3);
            if (PyArgs::IsLoc(py_arg(0)))
            {
                if (!py_isnone(py_arg(2)) || (!py_isnone(py_arg(1)) && !py_isnone(py_arg(3))))
                {
                    throw ScriptTypeError{"interact_loc takes a Loc and an op, or id, x, z and op"};
                }

                loc = PyArgs::ToLoc(py_arg(0), "loc");
                opArgument = py_isnone(py_arg(3)) ? py_arg(1) : py_arg(3);
            }
            else
            {
                loc = LocRef_s{.id = PyValue::ToU16(py_arg(0), "id"), .x = ToCoord(py_arg(1), "x"), .z = ToCoord(py_arg(2), "z")};
            }

            const auto op = ResolveOp(opArgument, [&context, &loc](std::string_view text)
            {
                return Menus::FindLocOp(context.GetCache(), loc.id, text);
            });

            context.GetActions().InteractLoc(loc.id, loc.x, loc.z, op);
            return ReturnBool(true);
        });
    }

    bool InteractLocVia(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            const auto points = PyArgs::ToPoints(py_arg(0), context.GetPosition().level, "points");
            const auto id = PyValue::ToU16(py_arg(1), "id");
            const auto op = ResolveOp(py_arg(4), [&context, id](std::string_view text)
            {
                return Menus::FindLocOp(context.GetCache(), id, text);
            });

            context.GetActions().InteractLocVia(points, id, ToCoord(py_arg(2), "x"), ToCoord(py_arg(3), "z"), op);
            return ReturnBool(true);
        });
    }

    bool InteractGroundItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            const auto item = PyArgs::ToGroundItem(py_arg(0), "item");
            const auto op = ResolveOp(py_arg(1), [&context, &item](std::string_view text)
            {
                return Menus::FindGroundItemOp(context.GetCache(), item.id, text);
            });

            return ReturnBool(context.GetActions().InteractGroundItem(item.id, item.x, item.z, op));
        });
    }

    bool TakeGroundItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto item = PyArgs::ToGroundItem(py_arg(0), "item");
            return ReturnBool(GetContext().GetActions().InteractGroundItem(item.id, item.x, item.z, MenuOp::TAKE));
        });
    }

    bool ItemOp(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            const auto item = PyArgs::ToItem(py_arg(0), "item");
            const auto op = ResolveOp(py_arg(1), [&context, &item](std::string_view text)
            {
                return Menus::FindItemOp(context.GetCache(), item.id, text);
            });

            return ReturnBool(context.GetActions().ItemOp(item, op));
        });
    }

    bool InvButton(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& context = GetContext();
            const auto item = PyArgs::ToItem(py_arg(0), "item");
            const auto op = ResolveOp(py_arg(1), [&context, &item](std::string_view text)
            {
                return Menus::FindInventoryOption(context.GetCache(), item.com, text);
            });

            return ReturnBool(context.GetActions().InventoryButton(item, op));
        });
    }

    bool DropItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            return ReturnBool(GetContext().GetActions().ItemOp(PyArgs::ToItem(py_arg(0), "item"), MenuOp::DROP));
        });
    }

    bool MoveItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            GetContext().GetActions().MoveItem(PyValue::ToU16(py_arg(0), "com"), PyValue::ToU16(py_arg(1), "from_slot"), PyValue::ToU16(py_arg(2), "to_slot"));
            return ReturnNone();
        });
    }

    bool UseItemOnNpc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto item = PyArgs::ToItem(py_arg(0), "item");
            return ReturnBool(GetContext().GetActions().UseItemOnNpc(item, PyArgs::ToIndex(py_arg(1), "npc", PyObjects::NPC_CLASS)));
        });
    }

    bool UseItemOnPlayer(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto item = PyArgs::ToItem(py_arg(0), "item");
            return ReturnBool(GetContext().GetActions().UseItemOnPlayer(item, PyArgs::ToIndex(py_arg(1), "player", PyObjects::PLAYER_CLASS)));
        });
    }

    bool UseItemOnLoc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto item = PyArgs::ToItem(py_arg(0), "item");
            return ReturnBool(GetContext().GetActions().UseItemOnLoc(item, PyValue::ToU16(py_arg(1), "id"), ToCoord(py_arg(2), "x"), ToCoord(py_arg(3), "z")));
        });
    }

    bool UseItemOnGroundItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto item = PyArgs::ToItem(py_arg(0), "item");
            const auto target = PyArgs::ToGroundItem(py_arg(1), "ground_item");
            return ReturnBool(GetContext().GetActions().UseItemOnGroundItem(item, target.id, target.x, target.z));
        });
    }

    bool UseItemOnItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto item = PyArgs::ToItem(py_arg(0), "item");
            return ReturnBool(GetContext().GetActions().UseItemOnItem(item, PyArgs::ToItem(py_arg(1), "target")));
        });
    }

    bool CastOnNpc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto spell = PyValue::ToU16(py_arg(0), "spell");
            return ReturnBool(GetContext().GetActions().CastOnNpc(spell, PyArgs::ToIndex(py_arg(1), "npc", PyObjects::NPC_CLASS)));
        });
    }

    bool CastOnPlayer(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto spell = PyValue::ToU16(py_arg(0), "spell");
            return ReturnBool(GetContext().GetActions().CastOnPlayer(spell, PyArgs::ToIndex(py_arg(1), "player", PyObjects::PLAYER_CLASS)));
        });
    }

    bool CastOnLoc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            GetContext().GetActions().CastOnLoc(PyValue::ToU16(py_arg(0), "spell"), PyValue::ToU16(py_arg(1), "id"), ToCoord(py_arg(2), "x"), ToCoord(py_arg(3), "z"));
            return ReturnNone();
        });
    }

    bool CastOnGroundItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto spell = PyValue::ToU16(py_arg(0), "spell");
            const auto target = PyArgs::ToGroundItem(py_arg(1), "ground_item");
            return ReturnBool(GetContext().GetActions().CastOnGroundItem(spell, target.id, target.x, target.z));
        });
    }

    bool CastOnItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto spell = PyValue::ToU16(py_arg(0), "spell");
            return ReturnBool(GetContext().GetActions().CastOnItem(spell, PyArgs::ToItem(py_arg(1), "item")));
        });
    }

    bool ClickButton(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            GetContext().GetActions().ClickButton(PyValue::ToU16(py_arg(0), "com"));
            return ReturnNone();
        });
    }

    bool ContinueDialogue(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            return ReturnBool(GetContext().GetActions().ContinueDialogue());
        });
    }

    bool AnswerCount(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto value = PyValue::ToInt(py_arg(0), "value", 0, std::numeric_limits<s32>::max());
            return ReturnBool(GetContext().GetActions().AnswerCountDialog(static_cast<s32>(value)));
        });
    }

    bool CloseInterfaces(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            GetContext().GetActions().CloseInterfaces();
            return ReturnNone();
        });
    }

    bool SetRun(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            GetContext().GetActions().SetRun(PyValue::ToBool(py_arg(0), "run"));
            return ReturnNone();
        });
    }

    bool Say(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            GetContext().GetActions().Say(PyValue::ToString(py_arg(0), "text"));
            return ReturnNone();
        });
    }

    bool SendPm(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            GetContext().GetActions().SendPrivateMessage(PyValue::ToString(py_arg(0), "name"), PyValue::ToString(py_arg(1), "text"));
            return ReturnNone();
        });
    }

    bool Command(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            GetContext().GetActions().SendCommand(PyValue::ToString(py_arg(0), "text"));
            return ReturnNone();
        });
    }

    bool SendBotMessage(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto username = PyValue::ToString(py_arg(0), "username");

            if (!py_json_dumps(py_arg(1), 0))
            {
                return false;
            }

            const auto sent = GetContext().SendBotMessage(username, PyValue::ToString(py_retval(), "message"));
            if (!sent)
            {
                throw std::invalid_argument{std::format("No account in this process has the username {}", username)};
            }

            return ReturnBool(*sent);
        });
    }

    template <void (ScriptActions::*TCall)(std::string_view)>
    bool CallWithName(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            (GetContext().GetActions().*TCall)(PyValue::ToString(py_arg(0), "name"));
            return ReturnNone();
        });
    }

    struct Function_s
    {
        std::string signature;
        py_CFunction function;
    };

    std::vector<Function_s> GetFunctions(const GameCache_s& cache)
    {
        return {
            {"step_time()", GetStepTime},
            {"is_placed()", IsPlaced},
            {"tick()", GetTick},
            {"note_progress()", NoteProgress},
            {"last_progress()", GetLastProgress},
            {"relog(delay_seconds=0)", Relog},
            {"can_set_run()", CanSetRun},
            {"is_appearance_screen_open()", IsAppearanceScreenOpen},
            {"set_appearance(female, kits, colours)", SetAppearance},
            {"get_tick()", GetTick},
            {"stop_script()", StopScript},
            {"stop_account()", StopAccount},
            {"send_bot_message(username, message)", SendBotMessage},
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
            {"get_loc_type(id)", GetLocType},
            {std::format("get_inventory(com={})", cache.inventoryComponent), GetInventory},
            {"get_equipment()", GetEquipment},
            {std::format("get_inventory_count_by_id(ids=None, com={})", cache.inventoryComponent), GetInventoryCountById},
            {std::format("get_inventory_item_by_id(ids=None, com={})", cache.inventoryComponent), GetInventoryItemById},
            {std::format("get_inventory_count_by_name(names, com={})", cache.inventoryComponent), GetInventoryCountByName},
            {std::format("get_inventory_item_by_name(names, com={})", cache.inventoryComponent), GetInventoryItemByName},
            {"get_empty_slots()", GetEmptySlots},
            {"is_inventory_full()", IsInventoryFull},
            {"get_main_modal()", GetMainModal},
            {"get_side_modal()", GetSideModal},
            {"get_chat_modal()", GetChatModal},
            {"is_interface_open(id)", IsInterfaceOpen},
            {"get_component_text(com)", GetComponentText},
            {"is_count_dialog_open()", IsCountDialogOpen},
            {"get_varp(id)", GetVarp},
            {"get_friends()", GetFriends},
            {"get_ignores()", GetIgnores},
            {"get_player_menu()", GetPlayerMenu},
            {"get_component(id)", GetComponent},
            {"get_interface(root)", GetInterface},
            {"find_components(text=None, button=None, root=None)", FindComponents},
            {"get_open_interfaces()", GetOpenInterfaces},
            {"get_tab_interface(tab)", GetTabInterface},
            {"click_component(id)", ClickComponent},
            {"click_text(text, root=None)", ClickText},
            {"can_reach_entity(x, z)", CanReachEntity},
            {"can_reach_ground_item(x, z)", CanReachGroundItem},
            {"can_reach_loc(id, x, z)", CanReachLoc},
            {"walk_to(x, z, run=False)", WalkTo},
            {"is_reachable(x, z)", IsReachable},
            {"find_path(x, z)", FindPath},
            {"walk_path(points, run=False)", WalkPath},
            {"interact_npc(npc, op)", InteractNpc},
            {"talk_to_npc(npc)", TalkToNpc},
            {"attack_npc(npc)", AttackNpc},
            {"interact_player(player, op)", InteractPlayer},
            {"interact_loc(target, x=None, z=None, op=None)", InteractLoc},
            {"interact_loc_via(points, id, x, z, op)", InteractLocVia},
            {"interact_ground_item(item, op)", InteractGroundItem},
            {"take_ground_item(item)", TakeGroundItem},
            {"item_op(item, op)", ItemOp},
            {"inv_button(item, op)", InvButton},
            {"drop_item(item)", DropItem},
            {"move_item(com, from_slot, to_slot)", MoveItem},
            {"use_item_on_npc(item, npc)", UseItemOnNpc},
            {"use_item_on_player(item, player)", UseItemOnPlayer},
            {"use_item_on_loc(item, id, x, z)", UseItemOnLoc},
            {"use_item_on_ground_item(item, ground_item)", UseItemOnGroundItem},
            {"use_item_on_item(item, target)", UseItemOnItem},
            {"cast_on_npc(spell, npc)", CastOnNpc},
            {"cast_on_player(spell, player)", CastOnPlayer},
            {"cast_on_loc(spell, id, x, z)", CastOnLoc},
            {"cast_on_ground_item(spell, ground_item)", CastOnGroundItem},
            {"cast_on_item(spell, item)", CastOnItem},
            {"click_button(com)", ClickButton},
            {"has_inventory(com)", HasInventory},
            {"find_world_path(request)", FindWorldPath},
            {"is_members()", IsMembers},
            {"find_type_ids(kind, name)", FindTypeIds},
            {"square_locs(x, z, level)", GetSquareLocs},
            {"took_damage(ticks=4)", TookDamage},
            {"in_scene(x, z)", InScene},
            {"nav_data(name)", GetNavData},
            {"walk_tile(x, z, level)", GetWalkTile},
            {"can_step(from_x, from_z, to_x, to_z)", CanStep},
            {"message_mark()", GetMessageMark},
            {"game_messages_since(mark)", GetGameMessagesSince},
            {"get_texts(root)", GetTexts},
            {"get_inventories(root)", GetInventories},
            {"modal_changes()", GetModalChanges},
            {"find_continue()", FindContinue},
            {"get_chat_options()", GetChatOptions},
            {"get_chat_texts()", GetChatTexts},
            {"get_make_products()", GetMakeProducts},
            {"get_make_panel()", GetMakePanel},
            {"continue_dialogue()", ContinueDialogue},
            {"answer_count(value)", AnswerCount},
            {"close_interfaces()", CloseInterfaces},
            {"set_run(run)", SetRun},
            {"say(text)", Say},
            {"send_pm(name, text)", SendPm},
            {"command(text)", Command},
            {"add_friend(name)", CallWithName<&ScriptActions::AddFriend>},
            {"remove_friend(name)", CallWithName<&ScriptActions::RemoveFriend>},
            {"add_ignore(name)", CallWithName<&ScriptActions::AddIgnore>},
            {"remove_ignore(name)", CallWithName<&ScriptActions::RemoveIgnore>},
        };
    }
}

void ScriptBindings::Bind(ScriptVm& vm, ScriptContext& context)
{
    const auto slot = static_cast<std::size_t>(vm.GetSlot());
    assert(boundContexts[slot] == nullptr && "The VM already has a ScriptContext bound");
    boundContexts[slot] = &context;

    try
    {
        const auto builtins = vm.GetBuiltins();
        const auto& cache = context.GetCache();
        for (const auto& constant : CONSTANTS)
        {
            SetConstant(builtins, constant);
        }

        for (const auto& constant : GetCacheConstants(cache))
        {
            SetConstant(builtins, constant);
        }

        // The standard library reads the game through _core, which scripts don't use.
        const auto core = py_newmodule(CORE_MODULE);
        for (const auto& function : GetFunctions(cache))
        {
            py_bind(core, function.signature.c_str(), function.function);

            const auto name = std::string_view{function.signature}.substr(0, function.signature.find('('));
            if (std::ranges::find(BUILTIN_FUNCTIONS, name) != BUILTIN_FUNCTIONS.end())
            {
                py_bind(builtins, function.signature.c_str(), function.function);
            }
        }

        RunStdlibFile(vm, PRELUDE_FILE, builtins);
        RunStdlibFile(vm, LOAD_STDLIB_FILE, builtins);
    }
    catch (const std::exception&)
    {
        Unbind(vm);
        throw;
    }
}

void ScriptBindings::Unbind(const ScriptVm& vm) noexcept
{
    boundContexts[static_cast<std::size_t>(vm.GetSlot())] = nullptr;
}

void ScriptBindings::SetSettings(ScriptVm& vm, std::string_view settingsJson)
{
    const auto builtins = vm.GetBuiltins();
    PyValue::FromString(py_r0(), settingsJson);
    py_setdict(builtins, py_name(SETTINGS_JSON), py_r0());
    vm.RunSource(LOAD_SETTINGS, "<settings>", builtins);
}
