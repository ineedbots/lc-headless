#pragma once

struct JsoncEdit_s
{
    std::string text;
    std::vector<std::string> added;
};

// Changes only what needs to change, keeping comments and layout, where a JSON library would rewrite all of it.
class JsoncEditor
{
public:
    // Members already there are kept, whatever their value.
    [[nodiscard]] static JsoncEdit_s AddMissing(std::string_view text, std::span<const std::string> path, std::string_view membersJson);
    // Members already there take the new value in place; added lists only the members added.
    [[nodiscard]] static JsoncEdit_s Set(std::string_view text, std::span<const std::string> path, std::string_view membersJson);
};
