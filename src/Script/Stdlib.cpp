#include "pch.hpp"
#include "Stdlib.hpp"

std::optional<std::string_view> Stdlib::Find(std::string_view path)
{
    auto normalized = std::string{path};
    std::ranges::replace(normalized, '\\', '/');
    const auto files = GetFiles();
    const auto found = std::ranges::find(files, normalized, &StdlibFile_s::path);
    if (found == files.end())
    {
        return std::nullopt;
    }

    return found->source;
}
