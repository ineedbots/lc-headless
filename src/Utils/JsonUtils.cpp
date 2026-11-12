#include "pch.hpp"
#include "JsonUtils.hpp"

std::string JsonUtils::EscapeString(std::string_view text)
{
    auto out = std::string{};
    out.reserve(text.size() + 2);
    for (const auto character : text)
    {
        switch (character)
        {
        case '"':
            out += "\\\"";
            break;
        case '\\':
            out += "\\\\";
            break;
        case '\n':
            out += "\\n";
            break;
        case '\t':
            out += "\\t";
            break;
        default:
            if (static_cast<unsigned char>(character) < 0x20)
            {
                std::format_to(std::back_inserter(out), "\\u{:04x}", static_cast<unsigned>(character));
            }
            else
            {
                out += character;
            }
            break;
        }
    }

    return out;
}
