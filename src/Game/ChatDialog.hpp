#pragma once

#include "InterfaceView.hpp"
#include "State/GameState_s.hpp"

struct ChatOption_s
{
    u16 com = 0;
    std::string text;
};

// One button of a make menu, and how many it makes.
struct MakeButton_s
{
    // A button that asks for the count, such as "Make X".
    static constexpr s32 X = -1;
    // A button that makes as many as there are materials for, such as the tanner's "Tan all".
    static constexpr s32 ALL = 0;

    u16 com = 0;
    s32 amount = 0;
};

// A product in a make menu: a stack of buttons, one per amount, with one rectangle.
struct MakeProduct_s
{
    std::string name;
    // The item drawn over the buttons, or -1.
    s32 item = -1;
    std::vector<MakeButton_s> buttons;
};

// A product in an inventory make panel, such as the anvil's: a slot whose options make it.
struct MakeSlot_s
{
    u16 com = 0;
    u16 slot = 0;
    // What the slot holds, and what it makes: the item drawn over the slot, as jewellery draws its products
    // over placeholders, or else the slot's own item.
    s32 id = -1;
    s32 product = -1;
};

// The chat box's dialogues, option lists and make menus, recognised by their shape rather than by their ids,
// as rs2b0t's ChatDialog does.
namespace ChatDialog
{
    // Text as the player reads it: without colour tags, and with line breaks as spaces.
    [[nodiscard]] std::string CleanText(std::string_view text);
    // The amount a make button's option names, such as 5 for "Make 5" or "Smelt 5 @lre@Bronze", or nullopt
    // when it names none.
    [[nodiscard]] std::optional<s32> ParseAmount(std::string_view option);

    // The chat modal's visible "Click here to continue" button, or nullopt.
    [[nodiscard]] std::optional<u16> FindContinue(const InterfaceView& view);
    // The chat modal's choices: visible text components with an Ok button and text, in drawing order,
    // leaving out make buttons, which share their rectangle with another button.
    [[nodiscard]] std::vector<ChatOption_s> GetOptions(const InterfaceView& view);
    // The chat modal's visible text, cleaned, such as an NPC's name and lines.
    [[nodiscard]] std::vector<std::string> GetTexts(const InterfaceView& view);
    // An interface's visible text, cleaned, in drawing order.
    [[nodiscard]] std::vector<std::string> GetTexts(const InterfaceView& view, u16 root);
    // The products of the make menu in the chat modal, or else in the main modal, such as fletching's or
    // the tanner's.
    [[nodiscard]] std::vector<MakeProduct_s> GetMakeProducts(const InterfaceView& view);
    // The products of the main modal's inventories whose options make things, such as the anvil's.
    [[nodiscard]] std::vector<MakeSlot_s> GetMakePanel(const InterfaceView& view, const GameState_s& state);
}
