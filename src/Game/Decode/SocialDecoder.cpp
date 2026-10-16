#include "pch.hpp"
#include "SocialDecoder.hpp"

#include "../../Io/Packet.hpp"
#include "../Protocol/Base37.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../Protocol/WordPack.hpp"
#include "../State/GameState_s.hpp"
#include "../State/Social_s.hpp"
#include "PacketFields.hpp"
#include "StateLog.hpp"

namespace
{
    constexpr auto TRADE_REQUEST_SUFFIX = ":tradereq:"sv;
    constexpr auto DUEL_REQUEST_SUFFIX = ":duelreq:"sv;
    constexpr auto TRADE_REQUEST_TEXT = "wishes to trade with you."sv;
    constexpr auto DUEL_REQUEST_TEXT = "wishes to duel with you."sv;

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
        const auto name37 = PacketFields::ReadName37(packet);
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
        while (packet.GetAvailable() >= PacketFields::NAME37_SIZE)
        {
            ignores.push_back(PacketFields::ReadName37(packet));
        }

        // A partial name at the end is skipped, as the webclient reads only whole entries.
        packet.SetPos(packet.GetLength());
    }
}

void SocialDecoder::Decode(ServerProt_e prot, Packet& packet, GameState_s& state)
{
    switch (prot)
    {
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

    default:
        assert(false && "Not a social packet");
        return;
    }
}

void SocialDecoder::Reset()
{
    m_privateMessageIds.clear();
}

void SocialDecoder::DecodePrivateMessage(Packet& packet, GameState_s& state)
{
    const auto from = PacketFields::ReadName37(packet);
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
