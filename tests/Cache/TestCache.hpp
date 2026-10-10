#pragma once

#include "Cache/GameCache_s.hpp"
#include "Cache/IfComponent_s.hpp"
#include "Cache/LocType_s.hpp"
#include "Cache/NpcType_s.hpp"
#include "Cache/ObjType_s.hpp"
#include "Game/Tile_s.hpp"

// A loc in a map square, by absolute tile, on the level it's seen on.
struct TestLoc_s
{
    u16 id = 0;
    Tile_s tile;
    u8 shape = 10;
    u8 angle = 0;
};

// Builds a GameCache_s's contents in place, without files. Names must be string literals, which outlive
// the cache; an empty option is a slot the menu doesn't show.
class TestCache
{
public:
    static constexpr u16 INVENTORY = 3214;
    static constexpr s32 INVENTORY_SIZE = 28;
    static constexpr u16 EQUIPMENT = 1688;
    static constexpr u16 BANK = 5382;
    static constexpr u16 BANK_INVENTORY = 2006;
    static constexpr u16 RUN_OFF_BUTTON = 152;
    static constexpr u16 RUN_ON_BUTTON = 153;
    static constexpr u16 RUN_VARP = 173;
    // SetTradeScreen's interface: an "Accept" label over an unlabelled Ok rect, a Close button, and a
    // layer that starts hidden with a "Waiting" label in it, as trademain has them.
    static constexpr u16 TRADE_SCREEN = 300;
    static constexpr u16 TRADE_ACCEPT = 301;
    static constexpr u16 TRADE_ACCEPT_LABEL = 302;
    static constexpr u16 TRADE_DECLINE = 303;
    static constexpr u16 TRADE_STATUS_LAYER = 304;
    static constexpr u16 TRADE_STATUS = 305;
    // SetChatInterfaces': a dialogue page with a continue button, two options as multi2 has them, and a
    // make menu of one product, a stack of Make X, 10, 5 and 1, as skill_multi has it.
    static constexpr u16 DIALOGUE = 310;
    static constexpr u16 DIALOGUE_TEXT = 311;
    static constexpr u16 DIALOGUE_CONTINUE = 312;
    static constexpr u16 OPTIONS = 320;
    static constexpr u16 OPTION_ONE = 321;
    static constexpr u16 OPTION_TWO = 322;
    static constexpr u16 MAKE_MENU = 330;
    static constexpr u16 MAKE_X = 331;
    static constexpr u16 MAKE_10 = 332;
    static constexpr u16 MAKE_5 = 333;
    static constexpr u16 MAKE_1 = 334;
    // SetBankScreen's: the bank, BANK in BANK_SCREEN beside BANK_INVENTORY in BANK_SIDE, as bank_main and
    // bank_side have them, with "Note" and "Item" labels over the note mode's Select buttons.
    static constexpr u16 BANK_SCREEN = 5292;
    static constexpr u16 BANK_NOTE = 5386;
    static constexpr u16 BANK_ITEM = 5387;
    static constexpr u16 BANK_NOTE_LABEL = 5390;
    static constexpr u16 BANK_ITEM_LABEL = 5391;
    static constexpr u16 BANK_SIDE = 2005;

    TestCache() = delete;

    static NpcType_s& AddNpc(GameCache_s& cache, u16 id, std::string_view name, std::initializer_list<std::string_view> ops = {});
    static ObjType_s& AddObj(GameCache_s& cache, u16 id, std::string_view name, std::initializer_list<std::string_view> ops = {}, std::initializer_list<std::string_view> inventoryOps = {});
    static LocType_s& AddLoc(GameCache_s& cache, u16 id, std::string_view name, std::initializer_list<std::string_view> ops = {});
    // Gives the cache the 289 cache's components and run varp, as the constants above.
    static void SetComponents(GameCache_s& cache);
    // Adds the components, setting each child's parent from the layers that list it.
    static void AddComponents(GameCache_s& cache, std::initializer_list<IfComponent_s> components);
    static void SetTradeScreen(GameCache_s& cache);
    static void SetChatInterfaces(GameCache_s& cache);
    static void SetBankScreen(GameCache_s& cache);
    // Replaces the map with squares holding these locs and blocked tiles.
    static void SetMap(GameCache_s& cache, std::span<const TestLoc_s> locs, std::span<const Tile_s> blocked = {});
};
