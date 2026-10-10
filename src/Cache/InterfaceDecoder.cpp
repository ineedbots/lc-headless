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
    constexpr auto SCROLL_HEIGHT_SIZE = sizeof(u16);
    constexpr auto UNUSED_TYPE_SIZE = std::size_t{3};
    constexpr auto OBJ_SWAP_SIZE = sizeof(u8);
    constexpr auto OBJ_REPLACE_SIZE = sizeof(u8);
    constexpr auto INV_BACKGROUND_XY_SIZE = 2 * sizeof(u16);
    constexpr auto CENTRE_FONT_SHADOW_SIZE = 3 * sizeof(u8);
    constexpr auto FILL_SIZE = sizeof(u8);
    constexpr auto COLOUR_SIZE = sizeof(u32);
    constexpr auto MODEL_ZOOM_ANGLES_SIZE = 3 * sizeof(u16);
    constexpr auto INV_TEXT_MARGINS_OBJ_OPS_SIZE = 2 * sizeof(u16) + sizeof(u8);
    constexpr auto TARGET_MASK_SIZE = sizeof(u16);

    constexpr auto INV_BACKGROUND_COUNT = 20;
    // A rect or text component's colour, then its active and hover colours, which aren't kept.
    constexpr auto OTHER_COLOUR_COUNT = std::size_t{3};
    constexpr auto GRAPHIC_STRING_COUNT = std::size_t{2};
    constexpr auto MODEL_REFERENCE_COUNT = 4;
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
        Skip(packet, OBJ_SWAP_SIZE);
        component.objOps = packet.G1() == ENABLED;
        component.objUse = packet.G1() == ENABLED;
        Skip(packet, OBJ_REPLACE_SIZE);
        component.marginX = packet.G1();
        component.marginY = packet.G1();
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

    void ReadLayer(Packet& packet, IfComponent_s& component)
    {
        Skip(packet, SCROLL_HEIGHT_SIZE);
        component.hidden = packet.G1() == ENABLED;
        component.children.resize(packet.G2());
        for (auto& child : component.children)
        {
            child.id = packet.G2();
            child.x = packet.G2B();
            child.y = packet.G2B();
        }
    }

    u32 ReadColour(Packet& packet)
    {
        return static_cast<u32>(packet.G4());
    }

    // IfType.init reads these in a run of ifs that some types share; each case here is one type's path
    // through them.
    void ReadTypeFields(Packet& packet, IfComponent_s& component)
    {
        switch (component.type)
        {
        case ComponentType_e::Layer:
            ReadLayer(packet, component);
            return;
        case ComponentType_e::Unused:
            Skip(packet, UNUSED_TYPE_SIZE + CENTRE_FONT_SHADOW_SIZE);
            component.colour = ReadColour(packet);
            return;
        case ComponentType_e::Inv:
            ReadInv(packet, component);
            return;
        case ComponentType_e::Rect:
            Skip(packet, FILL_SIZE);
            component.colour = ReadColour(packet);
            Skip(packet, OTHER_COLOUR_COUNT * COLOUR_SIZE);
            return;
        case ComponentType_e::Text:
            Skip(packet, CENTRE_FONT_SHADOW_SIZE);
            component.text = ReadString(packet);
            // The active text, shown while a script's condition holds, isn't kept.
            static_cast<void>(ReadString(packet));
            component.colour = ReadColour(packet);
            Skip(packet, OTHER_COLOUR_COUNT * COLOUR_SIZE);
            return;
        case ComponentType_e::Graphic:
            SkipStrings(packet, GRAPHIC_STRING_COUNT);
            return;
        case ComponentType_e::Model:
            SkipModel(packet);
            return;
        case ComponentType_e::InvText:
            Skip(packet, CENTRE_FONT_SHADOW_SIZE);
            component.colour = ReadColour(packet);
            Skip(packet, INV_TEXT_MARGINS_OBJ_OPS_SIZE);
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

    // IfType's default for a button with no text of its own.
    std::string_view GetDefaultButtonText(ButtonType_e buttonType)
    {
        switch (buttonType)
        {
        case ButtonType_e::Ok:
            return "Ok";
        case ButtonType_e::Toggle:
        case ButtonType_e::Select:
            return "Select";
        case ButtonType_e::Continue:
            return "Continue";
        default:
            return {};
        }
    }

    void ReadButtonFields(Packet& packet, IfComponent_s& component)
    {
        if (component.buttonType == ButtonType_e::Target || component.type == ComponentType_e::Inv)
        {
            component.targetVerb = ReadString(packet);
            component.targetName = ReadString(packet);
            Skip(packet, TARGET_MASK_SIZE);
        }

        if (HasButtonText(component.buttonType))
        {
            component.buttonText = ReadString(packet);
            if (component.buttonText.empty())
            {
                component.buttonText = GetDefaultButtonText(component.buttonType);
            }
        }
    }

    // Reads a component's fields, from just after its id.
    IfComponent_s ReadComponent(Packet& packet, u16 id, u16 root)
    {
        auto component = IfComponent_s{.id = id, .root = root};
        component.type = static_cast<ComponentType_e>(packet.G1());
        component.buttonType = static_cast<ButtonType_e>(packet.G1());
        component.clientCode = static_cast<ClientCode_e>(packet.G2());
        component.width = packet.G2();
        component.height = packet.G2();
        Skip(packet, TRANS_SIZE);
        SkipOptionalId(packet);
        ReadScripts(packet, component);
        ReadTypeFields(packet, component);
        ReadButtonFields(packet, component);
        return component;
    }

    // The first component of each interface's run comes after a marker and the interface's id, which
    // becomes the root of every component until the next marker.
    u16 ReadId(Packet& packet, std::optional<u16> previous, u16& root)
    {
        try
        {
            const auto id = packet.G2();
            if (id != NEW_LAYER)
            {
                return id;
            }

            root = packet.G2();
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
    auto root = u16{0};
    while (packet.GetAvailable() > 0)
    {
        const auto previous = components.empty() ? std::nullopt : std::optional{components.back().id};
        const auto id = ReadId(packet, previous, root);
        try
        {
            components.push_back(ReadComponent(packet, id, root));
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

    // Each child learns its parent from the layer that lists it.
    auto parents = std::unordered_map<u16, u16>{};
    for (const auto& component : components)
    {
        for (const auto& child : component.children)
        {
            parents.insert_or_assign(child.id, component.id);
        }
    }

    for (auto& component : components)
    {
        if (const auto parent = parents.find(component.id); parent != parents.end())
        {
            component.parent = parent->second;
        }
    }

    return components;
}
