#pragma once

// The console's platform calls, so the rest of Console/ is the same on every platform.
class Terminal
{
public:
    Terminal() = delete;

    // On a terminal that shows VT100 colors, and only when NO_COLOR isn't set.
    [[nodiscard]] static bool CanColor(std::FILE* stream);
    // Whether stdin is a console rather than a pipe or a file.
    [[nodiscard]] static bool IsInputConsole();
    // Returns how to undo it, or nothing when either side isn't a terminal that takes VT100 codes.
    [[nodiscard]] static std::function<void()> EnterRawMode();
    // Blocks for the next keys in raw mode. Empty after a Ctrl+C on Windows; nullopt once the terminal is gone.
    [[nodiscard]] static std::optional<std::string> ReadKeys();
};
