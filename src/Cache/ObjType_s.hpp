#pragma once

struct ObjType_s
{
    static constexpr std::size_t OP_COUNT = 5;

    u16 id = 0;
    bool stackable = false;
    bool members = false;
    s32 cost = 1;
    // For a banknote, the item it's a note of.
    std::optional<u16> noteOf;
    std::string_view name;
    std::string_view examine;
    // On the ground. The menu shows "Take" for op 3 when ops[2] is NO_OPTION.
    std::array<u16, OP_COUNT> ops{};
    // In an inventory. The menu shows "Drop" for op 5 when inventoryOps[4] is NO_OPTION.
    std::array<u16, OP_COUNT> inventoryOps{};
};
