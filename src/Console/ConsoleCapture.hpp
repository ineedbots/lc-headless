#pragma once

class ConsoleCapture
{
public:
    explicit ConsoleCapture(std::size_t limit)
        : m_limit{limit}
    {
    }

    void Append(std::string_view text);
    std::string output;
    bool truncated = false;

private:
    std::size_t m_limit;
};

class ConsoleCaptureScope
{
public:
    explicit ConsoleCaptureScope(ConsoleCapture* capture);
    ~ConsoleCaptureScope();
    ConsoleCaptureScope(const ConsoleCaptureScope&) = delete;
    ConsoleCaptureScope& operator=(const ConsoleCaptureScope&) = delete;
    static void Write(std::string_view text);

private:
    ConsoleCapture* m_previous;
    static thread_local ConsoleCapture* s_current;
};
