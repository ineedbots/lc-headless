#include "pch.hpp"
#include "InterfacePacketDecoder.hpp"

#include "../../Console/Logger.hpp"
#include "../../Io/Packet.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../State/GameEvent_s.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Interfaces_s.hpp"
#include "PacketFields.hpp"
#include "StateLog.hpp"

namespace
{
    constexpr auto RGB555_CHANNEL_MASK = 0x1F;

    u32 ToRgb888(u16 rgb555)
    {
        const auto red = static_cast<u32>((rgb555 >> 10) & RGB555_CHANNEL_MASK);
        const auto green = static_cast<u32>((rgb555 >> 5) & RGB555_CHANNEL_MASK);
        const auto blue = static_cast<u32>(rgb555 & RGB555_CHANNEL_MASK);
        return (red << 19) + (green << 11) + (blue << 3);
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

    void AddModalEvent(GameState_s& state)
    {
        auto& interfaces = state.interfaces;
        ++interfaces.modalChanges;
        StateLog::AddEvent(state, ModalChanged_s{.mainModal = interfaces.mainModal, .sideModal = interfaces.sideModal, .chatModal = interfaces.chatModal});
    }

    void DecodeOpenMain(Packet& packet, GameState_s& state)
    {
        auto& interfaces = state.interfaces;
        CloseModals(interfaces);
        interfaces.mainModal = packet.G2();
        AddModalEvent(state);
    }

    void DecodeOpenSide(Packet& packet, GameState_s& state)
    {
        auto& interfaces = state.interfaces;
        CloseModals(interfaces);
        interfaces.sideModal = packet.G2();
        AddModalEvent(state);
    }

    void DecodeOpenChat(Packet& packet, GameState_s& state)
    {
        auto& interfaces = state.interfaces;
        interfaces.mainModal = -1;
        interfaces.sideModal = -1;
        interfaces.chatModal = packet.G2();
        AddModalEvent(state);
    }

    void DecodeOpenMainSide(Packet& packet, GameState_s& state)
    {
        auto& interfaces = state.interfaces;
        CloseModals(interfaces);
        interfaces.mainModal = packet.G2();
        interfaces.sideModal = packet.G2();
        AddModalEvent(state);
    }

    void DecodeClose(GameState_s& state)
    {
        CloseModals(state.interfaces);
        AddModalEvent(state);
    }

    void DecodeCountDialog(GameState_s& state)
    {
        state.interfaces.countDialogOpen = true;
        AddModalEvent(state);
    }

    void DecodeTab(Packet& packet, GameState_s& state, Logger& logger)
    {
        const auto com = PacketFields::ReadId(packet);
        const auto tab = packet.G1();
        auto& tabs = state.interfaces.tabs;
        if (tab >= tabs.size())
        {
            logger.Warning("IF_SETTAB for tab {}, past the last of {}", tab, tabs.size());
            return;
        }

        tabs[tab] = com;
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
}

void InterfacePacketDecoder::Decode(ServerProt_e prot, Packet& packet, GameState_s& state, Logger& logger)
{
    auto& interfaces = state.interfaces;
    switch (prot)
    {
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
        DecodeClose(state);
        return;
    case ServerProt_e::IfOpenOverlay:
        interfaces.overlay = packet.G2B();
        return;
    case ServerProt_e::IfSetTab:
        DecodeTab(packet, state, logger);
        return;
    case ServerProt_e::IfSetTabActive:
        interfaces.activeTab = packet.G1();
        return;
    case ServerProt_e::PCountDialog:
        DecodeCountDialog(state);
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
    case ServerProt_e::IfSetRecol:
        // Recolours a component's model, which only rendering needs.
        packet.SetPos(packet.GetLength());
        return;

    default:
        assert(false && "Not an interface packet");
        return;
    }
}
