#pragma once

struct JsoncEdit_s
{
    std::string text;
    // The keys added to the object at the path, in order; empty when it already had them all.
    std::vector<std::string> added;
};

// Edits JSON-with-comments text where it needs to change, and leaves the rest as it was, comments and layout
// included, where a JSON library would rewrite all of it. Added members follow the indentation and line
// endings around them.
class JsoncEditor
{
public:
    // Adds the members of membersJson, a JSON object, that the object at path lacks, creating the objects on
    // path that are missing. Members already there are kept as they are, whatever their value. Throws
    // ConfigError when the text isn't a valid JSON object, or a key on path holds something else.
    [[nodiscard]] static JsoncEdit_s AddMissing(std::string_view text, std::span<const std::string> path, std::string_view membersJson);
};
