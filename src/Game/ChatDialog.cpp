#include "pch.hpp"
#include "ChatDialog.hpp"

#include "../Cache/GameCache_s.hpp"
#include "../Cache/IfComponent_s.hpp"

namespace
{
    constexpr auto COLOUR_TAG_SIZE = std::size_t{5};
    constexpr auto SLOT_SIZE = s32{32};

    struct Rect_s
    {
        s32 x = 0;
        s32 y = 0;
        s32 width = 0;
        s32 height = 0;

        bool operator==(const Rect_s&) const = default;
    };

    std::string Lower(std::string_view text)
    {
        auto result = std::string{text};
        std::ranges::transform(result, result.begin(), [](char c) { return static_cast<char>(std::tolower(static_cast<unsigned char>(c))); });
        return result;
    }

    std::vector<std::string_view> SplitWords(std::string_view text)
    {
        auto words = std::vector<std::string_view>{};
        auto start = std::size_t{0};
        while (start < text.size())
        {
            const auto end = std::min(text.find(' ', start), text.size());
            if (end > start)
            {
                words.push_back(text.substr(start, end - start));
            }

            start = end + 1;
        }

        return words;
    }

    Rect_s GetRect(const InterfaceView& view, const IfComponent_s& component)
    {
        const auto corner = view.GetPosition(component);
        return {.x = corner.x, .y = corner.y, .width = component.width, .height = component.height};
    }

    s32 GetOverlap(const Rect_s& a, const Rect_s& b)
    {
        const auto width = std::min(a.x + a.width, b.x + b.width) - std::max(a.x, b.x);
        const auto height = std::min(a.y + a.height, b.y + b.height) - std::max(a.y, b.y);
        return width > 0 && height > 0 ? width * height : 0;
    }

    // The visible Ok buttons of an interface, grouped by their rectangle, in drawing order.
    std::vector<std::vector<const IfComponent_s*>> GroupButtons(const InterfaceView& view, u16 root)
    {
        auto rects = std::vector<Rect_s>{};
        auto groups = std::vector<std::vector<const IfComponent_s*>>{};
        for (const auto* const component : view.GetTree(root))
        {
            if (component->buttonType != ButtonType_e::Ok || !view.IsVisible(*component))
            {
                continue;
            }

            const auto rect = GetRect(view, *component);
            const auto found = std::ranges::find(rects, rect);
            if (found == rects.end())
            {
                rects.push_back(rect);
                groups.push_back({component});
                continue;
            }

            groups[static_cast<std::size_t>(found - rects.begin())].push_back(component);
        }

        return groups;
    }

    // The item a visible model in the interface shows over the rectangle, covering most of it.
    std::optional<u16> FindObjectOver(const InterfaceView& view, u16 root, const Rect_s& rect)
    {
        auto best = std::optional<u16>{};
        auto bestOverlap = 0;
        for (const auto* const component : view.GetTree(root))
        {
            if (component->type != ComponentType_e::Model || !view.IsVisible(*component))
            {
                continue;
            }

            const auto object = view.GetObject(*component);
            const auto overlap = object ? GetOverlap(GetRect(view, *component), rect) : 0;
            if (overlap > bestOverlap)
            {
                best = object;
                bestOverlap = overlap;
            }
        }

        return best;
    }

    // What follows the verb and amount of a button's option, such as "Soft Leathers" for the tanner's
    // "Tan 1 @lre@Soft Leathers".
    std::string GetOptionSubject(std::string_view option)
    {
        const auto cleaned = ChatDialog::CleanText(option);
        const auto words = SplitWords(cleaned);
        auto subject = std::string{};
        for (std::size_t i = 2; i < words.size(); ++i)
        {
            subject += subject.empty() ? "" : " ";
            subject += words[i];
        }

        return subject;
    }

    std::string_view GetObjName(const GameCache_s& cache, s32 id)
    {
        const auto* const type = cache.FindObj(id);
        return type != nullptr ? type->name : std::string_view{};
    }

    std::optional<MakeProduct_s> ToProduct(const InterfaceView& view, u16 root, const std::vector<const IfComponent_s*>& group)
    {
        auto product = MakeProduct_s{};
        for (const auto* const button : group)
        {
            if (const auto amount = ChatDialog::ParseAmount(button->buttonText))
            {
                product.buttons.push_back({.com = button->id, .amount = *amount});
            }
        }

        if (product.buttons.size() < 2)
        {
            return std::nullopt;
        }

        const auto object = FindObjectOver(view, root, GetRect(view, *group.front()));
        product.item = object ? static_cast<s32>(*object) : -1;
        for (const auto* const button : group)
        {
            product.name = ChatDialog::CleanText(view.GetText(*button));
            if (!product.name.empty())
            {
                return product;
            }
        }

        product.name = object ? std::string{GetObjName(view.GetCache(), *object)} : GetOptionSubject(group.front()->buttonText);
        return product;
    }
}

std::string ChatDialog::CleanText(std::string_view text)
{
    auto spaced = std::string{};
    for (std::size_t i = 0; i < text.size(); ++i)
    {
        if (text[i] == '\\' && i + 1 < text.size() && text[i + 1] == 'n')
        {
            spaced += ' ';
            ++i;
        }
        else if (text[i] == '@' && i + COLOUR_TAG_SIZE - 1 < text.size() && text[i + COLOUR_TAG_SIZE - 1] == '@')
        {
            i += COLOUR_TAG_SIZE - 1;
        }
        else
        {
            spaced += text[i] == '\n' ? ' ' : text[i];
        }
    }

    auto cleaned = std::string{};
    for (const auto word : SplitWords(spaced))
    {
        cleaned += cleaned.empty() ? "" : " ";
        cleaned += word;
    }

    return cleaned;
}

std::optional<s32> ChatDialog::ParseAmount(std::string_view option)
{
    const auto cleaned = Lower(CleanText(option));
    const auto words = SplitWords(cleaned);
    if (words.size() < 2)
    {
        return std::nullopt;
    }

    const auto word = words[1];
    if (word == "x")
    {
        return MakeButton_s::X;
    }

    if (word == "all")
    {
        return MakeButton_s::ALL;
    }

    auto amount = s32{0};
    const auto [end, error] = std::from_chars(word.data(), word.data() + word.size(), amount);
    if (error != std::errc{} || end != word.data() + word.size() || amount <= 0)
    {
        return std::nullopt;
    }

    return amount;
}

std::optional<u16> ChatDialog::FindContinue(const InterfaceView& view)
{
    const auto& interfaces = view.GetInterfaces();
    if (interfaces.chatModal < 0)
    {
        return std::nullopt;
    }

    for (const auto* const component : view.GetTree(static_cast<u16>(interfaces.chatModal)))
    {
        if (component->buttonType == ButtonType_e::Continue && view.IsVisible(*component))
        {
            return component->id;
        }
    }

    return std::nullopt;
}

std::vector<ChatOption_s> ChatDialog::GetOptions(const InterfaceView& view)
{
    const auto chatModal = view.GetInterfaces().chatModal;
    auto options = std::vector<ChatOption_s>{};
    if (chatModal < 0)
    {
        return options;
    }

    auto buttons = std::vector<const IfComponent_s*>{};
    for (const auto& group : GroupButtons(view, static_cast<u16>(chatModal)))
    {
        if (group.size() == 1)
        {
            buttons.push_back(group.front());
        }
    }

    // In drawing order, which the groups may not keep when a later button shares an earlier one's place.
    for (const auto* const component : view.GetTree(static_cast<u16>(chatModal)))
    {
        if (component->type != ComponentType_e::Text || std::ranges::find(buttons, component) == buttons.end())
        {
            continue;
        }

        auto text = CleanText(view.GetText(*component));
        if (!text.empty())
        {
            options.push_back({.com = component->id, .text = std::move(text)});
        }
    }

    return options;
}

std::vector<std::string> ChatDialog::GetTexts(const InterfaceView& view)
{
    const auto chatModal = view.GetInterfaces().chatModal;
    auto texts = std::vector<std::string>{};
    if (chatModal < 0)
    {
        return texts;
    }

    for (const auto* const component : view.GetTree(static_cast<u16>(chatModal)))
    {
        if (component->type != ComponentType_e::Text || !view.IsVisible(*component))
        {
            continue;
        }

        auto text = CleanText(view.GetText(*component));
        if (!text.empty())
        {
            texts.push_back(std::move(text));
        }
    }

    return texts;
}

std::vector<MakeProduct_s> ChatDialog::GetMakeProducts(const InterfaceView& view)
{
    const auto& interfaces = view.GetInterfaces();
    const auto root = interfaces.chatModal >= 0 ? interfaces.chatModal : interfaces.mainModal;
    auto products = std::vector<MakeProduct_s>{};
    if (root < 0)
    {
        return products;
    }

    for (const auto& group : GroupButtons(view, static_cast<u16>(root)))
    {
        if (auto product = ToProduct(view, static_cast<u16>(root), group))
        {
            products.push_back(std::move(*product));
        }
    }

    return products;
}

std::vector<MakeSlot_s> ChatDialog::GetMakePanel(const InterfaceView& view, const GameState_s& state)
{
    const auto mainModal = view.GetInterfaces().mainModal;
    auto slots = std::vector<MakeSlot_s>{};
    if (mainModal < 0)
    {
        return slots;
    }

    for (const auto* const component : view.GetTree(static_cast<u16>(mainModal)))
    {
        const auto makes = std::ranges::any_of(component->options, [](const std::string& option) { return Lower(option).starts_with("make"); });
        if (component->type != ComponentType_e::Inv || !makes || component->width == 0 || !view.IsVisible(*component))
        {
            continue;
        }

        const auto inventory = state.inventories.find(component->id);
        if (inventory == state.inventories.end())
        {
            continue;
        }

        const auto corner = view.GetPosition(*component);
        const auto& items = inventory->second.slots;
        for (std::size_t slot = 0; slot < items.size(); ++slot)
        {
            if (items[slot].id < 0)
            {
                continue;
            }

            const auto column = static_cast<s32>(slot % component->width);
            const auto row = static_cast<s32>(slot / component->width);
            const auto rect = Rect_s{
                .x = corner.x + column * (SLOT_SIZE + component->marginX),
                .y = corner.y + row * (SLOT_SIZE + component->marginY),
                .width = SLOT_SIZE,
                .height = SLOT_SIZE,
            };

            const auto object = FindObjectOver(view, static_cast<u16>(mainModal), rect);
            slots.push_back({
                .com = component->id,
                .slot = static_cast<u16>(slot),
                .id = items[slot].id,
                .product = object ? static_cast<s32>(*object) : items[slot].id,
            });
        }
    }

    return slots;
}
