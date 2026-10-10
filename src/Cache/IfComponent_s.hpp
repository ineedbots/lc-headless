#pragma once

#include "ClientCode_e.hpp"

// The webclient's ComponentType.
enum class ComponentType_e : u8
{
    Layer,
    Unused,
    Inv,
    Rect,
    Text,
    Graphic,
    Model,
    InvText,
};

// The webclient's ButtonType.
enum class ButtonType_e : u8
{
    None,
    Ok,
    Target,
    Close,
    Toggle,
    Select,
    Continue,
};

// One child of a layer, at an offset from the layer's corner.
struct IfChild_s
{
    u16 id = 0;
    s16 x = 0;
    s16 y = 0;
};

// The fields of a component that the client finds, reads and clicks components by. The inventory fields
// are only set for ComponentType_e::Inv.
struct IfComponent_s
{
    static constexpr std::size_t OPTION_COUNT = 5;

    u16 id = 0;
    // The interface the component belongs to: the layer whose id opens its run in the data, IfType's
    // layerId. An interface's own layer is its root.
    u16 root = 0;
    // The layer that lists it as a child; nullopt for a root. Decode fills it in once every layer is read.
    std::optional<u16> parent;
    ComponentType_e type = ComponentType_e::Layer;
    ButtonType_e buttonType = ButtonType_e::None;
    ClientCode_e clientCode = ClientCode_e::None;
    u16 width = 0;
    u16 height = 0;
    // A layer's children in drawing order, and whether it starts hidden.
    std::vector<IfChild_s> children;
    bool hidden = false;
    // A text component's text and a text or rect component's colour, as RGB.
    std::string text;
    u32 colour = 0;
    // An Ok, Toggle, Select or Continue button's option, with IfType's defaults where the data has none.
    std::string buttonText;
    // A Target button's verb and what it names, such as "Cast on" and "Wind strike".
    std::string targetVerb;
    std::string targetName;
    // Each condition's operand, and each script's opcodes, as IfType keeps them.
    std::vector<u16> operands;
    std::vector<std::vector<u16>> scripts;
    // IfType's interactable, whether the menu offers the items' own options (OPHELD), as the backpack's
    // does; otherwise it offers the inventory's options (INV_BUTTON), as the bank's does. And objUse,
    // whether the items can be used on things.
    bool objOps = false;
    bool objUse = false;
    bool hasSlotBackgrounds = false;
    // The gap between slots: slot i of a width-column inventory is drawn at column i % width and row
    // i / width, each slot 32 pixels plus the margin from the next.
    u8 marginX = 0;
    u8 marginY = 0;
    // Empty where the slot has no option.
    std::array<std::string, OPTION_COUNT> options;
};
