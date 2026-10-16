#include "pch.hpp"
#include "InventoryQuery.hpp"

#include "../../Cache/GameCache_s.hpp"
#include "../State/GameState_s.hpp"
#include "InventoryItem_s.hpp"
#include "SearchFilter_s.hpp"

InventoryQuery::InventoryQuery(const GameState_s& state, const GameCache_s& cache)
    : m_state{state}
    , m_cache{cache}
{
}

std::vector<InventoryItem_s> InventoryQuery::GetInventory(u16 com) const
{
    auto items = std::vector<InventoryItem_s>{};
    const auto* inventory = m_state.FindInventory(com);
    if (inventory == nullptr)
    {
        return items;
    }

    for (auto slot = std::size_t{0}; slot < inventory->slots.size(); ++slot)
    {
        const auto& item = inventory->slots[slot];
        if (item.id < 0)
        {
            continue;
        }

        items.push_back({.com = com, .slot = static_cast<u16>(slot), .id = item.id, .count = item.count});
    }

    return items;
}

s32 InventoryQuery::CountItems(const SearchFilter_s& filter, u16 com) const
{
    auto total = 0;
    for (const auto& item : GetInventory(com))
    {
        if (filter.MatchesType(item.id, m_cache.FindObjName(item.id)))
        {
            total += item.count;
        }
    }

    return total;
}

std::optional<InventoryItem_s> InventoryQuery::FindItem(const SearchFilter_s& filter, u16 com) const
{
    const auto items = GetInventory(com);
    const auto found = std::ranges::find_if(items, [this, &filter](const InventoryItem_s& item)
    {
        return filter.MatchesType(item.id, m_cache.FindObjName(item.id));
    });

    if (found == items.end())
    {
        return std::nullopt;
    }

    return *found;
}

s32 InventoryQuery::GetEmptySlots() const
{
    return m_cache.inventorySize - static_cast<s32>(GetInventory(m_cache.inventoryComponent).size());
}

bool InventoryQuery::HasItem(const InventoryItem_s& item) const
{
    const auto* inventory = m_state.FindInventory(item.com);
    return inventory != nullptr && item.slot < inventory->slots.size() && inventory->slots[item.slot].id == item.id;
}
