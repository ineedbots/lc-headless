#pragma once

#include "../../Game/Map/WorldMap.hpp"
#include "../../Game/Query/InventoryItem_s.hpp"
#include "../../Game/State/Npc_s.hpp"
#include "../../Game/State/Player_s.hpp"
#include "../../Game/State/Social_s.hpp"
#include "../../Game/State/Zone_s.hpp"
#include "../../Game/Tile_s.hpp"
#include "../Convert/PyArgs.hpp"
#include "../Error/ScriptRaisedError.hpp"
#include "../Error/ScriptTypeError.hpp"
#include "../ScriptContext.hpp"

#include <pocketpy.h>

// A function a script can call, as py_bind takes it: "name(arg, default=value)" and the C function.
struct BoundFunction_s
{
    std::string signature;
    py_CFunction function;
};

// What every binding uses: the context of the VM it runs in, the guard that turns C++ exceptions into Python
// ones, and the return values.
class BindingSupport
{
public:
    BindingSupport() = delete;

    // Null to unbind.
    static void SetContext(s32 slot, ScriptContext* context);
    [[nodiscard]] static bool HasContext(s32 slot);
    [[nodiscard]] static ScriptContext& GetContext();

    // Script functions are called from pocketpy's C code, so every C++ exception becomes a Python one here.
    template <typename TBody>
    static bool Guard(TBody body) noexcept
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

    // A number is used as it is, and text is looked up in the target's menu by find.
    template <typename TFind>
    static auto ResolveOp(py_Ref value, TFind find) -> decltype(find(std::string_view{}))
    {
        const auto choice = PyArgs::ToOpChoice(value);
        if (const auto* const number = std::get_if<u8>(&choice))
        {
            return *number;
        }

        return find(std::get<std::string>(choice));
    }

    static bool ReturnNone();
    static bool ReturnInt(s64 value);
    static bool ReturnBool(bool value);
    static bool ReturnString(std::string_view text);

    // The stdlib's objects, for the current context's tick and cache.
    static void FromNpc(py_OutRef out, const Npc_s& npc);
    static void FromGroundItem(py_OutRef out, const GroundItem_s& item);
    static void FromItem(py_OutRef out, const InventoryItem_s& item);
    static void FromLoc(py_OutRef out, const SceneLoc_s& loc);
    static void FromTile(py_OutRef out, const Tile_s& tile);
    static void FromPlayer(py_OutRef out, const Player_s& player);
    // (name, world).
    static void FromFriend(py_OutRef out, const Friend_s& entry);
    static void FromName(py_OutRef out, u64 name37);
};
