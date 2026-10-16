#include "pch.hpp"
#include "ScriptBindings.hpp"

#include "../../Cache/GameCache_s.hpp"
#include "../../Game/State/EntityStatus.hpp"
#include "../../Game/State/Stat_e.hpp"
#include "../../Game/State/Zone_s.hpp"
#include "../Convert/PyValue.hpp"
#include "../ScriptContext.hpp"
#include "../ScriptVm.hpp"
#include "../Stdlib.hpp"
#include "ActionBindings.hpp"
#include "BindingSupport.hpp"
#include "ControlBindings.hpp"
#include "InterfaceBindings.hpp"
#include "InventoryBindings.hpp"
#include "NavigationBindings.hpp"
#include "PlayerBindings.hpp"
#include "SocialBindings.hpp"
#include "WorldBindings.hpp"

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

    constexpr auto SETTINGS_JSON = "_settings_json";

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

    std::vector<BoundFunction_s> GetFunctions(const GameCache_s& cache)
    {
        auto functions = std::vector<BoundFunction_s>{};
        ControlBindings::Add(functions);
        PlayerBindings::Add(functions);
        WorldBindings::Add(functions);
        InventoryBindings::Add(functions, cache);
        InterfaceBindings::Add(functions);
        ActionBindings::Add(functions);
        NavigationBindings::Add(functions);
        SocialBindings::Add(functions);
        return functions;
    }
}

void ScriptBindings::Bind(ScriptVm& vm, ScriptContext& context)
{
    assert(!BindingSupport::HasContext(vm.GetSlot()) && "The VM already has a ScriptContext bound");
    BindingSupport::SetContext(vm.GetSlot(), &context);

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
    BindingSupport::SetContext(vm.GetSlot(), nullptr);
}

void ScriptBindings::SetSettings(ScriptVm& vm, std::string_view settingsJson)
{
    const auto builtins = vm.GetBuiltins();
    PyValue::FromString(py_r0(), settingsJson);
    py_setdict(builtins, py_name(SETTINGS_JSON), py_r0());
    vm.RunSource(LOAD_SETTINGS, "<settings>", builtins);
}
