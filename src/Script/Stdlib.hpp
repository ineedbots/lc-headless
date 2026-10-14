#pragma once

struct StdlibFile_s
{
    // Relative to src/Script/Stdlib, with '/' between folders, such as "rs2004/bot.py".
    std::string_view path;
    std::string_view source;
};

// Embedded at build time by cmake/EmbedStdlib.cmake, so it can't drift from the client it belongs to.
class Stdlib
{
public:
    Stdlib() = delete;

    [[nodiscard]] static std::span<const StdlibFile_s> GetFiles();
    // Either separator works; nullopt when the library has no such file.
    [[nodiscard]] static std::optional<std::string_view> Find(std::string_view path);
};
