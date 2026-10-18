#pragma once

#include "../Config/Revision_e.hpp"

// An opcode only some revisions have: every revision from addedIn on, until removedIn if a later one dropped it.
struct RevisionedOpcode_s
{
    u8 opcode = 0;
    Revision_e addedIn = Revision_e::Rev225;
    std::optional<Revision_e> removedIn;

    [[nodiscard]] static constexpr RevisionedOpcode_s AddedIn(u8 opcode, Revision_e revision)
    {
        return {.opcode = opcode, .addedIn = revision};
    }

    [[nodiscard]] static constexpr RevisionedOpcode_s RemovedIn(u8 opcode, Revision_e revision)
    {
        return {.opcode = opcode, .removedIn = revision};
    }
};
