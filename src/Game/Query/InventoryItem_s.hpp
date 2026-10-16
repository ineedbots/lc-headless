#pragma once

// An item in an interface inventory, with where it sits: the component that shows it and its slot.
struct InventoryItem_s
{
    u16 com = 0;
    u16 slot = 0;
    s32 id = -1;
    s32 count = 0;
};
