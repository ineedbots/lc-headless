#pragma once

enum class LogLevel_e : u8
{
    Verbose,
    Info,
    Warning,
    Error,
};

struct LogEntry_s
{
    LogLevel_e level;
    std::chrono::system_clock::time_point time;
    std::optional<std::source_location> location;
    std::string_view message;
    // The name of the logger that wrote the entry, empty for an unnamed one.
    std::string_view source;
};

template <typename... TArgs>
struct LogFormat_s
{
    // Implicit, so the format string converts at the call site, which is where
    // std::source_location::current() is evaluated. Only Debug builds take the location,
    // the same switch as assert, so a Release binary carries no source paths.
#ifdef NDEBUG
    template <typename T>
        requires std::convertible_to<const T&, std::string_view>
    consteval LogFormat_s(const T& formatText) noexcept
        : text{formatText}
    {
    }
#else
    template <typename T>
        requires std::convertible_to<const T&, std::string_view>
    consteval LogFormat_s(const T& formatText, std::source_location callSite = std::source_location::current()) noexcept
        : text{formatText}
        , location{callSite}
        , hasLocation{true}
    {
    }
#endif

    [[nodiscard]] std::optional<std::source_location> GetLocation() const noexcept
    {
        if (!hasLocation)
        {
            return std::nullopt;
        }

        return location;
    }

    std::format_string<TArgs...> text;
    // Not a std::optional: MSVC 19.44 rejects a consteval conversion to any type with an
    // optional member (C2440, "invalid aggregate initialization").
    std::source_location location;
    bool hasLocation = false;
};

class Logger
{
public:
    using Sink = std::function<void(const LogEntry_s& entry)>;

    explicit Logger(LogLevel_e level = LogLevel_e::Info, Sink sink = WriteToConsole);

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

    static void WriteToConsole(const LogEntry_s& entry);
    [[nodiscard]] static std::string FormatLine(const LogEntry_s& entry);

private:
    void Write(LogLevel_e level, std::optional<std::source_location> location, std::string_view message);
    void Deliver(LogLevel_e level, std::optional<std::source_location> location, std::string_view message, std::string_view source);

    std::atomic<LogLevel_e> m_level;
    std::mutex m_mutex;
    Sink m_sink;
    std::shared_ptr<Logger> m_parent;
    std::string m_source;
};
