#include "pch.hpp"
#include "LogCapture.hpp"

#include "Core/Logger.hpp"

LogCapture::LogCapture(LogLevel_e level)
    : m_logger{std::make_shared<Logger>(level, [this](const LogEntry_s& entry)
    {
        Append(entry);
    })}
{
}

LogCapture::~LogCapture()
{
    m_logger->SetSink(nullptr);
}

std::shared_ptr<Logger> LogCapture::GetLogger() const
{
    return m_logger;
}

std::vector<CapturedLog_s> LogCapture::GetEntries() const
{
    const auto lock = std::scoped_lock{m_mutex};
    return m_entries;
}

void LogCapture::Append(const LogEntry_s& entry)
{
    const auto lock = std::scoped_lock{m_mutex};
    m_entries.push_back({.level = entry.level, .time = entry.time, .location = entry.location, .message = std::string{entry.message}, .source = std::string{entry.source}});
}
