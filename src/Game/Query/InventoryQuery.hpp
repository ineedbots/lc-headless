#pragma once

#include "../../Cache/GameCache_s.hpp"
#include "../State/GameState_s.hpp"
#include "InventoryItem_s.hpp"
#include "SearchFilter_s.hpp"

// The tracked inventories, read in place, so it's cheap to make and can't go stale. A filter's radius doesn't apply.
class InventoryQuery
{
public:
    InventoryQuery(const GameState_s& state, const GameCache_s& cache);

    // The slots that hold something; empty for an inventory the server hasn't sent.
    [[nodiscard]] std::vector<InventoryItem_s> GetInventory(u16 com) const;
    [[nodiscard]] s32 CountItems(const SearchFilter_s& filter, u16 com) const;
    // The first in slot order.
    [[nodiscard]] std::optional<InventoryItem_s> FindItem(const SearchFilter_s& filter, u16 com) const;
    // In the backpack.
    [[nodiscard]] s32 GetEmptySlots() const;
    // The item is still in that slot.
    [[nodiscard]] bool HasItem(const InventoryItem_s& item) const;

private:
    const GameState_s& m_state;
    const GameCache_s& m_cache;
};
