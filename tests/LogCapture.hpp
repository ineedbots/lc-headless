#pragma once

#include "Core/Logger.hpp"

struct CapturedLog_s
{
    LogLevel_e level;
    std::chrono::system_clock::time_point time;
    std::optional<std::source_location> location;
    std::string message;
};

class LogCapture
{
public:
    explicit LogCapture(LogLevel_e level = LogLevel_e::Verbose);
    ~LogCapture();

    LogCapture(const LogCapture&) = delete;
    LogCapture& operator=(const LogCapture&) = delete;

    [[nodiscard]] std::shared_ptr<Logger> GetLogger() const;
    [[nodiscard]] std::vector<CapturedLog_s> GetEntries() const;

private:
    void Append(const LogEntry_s& entry);

    mutable std::mutex m_mutex;
    std::vector<CapturedLog_s> m_entries;
    std::shared_ptr<Logger> m_logger;
};
