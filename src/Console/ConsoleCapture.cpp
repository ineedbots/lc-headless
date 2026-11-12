#include "pch.hpp"
#include "ConsoleCapture.hpp"

thread_local ConsoleCapture* ConsoleCaptureScope::s_current = nullptr;
ConsoleCaptureScope::ConsoleCaptureScope(ConsoleCapture* capture)
    : m_previous{std::exchange(s_current, capture)}
{
}
ConsoleCaptureScope::~ConsoleCaptureScope()
{
    s_current = m_previous;
}
void ConsoleCaptureScope::Write(std::string_view text)
{
    if (s_current)
    {
        s_current->Append(text);
    }
}
void ConsoleCapture::Append(std::string_view text)
{
    if (truncated)
    {
        return;
    }
    auto count = std::min(text.size(), m_limit - output.size());
    if (count < text.size())
    {
        while (count > 0 && (static_cast<unsigned char>(text[count]) & 0xc0) == 0x80)
        {
            --count;
        }
        truncated = true;
    }
    output.append(text.substr(0, count));
}
