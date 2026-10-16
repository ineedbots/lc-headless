#include "pch.hpp"
#include "JsoncScanner.hpp"

#include "Error/ConfigError.hpp"
#include "JsoncValue_s.hpp"

#include <nlohmann/json.hpp>

namespace
{
    constexpr auto UTF8_BOM = "\xEF\xBB\xBF"sv;

    bool IsLiteral(char character)
    {
        return std::isalnum(static_cast<unsigned char>(character)) != 0 || character == '-' || character == '+' || character == '.';
    }
}

JsoncScanner::JsoncScanner(std::string_view text)
    : m_text{text}
    , m_pos{text.starts_with(UTF8_BOM) ? UTF8_BOM.size() : 0}
{
}

JsoncValue_s JsoncScanner::ScanDocument()
{
    SkipSpace();

    auto value = ScanValue();
    SkipSpace();
    Expect(m_pos == m_text.size());
    return value;
}

bool JsoncScanner::IsSpace(char character)
{
    return character == ' ' || character == '\t' || character == '\r' || character == '\n';
}

void JsoncScanner::Expect(bool valid)
{
    if (!valid)
    {
        throw ConfigError{"invalid JSON"};
    }
}

char JsoncScanner::Peek() const
{
    Expect(m_pos < m_text.size());
    return m_text[m_pos];
}

void JsoncScanner::SkipSpace()
{
    while (m_pos < m_text.size())
    {
        const auto rest = m_text.substr(m_pos);
        if (rest.starts_with("//"))
        {
            m_pos = std::min(m_text.find('\n', m_pos), m_text.size());
        }
        else if (rest.starts_with("/*"))
        {
            const auto close = m_text.find("*/", m_pos + 2);
            Expect(close != std::string_view::npos);
            m_pos = close + 2;
        }
        else if (IsSpace(m_text[m_pos]))
        {
            ++m_pos;
        }
        else
        {
            return;
        }
    }
}

JsoncValue_s JsoncScanner::ScanValue()
{
    const auto begin = m_pos;

    switch (Peek())
    {
    case '{':
        return ScanObject();
    case '[':
        ScanArray();
        break;
    case '"':
        ScanString();
        break;
    default:
        ScanLiteral();
        break;
    }

    return JsoncValue_s{.begin = begin, .end = m_pos};
}

JsoncValue_s JsoncScanner::ScanObject()
{
    auto object = JsoncValue_s{.begin = m_pos, .isObject = true};
    ++m_pos;
    SkipSpace();

    if (Peek() != '}')
    {
        while (true)
        {
            auto member = JsoncValue_s::Member_s{.keyBegin = m_pos};
            Expect(Peek() == '"');
            ScanString();
            member.key = nlohmann::json::parse(std::string{m_text.substr(member.keyBegin, m_pos - member.keyBegin)}).get<std::string>();
            SkipSpace();
            Expect(Peek() == ':');
            ++m_pos;
            SkipSpace();
            auto value = ScanValue();
            object.members.push_back(std::move(member));
            object.values.push_back(std::move(value));
            SkipSpace();

            if (Peek() != ',')
            {
                break;
            }

            ++m_pos;
            SkipSpace();
        }
    }

    Expect(Peek() == '}');
    ++m_pos;
    object.end = m_pos;
    return object;
}

void JsoncScanner::ScanArray()
{
    ++m_pos;
    SkipSpace();

    if (Peek() != ']')
    {
        while (true)
        {
            static_cast<void>(ScanValue());
            SkipSpace();

            if (Peek() != ',')
            {
                break;
            }

            ++m_pos;
            SkipSpace();
        }
    }

    Expect(Peek() == ']');
    ++m_pos;
}

void JsoncScanner::ScanString()
{
    ++m_pos;

    while (Peek() != '"')
    {
        m_pos += Peek() == '\\' ? std::size_t{2} : std::size_t{1};
    }

    ++m_pos;
}

void JsoncScanner::ScanLiteral()
{
    const auto begin = m_pos;

    while (m_pos < m_text.size() && IsLiteral(m_text[m_pos]))
    {
        ++m_pos;
    }

    Expect(m_pos > begin);
}
