#include "pch.hpp"
#include "ActionBindings.hpp"

#include "../../Cache/GameCache_s.hpp"
#include "../../Game/Menu/MenuOp.hpp"
#include "../../Game/Menu/Menus.hpp"
#include "../../Game/Protocol/ClientPackets.hpp"
#include "../../Game/State/GameState_s.hpp"
#include "../../Game/Tile_s.hpp"
#include "../Convert/PyArgs.hpp"
#include "../Convert/PyObjects.hpp"
#include "../Convert/PyValue.hpp"
#include "../Error/ScriptTypeError.hpp"
#include "../ScriptActions.hpp"
#include "../ScriptContext.hpp"
#include "BindingSupport.hpp"

#include <pocketpy.h>

namespace
{
    bool ClickComponent(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().ClickComponent(PyValue::ToU16(py_arg(0), "id")));
        });
    }

    bool ClickText(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().ClickText(PyValue::ToString(py_arg(0), "text"), PyArgs::ToRoot(py_arg(1))));
        });
    }

    bool WalkTo(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().WalkTo(PyArgs::ToCoord(py_arg(0), "x"), PyArgs::ToCoord(py_arg(1), "z"), PyValue::ToBool(py_arg(2), "run")));
        });
    }

    bool WalkPath(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
            const auto points = PyArgs::ToPoints(py_arg(0), context.GetPosition().level, "points");
            context.GetActions().WalkPath(points, PyValue::ToBool(py_arg(1), "run"));
            return BindingSupport::ReturnNone();
        });
    }

    bool InteractNpc(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
            const auto index = PyArgs::ToIndex(py_arg(0), "npc", PyObjects::NPC_CLASS);
            const auto op = BindingSupport::ResolveOp(py_arg(1), [&context, index](std::string_view text)
            {
                return Menus::FindNpcOp(context.GetState(), context.GetCache(), index, text);
            });

            return BindingSupport::ReturnBool(op && context.GetActions().InteractNpc(index, *op));
        });
    }

    bool TalkToNpc(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().InteractNpc(PyArgs::ToIndex(py_arg(0), "npc", PyObjects::NPC_CLASS), MenuOp::TALK));
        });
    }

    bool AttackNpc(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().InteractNpc(PyArgs::ToIndex(py_arg(0), "npc", PyObjects::NPC_CLASS), MenuOp::ATTACK));
        });
    }

    bool InteractPlayer(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
            const auto index = PyArgs::ToIndex(py_arg(0), "player", PyObjects::PLAYER_CLASS);
            const auto op = BindingSupport::ResolveOp(py_arg(1), [&context](std::string_view text)
            {
                return Menus::FindPlayerOp(context.GetState(), text);
            });

            return BindingSupport::ReturnBool(context.GetActions().InteractPlayer(index, op));
        });
    }

    // interact_loc(loc, op) or interact_loc(id, x, z, op); a Loc stands in for the first three.
    bool InteractLoc(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
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
                loc = LocRef_s{.id = PyValue::ToU16(py_arg(0), "id"), .x = PyArgs::ToCoord(py_arg(1), "x"), .z = PyArgs::ToCoord(py_arg(2), "z")};
            }

            const auto op = BindingSupport::ResolveOp(opArgument, [&context, &loc](std::string_view text)
            {
                return Menus::FindLocOp(context.GetCache(), loc.id, text);
            });

            context.GetActions().InteractLoc(loc.id, loc.x, loc.z, op);
            return BindingSupport::ReturnBool(true);
        });
    }

    bool InteractLocVia(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
            const auto points = PyArgs::ToPoints(py_arg(0), context.GetPosition().level, "points");
            const auto id = PyValue::ToU16(py_arg(1), "id");
            const auto op = BindingSupport::ResolveOp(py_arg(4), [&context, id](std::string_view text)
            {
                return Menus::FindLocOp(context.GetCache(), id, text);
            });

            context.GetActions().InteractLocVia(points, id, PyArgs::ToCoord(py_arg(2), "x"), PyArgs::ToCoord(py_arg(3), "z"), op);
            return BindingSupport::ReturnBool(true);
        });
    }

    bool InteractGroundItem(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
            const auto item = PyArgs::ToGroundItem(py_arg(0), "item");
            const auto op = BindingSupport::ResolveOp(py_arg(1), [&context, &item](std::string_view text)
            {
                return Menus::FindGroundItemOp(context.GetCache(), item.id, text);
            });

            return BindingSupport::ReturnBool(context.GetActions().InteractGroundItem(item.id, item.x, item.z, op));
        });
    }

    bool TakeGroundItem(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto item = PyArgs::ToGroundItem(py_arg(0), "item");
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().InteractGroundItem(item.id, item.x, item.z, MenuOp::TAKE));
        });
    }

    bool ItemOp(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
            const auto item = PyArgs::ToItem(py_arg(0), "item");
            const auto op = BindingSupport::ResolveOp(py_arg(1), [&context, &item](std::string_view text)
            {
                return Menus::FindItemOp(context.GetCache(), item.id, text);
            });

            return BindingSupport::ReturnBool(context.GetActions().ItemOp(item, op));
        });
    }

    bool InvButton(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            auto& context = BindingSupport::GetContext();
            const auto item = PyArgs::ToItem(py_arg(0), "item");
            const auto op = BindingSupport::ResolveOp(py_arg(1), [&context, &item](std::string_view text)
            {
                return Menus::FindInventoryOption(context.GetCache(), item.com, text);
            });

            return BindingSupport::ReturnBool(context.GetActions().InventoryButton(item, op));
        });
    }

    bool DropItem(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().ItemOp(PyArgs::ToItem(py_arg(0), "item"), MenuOp::DROP));
        });
    }

    bool MoveItem(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            BindingSupport::GetContext().GetActions().MoveItem(PyValue::ToU16(py_arg(0), "com"), PyValue::ToU16(py_arg(1), "from_slot"), PyValue::ToU16(py_arg(2), "to_slot"));
            return BindingSupport::ReturnNone();
        });
    }

    bool UseItemOnNpc(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto item = PyArgs::ToItem(py_arg(0), "item");
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().UseItemOnNpc(item, PyArgs::ToIndex(py_arg(1), "npc", PyObjects::NPC_CLASS)));
        });
    }

    bool UseItemOnPlayer(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto item = PyArgs::ToItem(py_arg(0), "item");
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().UseItemOnPlayer(item, PyArgs::ToIndex(py_arg(1), "player", PyObjects::PLAYER_CLASS)));
        });
    }

    bool UseItemOnLoc(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto item = PyArgs::ToItem(py_arg(0), "item");
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().UseItemOnLoc(item, PyValue::ToU16(py_arg(1), "id"), PyArgs::ToCoord(py_arg(2), "x"), PyArgs::ToCoord(py_arg(3), "z")));
        });
    }

    bool UseItemOnGroundItem(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto item = PyArgs::ToItem(py_arg(0), "item");
            const auto target = PyArgs::ToGroundItem(py_arg(1), "ground_item");
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().UseItemOnGroundItem(item, target.id, target.x, target.z));
        });
    }

    bool UseItemOnItem(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto item = PyArgs::ToItem(py_arg(0), "item");
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().UseItemOnItem(item, PyArgs::ToItem(py_arg(1), "target")));
        });
    }

    bool CastOnNpc(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto spell = PyValue::ToU16(py_arg(0), "spell");
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().CastOnNpc(spell, PyArgs::ToIndex(py_arg(1), "npc", PyObjects::NPC_CLASS)));
        });
    }

    bool CastOnPlayer(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto spell = PyValue::ToU16(py_arg(0), "spell");
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().CastOnPlayer(spell, PyArgs::ToIndex(py_arg(1), "player", PyObjects::PLAYER_CLASS)));
        });
    }

    bool CastOnLoc(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            BindingSupport::GetContext().GetActions().CastOnLoc(PyValue::ToU16(py_arg(0), "spell"), PyValue::ToU16(py_arg(1), "id"), PyArgs::ToCoord(py_arg(2), "x"), PyArgs::ToCoord(py_arg(3), "z"));
            return BindingSupport::ReturnNone();
        });
    }

    bool CastOnGroundItem(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto spell = PyValue::ToU16(py_arg(0), "spell");
            const auto target = PyArgs::ToGroundItem(py_arg(1), "ground_item");
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().CastOnGroundItem(spell, target.id, target.x, target.z));
        });
    }

    bool CastOnItem(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto spell = PyValue::ToU16(py_arg(0), "spell");
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().CastOnItem(spell, PyArgs::ToItem(py_arg(1), "item")));
        });
    }

    bool ClickButton(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            BindingSupport::GetContext().GetActions().ClickButton(PyValue::ToU16(py_arg(0), "com"));
            return BindingSupport::ReturnNone();
        });
    }

    bool ContinueDialogue(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().ContinueDialogue());
        });
    }

    bool AnswerCount(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto value = PyValue::ToInt(py_arg(0), "value", 0, std::numeric_limits<s32>::max());
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().AnswerCountDialog(static_cast<s32>(value)));
        });
    }

    bool CloseInterfaces(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            BindingSupport::GetContext().GetActions().CloseInterfaces();
            return BindingSupport::ReturnNone();
        });
    }

    bool SetRun(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            BindingSupport::GetContext().GetActions().SetRun(PyValue::ToBool(py_arg(0), "run"));
            return BindingSupport::ReturnNone();
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
        return BindingSupport::Guard([argv]
        {
            const auto design = IdkDesign_s{
                .female = PyValue::ToBool(py_arg(0), "female"),
                .kits = ToBytes<IdkDesign_s::KIT_COUNT>(py_arg(1), "kits"),
                .colours = ToBytes<IdkDesign_s::COLOUR_COUNT>(py_arg(2), "colours"),
            };
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().SetAppearance(design));
        });
    }
}

void ActionBindings::Add(std::vector<BoundFunction_s>& functions)
{
    functions.insert(functions.end(), {
                                          {"set_appearance(female, kits, colours)", SetAppearance},
                                          {"click_component(id)", ClickComponent},
                                          {"click_text(text, root=None)", ClickText},
                                          {"walk_to(x, z, run=False)", WalkTo},
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
                                      });
}
