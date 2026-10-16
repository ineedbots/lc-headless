#include "pch.hpp"
#include "Logger.hpp"

#include "LogEntry_s.hpp"
#include "LogLevel_e.hpp"

namespace
{
    struct DefaultLogger_s
    {
        std::mutex mutex;
        std::shared_ptr<Logger> logger = std::make_shared<Logger>();
    };

    // A function-local static, so the default exists even when another file's static
    // initializer asks for it before this file's globals would have been initialized.
    DefaultLogger_s& GetDefaultLogger()
    {
        static auto defaultLogger = DefaultLogger_s{};
        return defaultLogger;
    }
}

Logger::Logger(LogLevel_e level, Sink sink)
    : m_level{level}
    , m_sink{std::move(sink)}
{
}

void Logger::SetLevel(LogLevel_e level) noexcept
{
    m_level.store(level, std::memory_order_relaxed);
}

LogLevel_e Logger::GetLevel() const noexcept
{
    return m_level.load(std::memory_order_relaxed);
}

bool Logger::IsEnabled(LogLevel_e level) const noexcept
{
    return level >= GetLevel() && (m_parent == nullptr || m_parent->IsEnabled(level));
}

Logger::Sink Logger::SetSink(Sink sink) noexcept
{
    const auto lock = std::scoped_lock{m_mutex};
    m_sink.swap(sink);
    return sink;
}

const std::string& Logger::GetSource() const noexcept
{
    return m_source;
}

std::shared_ptr<Logger> Logger::CreateNamed(std::shared_ptr<Logger> parent, std::string source)
{
    assert(parent && "A named logger needs a parent");

    auto named = std::make_shared<Logger>(LogLevel_e::Verbose, nullptr);
    named->m_parent = std::move(parent);
    named->m_source = std::move(source);
    return named;
}

std::shared_ptr<Logger> Logger::GetDefault() noexcept
{
    auto& defaultLogger = GetDefaultLogger();
    const auto lock = std::scoped_lock{defaultLogger.mutex};
    return defaultLogger.logger;
}

std::shared_ptr<Logger> Logger::SetDefault(std::shared_ptr<Logger> logger) noexcept
{
    assert(logger && "The default logger can't be null");

    auto& defaultLogger = GetDefaultLogger();
    const auto lock = std::scoped_lock{defaultLogger.mutex};
    defaultLogger.logger.swap(logger);
    return logger;
}

void Logger::Write(LogLevel_e level, std::optional<std::source_location> location, std::string_view message)
{
    Deliver(level, location, message, m_source);
}

void Logger::Deliver(LogLevel_e level, std::optional<std::source_location> location, std::string_view message, std::string_view source)
{
    if (m_parent)
    {
        m_parent->Deliver(level, location, message, source);
        return;
    }

    const auto lock = std::scoped_lock{m_mutex};

    if (!m_sink)
    {
        return;
    }

    // The time is read under the lock, so times in the output only go backwards if the wall clock does.
    m_sink(LogEntry_s{.level = level, .time = std::chrono::system_clock::now(), .location = location, .message = message, .source = source});
}
