#pragma once

#include "LogEntry_s.hpp"

// Each entry is flushed as it's written, so a crash loses none. Not thread-safe on its own: a Logger's
// sink is only called under the logger's lock.
class LogFile
{
public:
    explicit LogFile(std::filesystem::path path);

    // A failed write is dropped: logging must never fail the caller.
    void Write(const LogEntry_s& entry);
    [[nodiscard]] const std::filesystem::path& GetPath() const;

private:
    std::filesystem::path m_path;
    std::ofstream m_stream;
};
