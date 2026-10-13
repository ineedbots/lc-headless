#pragma once

#include "Logger.hpp"

// Appends log entries to a file as plain lines, with no colors, each flushed as it's written so a crash
// loses none. Not thread-safe on its own: a Logger's sink is only called under the logger's lock.
class LogFile
{
public:
    // Opens the file to append to, making its folder if need be. Throws std::runtime_error when it can't.
    explicit LogFile(std::filesystem::path path);

    // A failed write is dropped, as logging must never fail the caller.
    void Write(const LogEntry_s& entry);
    [[nodiscard]] const std::filesystem::path& GetPath() const;

private:
    std::filesystem::path m_path;
    std::ofstream m_stream;
};
