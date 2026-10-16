#pragma once

// A packet as one revision puts it on the wire: its opcode, and its size or a VAR_ length marker.
struct WireProt_s
{
    u8 opcode = 0;
    s32 size = 0;
};
