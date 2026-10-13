#pragma once

#include "LineEditor.hpp"

// Lines typed into the console. ReadStdin reads them on a thread of its own, so the caller's loop never
// blocks on input: it takes what has arrived, and can sleep until a time or the next line, whichever is
// first. Tests push lines instead.
//
// When standard input and output are both a terminal, it's interactive: the terminal goes into raw VT100
// mode, a LineEditor draws a prompt on the last line, and output given to Print goes above the prompt, so
// it never runs through what's being typed. Otherwise, as with piped input, lines are read as they come.
class ConsoleInput
{
public:
    using Clock = std::chrono::steady_clock;

    // Starts reading standard input on a detached thread, which outlives the returned object if need be
    // and ends at the end of the input. A Ctrl+C at the console doesn't end it.
    [[nodiscard]] static std::shared_ptr<ConsoleInput> ReadStdin();

    void Push(std::string line);
    // The lines that have arrived since the last call, oldest first.
    [[nodiscard]] std::vector<std::string> TakeLines();
    // Sleeps until the time, or until a line arrives that hasn't been taken yet.
    void WaitUntil(Clock::time_point time);

    [[nodiscard]] bool IsInteractive() const;
    // Writes the text and a line break to the stream, above the prompt while there is one.
    void Print(std::FILE* stream, std::string_view text);
    // Erases the prompt and puts the terminal back as it was. Typing after that is ignored.
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
