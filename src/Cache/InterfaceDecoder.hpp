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

// The fields of a component that the client finds components by. The inventory fields are only set for
// ComponentType_e::Inv.
struct IfComponent_s
{
    static constexpr std::size_t OPTION_COUNT = 5;

    u16 id = 0;
    ComponentType_e type = ComponentType_e::Layer;
    ButtonType_e buttonType = ButtonType_e::None;
    ClientCode_e clientCode = ClientCode_e::None;
    u16 width = 0;
    u16 height = 0;
    // Each condition's operand, and each script's opcodes, as IfType keeps them.
    std::vector<u16> operands;
    std::vector<std::vector<u16>> scripts;
    // IfType's objUse: whether the items can be used on things.
    bool objUse = false;
    bool hasSlotBackgrounds = false;
    // Empty where the slot has no option.
    std::array<std::string, OPTION_COUNT> options;
};

class InterfaceDecoder
{
public:
    InterfaceDecoder() = delete;

    // Takes the interface archive's data entry and returns its components in the order it lists them.
    // Throws CacheError, naming the component, for data that doesn't decode.
    [[nodiscard]] static std::vector<IfComponent_s> Decode(std::span<const u8> data);
};
