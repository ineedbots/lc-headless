#pragma once

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
