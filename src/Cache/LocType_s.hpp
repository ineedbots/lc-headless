#pragma once

struct LocType_s
{
    static constexpr std::size_t OP_COUNT = 5;

    u16 id = 0;
    u8 width = 1;
    u8 length = 1;
    bool blockWalk = true;
    bool blockRange = true;
    // Ground decor only blocks walking when it's active.
    bool active = false;
    // Sides the loc can't be used from, at angle 0: 1 north, 2 east, 4 south, 8 west.
    u8 forceApproach = 0;
    // Views into the cache's TextPool; an empty name means the type has none.
    std::string_view name;
    std::string_view examine;
    // Ids into the cache's option table. TextPool::NO_OPTION is a slot the menu doesn't show.
    std::array<u16, OP_COUNT> ops{};
};
