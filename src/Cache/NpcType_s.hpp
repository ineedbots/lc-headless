#pragma once

struct NpcType_s
{
    static constexpr std::size_t OP_COUNT = 5;

    u16 id = 0;
    u8 size = 1;
    // The level the menu shows, if any.
    std::optional<u16> combatLevel;
    std::string_view name;
    std::string_view examine;
    std::array<u16, OP_COUNT> ops{};
};
