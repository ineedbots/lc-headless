#include "pch.hpp"
#include "JsoncEditor.hpp"

#include "../Utils/StringUtils.hpp"
#include "Error/ConfigError.hpp"
#include "JsoncScanner.hpp"
#include "JsoncValue_s.hpp"

#include <nlohmann/json.hpp>

namespace
{
    using Json = nlohmann::ordered_json;

    constexpr auto CRLF = "\r\n"sv;
    constexpr auto LF = "\n"sv;
    constexpr auto DEFAULT_INDENT = "    "sv;

    struct Layout_s
    {
        std::string_view eol;
        std::string_view indentUnit;
    };

    struct Replacement_s
    {
        std::size_t offset = 0;
        std::size_t length = 0;
        std::string text;
    };

    bool IsScalar(const Json& value)
    {
        return !value.is_object() && !value.is_array();
    }

    std::size_t GetLineStart(std::string_view text, std::size_t pos)
    {
        const auto newline = text.substr(0, pos).rfind('\n');
        return newline == std::string_view::npos ? 0 : newline + 1;
    }

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

    // A block comment that runs onto another line counts as more on this one.
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

    Layout_s DetectLayout(std::string_view text, const JsoncValue_s& root)
    {
        auto layout = Layout_s{.eol = text.find(CRLF) == std::string_view::npos ? LF : CRLF, .indentUnit = DEFAULT_INDENT};
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
                layout.indentUnit = indent.substr(rootIndent.size());
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

        const auto inner = indent + std::string{layout.indentUnit};
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

    // Without the first line's break or the last's.
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

    Replacement_s AddMembers(std::string_view text, const JsoncValue_s& object, const Json& members, const Layout_s& layout)
    {
        const auto close = object.end - 1;
        const auto objectIndent = std::string{GetIndent(text, object.begin)};
        const auto eol = std::string{layout.eol};
        const auto unit = std::string{layout.indentUnit};
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
            if (std::ranges::all_of(inside, JsoncScanner::IsSpace))
            {
                return {.offset = object.begin + 1, .length = inside.size(), .text = lines};
            }

            return {.offset = close, .text = lines};
        }

        const auto& last = object.members.back();
        const auto& lastValue = object.values.back();
        if (oneLine)
        {
            auto added = std::string{};
            for (const auto& [key, value] : members.items())
            {
                added += ", " + Quote(key) + ": " + FormatInline(value);
            }

            return {.offset = lastValue.end, .text = added};
        }

        // The comma goes after the last member's value, and the new members after any comment on its line.
        const auto indent = StartsLine(text, last.keyBegin) ? std::string{GetIndent(text, last.keyBegin)} : objectIndent + unit;
        const auto lineEnd = SkipToLineEnd(text, lastValue.end);
        auto between = text.substr(lastValue.end, lineEnd - lastValue.end);
        between = between.substr(0, between.find_last_not_of(" \t") + 1);

        auto replacement = "," + std::string{between} + eol + FormatMemberLines(members, indent, layout);
        if (lineEnd == close)
        {
            replacement += eol + objectIndent;
        }

        return {.offset = lastValue.end, .length = lineEnd - lastValue.end, .text = std::move(replacement)};
    }

    // The last, as a JSON parser keeps the last of a repeated key.
    std::optional<std::size_t> FindMember(const JsoncValue_s& object, std::string_view key)
    {
        for (auto i = object.members.size(); i > 0; --i)
        {
            if (object.members[i - 1].key == key)
            {
                return i - 1;
            }
        }

        return std::nullopt;
    }

    const JsoncValue_s* FindMemberValue(const JsoncValue_s& object, std::string_view key)
    {
        const auto index = FindMember(object, key);
        return index ? &object.values[*index] : nullptr;
    }

    // The object at the end of the path, or null when one on the way is missing.
    const JsoncValue_s* FindObject(const JsoncValue_s& root, std::span<const std::string> path)
    {
        const auto* object = &root;
        for (auto depth = std::size_t{0}; depth < path.size(); ++depth)
        {
            const auto* value = FindMemberValue(*object, path[depth]);
            if (value == nullptr)
            {
                return nullptr;
            }

            if (!value->isObject)
            {
                throw ConfigError{std::format("{}: must be an object", StringUtils::Join(path.first(depth + 1), "."))};
            }

            object = value;
        }

        return object;
    }
}

JsoncEdit_s JsoncEditor::AddMissing(std::string_view text, std::span<const std::string> path, std::string_view membersJson)
{
    const auto members = Json::parse(membersJson);
    assert(members.is_object() && "JsoncEditor::AddMissing takes a JSON object of members");

    const auto root = JsoncScanner{text}.ScanDocument();
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
        const auto* value = FindMemberValue(*object, path[depth]);
        if (value == nullptr)
        {
            break;
        }

        if (!value->isObject)
        {
            throw ConfigError{std::format("{}: must be an object", StringUtils::Join(path.first(depth + 1), "."))};
        }

        object = value;
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
            if (FindMemberValue(*object, key) == nullptr)
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

// The values already there are replaced from the last in the text back, so earlier offsets stay right; the rest
// are then added as AddMissing adds them.
JsoncEdit_s JsoncEditor::Set(std::string_view text, std::span<const std::string> path, std::string_view membersJson)
{
    const auto members = Json::parse(membersJson);
    assert(members.is_object() && "JsoncEditor::Set takes a JSON object of members");

    const auto root = JsoncScanner{text}.ScanDocument();
    if (!root.isObject)
    {
        throw ConfigError{"the top level must be an object"};
    }

    const auto* object = FindObject(root, path);
    if (object == nullptr)
    {
        return AddMissing(text, path, membersJson);
    }

    const auto layout = DetectLayout(text, root);
    const auto objectIndent = std::string{GetIndent(text, object->begin)};
    auto replacements = std::vector<Replacement_s>{};
    auto missing = Json::object();
    for (const auto& [key, value] : members.items())
    {
        const auto index = FindMember(*object, key);
        if (!index)
        {
            missing[key] = value;
            continue;
        }

        const auto& member = object->members[*index];
        const auto& old = object->values[*index];
        const auto indent = StartsLine(text, member.keyBegin) ? std::string{GetIndent(text, member.keyBegin)} : objectIndent + std::string{layout.indentUnit};
        replacements.push_back({.offset = old.begin, .length = old.end - old.begin, .text = FormatBlock(value, indent, layout)});
    }

    std::ranges::sort(replacements, std::ranges::greater{}, &Replacement_s::offset);

    auto result = std::string{text};
    for (const auto& replacement : replacements)
    {
        result.replace(replacement.offset, replacement.length, replacement.text);
    }

    if (missing.empty())
    {
        return {.text = std::move(result)};
    }

    return AddMissing(result, path, missing.dump());
}
