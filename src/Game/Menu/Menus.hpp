#pragma once

#include "../../Cache/GameCache_s.hpp"
#include "../../Config/Revision_e.hpp"
#include "../State/GameState_s.hpp"
#include "MenuOp.hpp"

// Each kind of target's right-click menu, by slot, as the webclient builds it, and choosing an option from one.
class Menus
{
public:
    // A target's options by slot; empty where there's none.
    using Menu = std::array<std::string_view, MenuOp::COUNT>;

    Menus() = delete;

    // With the "Take" and "Drop" the menu adds where the type has nothing there. A type the cache doesn't
    // have has an empty menu, apart from those.
    [[nodiscard]] static Menu GetNpcMenu(const GameCache_s& cache, s32 npc);
    [[nodiscard]] static Menu GetLocMenu(const GameCache_s& cache, s32 loc);
    [[nodiscard]] static Menu GetGroundItemMenu(const GameCache_s& cache, s32 obj);
    [[nodiscard]] static Menu GetItemMenu(const GameCache_s& cache, s32 obj);
    // The options of an inventory whose menu offers its own rather than its items', such as the bank's
    // "Withdraw 1", or nullopt for one that offers its items', such as the backpack.
    [[nodiscard]] static std::optional<Menu> GetInventoryMenu(const GameCache_s& cache, u16 com);
    // 289's comes from SET_PLAYER_OP. 225 has no such packet, and its webclient's menu is fixed.
    [[nodiscard]] static Menu GetPlayerMenu(const GameState_s& state, Revision_e revision);

    // Matched without regard to case. Text that matches no option throws std::invalid_argument, listing the
    // options there are, as does a type the cache doesn't have.
    // Nullopt when the NPC isn't tracked.
    [[nodiscard]] static std::optional<u8> FindNpcOp(const GameState_s& state, const GameCache_s& cache, u16 index, std::string_view text);
    [[nodiscard]] static u8 FindPlayerOp(const GameState_s& state, Revision_e revision, std::string_view text);
    [[nodiscard]] static u8 FindLocOp(const GameCache_s& cache, u16 loc, std::string_view text);
    [[nodiscard]] static u8 FindGroundItemOp(const GameCache_s& cache, u16 obj, std::string_view text);
    [[nodiscard]] static u8 FindItemOp(const GameCache_s& cache, s32 obj, std::string_view text);
    // Such as the bank's "Withdraw 5".
    [[nodiscard]] static u8 FindInventoryOption(const GameCache_s& cache, u16 com, std::string_view text);
};
