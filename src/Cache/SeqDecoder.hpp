#pragma once

// A sequence's frames and how it repeats, which is what its length is read from.
struct SeqType_s
{
    std::vector<u16> frames;
    // Client cycles each frame shows; 0 means the frame's own delay, from its anim file.
    std::vector<u16> delays;
    // How many frames from the end a repeat replays; -1 for none.
    s32 loops = -1;
    s32 maxLoops = 99;
};

// Frame id to its delay in client cycles, from the anim frames.
using FrameDelays = std::unordered_map<u16, u8>;

// How long the client plays each animation, so a script can tell when one has finished: the server says when an
// animation starts, never when it ends.
class SeqDecoder
{
public:
    // A client cycle is 20 ms, so a 600 ms server tick is 30 of them.
    static constexpr u32 CYCLES_PER_TICK = 30;

    SeqDecoder() = delete;

    // seq.dat from the config archive: a count, then each type's opcodes.
    [[nodiscard]] static std::vector<SeqType_s> DecodeTypes(std::span<const u8> dat);
    // One 274 or 289 anim file, gunzipped: its frames' heads and delays, with their lengths in the last 8 bytes.
    static void ReadFrameDelays(std::span<const u8> file, FrameDelays& delays);
    // 225's frame_head.dat and frame_del.dat, from the models archive.
    static void ReadFrameDelays225(std::span<const u8> head, std::span<const u8> del, FrameDelays& delays);
    // The client cycles a sequence plays for, its repeats included, as the client steps it: a frame's delay is
    // its own when the sequence gives 0, and 1 when that's 0 too.
    [[nodiscard]] static u32 GetLength(const SeqType_s& type, const FrameDelays& delays);
};
