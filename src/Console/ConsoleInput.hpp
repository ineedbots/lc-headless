#pragma once

#include "LineEditor.hpp"

// ReadStdin reads on a thread of its own, so the caller's loop never blocks on input. On a terminal, a
// LineEditor keeps a prompt on the last line and Print writes above it.
class ConsoleInput
{
public:
    using Clock = std::chrono::steady_clock;

    // The thread is detached: it outlives the returned object if need be, and ends with the input.
    [[nodiscard]] static std::shared_ptr<ConsoleInput> ReadStdin();

    void Push(std::string line);
    [[nodiscard]] std::vector<std::string> TakeLines();
    // Returns early when a line arrives.
    void WaitUntil(Clock::time_point time);

    [[nodiscard]] bool IsInteractive() const;
    // Above the prompt while there is one.
    void Print(std::FILE* stream, std::string_view text);
    // Typing after this is ignored.
    void Close();

private:
    void ReadLines();
    void ReadKeys();

    std::mutex m_mutex;
    std::condition_variable m_arrived;
    std::vector<std::string> m_lines;
    // The prompt and the output around it; the reader thread draws the keys under it too.
    std::mutex m_outputMutex;
    std::optional<LineEditor> m_editor;
    std::function<void()> m_restoreTerminal;
    bool m_closed = false;
};
