#pragma once

#include "ConsoleOutput.hpp"
#include "LogEntry_s.hpp"
#include "LogFormat_s.hpp"
#include "LogLevel_e.hpp"

class Logger
{
public:
    using Sink = std::function<void(const LogEntry_s& entry)>;

    explicit Logger(LogLevel_e level = LogLevel_e::Info, Sink sink = ConsoleOutput::Write);

    template <typename... TArgs>
    void Verbose(LogFormat_s<std::type_identity_t<TArgs>...> format, TArgs&&... args) noexcept
    {
        Log(LogLevel_e::Verbose, format, std::forward<TArgs>(args)...);
    }

    template <typename... TArgs>
    void Info(LogFormat_s<std::type_identity_t<TArgs>...> format, TArgs&&... args) noexcept
    {
        Log(LogLevel_e::Info, format, std::forward<TArgs>(args)...);
    }

    template <typename... TArgs>
    void Warning(LogFormat_s<std::type_identity_t<TArgs>...> format, TArgs&&... args) noexcept
    {
        Log(LogLevel_e::Warning, format, std::forward<TArgs>(args)...);
    }

    template <typename... TArgs>
    void Error(LogFormat_s<std::type_identity_t<TArgs>...> format, TArgs&&... args) noexcept
    {
        Log(LogLevel_e::Error, format, std::forward<TArgs>(args)...);
    }

    template <typename... TArgs>
    void Log(LogLevel_e level, LogFormat_s<std::type_identity_t<TArgs>...> format, TArgs&&... args) noexcept
    {
        if (!IsEnabled(level))
        {
            return;
        }

        try
        {
            Write(level, format.GetLocation(), std::format(format.text, std::forward<TArgs>(args)...));
        }
        catch (const std::exception&)
        {
            // Logging must never fail the caller, so a message that can't be formatted or written is dropped.
        }
    }

    void SetLevel(LogLevel_e level) noexcept;
    [[nodiscard]] LogLevel_e GetLevel() const noexcept;
    [[nodiscard]] bool IsEnabled(LogLevel_e level) const noexcept;

    Sink SetSink(Sink sink) noexcept;
    [[nodiscard]] const std::string& GetSource() const noexcept;

    // A logger whose entries carry `source` and go through `parent`: the parent's level and sink apply,
    // and the named logger's own level can only narrow them.
    [[nodiscard]] static std::shared_ptr<Logger> CreateNamed(std::shared_ptr<Logger> parent, std::string source);
    [[nodiscard]] static std::shared_ptr<Logger> GetDefault() noexcept;
    static std::shared_ptr<Logger> SetDefault(std::shared_ptr<Logger> logger) noexcept;

private:
    void Write(LogLevel_e level, std::optional<std::source_location> location, std::string_view message);
    void Deliver(LogLevel_e level, std::optional<std::source_location> location, std::string_view message, std::string_view source);

    std::atomic<LogLevel_e> m_level;
    std::mutex m_mutex;
    Sink m_sink;
    std::shared_ptr<Logger> m_parent;
    std::string m_source;
};
