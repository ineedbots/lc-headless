#pragma once

struct ObjType_s
{
    static constexpr std::size_t OP_COUNT = 5;

    u16 id = 0;
    bool stackable = false;
    bool members = false;
    s32 cost = 1;
    // It has a model for a man to wear, which is what tells a strung bow from its unstrung twin of the same name.
    bool equippable = false;
    // One of a stackable's pile-size models: an obj that repeats the base item's name and isn't an item of its own.
    bool stackVariant = false;
    std::optional<u16> noteOf;
    std::string_view name;
    std::string_view examine;
    // On the ground. The menu shows "Take" for op 3 when ops[2] is NO_OPTION.
    std::array<u16, OP_COUNT> ops{};
    // In an inventory. The menu shows "Drop" for op 5 when inventoryOps[4] is NO_OPTION.
    std::array<u16, OP_COUNT> inventoryOps{};
};
