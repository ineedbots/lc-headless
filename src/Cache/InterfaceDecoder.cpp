#include "pch.hpp"
#include "InterfaceDecoder.hpp"

#include "../Io/Packet.hpp"
#include "CacheError.hpp"

namespace
{
    constexpr auto COUNT_SIZE = std::size_t{2};
    constexpr auto NEW_LAYER = u16{0xFFFF};
    constexpr auto NONE = u8{0};
    constexpr auto PRESENT = u8{1};
    constexpr auto STRING_TERMINATOR = u8{'\n'};

    // The webclient's ComponentType and ButtonType.
    constexpr auto TYPE_LAYER = u8{0};
    constexpr auto TYPE_UNUSED = u8{1};
    constexpr auto TYPE_INV = u8{2};
    constexpr auto TYPE_RECT = u8{3};
    constexpr auto TYPE_TEXT = u8{4};
    constexpr auto TYPE_GRAPHIC = u8{5};
    constexpr auto TYPE_MODEL = u8{6};
    constexpr auto TYPE_INV_TEXT = u8{7};
    constexpr auto BUTTON_OK = u8{1};
    constexpr auto BUTTON_TARGET = u8{2};
    constexpr auto BUTTON_TOGGLE = u8{4};
    constexpr auto BUTTON_SELECT = u8{5};
    constexpr auto BUTTON_CONTINUE = u8{6};

    // Fields read and dropped whole, named as IfType names them.
    constexpr auto WIDTH_HEIGHT_TRANS_SIZE = 2 * sizeof(u16) + sizeof(u8);
    constexpr auto CONDITION_SIZE = sizeof(u8) + sizeof(u16);
    constexpr auto SCRIPT_OPCODE_SIZE = sizeof(u16);
    constexpr auto SCROLL_HEIGHT_HIDE_SIZE = sizeof(u16) + sizeof(u8);
    constexpr auto CHILD_SIZE = 3 * sizeof(u16);
    constexpr auto UNUSED_TYPE_SIZE = std::size_t{3};
    constexpr auto INV_FLAGS_MARGINS_SIZE = 6 * sizeof(u8);
    constexpr auto INV_BACKGROUND_XY_SIZE = 2 * sizeof(u16);
    constexpr auto CENTRE_FONT_SHADOW_SIZE = 3 * sizeof(u8);
    constexpr auto FILL_SIZE = sizeof(u8);
    constexpr auto COLOUR_SIZE = sizeof(u32);
    constexpr auto MODEL_ZOOM_ANGLES_SIZE = 3 * sizeof(u16);
    constexpr auto INV_TEXT_MARGINS_OBJ_OPS_SIZE = 2 * sizeof(u16) + sizeof(u8);
    constexpr auto TARGET_MASK_SIZE = sizeof(u16);

    constexpr auto INV_BACKGROUND_COUNT = 20;
    constexpr auto INV_OPTION_COUNT = std::size_t{5};
    constexpr auto RECT_TEXT_COLOUR_COUNT = std::size_t{4};
    constexpr auto TEXT_STRING_COUNT = std::size_t{2};
    constexpr auto GRAPHIC_STRING_COUNT = std::size_t{2};
    constexpr auto MODEL_REFERENCE_COUNT = 4;
    constexpr auto TARGET_STRING_COUNT = std::size_t{2};
    constexpr auto BUTTON_STRING_COUNT = std::size_t{1};
    constexpr auto INV_BACKGROUND_STRING_COUNT = std::size_t{1};

    void Skip(Packet& packet, std::size_t count)
    {
        if (packet.GetAvailable() < count)
        {
            throw std::out_of_range{"value runs past the end"};
        }

        packet.SetPos(packet.GetPos() + count);
    }

    void SkipStrings(Packet& packet, std::size_t count)
    {
        for (std::size_t i = 0; i < count; ++i)
        {
            const auto unread = packet.GetData().subspan(packet.GetPos());
            const auto terminator = std::ranges::find(unread, STRING_TERMINATOR);
            if (terminator == unread.end())
            {
                throw CacheError{"a string runs past the end without its newline"};
            }

            Skip(packet, static_cast<std::size_t>(terminator - unread.begin()) + 1);
        }
    }

    // A hover layer, model or animation: 0 for none, or else its high byte plus 1, then its low byte.
    void SkipOptionalId(Packet& packet)
    {
        if (packet.G1() != NONE)
        {
            Skip(packet, sizeof(u8));
        }
    }

    void SkipScripts(Packet& packet)
    {
        Skip(packet, std::size_t{packet.G1()} * CONDITION_SIZE);
        const auto scriptCount = packet.G1();
        for (auto i = 0; i < scriptCount; ++i)
        {
            Skip(packet, std::size_t{packet.G2()} * SCRIPT_OPCODE_SIZE);
        }
    }

    void SkipInv(Packet& packet)
    {
        Skip(packet, INV_FLAGS_MARGINS_SIZE);
        for (auto i = 0; i < INV_BACKGROUND_COUNT; ++i)
        {
            if (packet.G1() != PRESENT)
            {
                continue;
            }

            Skip(packet, INV_BACKGROUND_XY_SIZE);
            SkipStrings(packet, INV_BACKGROUND_STRING_COUNT);
        }

        SkipStrings(packet, INV_OPTION_COUNT);
    }

    void SkipModel(Packet& packet)
    {
        for (auto i = 0; i < MODEL_REFERENCE_COUNT; ++i)
        {
            SkipOptionalId(packet);
        }

        Skip(packet, MODEL_ZOOM_ANGLES_SIZE);
    }

    // IfType.init reads these in a run of ifs that some types share; each case here is one type's path
    // through them.
    void SkipTypeFields(Packet& packet, u8 type)
    {
        switch (type)
        {
        case TYPE_LAYER:
            Skip(packet, SCROLL_HEIGHT_HIDE_SIZE);
            Skip(packet, std::size_t{packet.G2()} * CHILD_SIZE);
            return;
        case TYPE_UNUSED:
            Skip(packet, UNUSED_TYPE_SIZE + CENTRE_FONT_SHADOW_SIZE + COLOUR_SIZE);
            return;
        case TYPE_INV:
            SkipInv(packet);
            return;
        case TYPE_RECT:
            Skip(packet, FILL_SIZE + RECT_TEXT_COLOUR_COUNT * COLOUR_SIZE);
            return;
        case TYPE_TEXT:
            Skip(packet, CENTRE_FONT_SHADOW_SIZE);
            SkipStrings(packet, TEXT_STRING_COUNT);
            Skip(packet, RECT_TEXT_COLOUR_COUNT * COLOUR_SIZE);
            return;
        case TYPE_GRAPHIC:
            SkipStrings(packet, GRAPHIC_STRING_COUNT);
            return;
        case TYPE_MODEL:
            SkipModel(packet);
            return;
        case TYPE_INV_TEXT:
            Skip(packet, CENTRE_FONT_SHADOW_SIZE + COLOUR_SIZE + INV_TEXT_MARGINS_OBJ_OPS_SIZE);
            SkipStrings(packet, INV_OPTION_COUNT);
            return;
        default:
            throw CacheError{std::format("unknown type {}", type)};
        }
    }

    bool HasButtonText(u8 buttonType)
    {
        return buttonType == BUTTON_OK || buttonType == BUTTON_TOGGLE || buttonType == BUTTON_SELECT || buttonType == BUTTON_CONTINUE;
    }

    void SkipButtonFields(Packet& packet, u8 type, u8 buttonType)
    {
        if (buttonType == BUTTON_TARGET || type == TYPE_INV)
        {
            SkipStrings(packet, TARGET_STRING_COUNT);
            Skip(packet, TARGET_MASK_SIZE);
        }

        if (HasButtonText(buttonType))
        {
            SkipStrings(packet, BUTTON_STRING_COUNT);
        }
    }

    // Reads past a component's fields, from just after its id, and returns its client code.
    u16 SkipComponent(Packet& packet)
    {
        const auto type = packet.G1();
        const auto buttonType = packet.G1();
        const auto clientCode = packet.G2();
        Skip(packet, WIDTH_HEIGHT_TRANS_SIZE);
        SkipOptionalId(packet);
        SkipScripts(packet);
        SkipTypeFields(packet, type);
        SkipButtonFields(packet, type, buttonType);
        return clientCode;
    }

    // The first component of each layer's group comes after a marker and the layer's id, which nothing
    // here needs.
    u16 ReadId(Packet& packet, std::optional<u16> previous)
    {
        try
        {
            const auto id = packet.G2();
            if (id != NEW_LAYER)
            {
                return id;
            }

            Skip(packet, sizeof(u16));
            return packet.G2();
        }
        catch (const std::out_of_range&)
        {
            const auto next = previous ? std::format("the component after {}", *previous) : "the first component"s;
            throw CacheError{std::format("data ends inside the id of {}", next)};
        }
    }
}

std::optional<u16> InterfaceDecoder::FindClientCode(std::span<const u8> data, u16 clientCode)
{
    if (data.size() < COUNT_SIZE)
    {
        throw CacheError{"data is too short for its count"};
    }

    auto packet = Packet{data};
    packet.SetPos(COUNT_SIZE);
    auto previous = std::optional<u16>{};
    while (packet.GetAvailable() > 0)
    {
        const auto id = ReadId(packet, previous);
        try
        {
            if (SkipComponent(packet) == clientCode)
            {
                return id;
            }
        }
        catch (const CacheError& e)
        {
            throw CacheError{std::format("component {}: {}", id, e.what())};
        }
        catch (const std::out_of_range&)
        {
            throw CacheError{std::format("component {}: runs past the end of the data", id)};
        }

        previous = id;
    }

    return std::nullopt;
}
