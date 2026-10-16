#include "pch.hpp"
#include "Menus.hpp"

#include "../../Cache/GameCache_s.hpp"
#include "../../Cache/IfComponent_s.hpp"
#include "../../Cache/LocType_s.hpp"
#include "../../Cache/NpcType_s.hpp"
#include "../../Cache/ObjType_s.hpp"
#include "../../Config/Revision_e.hpp"
#include "../../Utils/StringUtils.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Npc_s.hpp"
#include "MenuOp.hpp"

namespace
{
    using Menu = Menus::Menu;

    constexpr auto TAKE_SLOT = MenuOp::GetSlot(MenuOp::TAKE);
    constexpr auto DROP_SLOT = MenuOp::GetSlot(MenuOp::DROP);
    // The 225 webclient's player menu, by slot: OPPLAYER1 to OPPLAYER4.
    constexpr auto PLAYER_MENU_225 = Menu{"Duel-with", "Attack", "Follow", "Trade with", ""};

    Menu MakeMenu(const GameCache_s& cache, std::span<const u16> ops)
    {
        auto menu = Menu{};
        for (auto slot = std::size_t{0}; slot < menu.size() && slot < ops.size(); ++slot)
        {
            menu[slot] = cache.GetOption(ops[slot]);
        }

        return menu;
    }

    Menu MakeInventoryMenu(const IfComponent_s& component)
    {
        auto menu = Menu{};
        for (auto slot = std::size_t{0}; slot < menu.size(); ++slot)
        {
            menu[slot] = component.options[slot];
        }

        return menu;
    }

    std::string DescribeMenu(const Menu& menu)
    {
        auto text = std::string{};
        for (auto slot = std::size_t{0}; slot < menu.size(); ++slot)
        {
            if (menu[slot].empty())
            {
                continue;
            }

            if (!text.empty())
            {
                text += ", ";
            }

            std::format_to(std::back_inserter(text), "{} ({})", menu[slot], slot + 1);
        }

        return text.empty() ? "none" : text;
    }

    u8 ChooseOption(const Menu& menu, std::string_view text, std::string_view target)
    {
        const auto found = std::ranges::find_if(menu, [text](std::string_view option)
        {
            return !option.empty() && StringUtils::EqualsIgnoringCase(option, text);
        });

        if (found == menu.end())
        {
            throw std::invalid_argument{std::format("{} has no option '{}'; its options are {}", target, text, DescribeMenu(menu))};
        }

        return static_cast<u8>(found - menu.begin() + 1);
    }

    std::string DescribeType(std::string_view kind, s32 id, std::string_view name)
    {
        if (name.empty())
        {
            return std::format("{} {}", kind, id);
        }

        return std::format("{} ({} {})", name, kind, id);
    }

    template <typename T>
    const T& RequireType(const T* type, std::string_view kind, s32 id)
    {
        if (type == nullptr)
        {
            throw std::invalid_argument{std::format("{} {} isn't in the cache, so its options can only be chosen by number", kind, id)};
        }

        return *type;
    }
}

Menu Menus::GetNpcMenu(const GameCache_s& cache, s32 npc)
{
    const auto* const type = cache.FindNpc(npc);
    return type == nullptr ? Menu{} : MakeMenu(cache, type->ops);
}

Menu Menus::GetLocMenu(const GameCache_s& cache, s32 loc)
{
    const auto* const type = cache.FindLoc(loc);
    return type == nullptr ? Menu{} : MakeMenu(cache, type->ops);
}

Menu Menus::GetGroundItemMenu(const GameCache_s& cache, s32 obj)
{
    const auto* const type = cache.FindObj(obj);
    auto menu = type == nullptr ? Menu{} : MakeMenu(cache, type->ops);
    if (menu[TAKE_SLOT].empty())
    {
        menu[TAKE_SLOT] = MenuOp::TAKE_OPTION;
    }

    return menu;
}

Menu Menus::GetItemMenu(const GameCache_s& cache, s32 obj)
{
    const auto* const type = cache.FindObj(obj);
    auto menu = type == nullptr ? Menu{} : MakeMenu(cache, type->inventoryOps);
    if (menu[DROP_SLOT].empty())
    {
        menu[DROP_SLOT] = MenuOp::DROP_OPTION;
    }

    return menu;
}

std::optional<Menu> Menus::GetInventoryMenu(const GameCache_s& cache, u16 com)
{
    const auto* const component = cache.FindComponent(com);
    if (component == nullptr || component->type != ComponentType_e::Inv || component->objOps)
    {
        return std::nullopt;
    }

    return MakeInventoryMenu(*component);
}

Menu Menus::GetPlayerMenu(const GameState_s& state, Revision_e revision)
{
    // The server still decides whether an option is allowed where the player is.
    if (revision < Revision_e::Rev289)
    {
        return PLAYER_MENU_225;
    }

    auto menu = Menu{};
    for (auto slot = std::size_t{0}; slot < menu.size() && slot < state.playerOps.size(); ++slot)
    {
        if (state.playerOps[slot])
        {
            menu[slot] = state.playerOps[slot]->text;
        }
    }

    return menu;
}

std::optional<u8> Menus::FindNpcOp(const GameState_s& state, const GameCache_s& cache, u16 index, std::string_view text)
{
    const auto* const npc = state.FindNpc(index);
    if (npc == nullptr)
    {
        return std::nullopt;
    }

    const auto& type = RequireType(cache.FindNpc(npc->type), "NPC", npc->type);
    return ChooseOption(GetNpcMenu(cache, type.id), text, DescribeType("NPC", type.id, type.name));
}

u8 Menus::FindPlayerOp(const GameState_s& state, Revision_e revision, std::string_view text)
{
    return ChooseOption(GetPlayerMenu(state, revision), text, "a player");
}

u8 Menus::FindLocOp(const GameCache_s& cache, u16 loc, std::string_view text)
{
    const auto& type = RequireType(cache.FindLoc(loc), "loc", loc);
    return ChooseOption(GetLocMenu(cache, type.id), text, DescribeType("loc", type.id, type.name));
}

u8 Menus::FindGroundItemOp(const GameCache_s& cache, u16 obj, std::string_view text)
{
    const auto& type = RequireType(cache.FindObj(obj), "item", obj);
    return ChooseOption(GetGroundItemMenu(cache, type.id), text, DescribeType("item", type.id, type.name));
}

u8 Menus::FindItemOp(const GameCache_s& cache, s32 obj, std::string_view text)
{
    const auto& type = RequireType(cache.FindObj(obj), "item", obj);
    return ChooseOption(GetItemMenu(cache, type.id), text, DescribeType("item", type.id, type.name));
}

// Unlike GetInventoryMenu, an inventory whose items have options of their own still has these.
u8 Menus::FindInventoryOption(const GameCache_s& cache, u16 com, std::string_view text)
{
    const auto* const component = cache.FindComponent(com);
    if (component == nullptr || component->type != ComponentType_e::Inv)
    {
        throw std::invalid_argument{std::format("component {} isn't an inventory", com)};
    }

    return ChooseOption(MakeInventoryMenu(*component), text, std::format("inventory {}", com));
}
