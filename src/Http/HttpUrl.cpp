#include "pch.hpp"
#include "HttpUrl.hpp"

namespace
{
    int Hex(unsigned char value)
    {
        if (value >= '0' && value <= '9')
        {
            return value - '0';
        }

        if (value >= 'a' && value <= 'f')
        {
            return value - 'a' + 10;
        }

        if (value >= 'A' && value <= 'F')
        {
            return value - 'A' + 10;
        }

        return -1;
    }
}

bool HttpUrl::IsUtf8(std::string_view text)
{
    for (std::size_t i = 0; i < text.size();)
    {
        const auto first = static_cast<unsigned char>(text[i++]);
        if (first < 0x80)
        {
            continue;
        }

        auto remaining = 0;
        auto code = u32{0};
        auto minimum = u32{0};
        if (first >= 0xc2 && first <= 0xdf)
        {
            remaining = 1;
            code = first & 0x1f;
            minimum = 0x80;
        }
        else if (first >= 0xe0 && first <= 0xef)
        {
            remaining = 2;
            code = first & 0x0f;
            minimum = 0x800;
        }
        else if (first >= 0xf0 && first <= 0xf4)
        {
            remaining = 3;
            code = first & 0x07;
            minimum = 0x10000;
        }
        else
        {
            return false;
        }

        for (auto n = 0; n < remaining; ++n)
        {
            if (i == text.size())
            {
                return false;
            }

            const auto next = static_cast<unsigned char>(text[i++]);
            if ((next & 0xc0) != 0x80)
            {
                return false;
            }

            code = (code << 6) | (next & 0x3f);
        }

        if (code < minimum || code > 0x10ffff || (code >= 0xd800 && code <= 0xdfff))
        {
            return false;
        }
    }

    return true;
}

std::optional<std::string> HttpUrl::Decode(std::string_view value, bool query)
{
    auto decoded = std::string{};
    decoded.reserve(value.size());
    for (std::size_t i = 0; i < value.size(); ++i)

    {
        auto byte = static_cast<unsigned char>(value[i]);
        if (byte == '%')
        {
            if (i + 2 >= value.size())
            {
                return {};
            }

            const auto high = Hex(static_cast<unsigned char>(value[i + 1]));
            const auto low = Hex(static_cast<unsigned char>(value[i + 2]));
            if (high < 0 || low < 0)
            {
                return {};
            }

            byte = static_cast<unsigned char>((high << 4) | low);
            i += 2;
        }
        else if (query && byte == '+')
        {
            byte = ' ';
        }

        if (byte < 0x20 || byte == 0x7f)
        {
            return {};
        }

        decoded += static_cast<char>(byte);
    }

    if (!IsUtf8(decoded))
    {
        return {};
    }

    return decoded;
}

std::vector<std::string_view> HttpUrl::Segments(std::string_view path)
{
    assert(path.starts_with('/'));
    path.remove_prefix(1);

    auto segments = std::vector<std::string_view>{};
    for (;;)
    {
        const auto slash = path.find('/');
        segments.push_back(path.substr(0, slash));

        if (slash == std::string_view::npos)
        {
            break;
        }

        path.remove_prefix(slash + 1);
    }

    return segments;
}

std::optional<HttpUrl_s> HttpUrl::Parse(std::string_view target)
{
    if (!target.starts_with('/') || target.find('#') != std::string_view::npos ||
        std::ranges::any_of(target, [](unsigned char c)
    {
        return c <= 0x20 || c == 0x7f;
    }))
    {
        return {};
    }

    auto result = HttpUrl_s{};
    const auto question = target.find('?');
    for (const auto segment : Segments(target.substr(0, question)))
    {
        auto decoded = Decode(segment, false);
        if (!decoded)
        {
            return {};
        }

        result.segments.push_back(std::move(*decoded));
    }

    if (question == std::string_view::npos)
    {
        return result;
    }

    auto query = target.substr(question + 1);
    while (!query.empty())
    {
        const auto ampersand = query.find('&');
        const auto field = query.substr(0, ampersand);
        if (!field.empty())
        {
            const auto equals = field.find('=');
            auto key = Decode(field.substr(0, equals), true);
            auto value = Decode(equals == std::string_view::npos ? std::string_view{} : field.substr(equals + 1), true);
            if (!key || key->empty() || !value)
            {
                return {};
            }

            result.query[*key].push_back(std::move(*value));
        }

        if (ampersand == std::string_view::npos)
        {
            break;
        }

        query.remove_prefix(ampersand + 1);
    }

    return result;
}
