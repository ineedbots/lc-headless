#include "pch.hpp"
#include "InterfaceDecoder.hpp"

#include "../Io/Packet.hpp"
#include "CacheError.hpp"
#include "ClientCode_e.hpp"

namespace
{
    constexpr auto COUNT_SIZE = std::size_t{2};
    constexpr auto NEW_LAYER = u16{0xFFFF};
    constexpr auto NONE = u8{0};
    constexpr auto PRESENT = u8{1};
    constexpr auto ENABLED = u8{1};
    constexpr auto STRING_TERMINATOR = u8{'\n'};

    // Fields read and dropped whole, named as IfType names them.
    constexpr auto TRANS_SIZE = sizeof(u8);
    constexpr auto COMPARATOR_SIZE = sizeof(u8);
    constexpr auto SCROLL_HEIGHT_HIDE_SIZE = sizeof(u16) + sizeof(u8);
    constexpr auto CHILD_SIZE = 3 * sizeof(u16);
    constexpr auto UNUSED_TYPE_SIZE = std::size_t{3};
    constexpr auto OBJ_SWAP_OPS_SIZE = 2 * sizeof(u8);
    constexpr auto OBJ_REPLACE_MARGINS_SIZE = 3 * sizeof(u8);
    constexpr auto INV_BACKGROUND_XY_SIZE = 2 * sizeof(u16);
    constexpr auto CENTRE_FONT_SHADOW_SIZE = 3 * sizeof(u8);
    constexpr auto FILL_SIZE = sizeof(u8);
    constexpr auto COLOUR_SIZE = sizeof(u32);
    constexpr auto MODEL_ZOOM_ANGLES_SIZE = 3 * sizeof(u16);
    constexpr auto INV_TEXT_MARGINS_OBJ_OPS_SIZE = 2 * sizeof(u16) + sizeof(u8);
    constexpr auto TARGET_MASK_SIZE = sizeof(u16);

    constexpr auto INV_BACKGROUND_COUNT = 20;
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

    std::string ReadString(Packet& packet)
    {
        const auto unread = packet.GetData().subspan(packet.GetPos());
        if (std::ranges::find(unread, STRING_TERMINATOR) == unread.end())
        {
            throw CacheError{"a string runs past the end without its newline"};
        }

        return packet.GJStr();
    }

    void SkipStrings(Packet& packet, std::size_t count)
    {
        for (std::size_t i = 0; i < count; ++i)
        {
            static_cast<void>(ReadString(packet));
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

    void ReadScripts(Packet& packet, IfComponent_s& component)
    {
        const auto conditionCount = packet.G1();
        for (auto i = 0; i < conditionCount; ++i)
        {
            Skip(packet, COMPARATOR_SIZE);
            component.operands.push_back(packet.G2());
        }

        component.scripts.resize(packet.G1());
        for (auto& script : component.scripts)
        {
            script.resize(packet.G2());
            for (auto& opcode : script)
            {
                opcode = packet.G2();
            }
        }
    }

    void ReadInv(Packet& packet, IfComponent_s& component)
    {
        Skip(packet, OBJ_SWAP_OPS_SIZE);
        component.objUse = packet.G1() == ENABLED;
        Skip(packet, OBJ_REPLACE_MARGINS_SIZE);
        for (auto i = 0; i < INV_BACKGROUND_COUNT; ++i)
        {
            if (packet.G1() != PRESENT)
            {
                continue;
            }

            component.hasSlotBackgrounds = true;
            Skip(packet, INV_BACKGROUND_XY_SIZE);
            SkipStrings(packet, INV_BACKGROUND_STRING_COUNT);
        }

        for (auto& option : component.options)
        {
            option = ReadString(packet);
        }
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
    void ReadTypeFields(Packet& packet, IfComponent_s& component)
    {
        switch (component.type)
        {
        case ComponentType_e::Layer:
            Skip(packet, SCROLL_HEIGHT_HIDE_SIZE);
            Skip(packet, std::size_t{packet.G2()} * CHILD_SIZE);
            return;
        case ComponentType_e::Unused:
            Skip(packet, UNUSED_TYPE_SIZE + CENTRE_FONT_SHADOW_SIZE + COLOUR_SIZE);
            return;
        case ComponentType_e::Inv:
            ReadInv(packet, component);
            return;
        case ComponentType_e::Rect:
            Skip(packet, FILL_SIZE + RECT_TEXT_COLOUR_COUNT * COLOUR_SIZE);
            return;
        case ComponentType_e::Text:
            Skip(packet, CENTRE_FONT_SHADOW_SIZE);
            SkipStrings(packet, TEXT_STRING_COUNT);
            Skip(packet, RECT_TEXT_COLOUR_COUNT * COLOUR_SIZE);
            return;
        case ComponentType_e::Graphic:
            SkipStrings(packet, GRAPHIC_STRING_COUNT);
            return;
        case ComponentType_e::Model:
            SkipModel(packet);
            return;
        case ComponentType_e::InvText:
            Skip(packet, CENTRE_FONT_SHADOW_SIZE + COLOUR_SIZE + INV_TEXT_MARGINS_OBJ_OPS_SIZE);
            SkipStrings(packet, IfComponent_s::OPTION_COUNT);
            return;
        default:
            throw CacheError{std::format("unknown type {}", static_cast<u8>(component.type))};
        }
    }

    bool HasButtonText(ButtonType_e buttonType)
    {
        return buttonType == ButtonType_e::Ok || buttonType == ButtonType_e::Toggle || buttonType == ButtonType_e::Select || buttonType == ButtonType_e::Continue;
    }

    void SkipButtonFields(Packet& packet, const IfComponent_s& component)
    {
        if (component.buttonType == ButtonType_e::Target || component.type == ComponentType_e::Inv)
        {
            SkipStrings(packet, TARGET_STRING_COUNT);
            Skip(packet, TARGET_MASK_SIZE);
        }

        if (HasButtonText(component.buttonType))
        {
            SkipStrings(packet, BUTTON_STRING_COUNT);
        }
    }

    // Reads a component's fields, from just after its id.
    IfComponent_s ReadComponent(Packet& packet, u16 id)
    {
        auto component = IfComponent_s{.id = id};
        component.type = static_cast<ComponentType_e>(packet.G1());
        component.buttonType = static_cast<ButtonType_e>(packet.G1());
        component.clientCode = static_cast<ClientCode_e>(packet.G2());
        component.width = packet.G2();
        component.height = packet.G2();
        Skip(packet, TRANS_SIZE);
        SkipOptionalId(packet);
        ReadScripts(packet, component);
        ReadTypeFields(packet, component);
        SkipButtonFields(packet, component);
        return component;
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

std::vector<IfComponent_s> InterfaceDecoder::Decode(std::span<const u8> data)
{
    if (data.size() < COUNT_SIZE)
    {
        throw CacheError{"data is too short for its count"};
    }

    auto packet = Packet{data};
    packet.SetPos(COUNT_SIZE);
    auto components = std::vector<IfComponent_s>{};
    while (packet.GetAvailable() > 0)
    {
        const auto previous = components.empty() ? std::nullopt : std::optional{components.back().id};
        const auto id = ReadId(packet, previous);
        try
        {
            components.push_back(ReadComponent(packet, id));
        }
        catch (const CacheError& e)
        {
            throw CacheError{std::format("component {}: {}", id, e.what())};
        }
        catch (const std::out_of_range&)
        {
            throw CacheError{std::format("component {}: runs past the end of the data", id)};
        }
    }

    return components;
}
