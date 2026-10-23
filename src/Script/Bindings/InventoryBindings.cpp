#include "pch.hpp"
#include "InventoryBindings.hpp"

#include "../../Cache/GameCache_s.hpp"
#include "../../Cache/IfComponent_s.hpp"
#include "../../Game/Interface/InterfaceView.hpp"
#include "../../Game/Query/InventoryQuery.hpp"
#include "../../Game/Query/SearchFilter_s.hpp"
#include "../../Game/State/GameState_s.hpp"
#include "../Convert/PyArgs.hpp"
#include "../Convert/PyObjects.hpp"
#include "../Convert/PyValue.hpp"
#include "../ScriptContext.hpp"
#include "BindingSupport.hpp"

#include <pocketpy.h>

namespace
{
    bool GetInventory(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            PyValue::FromList(py_retval(), BindingSupport::GetContext().GetInventories().GetInventory(PyValue::ToU16(py_arg(0), "com")), BindingSupport::FromItem);
            return true;
        });
    }

    bool GetEquipment(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            PyValue::FromList(py_retval(), BindingSupport::GetContext().GetInventories().GetInventory(BindingSupport::GetContext().GetCache().equipmentComponent), BindingSupport::FromItem);
            return true;
        });
    }

    bool GetInventoryCountById(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto filter = SearchFilter_s{.ids = PyArgs::ToIds(py_arg(0), "ids")};
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetInventories().CountItems(filter, PyValue::ToU16(py_arg(1), "com")));
        });
    }

    bool GetInventoryItemById(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto filter = SearchFilter_s{.ids = PyArgs::ToIds(py_arg(0), "ids")};
            PyValue::FromOptional(py_retval(), BindingSupport::GetContext().GetInventories().FindItem(filter, PyValue::ToU16(py_arg(1), "com")), BindingSupport::FromItem);
            return true;
        });
    }

    bool GetInventoryCountByName(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto filter = SearchFilter_s{.names = PyArgs::ToNames(py_arg(0), "names")};
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetInventories().CountItems(filter, PyValue::ToU16(py_arg(1), "com")));
        });
    }

    bool GetInventoryItemByName(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto filter = SearchFilter_s{.names = PyArgs::ToNames(py_arg(0), "names")};
            PyValue::FromOptional(py_retval(), BindingSupport::GetContext().GetInventories().FindItem(filter, PyValue::ToU16(py_arg(1), "com")), BindingSupport::FromItem);
            return true;
        });
    }

    bool GetEmptySlots(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnInt(BindingSupport::GetContext().GetInventories().GetEmptySlots());
        });
    }

    bool IsInventoryFull(int, py_StackRef) noexcept
    {
        return BindingSupport::Guard([]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetInventories().GetEmptySlots() == 0);
        });
    }

    bool HasInventory(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            return BindingSupport::ReturnBool(BindingSupport::GetContext().GetState().inventories.contains(PyValue::ToU16(py_arg(0), "com")));
        });
    }

    // The tick an inventory last changed, or -1 when the server hasn't sent it: rs2b0t's snapshot generation,
    // since what an action changes arrives a tick after it at the soonest.
    bool GetInventoryTick(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto& inventories = BindingSupport::GetContext().GetState().inventories;
            const auto found = inventories.find(PyValue::ToU16(py_arg(0), "com"));
            return BindingSupport::ReturnInt(found == inventories.end() ? -1 : static_cast<s64>(found->second.tick));
        });
    }

    // (com, type, x, options) for the inventories in an interface, x from its corner and options with None
    // where empty, so the stdlib can find the shop's and the trade's by what they offer.
    bool GetInventories(int, py_StackRef argv) noexcept
    {
        return BindingSupport::Guard([argv]
        {
            const auto view = BindingSupport::GetContext().GetInterfaces();
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
}

void InventoryBindings::Add(std::vector<BoundFunction_s>& functions, const GameCache_s& cache)
{
    functions.insert(functions.end(), {
                                          {std::format("get_inventory(com={})", cache.inventoryComponent), GetInventory},
                                          {"get_equipment()", GetEquipment},
                                          {std::format("get_inventory_count_by_id(ids=None, com={})", cache.inventoryComponent), GetInventoryCountById},
                                          {std::format("get_inventory_item_by_id(ids=None, com={})", cache.inventoryComponent), GetInventoryItemById},
                                          {std::format("get_inventory_count_by_name(names, com={})", cache.inventoryComponent), GetInventoryCountByName},
                                          {std::format("get_inventory_item_by_name(names, com={})", cache.inventoryComponent), GetInventoryItemByName},
                                          {"get_empty_slots()", GetEmptySlots},
                                          {"is_inventory_full()", IsInventoryFull},
                                          {"has_inventory(com)", HasInventory},
                                          {"inventory_tick(com)", GetInventoryTick},
                                          {"get_inventories(root)", GetInventories},
                                      });
}
