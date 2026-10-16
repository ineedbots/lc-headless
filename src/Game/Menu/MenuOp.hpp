#pragma once

// A right-click menu's options are numbered from 1, so slot i of a menu holds op i + 1.
class MenuOp
{
public:
    static constexpr u8 MIN = 1;
    static constexpr u8 MAX = 5;
    static constexpr std::size_t COUNT = MAX;

    static constexpr u8 TALK = 1;
    static constexpr u8 ATTACK = 2;
    // The menu adds these to a ground item and an inventory item whose type has nothing there.
    static constexpr u8 TAKE = 3;
    static constexpr u8 DROP = 5;
    static constexpr auto TAKE_OPTION = "Take"sv;
    static constexpr auto DROP_OPTION = "Drop"sv;

    MenuOp() = delete;

    [[nodiscard]] static constexpr std::size_t GetSlot(u8 op)
    {
        return static_cast<std::size_t>(op - MIN);
    }
};
