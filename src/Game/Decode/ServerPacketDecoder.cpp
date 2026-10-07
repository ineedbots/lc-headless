#include "pch.hpp"
#include "ServerPacketDecoder.hpp"

#include "../../Core/Logger.hpp"
#include "../../Io/Packet.hpp"
#include "../Protocol/Base37.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../Protocol/WordPack.hpp"
#include "../ProtocolError.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Interfaces_s.hpp"
#include "../State/Social_s.hpp"
#include "../Tile_s.hpp"
#include "NpcInfoDecoder.hpp"
#include "PlayerInfoDecoder.hpp"
#include "StateLog.hpp"
#include "ZoneDecoder.hpp"

namespace
{
    constexpr auto NONE = u16{0xFFFF};
    constexpr auto ITEM_COUNT_ESCAPE = u8{255};
    constexpr auto BUILD_AREA_RADIUS_ZONES = 6;
    constexpr auto ZONE_SIZE = 8;
    constexpr auto NAME37_SIZE = std::size_t{8};
    constexpr auto MAX_BASE_LEVEL_INDEX = std::size_t{98};
    constexpr auto RGB555_CHANNEL_MASK = 0x1F;
    constexpr auto TRADE_REQUEST_SUFFIX = ":tradereq:"sv;
    constexpr auto DUEL_REQUEST_SUFFIX = ":duelreq:"sv;
    constexpr auto TRADE_REQUEST_TEXT = "wishes to trade with you."sv;
    constexpr auto DUEL_REQUEST_TEXT = "wishes to duel with you."sv;
    constexpr auto REMOVED_PLAYER_OP = "null"sv;

    constexpr auto HINT_NPC = u8{1};
    constexpr auto HINT_FIRST_TILE = u8{2};
    constexpr auto HINT_LAST_TILE = u8{6};
    constexpr auto HINT_PLAYER = u8{10};

    const auto LEVEL_XP = []
    {
        constexpr auto MAX_LEVEL = 99;
        auto table = std::array<s32, MAX_LEVEL>{};
        auto total = 0.0;
        for (auto i = 0; i < MAX_LEVEL; ++i)
        {
            const auto level = i + 1;
            total += static_cast<s32>(level + std::pow(2.0, level / 7.0) * 300.0);
            table[static_cast<std::size_t>(i)] = static_cast<s32>(total / 4);
        }

        return table;
    }();

    s32 ToId(u16 value)
    {
        return value == NONE ? -1 : value;
    }

    u8 GetBaseLevel(s32 xp)
    {
        auto level = 1;
        for (std::size_t i = 0; i < MAX_BASE_LEVEL_INDEX; ++i)
        {
            if (xp >= LEVEL_XP[i])
            {
                level = static_cast<s32>(i) + 2;
            }
        }

        return static_cast<u8>(level);
    }

    u32 ToRgb888(u16 rgb555)
    {
        const auto red = static_cast<u32>((rgb555 >> 10) & RGB555_CHANNEL_MASK);
        const auto green = static_cast<u32>((rgb555 >> 5) & RGB555_CHANNEL_MASK);
        const auto blue = static_cast<u32>(rgb555 & RGB555_CHANNEL_MASK);
        return (red << 19) + (green << 11) + (blue << 3);
    }

    bool EqualsIgnoringCase(std::string_view left, std::string_view right)
    {
        return std::ranges::equal(left, right, [](char a, char b)
        {
            return std::tolower(static_cast<unsigned char>(a)) == std::tolower(static_cast<unsigned char>(b));
        });
    }

    u64 ReadName37(Packet& packet)
    {
        return std::bit_cast<u64>(packet.G8());
    }

    Item_s ReadItem(Packet& packet)
    {
        const auto id = packet.G2();
        auto count = s32{packet.G1()};
        if (count == ITEM_COUNT_ESCAPE)
        {
            count = packet.G4();
        }

        if (id == 0)
        {
            return {};
        }

        return {.id = id - 1, .count = count};
    }

    Component_s& TouchComponent(GameState_s& state, u16 com)
    {
        auto& component = state.interfaces.components[com];
        component.tick = state.tick;
        return component;
    }

    void CloseModals(Interfaces_s& interfaces)
    {
        interfaces.mainModal = -1;
        interfaces.sideModal = -1;
        interfaces.chatModal = -1;
        interfaces.countDialogOpen = false;
    }

    void DecodeOpenMain(Packet& packet, GameState_s& state)
    {
        auto& interfaces = state.interfaces;
        CloseModals(interfaces);
        interfaces.mainModal = packet.G2();
    }

    void DecodeOpenSide(Packet& packet, GameState_s& state)
    {
        auto& interfaces = state.interfaces;
        CloseModals(interfaces);
        interfaces.sideModal = packet.G2();
    }

    void DecodeOpenChat(Packet& packet, GameState_s& state)
    {
        auto& interfaces = state.interfaces;
        interfaces.mainModal = -1;
        interfaces.sideModal = -1;
        interfaces.chatModal = packet.G2();
    }

    void DecodeOpenMainSide(Packet& packet, GameState_s& state)
    {
        auto& interfaces = state.interfaces;
        CloseModals(interfaces);
        interfaces.mainModal = packet.G2();
        interfaces.sideModal = packet.G2();
    }

    void DecodeSetModel(Packet& packet, GameState_s& state, ComponentModelKind_e kind)
    {
        const auto com = packet.G2();
        auto model = ComponentModel_s{.kind = kind};
        if (kind != ComponentModelKind_e::PlayerHead)
        {
            model.id = packet.G2();
        }

        if (kind == ComponentModelKind_e::Object)
        {
            model.zoom = packet.G2();
        }

        TouchComponent(state, com).model = model;
    }

    void DecodeInvFull(Packet& packet, GameState_s& state)
    {
        const auto com = packet.G2();
        const auto size = packet.G2();
        auto inventory = Inventory_s{.com = com, .tick = state.tick};
        inventory.slots.reserve(size);
        for (auto slot = 0; slot < size; ++slot)
        {
            inventory.slots.push_back(ReadItem(packet));
        }

        state.inventories.insert_or_assign(com, std::move(inventory));
    }

    void DecodeInvPartial(Packet& packet, GameState_s& state)
    {
        const auto com = packet.G2();
        auto& inventory = state.inventories[com];
        inventory.com = com;
        inventory.tick = state.tick;
        while (packet.GetAvailable() > 0)
        {
            const auto slot = static_cast<std::size_t>(packet.GSmart());
            const auto item = ReadItem(packet);
            if (slot >= inventory.slots.size())
            {
                inventory.slots.resize(slot + 1);
            }

            inventory.slots[slot] = item;
        }
    }

    void DecodeMessageGame(Packet& packet, GameState_s& state)
    {
        auto text = packet.GJStr();
        const auto addRequest = [&state, &text](MessageType_e type, std::string_view requestText)
        {
            auto sender = text.substr(0, text.find(':'));
            const auto sender37 = Base37::Encode(sender);
            StateLog::AddMessage(state, type, std::move(sender), sender37, 0, std::string{requestText});
        };

        if (text.ends_with(TRADE_REQUEST_SUFFIX))
        {
            addRequest(MessageType_e::TradeRequest, TRADE_REQUEST_TEXT);
            return;
        }

        if (text.ends_with(DUEL_REQUEST_SUFFIX))
        {
            addRequest(MessageType_e::DuelRequest, DUEL_REQUEST_TEXT);
            return;
        }

        StateLog::AddMessage(state, MessageType_e::Game, {}, 0, 0, std::move(text));
    }

    void DecodeFriend(Packet& packet, GameState_s& state)
    {
        const auto name37 = ReadName37(packet);
        const auto world = packet.G1();
        auto& friends = state.social.friends;
        const auto found = std::ranges::find(friends, name37, &Friend_s::name37);
        if (found != friends.end())
        {
            found->world = world;
            return;
        }

        friends.push_back({.name37 = name37, .name = Base37::DecodeDisplayName(name37), .world = world});
    }

    void DecodeIgnoreList(Packet& packet, GameState_s& state)
    {
        auto& ignores = state.social.ignores;
        ignores.clear();
        while (packet.GetAvailable() >= NAME37_SIZE)
        {
            ignores.push_back(ReadName37(packet));
        }

        // A partial name at the end is skipped, as the webclient reads only whole entries.
        packet.SetPos(packet.GetLength());
    }

    void DecodeHintArrow(Packet& packet, GameState_s& state)
    {
        const auto type = packet.G1();
        if (type == HINT_NPC || type == HINT_PLAYER)
        {
            const auto kind = type == HINT_NPC ? HintArrowKind_e::Npc : HintArrowKind_e::Player;
            state.hintArrow = HintArrow_s{.kind = kind, .index = packet.G2()};
        }
        else if (type >= HINT_FIRST_TILE && type <= HINT_LAST_TILE)
        {
            auto arrow = HintArrow_s{.kind = HintArrowKind_e::Tile, .position = type};
            arrow.tile.x = packet.G2();
            arrow.tile.z = packet.G2();
            arrow.tile.level = state.localPlayer.tile.level;
            arrow.height = packet.G1();
            state.hintArrow = arrow;
        }
        else
        {
            state.hintArrow.reset();
        }

        // Every type pads its fields to the same fixed size.
        packet.SetPos(packet.GetLength());
    }

    void DecodeSetPlayerOp(Packet& packet, GameState_s& state)
    {
        const auto op = packet.G1();
        const auto priority = packet.G1();
        auto text = packet.GJStr();
        if (op < 1 || op > GameState_s::PLAYER_OP_COUNT)
        {
            return;
        }

        auto& slot = state.playerOps[op - 1];
        if (EqualsIgnoringCase(text, REMOVED_PLAYER_OP))
        {
            slot.reset();
            return;
        }

        slot = PlayerOp_s{.text = std::move(text), .deprioritised = priority == 0};
    }

    void DecodeRebuild(Packet& packet, GameState_s& state)
    {
        const auto zoneX = packet.G2();
        const auto zoneZ = packet.G2();
        state.buildArea = BuildArea_s{
            .loaded = true,
            .centreZoneX = zoneX,
            .centreZoneZ = zoneZ,
            .baseX = (zoneX - BUILD_AREA_RADIUS_ZONES) * ZONE_SIZE,
            .baseZ = (zoneZ - BUILD_AREA_RADIUS_ZONES) * ZONE_SIZE,
        };

        // The server resends every zone in view after a rebuild.
        state.groundItems.clear();
        state.locChanges.clear();
    }

    void DecodeLastLogin(Packet& packet, GameState_s& state)
    {
        auto lastLogin = LastLogin_s{};
        lastLogin.lastIp = std::bit_cast<u32>(packet.G4());
        lastLogin.daysSinceLogin = packet.G2();
        lastLogin.daysSinceRecoveryChange = packet.G1();
        lastLogin.unreadMessages = packet.G2();
        lastLogin.warnMembers = packet.G1() == 1;
        state.lastLogin = lastLogin;
    }

    void ResetAnimations(GameState_s& state)
    {
        state.localPlayer.animation.id = -1;
        for (auto& player : state.players)
        {
            player.animation.id = -1;
        }

        for (auto& npc : state.npcs)
        {
            npc.animation.id = -1;
        }
    }

    void SkipCamera(Packet& packet, GameState_s& state)
    {
        state.cinematicCamera = true;
        packet.SetPos(packet.GetLength());
    }
}

ServerPacketDecoder::ServerPacketDecoder(std::shared_ptr<Logger> logger)
    : m_logger{std::move(logger)}
{
    assert(m_logger && "ServerPacketDecoder needs a logger");
}

void ServerPacketDecoder::Decode(ServerProt_e prot, std::span<const u8> payload, GameState_s& state)
{
    const auto name = ServerProt::GetName(static_cast<u8>(prot));
    auto packet = Packet{payload};
    try
    {
        DecodePacket(prot, packet, state);
    }
    catch (const std::out_of_range& e)
    {
        throw ProtocolError{std::format("{} payload of {} bytes is too short: {}", name, payload.size(), e.what())};
    }

    if (packet.GetAvailable() != 0)
    {
        throw ProtocolError{std::format("{} payload has {} bytes left over", name, packet.GetAvailable())};
    }
}

void ServerPacketDecoder::Reset()
{
    m_playerInfo.Reset();
    m_privateMessageIds.clear();
}

void ServerPacketDecoder::DecodePacket(ServerProt_e prot, Packet& packet, GameState_s& state)
{
    auto& interfaces = state.interfaces;
    switch (prot)
    {
    case ServerProt_e::PlayerInfo:
        DecodePlayerInfo(packet, state);
        return;
    case ServerProt_e::NpcInfo:
        NpcInfoDecoder::Decode(packet.GetData(), state);
        packet.SetPos(packet.GetLength());
        return;
    case ServerProt_e::RebuildNormal:
        DecodeRebuild(packet, state);
        return;

    case ServerProt_e::UpdateZoneFullFollows:
        m_zone.SetZone(packet);
        m_zone.ResetZone(state);
        return;
    case ServerProt_e::UpdateZonePartialFollows:
        m_zone.SetZone(packet);
        return;
    case ServerProt_e::UpdateZonePartialEnclosed:
        m_zone.SetZone(packet);
        m_zone.DecodeEnclosed(packet, state);
        return;
    case ServerProt_e::ObjAdd:
    case ServerProt_e::ObjDel:
    case ServerProt_e::ObjCount:
    case ServerProt_e::ObjReveal:
    case ServerProt_e::LocAddChange:
    case ServerProt_e::LocDel:
    case ServerProt_e::LocAnim:
    case ServerProt_e::LocMerge:
    case ServerProt_e::MapAnim:
    case ServerProt_e::MapProjAnim:
        m_zone.DecodeSubPacket(static_cast<u8>(prot), packet, state);
        return;

    case ServerProt_e::IfOpenMain:
        DecodeOpenMain(packet, state);
        return;
    case ServerProt_e::IfOpenSide:
        DecodeOpenSide(packet, state);
        return;
    case ServerProt_e::IfOpenChat:
        DecodeOpenChat(packet, state);
        return;
    case ServerProt_e::IfOpenMainSide:
        DecodeOpenMainSide(packet, state);
        return;
    case ServerProt_e::IfClose:
        CloseModals(interfaces);
        return;
    case ServerProt_e::IfOpenOverlay:
        interfaces.overlay = packet.G2B();
        return;
    case ServerProt_e::IfSetTab:
        DecodeTab(packet, state);
        return;
    case ServerProt_e::IfSetTabActive:
        interfaces.activeTab = packet.G1();
        return;
    case ServerProt_e::PCountDialog:
        interfaces.countDialogOpen = true;
        return;
    case ServerProt_e::TutOpen:
        interfaces.tutorialComponent = packet.G2B();
        return;
    case ServerProt_e::TutFlash:
        interfaces.flashingTab = packet.G1();
        return;

    case ServerProt_e::IfSetText:
    {
        const auto com = packet.G2();
        TouchComponent(state, com).text = packet.GJStr();
        return;
    }
    case ServerProt_e::IfSetHide:
    {
        const auto com = packet.G2();
        TouchComponent(state, com).hidden = packet.G1() == 1;
        return;
    }
    case ServerProt_e::IfSetColour:
    {
        const auto com = packet.G2();
        TouchComponent(state, com).colour = ToRgb888(packet.G2());
        return;
    }
    case ServerProt_e::IfSetAnim:
    {
        const auto com = packet.G2();
        TouchComponent(state, com).animation = packet.G2B();
        return;
    }
    case ServerProt_e::IfSetPosition:
    {
        const auto com = packet.G2();
        const auto x = packet.G2B();
        const auto y = packet.G2B();
        TouchComponent(state, com).position = ComponentPosition_s{.x = x, .y = y};
        return;
    }
    case ServerProt_e::IfSetScrollPos:
    {
        const auto com = packet.G2();
        TouchComponent(state, com).scrollPosition = packet.G2();
        return;
    }
    case ServerProt_e::IfSetObject:
        DecodeSetModel(packet, state, ComponentModelKind_e::Object);
        return;
    case ServerProt_e::IfSetModel:
        DecodeSetModel(packet, state, ComponentModelKind_e::Model);
        return;
    case ServerProt_e::IfSetNpcHead:
        DecodeSetModel(packet, state, ComponentModelKind_e::NpcHead);
        return;
    case ServerProt_e::IfSetPlayerHead:
        DecodeSetModel(packet, state, ComponentModelKind_e::PlayerHead);
        return;

    case ServerProt_e::UpdateInvFull:
        DecodeInvFull(packet, state);
        return;
    case ServerProt_e::UpdateInvPartial:
        DecodeInvPartial(packet, state);
        return;
    case ServerProt_e::UpdateInvStopTransmit:
        state.inventories.erase(packet.G2());
        return;

    case ServerProt_e::VarpSmall:
    {
        const auto varp = packet.G2();
        state.varps.insert_or_assign(varp, packet.G1B());
        return;
    }
    case ServerProt_e::VarpLarge:
    {
        const auto varp = packet.G2();
        state.varps.insert_or_assign(varp, packet.G4());
        return;
    }
    case ServerProt_e::ResetClientVarCache:
        return;

    case ServerProt_e::UpdateStat:
        DecodeStat(packet, state);
        return;
    case ServerProt_e::UpdateRunEnergy:
        state.runEnergy = packet.G1();
        return;
    case ServerProt_e::UpdateRunWeight:
        state.runWeight = packet.G2B();
        return;
    case ServerProt_e::UpdatePid:
        state.pid = packet.G2();
        state.members = packet.G1() == 1;
        state.localPlayer.index = state.pid;
        return;
    case ServerProt_e::UpdateRebootTimer:
        state.rebootTimer = RebootTimer_s{.ticks = packet.G2(), .tick = state.tick};
        return;
    case ServerProt_e::LastLoginInfo:
        DecodeLastLogin(packet, state);
        return;
    case ServerProt_e::HintArrow:
        DecodeHintArrow(packet, state);
        return;
    case ServerProt_e::SetPlayerOp:
        DecodeSetPlayerOp(packet, state);
        return;
    case ServerProt_e::SetMultiway:
        state.multiway = packet.G1() == 1;
        return;
    case ServerProt_e::MinimapToggle:
        state.minimapState = packet.G1();
        return;
    case ServerProt_e::UnsetMapFlag:
        state.walkDestination.reset();
        return;
    case ServerProt_e::ResetAnims:
        ResetAnimations(state);
        return;
    case ServerProt_e::Logout:
        return;

    case ServerProt_e::MessageGame:
        DecodeMessageGame(packet, state);
        return;
    case ServerProt_e::MessagePrivate:
        DecodePrivateMessage(packet, state);
        return;
    case ServerProt_e::UpdateFriendList:
        DecodeFriend(packet, state);
        return;
    case ServerProt_e::UpdateIgnoreList:
        DecodeIgnoreList(packet, state);
        return;
    case ServerProt_e::FriendListLoaded:
        state.social.friendServerStatus = packet.G1();
        return;
    case ServerProt_e::ChatFilterSettings:
        state.social.publicMode = packet.G1();
        state.social.privateMode = packet.G1();
        state.social.tradeMode = packet.G1();
        return;

    case ServerProt_e::CamMoveTo:
    case ServerProt_e::CamLookAt:
        SkipCamera(packet, state);
        return;
    case ServerProt_e::CamShake:
        packet.SetPos(packet.GetLength());
        return;
    case ServerProt_e::CamReset:
        state.cinematicCamera = false;
        return;

    case ServerProt_e::MidiSong:
        state.audio.song = ToId(packet.G2());
        return;
    case ServerProt_e::MidiJingle:
        state.audio.jingle = packet.G2();
        packet.G2();
        return;
    case ServerProt_e::SynthSound:
    {
        auto sound = SoundEffect_s{.tick = state.tick};
        sound.id = packet.G2();
        sound.loops = packet.G1();
        sound.delay = packet.G2();
        StateLog::Push(state.sounds, sound);
        return;
    }
    }

    throw ProtocolError{std::format("No decoder for server opcode {}", static_cast<u8>(prot))};
}

void ServerPacketDecoder::DecodePlayerInfo(Packet& packet, GameState_s& state)
{
    m_playerInfo.Decode(packet.GetData(), state);
    packet.SetPos(packet.GetLength());

    ZoneDecoder::PruneInactive(state);
    if (state.walkDestination && state.placed && state.localPlayer.tile == *state.walkDestination)
    {
        state.walkDestination.reset();
    }
}

void ServerPacketDecoder::DecodeStat(Packet& packet, GameState_s& state)
{
    const auto stat = packet.G1();
    const auto xp = packet.G4();
    const auto level = packet.G1();
    if (stat >= state.stats.size())
    {
        m_logger->Warning("UPDATE_STAT for stat {}, past the last of {}", stat, state.stats.size());
        return;
    }

    state.stats[stat] = Stat_s{.xp = xp, .level = level, .baseLevel = GetBaseLevel(xp)};
}

void ServerPacketDecoder::DecodeTab(Packet& packet, GameState_s& state)
{
    const auto com = ToId(packet.G2());
    const auto tab = packet.G1();
    auto& tabs = state.interfaces.tabs;
    if (tab >= tabs.size())
    {
        m_logger->Warning("IF_SETTAB for tab {}, past the last of {}", tab, tabs.size());
        return;
    }

    tabs[tab] = com;
}

void ServerPacketDecoder::DecodePrivateMessage(Packet& packet, GameState_s& state)
{
    const auto from = ReadName37(packet);
    const auto messageId = packet.G4();
    const auto staffLevel = packet.G1();
    auto packed = std::vector<u8>(packet.GetAvailable());
    packet.GData(packed);

    if (std::ranges::find(m_privateMessageIds, messageId) != m_privateMessageIds.end())
    {
        return;
    }

    StateLog::Push(m_privateMessageIds, messageId, MAX_REMEMBERED_MESSAGE_IDS);
    StateLog::AddMessage(state, MessageType_e::Private, Base37::DecodeDisplayName(from), from, staffLevel, WordPack::Unpack(packed));
}
