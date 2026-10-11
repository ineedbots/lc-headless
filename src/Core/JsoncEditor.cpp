#include "pch.hpp"
#include "JsoncEditor.hpp"

#include "ConfigError.hpp"

#include <nlohmann/json.hpp>

namespace
{
    using Json = nlohmann::ordered_json;

    constexpr auto UTF8_BOM = "\xEF\xBB\xBF"sv;
    constexpr auto CRLF = "\r\n"sv;
    constexpr auto LF = "\n"sv;
    constexpr auto DEFAULT_INDENT = "    "sv;

    struct Member_s;

    // Where a value is in the text, and for an object, where its members are.
    struct Value_s
    {
        std::size_t begin = 0;
        std::size_t end = 0;
        bool isObject = false;
        std::vector<Member_s> members;
    };

    struct Member_s
    {
        std::string key;
        std::size_t keyBegin = 0;
        Value_s value;
    };

    struct Layout_s
    {
        std::string_view eol;
        // One level of indentation.
        std::string_view unit;
    };

    struct Replacement_s
    {
        std::size_t offset = 0;
        std::size_t length = 0;
        std::string text;
    };

    bool IsSpace(char character)
    {
        return character == ' ' || character == '\t' || character == '\r' || character == '\n';
    }

    bool IsLiteral(char character)
    {
        return std::isalnum(static_cast<unsigned char>(character)) != 0 || character == '-' || character == '+' || character == '.';
    }

    bool IsScalar(const Json& value)
    {
        return !value.is_object() && !value.is_array();
    }

    // Finds where each value is. Anything it doesn't expect is an error, so a bad edit is never made.
    class Scanner
    {
    public:
        explicit Scanner(std::string_view text)
            : m_text{text}
            , m_pos{text.starts_with(UTF8_BOM) ? UTF8_BOM.size() : 0}
        {
        }

        Value_s ScanDocument()
        {
            SkipSpace();
            auto value = ScanValue();
            SkipSpace();
            Expect(m_pos == m_text.size());
            return value;
        }

    private:
        static void Expect(bool valid)
        {
            if (!valid)
            {
                throw ConfigError{"invalid JSON"};
            }
        }

        [[nodiscard]] char Peek() const
        {
            Expect(m_pos < m_text.size());
            return m_text[m_pos];
        }

        void SkipSpace()
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

        Value_s ScanValue()
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

            return Value_s{.begin = begin, .end = m_pos};
        }

        Value_s ScanObject()
        {
            auto object = Value_s{.begin = m_pos, .isObject = true};
            ++m_pos;
            SkipSpace();
            if (Peek() != '}')
            {
                while (true)
                {
                    auto member = Member_s{.keyBegin = m_pos};
                    Expect(Peek() == '"');
                    ScanString();
                    member.key = Json::parse(std::string{m_text.substr(member.keyBegin, m_pos - member.keyBegin)}).get<std::string>();
                    SkipSpace();
                    Expect(Peek() == ':');
                    ++m_pos;
                    SkipSpace();
                    member.value = ScanValue();
                    object.members.push_back(std::move(member));
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

        void ScanArray()
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

        void ScanString()
        {
            ++m_pos;
            while (Peek() != '"')
            {
                m_pos += Peek() == '\\' ? std::size_t{2} : std::size_t{1};
            }

            ++m_pos;
        }

        void ScanLiteral()
        {
            const auto begin = m_pos;
            while (m_pos < m_text.size() && IsLiteral(m_text[m_pos]))
            {
                ++m_pos;
            }

            Expect(m_pos > begin);
        }

        std::string_view m_text;
        std::size_t m_pos;
    };

    std::size_t GetLineStart(std::string_view text, std::size_t pos)
    {
        const auto newline = text.substr(0, pos).rfind('\n');
        return newline == std::string_view::npos ? 0 : newline + 1;
    }

    // The spaces and tabs that start pos's line.
    std::string_view GetIndent(std::string_view text, std::size_t pos)
    {
        const auto start = GetLineStart(text, pos);
        auto end = start;
        while (end < text.size() && (text[end] == ' ' || text[end] == '\t'))
        {
            ++end;
        }

        return text.substr(start, end - start);
    }

    bool StartsLine(std::string_view text, std::size_t pos)
    {
        return GetLineStart(text, pos) + GetIndent(text, pos).size() == pos;
    }

    // Past the spaces and comments that follow pos on its line: the line's end, or what else is on it. A block
    // comment that runs onto another line counts as what else is on it.
    std::size_t SkipToLineEnd(std::string_view text, std::size_t pos)
    {
        while (pos < text.size())
        {
            const auto rest = text.substr(pos);
            if (rest.starts_with("//"))
            {
                return std::min(text.find_first_of("\r\n", pos), text.size());
            }

            if (rest.starts_with("/*"))
            {
                const auto close = text.find("*/", pos + 2);
                if (close == std::string_view::npos || text.substr(pos, close - pos).find('\n') != std::string_view::npos)
                {
                    return pos;
                }

                pos = close + 2;
                continue;
            }

            if (text[pos] != ' ' && text[pos] != '\t')
            {
                return pos;
            }

            ++pos;
        }

        return pos;
    }

    Layout_s DetectLayout(std::string_view text, const Value_s& root)
    {
        auto layout = Layout_s{.eol = text.find(CRLF) == std::string_view::npos ? LF : CRLF, .unit = DEFAULT_INDENT};
        const auto rootIndent = GetIndent(text, root.begin);
        for (const auto& member : root.members)
        {
            if (!StartsLine(text, member.keyBegin))
            {
                continue;
            }

            const auto indent = GetIndent(text, member.keyBegin);
            if (indent.size() > rootIndent.size() && indent.starts_with(rootIndent))
            {
                layout.unit = indent.substr(rootIndent.size());
            }

            break;
        }

        return layout;
    }

    std::string Quote(const std::string& key)
    {
        return Json(key).dump();
    }

    std::string FormatInline(const Json& value)
    {
        if (IsScalar(value))
        {
            return value.dump();
        }

        const auto isObject = value.is_object();
        auto text = std::string{isObject ? "{" : "["};
        auto first = true;
        for (const auto& [key, item] : value.items())
        {
            text += first ? "" : ", ";
            text += isObject ? Quote(key) + ": " : "";
            text += FormatInline(item);
            first = false;
        }

        return text + (isObject ? "}" : "]");
    }

    // Objects take a line per member, as do arrays of anything but scalars; the rest stays on one line.
    std::string FormatBlock(const Json& value, const std::string& indent, const Layout_s& layout)
    {
        const auto isObject = value.is_object();
        if (value.empty() || IsScalar(value) || (!isObject && std::all_of(value.begin(), value.end(), IsScalar)))
        {
            return FormatInline(value);
        }

        const auto inner = indent + std::string{layout.unit};
        auto text = std::string{isObject ? "{" : "["};
        auto first = true;
        for (const auto& [key, item] : value.items())
        {
            text += first ? "" : ",";
            text += layout.eol;
            text += inner;
            text += isObject ? Quote(key) + ": " : "";
            text += FormatBlock(item, inner, layout);
            first = false;
        }

        text += layout.eol;
        text += indent;
        return text + (isObject ? "}" : "]");
    }

    // A line for each member, without the first line's break or the last's.
    std::string FormatMemberLines(const Json& members, const std::string& indent, const Layout_s& layout)
    {
        auto text = std::string{};
        for (const auto& [key, value] : members.items())
        {
            if (!text.empty())
            {
                text += ",";
                text += layout.eol;
            }

            text += indent + Quote(key) + ": " + FormatBlock(value, indent, layout);
        }

        return text;
    }

    Replacement_s AddMembers(std::string_view text, const Value_s& object, const Json& members, const Layout_s& layout)
    {
        const auto close = object.end - 1;
        const auto objectIndent = std::string{GetIndent(text, object.begin)};
        const auto eol = std::string{layout.eol};
        const auto unit = std::string{layout.unit};
        const auto oneLine = text.substr(object.begin, object.end - object.begin).find('\n') == std::string_view::npos;

        if (object.members.empty())
        {
            // A closing brace on a line of its own keeps it, below the new members.
            if (!oneLine && StartsLine(text, close))
            {
                const auto indent = std::string{GetIndent(text, close)} + unit;
                return {.offset = GetLineStart(text, close), .text = FormatMemberLines(members, indent, layout) + eol};
            }

            const auto lines = eol + FormatMemberLines(members, objectIndent + unit, layout) + eol + objectIndent;
            const auto inside = text.substr(object.begin + 1, close - object.begin - 1);
            if (std::ranges::all_of(inside, IsSpace))
            {
                return {.offset = object.begin + 1, .length = inside.size(), .text = lines};
            }

            return {.offset = close, .text = lines};
        }

        const auto& last = object.members.back();
        if (oneLine)
        {
            auto added = std::string{};
            for (const auto& [key, value] : members.items())
            {
                added += ", " + Quote(key) + ": " + FormatInline(value);
            }

            return {.offset = last.value.end, .text = added};
        }

        // The comma goes after the last member's value, and the new members after any comment on its line.
        const auto indent = StartsLine(text, last.keyBegin) ? std::string{GetIndent(text, last.keyBegin)} : objectIndent + unit;
        const auto lineEnd = SkipToLineEnd(text, last.value.end);
        auto between = text.substr(last.value.end, lineEnd - last.value.end);
        between = between.substr(0, between.find_last_not_of(" \t") + 1);
        auto replacement = "," + std::string{between} + eol + FormatMemberLines(members, indent, layout);
        if (lineEnd == close)
        {
            replacement += eol + objectIndent;
        }

        return {.offset = last.value.end, .length = lineEnd - last.value.end, .text = std::move(replacement)};
    }

    // The last, as a JSON parser keeps the last of a repeated key.
    const Member_s* FindMember(const Value_s& object, std::string_view key)
    {
        for (auto member = object.members.rbegin(); member != object.members.rend(); ++member)
        {
            if (member->key == key)
            {
                return &*member;
            }
        }

        return nullptr;
    }

    std::string JoinPath(std::span<const std::string> path)
    {
        auto text = std::string{};
        for (const auto& key : path)
        {
            text += text.empty() ? key : "." + key;
        }

        return text;
    }
}

JsoncEdit_s JsoncEditor::AddMissing(std::string_view text, std::span<const std::string> path, std::string_view membersJson)
{
    const auto members = Json::parse(membersJson);
    assert(members.is_object() && "JsoncEditor::AddMissing takes a JSON object of members");

    const auto root = Scanner{text}.ScanDocument();
    if (!root.isObject)
    {
        throw ConfigError{"the top level must be an object"};
    }

    auto edit = JsoncEdit_s{.text = std::string{text}};
    if (members.empty())
    {
        return edit;
    }

    const auto* object = &root;
    auto depth = std::size_t{0};
    for (; depth < path.size(); ++depth)
    {
        const auto* member = FindMember(*object, path[depth]);
        if (member == nullptr)
        {
            break;
        }

        if (!member->value.isObject)
        {
            throw ConfigError{std::format("{}: must be an object", JoinPath(path.first(depth + 1)))};
        }

        object = &member->value;
    }

    auto missing = Json::object();
    if (depth < path.size())
    {
        auto nested = members;
        for (auto i = path.size() - 1; i > depth; --i)
        {
            auto parent = Json::object();
            parent[path[i]] = std::move(nested);
            nested = std::move(parent);
        }

        missing[path[depth]] = std::move(nested);
        for (const auto& [key, value] : members.items())
        {
            edit.added.push_back(key);
        }
    }
    else
    {
        for (const auto& [key, value] : members.items())
        {
            if (FindMember(*object, key) == nullptr)
            {
                missing[key] = value;
                edit.added.push_back(key);
            }
        }
    }

    if (missing.empty())
    {
        return edit;
    }

    const auto replacement = AddMembers(text, *object, missing, DetectLayout(text, root));
    edit.text = std::string{text.substr(0, replacement.offset)} + replacement.text + std::string{text.substr(replacement.offset + replacement.length)};
    return edit;
}
