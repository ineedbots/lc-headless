#include "pch.hpp"
#include "InterfaceBindings.hpp"

#include "../../Cache/GameCache_s.hpp"
#include "../../Cache/IfComponent_s.hpp"
#include "../../Config/Revision_e.hpp"
#include "../../Game/Interface/ChatDialog.hpp"
#include "../../Game/Interface/InterfaceView.hpp"
#include "../../Game/Menu/Menus.hpp"
#include "../../Game/Query/InventoryItem_s.hpp"
#include "../../Game/Query/PlayerQuery.hpp"
#include "../../Game/State/GameState_s.hpp"
#include "../../Utils/StringUtils.hpp"
#include "../Convert/PyObjects.hpp"
#include "../Convert/PyValue.hpp"
#include "../ScriptActions.hpp"
#include "../ScriptContext.hpp"
#include "BindingSupport.hpp"

#include <pocketpy.h>

namespace
{
    bool GetMainModal(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetState().interfaces.mainModal);
        });
    }

    bool GetSideModal(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetState().interfaces.sideModal);
        });
    }

    bool GetChatModal(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetState().interfaces.chatModal);
        });
    }

    bool IsInterfaceOpen(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetPlayer().IsInterfaceOpen(static_cast<s32>(PyValue::ToInt(py_arg(0), "id"))));
        });
    }

    bool GetComponentText(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto text = BindingSupport::GetContext().GetPlayer().GetComponentText(PyValue::ToU16(py_arg(0), "com"));
            return text ? BindingSupport::ReturnString(*text) : BindingSupport::ReturnNone();
        });
    }

    bool IsCountDialogOpen(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().IsCountDialogOpen());
        });
    }

    bool GetTexts(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto texts = ChatDialog::GetTexts(BindingSupport::GetContext().GetInterfaces(), PyValue::ToU16(py_arg(0), "root"));
            PyValue::FromList(py_retval(), texts, [](py_OutRef out, const std::string& text)
            {
                PyValue::FromString(out, text);
            });
            return true;
        });
    }

    bool GetModalChanges(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetState().interfaces.modalChanges);
        });
    }

    bool FindContinue(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            PyValue::FromOptional(py_retval(), BindingSupport::GetContext().GetActions().FindContinue(), [](py_OutRef out, u16 com)
            {
                py_newint(out, com);
            });
            return true;
        });
    }

    bool GetChatOptions(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            PyValue::FromList(py_retval(), ChatDialog::GetOptions(BindingSupport::GetContext().GetInterfaces()), [](py_OutRef out, const ChatOption_s& option)
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
        return BindingSupport::Guard([]
        {
            PyValue::FromList(py_retval(), ChatDialog::GetTexts(BindingSupport::GetContext().GetInterfaces()), [](py_OutRef out, const std::string& text)
            {
                PyValue::FromString(out, text);
            });
            return true;
        });
    }

    // (name, item or -1, [(amount, com)]), with MakeButton_s's amounts.
    bool GetMakeProducts(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            PyValue::FromList(py_retval(), ChatDialog::GetMakeProducts(BindingSupport::GetContext().GetInterfaces()), [](py_OutRef out, const MakeProduct_s& product)
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
        return BindingSupport::Guard([]
        {
            auto& context = BindingSupport::GetContext();
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

    void FromComponents(py_OutRef out, const std::vector<const IfComponent_s*>& components, const InterfaceView& view)
    {
        PyValue::FromList(out, components, [&view](py_OutRef item, const IfComponent_s* component)
        {
            PyObjects::FromComponent(item, *component, view);
        });
    }

    bool GetComponent(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto view = BindingSupport::GetContext().GetInterfaces();
            const auto* const component = view.Find(static_cast<s32>(PyValue::ToInt(py_arg(0), "id")));
            if (component == nullptr)
            {
                return BindingSupport::ReturnNone();
            }

            PyObjects::FromComponent(py_retval(), *component, view);
            return true;
        });
    }

    bool GetInterface(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto view = BindingSupport::GetContext().GetInterfaces();
            FromComponents(py_retval(), view.GetTree(PyValue::ToU16(py_arg(0), "root")), view);
            return true;
        });
    }

    // Visible components, in the open interfaces or one root's, with that text (without regard to case)
    // and that button type, where each is given.
    bool FindComponents(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto view = BindingSupport::GetContext().GetInterfaces();
            const auto text = py_isnone(py_arg(0)) ? std::nullopt : std::optional{PyValue::ToString(py_arg(0), "text")};
            const auto button = py_isnone(py_arg(1)) ? std::nullopt : std::optional{PyValue::ToString(py_arg(1), "button")};
            const auto root = PyArgs::ToRoot(py_arg(2));
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
        return BindingSupport::Guard([]
        {
            PyValue::FromList(py_retval(), BindingSupport::GetContext().GetInterfaces().GetOpenRoots(), [](py_OutRef item, u16 root)
            {
                py_newint(item, root);
            });
            return true;
        });
    }

    bool GetTabInterface(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto& tabs = BindingSupport::GetContext().GetState().interfaces.tabs;
            const auto tab = PyValue::ToInt(py_arg(0), "tab", 0, static_cast<s64>(tabs.size()) - 1);
            return BindingSupport::ReturnInt(tabs[static_cast<std::size_t>(tab)]);
        });
    }

    bool GetPlayerMenu(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            const auto& context = BindingSupport::GetContext();
            const auto menu = Menus::GetPlayerMenu(context.GetState(), context.GetRevision());
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

    bool CanSetRun(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().CanSetRun());
        });
    }

    bool IsAppearanceScreenOpen(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetActions().IsAppearanceScreenOpen());
        });
    }
}

void InterfaceBindings::Add(std::vector<BoundFunction_s>& functions)
{
    functions.insert(functions.end(), {
                                          {"can_set_run()", CanSetRun},
                                          {"is_appearance_screen_open()", IsAppearanceScreenOpen},
                                          {"get_main_modal()", GetMainModal},
                                          {"get_side_modal()", GetSideModal},
                                          {"get_chat_modal()", GetChatModal},
                                          {"is_interface_open(id)", IsInterfaceOpen},
                                          {"get_component_text(com)", GetComponentText},
                                          {"is_count_dialog_open()", IsCountDialogOpen},
                                          {"get_player_menu()", GetPlayerMenu},
                                          {"get_component(id)", GetComponent},
                                          {"get_interface(root)", GetInterface},
                                          {"find_components(text=None, button=None, root=None)", FindComponents},
                                          {"get_open_interfaces()", GetOpenInterfaces},
                                          {"get_tab_interface(tab)", GetTabInterface},
                                          {"get_texts(root)", GetTexts},
                                          {"modal_changes()", GetModalChanges},
                                          {"find_continue()", FindContinue},
                                          {"get_chat_options()", GetChatOptions},
                                          {"get_chat_texts()", GetChatTexts},
                                          {"get_make_products()", GetMakeProducts},
                                          {"get_make_panel()", GetMakePanel},
                                      });
}
