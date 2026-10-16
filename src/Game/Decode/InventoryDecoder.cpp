#include "pch.hpp"
#include "InventoryDecoder.hpp"

#include "../../Io/Packet.hpp"
#include "../Protocol/ServerProt.hpp"
#include "../State/GameEvent_s.hpp"
#include "../State/GameState_s.hpp"
#include "StateLog.hpp"

namespace
{
    constexpr auto ITEM_COUNT_ESCAPE = u8{255};

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

    void DecodeFull(Packet& packet, GameState_s& state)
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
        StateLog::AddEvent(state, InventoryChanged_s{.com = com});
    }

    void DecodePartial(Packet& packet, GameState_s& state)
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

        StateLog::AddEvent(state, InventoryChanged_s{.com = com});
    }

    void DecodeStopTransmit(Packet& packet, GameState_s& state)
    {
        const auto com = packet.G2();
        state.inventories.erase(com);
        StateLog::AddEvent(state, InventoryChanged_s{.com = com});
    }
}

void InventoryDecoder::Decode(ServerProt_e prot, Packet& packet, GameState_s& state)
{
    switch (prot)
    {
    case ServerProt_e::UpdateInvFull:
        DecodeFull(packet, state);
        return;
    case ServerProt_e::UpdateInvPartial:
        DecodePartial(packet, state);
        return;
    case ServerProt_e::UpdateInvStopTransmit:
        DecodeStopTransmit(packet, state);
        return;

    default:
        assert(false && "Not an inventory packet");
        return;
    }
}
