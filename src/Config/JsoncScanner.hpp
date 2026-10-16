#pragma once

#include "JsoncValue_s.hpp"

// Finds where each value of a JSON document with comments sits in its text. Anything it doesn't expect throws a
// ConfigError, so a bad edit is never made.
class JsoncScanner
{
public:
    explicit JsoncScanner(std::string_view text);

    [[nodiscard]] JsoncValue_s ScanDocument();

    [[nodiscard]] static bool IsSpace(char character);

private:
    static void Expect(bool valid);
    [[nodiscard]] char Peek() const;
    void SkipSpace();
    [[nodiscard]] JsoncValue_s ScanValue();
    [[nodiscard]] JsoncValue_s ScanObject();
    void ScanArray();
    void ScanString();
    void ScanLiteral();

    std::string_view m_text;
    std::size_t m_pos;
};
