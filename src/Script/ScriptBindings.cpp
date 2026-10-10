#include "pch.hpp"
#include "ScriptBindings.hpp"

#include "../Cache/GameCache_s.hpp"
#include "../Game/Map/WorldMap.hpp"
#include "../Game/Protocol/Base37.hpp"
#include "../Game/State/GameState_s.hpp"
#include "../Game/State/Npc_s.hpp"
#include "../Game/State/Player_s.hpp"
#include "../Game/State/Social_s.hpp"
#include "../Game/State/Zone_s.hpp"
#include "../Game/Tile_s.hpp"
#include "PyConvert.hpp"
#include "ScriptApi.hpp"
#include "ScriptRuntime.hpp"
#include "ScriptVm.hpp"

#include <pocketpy.h>

namespace
{
    constexpr auto PRELUDE = R"python(
class _Entity:
    def is_moving(self):
        return self.moving

    def in_combat(self):
        return self.last_hit_tick is not None and get_tick() - self.last_hit_tick <= COMBAT_TICKS


class Npc(_Entity):
    def __repr__(self):
        return f'Npc(index={self.index}, id={self.id}, name={self.name}, x={self.x}, z={self.z})'


class Player(_Entity):
    def __repr__(self):
        return f'Player(index={self.index}, name={self.name}, x={self.x}, z={self.z})'


class GroundItem:
    def __repr__(self):
        return f'GroundItem(id={self.id}, name={self.name}, count={self.count}, x={self.x}, z={self.z})'


class Loc:
    def __repr__(self):
        return f'Loc(id={self.id}, name={self.name}, x={self.x}, z={self.z}, layer={self.layer})'


class Item:
    def __repr__(self):
        return f'Item(id={self.id}, name={self.name}, count={self.count}, slot={self.slot})'


class NpcType:
    def __repr__(self):
        return f'NpcType(id={self.id}, name={self.name})'


class ItemType:
    def __repr__(self):
        return f'ItemType(id={self.id}, name={self.name})'


class LocType:
    def __repr__(self):
        return f'LocType(id={self.id}, name={self.name})'


def _report_rows(report):
    if not isinstance(report, dict):
        raise TypeError(f'on_progress_report() must return a dict, not {type(report).__name__}')
    return [[str(name), str(value)] for name, value in report.items()]
)python"sv;

    // Loads the standard library's public names into builtins, and names the runtime's entry points the
    // host calls, which CallBuiltin finds there.
    constexpr auto LOAD_STDLIB = R"python(
from rs2004.bot import *
from rs2004.settings import *
from rs2004.geometry import *
from rs2004.events import *
from rs2004 import execution
from rs2004 import _runtime
from rs2004.events import listening as _listening

_rt_make_settings = _runtime.make_settings
_rt_load = _runtime.load
_rt_start = _runtime.start
_rt_dispatch = _runtime.dispatch
_rt_step = _runtime.step
_rt_reset = _runtime.reset
_rt_finish = _runtime.finish
)python"sv;

    constexpr auto LOAD_SETTINGS = "settings = _rt_make_settings(_settings_json)\ndel _settings_json\n"sv;
    constexpr auto CORE_MODULE = "_core";
    constexpr auto SETTINGS_JSON = "_settings_json";
    constexpr auto MAX_COORD = s64{32767};
    constexpr auto PERCENT = 100;
    constexpr auto HITPOINTS = 3;

    struct Constant_s
    {
        const char* name;
        s64 value;
    };

    constexpr auto CONSTANTS = std::to_array<Constant_s>({
        {"COMBAT_TICKS", static_cast<s64>(ScriptApi::COMBAT_TICKS)},
        {"ATTACK", 0},
        {"DEFENCE", 1},
        {"STRENGTH", 2},
        {"HITPOINTS", HITPOINTS},
        {"RANGED", 4},
        {"PRAYER", 5},
        {"MAGIC", 6},
        {"COOKING", 7},
        {"WOODCUTTING", 8},
        {"FLETCHING", 9},
        {"FISHING", 10},
        {"FIREMAKING", 11},
        {"CRAFTING", 12},
        {"SMITHING", 13},
        {"MINING", 14},
        {"HERBLORE", 15},
        {"AGILITY", 16},
        {"THIEVING", 17},
        {"RUNECRAFT", 20},
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

    std::array<ScriptApi*, ScriptRuntime::MAX_VMS> boundApis{};

    ScriptApi& GetApi()
    {
        auto* api = boundApis[static_cast<std::size_t>(py_currentvm())];
        assert(api != nullptr && "A script function ran in a VM with no ScriptApi bound");
        return *api;
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
        PyConvert::FromString(py_retval(), text);
        return true;
    }

    s32 ToCoord(py_Ref value, std::string_view name)
    {
        return static_cast<s32>(PyConvert::ToInt(value, name, 0, MAX_COORD));
    }

    std::optional<s32> ToRadius(py_Ref value)
    {
        const auto radius = PyConvert::ToOptionalInt(value, "radius");
        if (!radius)
        {
            return std::nullopt;
        }

        return static_cast<s32>(PyConvert::ToInt(value, "radius", 0, MAX_COORD));
    }

    SearchFilter_s ToFilter(py_Ref ids, py_Ref radius)
    {
        return {.ids = PyConvert::ToIds(ids, "ids"), .radius = ToRadius(radius)};
    }

    SearchFilter_s ToNameFilter(py_Ref names, py_Ref radius)
    {
        return {.names = PyConvert::ToNames(names, "names"), .radius = ToRadius(radius)};
    }

    std::optional<LocLayer_e> ToLayer(py_Ref value)
    {
        if (py_isnone(value))
        {
            return std::nullopt;
        }

        return static_cast<LocLayer_e>(PyConvert::ToInt(value, "layer", 0, static_cast<s64>(LocLayer_e::GroundDecor)));
    }

    // A number is used as it is, and text is looked up in the target's menu by find.
    template <typename TFind>
    auto ResolveOp(py_Ref value, TFind find) -> decltype(find(std::string_view{}))
    {
        const auto choice = PyConvert::ToOpChoice(value);
        if (const auto* const number = std::get_if<u8>(&choice))
        {
            return *number;
        }

        return find(std::get<std::string>(choice));
    }

    void FromNpc(py_OutRef out, const Npc_s& npc)
    {
        const auto& api = GetApi();
        PyConvert::FromNpc(out, npc, api.GetState().tick, api.GetCache());
    }

    void FromGroundItem(py_OutRef out, const GroundItem_s& item)
    {
        PyConvert::FromGroundItem(out, item, GetApi().GetCache());
    }

    void FromItem(py_OutRef out, const InventoryItem_s& item)
    {
        PyConvert::FromItem(out, item, GetApi().GetCache());
    }

    void FromLoc(py_OutRef out, const SceneLoc_s& loc)
    {
        PyConvert::FromLoc(out, loc, GetApi().GetCache());
    }

    void FromTile(py_OutRef out, const Tile_s& tile)
    {
        PyConvert::FromPoint(out, tile.x, tile.z);
    }

    void FromPlayer(py_OutRef out, const Player_s& player)
    {
        PyConvert::FromPlayer(out, player, GetApi().GetState().tick);
    }

    void FromFriend(py_OutRef out, const Friend_s& entry)
    {
        py_newtuple(out, 2);
        py_newnone(py_tuple_getitem(out, 0));
        py_newint(py_tuple_getitem(out, 1), entry.world);
        PyConvert::FromString(py_tuple_getitem(out, 0), entry.name);
    }

    void FromName(py_OutRef out, u64 name37)
    {
        PyConvert::FromString(out, Base37::DecodeDisplayName(name37));
    }

    // Control and the local player

    bool GetTick(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnInt(static_cast<s64>(GetApi().GetState().tick)); });
    }

    bool GetStepTime(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnInt(GetApi().GetStepTime()); });
    }

    bool NoteProgress(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            GetApi().NoteProgress();
            return ReturnNone();
        });
    }

    bool StopScript(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            GetApi().RequestStop(StopRequest_e::Script);
            return ReturnNone();
        });
    }

    bool StopAccount(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            GetApi().RequestStop(StopRequest_e::Account);
            return ReturnNone();
        });
    }

    bool GetX(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnInt(GetApi().GetPosition().x); });
    }

    bool GetZ(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnInt(GetApi().GetPosition().z); });
    }

    bool GetLevel(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnInt(GetApi().GetPosition().level); });
    }

    bool GetPosition(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            const auto position = GetApi().GetPosition();
            PyConvert::FromPoint(py_retval(), position.x, position.z);
            return true;
        });
    }

    bool GetPid(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnInt(GetApi().GetState().pid); });
    }

    bool GetName(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            const auto& appearance = GetApi().GetLocalPlayer().appearance;
            return appearance ? ReturnString(appearance->name) : ReturnNone();
        });
    }

    bool GetCombatLevel(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            const auto& appearance = GetApi().GetLocalPlayer().appearance;
            return ReturnInt(appearance ? appearance->combatLevel : 0);
        });
    }

    bool GetRunEnergy(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnInt(GetApi().GetState().runEnergy); });
    }

    bool GetWeight(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnInt(GetApi().GetState().runWeight); });
    }

    bool IsMoving(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnBool(GetApi().IsMoving()); });
    }

    bool GetWalkDestination(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            PyConvert::FromOptional(py_retval(), GetApi().GetState().walkDestination, [](py_OutRef out, const Tile_s& tile)
            {
                PyConvert::FromPoint(out, tile.x, tile.z);
            });
            return true;
        });
    }

    bool InCombat(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnBool(GetApi().InCombat()); });
    }

    bool IsRunning(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnBool(GetApi().IsRunning()); });
    }

    bool GetLocalPlayer(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            FromPlayer(py_retval(), GetApi().GetLocalPlayer());
            return true;
        });
    }

    // Stats

    const Stat_s& GetStatArgument(py_StackRef argv)
    {
        return GetApi().GetStat(static_cast<s32>(PyConvert::ToInt(py_arg(0), "stat")));
    }

    bool GetCurrentStat(int, py_StackRef argv) noexcept
    {
        return Guard([argv] { return ReturnInt(GetStatArgument(argv).level); });
    }

    bool GetMaxStat(int, py_StackRef argv) noexcept
    {
        return Guard([argv] { return ReturnInt(GetStatArgument(argv).baseLevel); });
    }

    bool GetExperience(int, py_StackRef argv) noexcept
    {
        return Guard([argv] { return ReturnInt(GetStatArgument(argv).xp); });
    }

    bool GetHp(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnInt(GetApi().GetStat(HITPOINTS).level); });
    }

    bool GetMaxHp(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnInt(GetApi().GetStat(HITPOINTS).baseLevel); });
    }

    bool GetHpPercent(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            const auto& hitpoints = GetApi().GetStat(HITPOINTS);
            return ReturnInt(hitpoints.baseLevel == 0 ? 0 : hitpoints.level * PERCENT / hitpoints.baseLevel);
        });
    }

    // Area

    bool DistanceTo(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto& api = GetApi();
            return ReturnInt(api.GetPosition().GetDistance(api.ToTile(ToCoord(py_arg(0), "x"), ToCoord(py_arg(1), "z"))));
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
            const auto& api = GetApi();
            const auto centre = api.ToTile(ToCoord(py_arg(0), "x"), ToCoord(py_arg(1), "z"));
            return ReturnBool(api.GetPosition().GetDistance(centre) <= PyConvert::ToInt(py_arg(2), "radius"));
        });
    }

    bool InRect(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto x = ToCoord(py_arg(0), "x");
            const auto z = ToCoord(py_arg(1), "z");
            const auto width = PyConvert::ToInt(py_arg(2), "width");
            const auto height = PyConvert::ToInt(py_arg(3), "height");
            const auto here = GetApi().GetPosition();
            return ReturnBool(here.x >= x && here.x < x + width && here.z >= z && here.z < z + height);
        });
    }

    bool At(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto& api = GetApi();
            return ReturnBool(api.GetPosition() == api.ToTile(ToCoord(py_arg(0), "x"), ToCoord(py_arg(1), "z")));
        });
    }

    // NPCs, players, ground items and scenery

    bool GetNpcs(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            PyConvert::FromList(py_retval(), GetApi().GetNpcs(ToFilter(py_arg(0), py_arg(1))), FromNpc);
            return true;
        });
    }

    bool GetNearestNpcById(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto inCombat = PyConvert::ToOptionalBool(py_arg(2), "in_combat");
            const auto reachable = PyConvert::ToBool(py_arg(3), "reachable");
            PyConvert::FromOptional(py_retval(), GetApi().GetNearestNpc(ToFilter(py_arg(0), py_arg(1)), inCombat, reachable), FromNpc);
            return true;
        });
    }

    bool GetNearestNpcByName(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto inCombat = PyConvert::ToOptionalBool(py_arg(2), "in_combat");
            const auto reachable = PyConvert::ToBool(py_arg(3), "reachable");
            PyConvert::FromOptional(py_retval(), GetApi().GetNearestNpc(ToNameFilter(py_arg(0), py_arg(1)), inCombat, reachable), FromNpc);
            return true;
        });
    }

    bool GetNpc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            PyConvert::FromOptional(py_retval(), GetApi().GetNpc(PyConvert::ToU16(py_arg(0), "index")), FromNpc);
            return true;
        });
    }

    bool GetPlayers(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            PyConvert::FromList(py_retval(), GetApi().GetPlayers(ToRadius(py_arg(0))), FromPlayer);
            return true;
        });
    }

    bool GetPlayerByName(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            PyConvert::FromOptional(py_retval(), GetApi().GetPlayerByName(PyConvert::ToString(py_arg(0), "name")), FromPlayer);
            return true;
        });
    }

    bool GetGroundItems(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            PyConvert::FromList(py_retval(), GetApi().GetGroundItems(ToFilter(py_arg(0), py_arg(1))), FromGroundItem);
            return true;
        });
    }

    bool GetNearestGroundItemById(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto reachable = PyConvert::ToBool(py_arg(2), "reachable");
            PyConvert::FromOptional(py_retval(), GetApi().GetNearestGroundItem(ToFilter(py_arg(0), py_arg(1)), reachable), FromGroundItem);
            return true;
        });
    }

    bool GetNearestGroundItemByName(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto reachable = PyConvert::ToBool(py_arg(2), "reachable");
            PyConvert::FromOptional(py_retval(), GetApi().GetNearestGroundItem(ToNameFilter(py_arg(0), py_arg(1)), reachable), FromGroundItem);
            return true;
        });
    }

    bool GetLocAt(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto loc = GetApi().GetLocAt(ToCoord(py_arg(0), "x"), ToCoord(py_arg(1), "z"), ToLayer(py_arg(2)));
            PyConvert::FromOptional(py_retval(), loc, FromLoc);
            return true;
        });
    }

    bool GetLocs(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            PyConvert::FromList(py_retval(), GetApi().GetLocs(ToFilter(py_arg(0), py_arg(1)), ToLayer(py_arg(2))), FromLoc);
            return true;
        });
    }

    bool GetNearestLocById(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto reachable = PyConvert::ToBool(py_arg(3), "reachable");
            const auto loc = GetApi().GetNearestLoc(ToFilter(py_arg(0), py_arg(1)), ToLayer(py_arg(2)), reachable);
            PyConvert::FromOptional(py_retval(), loc, FromLoc);
            return true;
        });
    }

    bool GetNearestLocByName(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto reachable = PyConvert::ToBool(py_arg(3), "reachable");
            const auto loc = GetApi().GetNearestLoc(ToNameFilter(py_arg(0), py_arg(1)), ToLayer(py_arg(2)), reachable);
            PyConvert::FromOptional(py_retval(), loc, FromLoc);
            return true;
        });
    }

    // Types

    bool GetNpcType(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto& cache = GetApi().GetCache();
            const auto* const type = cache.FindNpc(static_cast<s32>(PyConvert::ToInt(py_arg(0), "id")));
            if (type == nullptr)
            {
                return ReturnNone();
            }

            PyConvert::FromNpcType(py_retval(), *type, cache);
            return true;
        });
    }

    bool GetItemType(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto& cache = GetApi().GetCache();
            const auto* const type = cache.FindObj(static_cast<s32>(PyConvert::ToInt(py_arg(0), "id")));
            if (type == nullptr)
            {
                return ReturnNone();
            }

            PyConvert::FromItemType(py_retval(), *type, cache);
            return true;
        });
    }

    bool GetLocType(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto& cache = GetApi().GetCache();
            const auto* const type = cache.FindLoc(static_cast<s32>(PyConvert::ToInt(py_arg(0), "id")));
            if (type == nullptr)
            {
                return ReturnNone();
            }

            PyConvert::FromLocType(py_retval(), *type, cache);
            return true;
        });
    }

    // Inventories

    bool GetInventory(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            PyConvert::FromList(py_retval(), GetApi().GetInventory(PyConvert::ToU16(py_arg(0), "com")), FromItem);
            return true;
        });
    }

    bool GetEquipment(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            PyConvert::FromList(py_retval(), GetApi().GetInventory(GetApi().GetCache().equipmentComponent), FromItem);
            return true;
        });
    }

    bool GetInventoryCountById(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto filter = SearchFilter_s{.ids = PyConvert::ToIds(py_arg(0), "ids")};
            return ReturnInt(GetApi().CountItems(filter, PyConvert::ToU16(py_arg(1), "com")));
        });
    }

    bool GetInventoryItemById(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto filter = SearchFilter_s{.ids = PyConvert::ToIds(py_arg(0), "ids")};
            PyConvert::FromOptional(py_retval(), GetApi().FindItem(filter, PyConvert::ToU16(py_arg(1), "com")), FromItem);
            return true;
        });
    }

    bool GetInventoryCountByName(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto filter = SearchFilter_s{.names = PyConvert::ToNames(py_arg(0), "names")};
            return ReturnInt(GetApi().CountItems(filter, PyConvert::ToU16(py_arg(1), "com")));
        });
    }

    bool GetInventoryItemByName(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto filter = SearchFilter_s{.names = PyConvert::ToNames(py_arg(0), "names")};
            PyConvert::FromOptional(py_retval(), GetApi().FindItem(filter, PyConvert::ToU16(py_arg(1), "com")), FromItem);
            return true;
        });
    }

    bool GetEmptySlots(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnInt(GetApi().GetEmptySlots()); });
    }

    bool IsInventoryFull(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnBool(GetApi().GetEmptySlots() == 0); });
    }

    // Interfaces, varps and social lists

    bool GetMainModal(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnInt(GetApi().GetState().interfaces.mainModal); });
    }

    bool GetSideModal(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnInt(GetApi().GetState().interfaces.sideModal); });
    }

    bool GetChatModal(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnInt(GetApi().GetState().interfaces.chatModal); });
    }

    bool IsInterfaceOpen(int, py_StackRef argv) noexcept
    {
        return Guard([argv] { return ReturnBool(GetApi().IsInterfaceOpen(static_cast<s32>(PyConvert::ToInt(py_arg(0), "id")))); });
    }

    bool GetComponentText(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto text = GetApi().GetComponentText(PyConvert::ToU16(py_arg(0), "com"));
            return text ? ReturnString(*text) : ReturnNone();
        });
    }

    bool IsCountDialogOpen(int, py_StackRef) noexcept
    {
        return Guard([] { return ReturnBool(GetApi().GetState().interfaces.countDialogOpen); });
    }

    bool GetVarp(int, py_StackRef argv) noexcept
    {
        return Guard([argv] { return ReturnInt(GetApi().GetState().GetVarp(PyConvert::ToU16(py_arg(0), "id"))); });
    }

    bool GetFriends(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            PyConvert::FromList(py_retval(), GetApi().GetState().social.friends, FromFriend);
            return true;
        });
    }

    bool GetIgnores(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            PyConvert::FromList(py_retval(), GetApi().GetState().social.ignores, FromName);
            return true;
        });
    }

    // Movement and interactions

    bool WalkTo(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            return ReturnBool(GetApi().WalkTo(ToCoord(py_arg(0), "x"), ToCoord(py_arg(1), "z"), PyConvert::ToBool(py_arg(2), "run")));
        });
    }

    bool IsReachable(int, py_StackRef argv) noexcept
    {
        return Guard([argv] { return ReturnBool(GetApi().IsReachable(ToCoord(py_arg(0), "x"), ToCoord(py_arg(1), "z"))); });
    }

    bool FindPath(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto path = GetApi().FindPath(ToCoord(py_arg(0), "x"), ToCoord(py_arg(1), "z"));
            PyConvert::FromOptional(py_retval(), path, [](py_OutRef out, const std::vector<Tile_s>& waypoints)
            {
                PyConvert::FromList(out, waypoints, FromTile);
            });
            return true;
        });
    }

    bool WalkPath(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& api = GetApi();
            const auto points = PyConvert::ToPoints(py_arg(0), api.GetPosition().level, "points");
            api.WalkPath(points, PyConvert::ToBool(py_arg(1), "run"));
            return ReturnNone();
        });
    }

    bool InteractNpc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& api = GetApi();
            const auto index = PyConvert::ToIndex(py_arg(0), "npc", PyConvert::NPC_CLASS);
            const auto op = ResolveOp(py_arg(1), [&api, index](std::string_view text)
            {
                return api.FindNpcOp(index, text);
            });

            return ReturnBool(op && api.InteractNpc(index, *op));
        });
    }

    bool TalkToNpc(int, py_StackRef argv) noexcept
    {
        return Guard([argv] { return ReturnBool(GetApi().InteractNpc(PyConvert::ToIndex(py_arg(0), "npc", PyConvert::NPC_CLASS), ScriptApi::OP_TALK)); });
    }

    bool AttackNpc(int, py_StackRef argv) noexcept
    {
        return Guard([argv] { return ReturnBool(GetApi().InteractNpc(PyConvert::ToIndex(py_arg(0), "npc", PyConvert::NPC_CLASS), ScriptApi::OP_ATTACK)); });
    }

    bool InteractPlayer(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& api = GetApi();
            const auto index = PyConvert::ToIndex(py_arg(0), "player", PyConvert::PLAYER_CLASS);
            const auto op = ResolveOp(py_arg(1), [&api](std::string_view text)
            {
                return api.FindPlayerOp(text);
            });

            return ReturnBool(api.InteractPlayer(index, op));
        });
    }

    // interact_loc(loc, op) or interact_loc(id, x, z, op); a Loc stands in for the first three.
    bool InteractLoc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& api = GetApi();
            auto loc = LocRef_s{};
            auto opArgument = py_arg(3);
            if (PyConvert::IsLoc(py_arg(0)))
            {
                if (!py_isnone(py_arg(2)) || (!py_isnone(py_arg(1)) && !py_isnone(py_arg(3))))
                {
                    throw ScriptTypeError{"interact_loc takes a Loc and an op, or id, x, z and op"};
                }

                loc = PyConvert::ToLoc(py_arg(0), "loc");
                opArgument = py_isnone(py_arg(3)) ? py_arg(1) : py_arg(3);
            }
            else
            {
                loc = LocRef_s{.id = PyConvert::ToU16(py_arg(0), "id"), .x = ToCoord(py_arg(1), "x"), .z = ToCoord(py_arg(2), "z")};
            }

            const auto op = ResolveOp(opArgument, [&api, &loc](std::string_view text)
            {
                return api.FindLocOp(loc.id, text);
            });

            api.InteractLoc(loc.id, loc.x, loc.z, op);
            return ReturnNone();
        });
    }

    bool InteractLocVia(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& api = GetApi();
            const auto points = PyConvert::ToPoints(py_arg(0), api.GetPosition().level, "points");
            const auto id = PyConvert::ToU16(py_arg(1), "id");
            const auto op = ResolveOp(py_arg(4), [&api, id](std::string_view text)
            {
                return api.FindLocOp(id, text);
            });

            api.InteractLocVia(points, id, ToCoord(py_arg(2), "x"), ToCoord(py_arg(3), "z"), op);
            return ReturnNone();
        });
    }

    bool InteractGroundItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& api = GetApi();
            const auto item = PyConvert::ToGroundItem(py_arg(0), "item");
            const auto op = ResolveOp(py_arg(1), [&api, &item](std::string_view text)
            {
                return api.FindGroundItemOp(item.id, text);
            });

            return ReturnBool(api.InteractGroundItem(item.id, item.x, item.z, op));
        });
    }

    bool TakeGroundItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto item = PyConvert::ToGroundItem(py_arg(0), "item");
            return ReturnBool(GetApi().InteractGroundItem(item.id, item.x, item.z, ScriptApi::OP_TAKE));
        });
    }

    // Items

    bool ItemOp(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            auto& api = GetApi();
            const auto item = PyConvert::ToItem(py_arg(0), "item");
            const auto op = ResolveOp(py_arg(1), [&api, &item](std::string_view text)
            {
                return api.FindItemOp(item.id, text);
            });

            return ReturnBool(api.ItemOp(item, op));
        });
    }

    bool InvButton(int, py_StackRef argv) noexcept
    {
        return Guard([argv] { return ReturnBool(GetApi().InventoryButton(PyConvert::ToItem(py_arg(0), "item"), PyConvert::ToOp(py_arg(1)))); });
    }

    bool DropItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv] { return ReturnBool(GetApi().ItemOp(PyConvert::ToItem(py_arg(0), "item"), ScriptApi::OP_DROP)); });
    }

    bool MoveItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            GetApi().MoveItem(PyConvert::ToU16(py_arg(0), "com"), PyConvert::ToU16(py_arg(1), "from_slot"), PyConvert::ToU16(py_arg(2), "to_slot"));
            return ReturnNone();
        });
    }

    bool UseItemOnNpc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto item = PyConvert::ToItem(py_arg(0), "item");
            return ReturnBool(GetApi().UseItemOnNpc(item, PyConvert::ToIndex(py_arg(1), "npc", PyConvert::NPC_CLASS)));
        });
    }

    bool UseItemOnPlayer(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto item = PyConvert::ToItem(py_arg(0), "item");
            return ReturnBool(GetApi().UseItemOnPlayer(item, PyConvert::ToIndex(py_arg(1), "player", PyConvert::PLAYER_CLASS)));
        });
    }

    bool UseItemOnLoc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto item = PyConvert::ToItem(py_arg(0), "item");
            return ReturnBool(GetApi().UseItemOnLoc(item, PyConvert::ToU16(py_arg(1), "id"), ToCoord(py_arg(2), "x"), ToCoord(py_arg(3), "z")));
        });
    }

    bool UseItemOnGroundItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto item = PyConvert::ToItem(py_arg(0), "item");
            const auto target = PyConvert::ToGroundItem(py_arg(1), "ground_item");
            return ReturnBool(GetApi().UseItemOnGroundItem(item, target.id, target.x, target.z));
        });
    }

    bool UseItemOnItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto item = PyConvert::ToItem(py_arg(0), "item");
            return ReturnBool(GetApi().UseItemOnItem(item, PyConvert::ToItem(py_arg(1), "target")));
        });
    }

    // Magic

    bool CastOnNpc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto spell = PyConvert::ToU16(py_arg(0), "spell");
            return ReturnBool(GetApi().CastOnNpc(spell, PyConvert::ToIndex(py_arg(1), "npc", PyConvert::NPC_CLASS)));
        });
    }

    bool CastOnPlayer(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto spell = PyConvert::ToU16(py_arg(0), "spell");
            return ReturnBool(GetApi().CastOnPlayer(spell, PyConvert::ToIndex(py_arg(1), "player", PyConvert::PLAYER_CLASS)));
        });
    }

    bool CastOnLoc(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            GetApi().CastOnLoc(PyConvert::ToU16(py_arg(0), "spell"), PyConvert::ToU16(py_arg(1), "id"), ToCoord(py_arg(2), "x"), ToCoord(py_arg(3), "z"));
            return ReturnNone();
        });
    }

    bool CastOnGroundItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto spell = PyConvert::ToU16(py_arg(0), "spell");
            const auto target = PyConvert::ToGroundItem(py_arg(1), "ground_item");
            return ReturnBool(GetApi().CastOnGroundItem(spell, target.id, target.x, target.z));
        });
    }

    bool CastOnItem(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto spell = PyConvert::ToU16(py_arg(0), "spell");
            return ReturnBool(GetApi().CastOnItem(spell, PyConvert::ToItem(py_arg(1), "item")));
        });
    }

    // Interfaces, settings and chat

    bool ClickButton(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            GetApi().ClickButton(PyConvert::ToU16(py_arg(0), "com"));
            return ReturnNone();
        });
    }

    bool ContinueDialogue(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            GetApi().ContinueDialogue();
            return ReturnNone();
        });
    }

    bool AnswerCount(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto value = PyConvert::ToInt(py_arg(0), "value", 0, std::numeric_limits<s32>::max());
            GetApi().AnswerCountDialog(static_cast<s32>(value));
            return ReturnNone();
        });
    }

    bool CloseInterfaces(int, py_StackRef) noexcept
    {
        return Guard([]
        {
            GetApi().CloseInterfaces();
            return ReturnNone();
        });
    }

    bool SetRun(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            GetApi().SetRun(PyConvert::ToBool(py_arg(0), "run"));
            return ReturnNone();
        });
    }

    bool Say(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            GetApi().Say(PyConvert::ToString(py_arg(0), "text"));
            return ReturnNone();
        });
    }

    bool SendPm(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            GetApi().SendPrivateMessage(PyConvert::ToString(py_arg(0), "name"), PyConvert::ToString(py_arg(1), "text"));
            return ReturnNone();
        });
    }

    bool Command(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            GetApi().SendCommand(PyConvert::ToString(py_arg(0), "text"));
            return ReturnNone();
        });
    }

    bool SendBotMessage(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            const auto username = PyConvert::ToString(py_arg(0), "username");
            if (!py_json_dumps(py_arg(1), 0))
            {
                return false;
            }

            const auto sent = GetApi().SendBotMessage(username, PyConvert::ToString(py_retval(), "message"));
            if (!sent)
            {
                throw std::invalid_argument{std::format("No account in this process has the username {}", username)};
            }

            return ReturnBool(*sent);
        });
    }

    template <void (ScriptApi::*TCall)(std::string_view)>
    bool CallWithName(int, py_StackRef argv) noexcept
    {
        return Guard([argv]
        {
            (GetApi().*TCall)(PyConvert::ToString(py_arg(0), "name"));
            return ReturnNone();
        });
    }

    struct Function_s
    {
        std::string signature;
        py_CFunction function;
    };

    std::vector<Function_s> GetCoreFunctions()
    {
        return {
            {"step_time()", GetStepTime},
            {"tick()", GetTick},
            {"note_progress()", NoteProgress},
        };
    }

    std::vector<Function_s> GetFunctions(const GameCache_s& cache)
    {
        return {
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
            {"get_npcs(ids=None, radius=None)", GetNpcs},
            {"get_nearest_npc_by_id(ids=None, radius=None, in_combat=None, reachable=False)", GetNearestNpcById},
            {"get_nearest_npc_by_name(names, radius=None, in_combat=None, reachable=False)", GetNearestNpcByName},
            {"get_npc(index)", GetNpc},
            {"get_players(radius=None)", GetPlayers},
            {"get_player_by_name(name)", GetPlayerByName},
            {"get_ground_items(ids=None, radius=None)", GetGroundItems},
            {"get_nearest_ground_item_by_id(ids=None, radius=None, reachable=False)", GetNearestGroundItemById},
            {"get_nearest_ground_item_by_name(names, radius=None, reachable=False)", GetNearestGroundItemByName},
            {"get_loc_at(x, z, layer=None)", GetLocAt},
            {"get_locs(ids=None, radius=None, layer=None)", GetLocs},
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
            {"continue_dialogue()", ContinueDialogue},
            {"answer_count(value)", AnswerCount},
            {"close_interfaces()", CloseInterfaces},
            {"set_run(run)", SetRun},
            {"say(text)", Say},
            {"send_pm(name, text)", SendPm},
            {"command(text)", Command},
            {"add_friend(name)", CallWithName<&ScriptApi::AddFriend>},
            {"remove_friend(name)", CallWithName<&ScriptApi::RemoveFriend>},
            {"add_ignore(name)", CallWithName<&ScriptApi::AddIgnore>},
            {"remove_ignore(name)", CallWithName<&ScriptApi::RemoveIgnore>},
        };
    }
}

void ScriptBindings::Bind(ScriptVm& vm, ScriptApi& api)
{
    const auto slot = static_cast<std::size_t>(vm.GetSlot());
    assert(boundApis[slot] == nullptr && "The VM already has a ScriptApi bound");
    boundApis[slot] = &api;

    try
    {
        const auto builtins = vm.GetBuiltins();
        const auto& cache = api.GetCache();
        for (const auto& constant : CONSTANTS)
        {
            SetConstant(builtins, constant);
        }

        for (const auto& constant : GetCacheConstants(cache))
        {
            SetConstant(builtins, constant);
        }

        for (const auto& function : GetFunctions(cache))
        {
            py_bind(builtins, function.signature.c_str(), function.function);
        }

        // The standard library reads the game through _core, which scripts don't use.
        const auto core = py_newmodule(CORE_MODULE);
        for (const auto& function : GetCoreFunctions())
        {
            py_bind(core, function.signature.c_str(), function.function);
        }

        vm.RunSource(PRELUDE, "<prelude>", builtins);
        vm.RunSource(LOAD_STDLIB, "<stdlib>", builtins);
    }
    catch (const std::exception&)
    {
        Unbind(vm);
        throw;
    }
}

void ScriptBindings::Unbind(const ScriptVm& vm) noexcept
{
    boundApis[static_cast<std::size_t>(vm.GetSlot())] = nullptr;
}

void ScriptBindings::SetSettings(ScriptVm& vm, std::string_view settingsJson)
{
    const auto builtins = vm.GetBuiltins();
    PyConvert::FromString(py_r0(), settingsJson);
    py_setdict(builtins, py_name(SETTINGS_JSON), py_r0());
    vm.RunSource(LOAD_SETTINGS, "<settings>", builtins);
}
