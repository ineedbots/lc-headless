#include "pch.hpp"
#include "FileUtils.hpp"

namespace
{
    constexpr auto TEMPORARY_EXTENSION = ".tmp";
}

std::optional<std::string> FileUtils::ReadText(const std::filesystem::path& path)
{
    // Linux opens a directory fine and only fails on the first read, with an exception
    auto error = std::error_code{};
    if (std::filesystem::is_directory(path, error))
    {
        return std::nullopt;
    }

    auto file = std::ifstream{path, std::ios::binary};
    if (!file)
    {
        return std::nullopt;
    }

    try
    {
        auto text = std::string{std::istreambuf_iterator<char>{file}, std::istreambuf_iterator<char>{}};

        if (file.bad())
        {
            return std::nullopt;
        }

        return text;
    }
    catch (const std::ios_base::failure&)
    {
        return std::nullopt;
    }
}

std::optional<std::vector<u8>> FileUtils::ReadBytes(const std::filesystem::path& path)
{
    const auto text = ReadText(path);
    if (!text)
    {
        return std::nullopt;
    }

    return std::vector<u8>{text->begin(), text->end()};
}

void FileUtils::ReplaceFile(const std::filesystem::path& path, std::string_view text)
{
    auto temporary = path;
    temporary += TEMPORARY_EXTENSION;
    {
        auto file = std::ofstream{temporary, std::ios::binary | std::ios::trunc};
        file << text;
        file.flush();
        if (!file)
        {
            throw std::runtime_error{std::format("{}: couldn't be written", temporary.string())};
        }
    }

    auto error = std::error_code{};
    std::filesystem::rename(temporary, path, error);

    if (error)
    {
        std::filesystem::remove(temporary, error);
        throw std::runtime_error{std::format("{}: couldn't be replaced", path.string())};
    }
}

bool FileUtils::IsInsideFolder(const std::filesystem::path& relative)
{
    if (relative.empty() || relative.has_root_name() || relative.has_root_directory())
    {
        return false;
    }

    return std::ranges::none_of(relative, [](const std::filesystem::path& part)
    {
        return part == "..";
    });
}
