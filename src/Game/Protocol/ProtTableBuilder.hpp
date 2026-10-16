#pragma once

#include "WireProt_s.hpp"

// Builds one revision's opcode table at compile time, for ServerProt and ClientProt. A table has
// `byOpcode` and `byProt` arrays; a row has `prot`, `opcode` and `size`.
class ProtTableBuilder
{
public:
    ProtTableBuilder() = delete;

    template <typename TTable, typename TRow, std::size_t TCount>
    [[nodiscard]] static constexpr TTable Build(const std::array<TRow, TCount>& rows)
    {
        auto table = TTable{};
        for (const auto& row : rows)
        {
            table.byOpcode[row.opcode] = row.prot;
            table.byProt[static_cast<std::size_t>(row.prot)] = WireProt_s{.opcode = row.opcode, .size = row.size};
        }

        return table;
    }

    // A repeated opcode or packet would leave one of its rows unreachable.
    template <typename TRow, std::size_t TCount>
    [[nodiscard]] static constexpr bool HasUniqueRows(const std::array<TRow, TCount>& rows)
    {
        for (auto i = std::size_t{0}; i < rows.size(); ++i)
        {
            for (auto j = i + 1; j < rows.size(); ++j)
            {
                if (rows[i].opcode == rows[j].opcode || rows[i].prot == rows[j].prot)
                {
                    return false;
                }
            }
        }

        return true;
    }

    // Each info entry sits at its packet's value, so a packet's info is found by indexing.
    template <typename TInfo, std::size_t TCount>
    [[nodiscard]] static constexpr bool IsInProtOrder(const std::array<TInfo, TCount>& infos)
    {
        for (auto i = std::size_t{0}; i < infos.size(); ++i)
        {
            if (static_cast<std::size_t>(infos[i].prot) != i)
            {
                return false;
            }
        }

        return true;
    }
};
