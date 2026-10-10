#pragma once

struct StdlibFile_s
{
    // Relative to src/Script/Stdlib, with '/' between folders, such as "rs2004/bot.py".
    std::string_view path;
    std::string_view source;
};

// The Python standard library, embedded in the executable at build time from src/Script/Stdlib by
// cmake/EmbedStdlib.cmake, so it can't drift from the client it belongs to.
class Stdlib
{
public:
    Stdlib() = delete;

    [[nodiscard]] static std::span<const StdlibFile_s> GetFiles();
    // Takes a path as pocketpy asks for it, with either separator; nullopt when the library has no such file.
    [[nodiscard]] static std::optional<std::string_view> Find(std::string_view path);
};
