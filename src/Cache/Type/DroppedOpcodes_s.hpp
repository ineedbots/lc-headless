#pragma once

// Opcodes first to last whose values the client never reads, so they're read and dropped to save
// memory: size bytes each, or with counted, a u8 count and then that many items of size bytes.
struct DroppedOpcodes_s
{
    static constexpr std::size_t NO_VALUE = 0;

    u8 first;
    u8 last;
    std::size_t size;
    bool counted = false;

    [[nodiscard]] static constexpr DroppedOpcodes_s Drop(u8 opcode, std::size_t size)
    {
        return {.first = opcode, .last = opcode, .size = size};
    }

    [[nodiscard]] static constexpr DroppedOpcodes_s DropCounted(u8 opcode, std::size_t itemSize)
    {
        return {.first = opcode, .last = opcode, .size = itemSize, .counted = true};
    }

    [[nodiscard]] static constexpr DroppedOpcodes_s DropRange(u8 first, u8 last, std::size_t size)
    {
        return {.first = first, .last = last, .size = size};
    }
};
