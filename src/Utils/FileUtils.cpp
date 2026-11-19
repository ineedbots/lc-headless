#include "pch.hpp"
#include "FileUtils.hpp"

#ifdef _WIN32
#include <share.h>
#endif

namespace
{
    constexpr auto TEMPORARY_EXTENSION = ".tmp";
}

std::optional<std::string> FileUtils::ReadText(const std::filesystem::path& path)
{
    // Linux can open a directory as a file.
    auto error = std::error_code{};
    if (std::filesystem::is_directory(path, error))
    {
        return std::nullopt;
    }

#ifdef _WIN32
    auto* stream = _wfsopen(path.c_str(), L"rb", _SH_DENYNO);
#else
    auto* stream = std::fopen(path.c_str(), "rb");
#endif

    auto file = std::unique_ptr<std::FILE, decltype(&std::fclose)>{stream, &std::fclose};
    if (!file)
    {
        return std::nullopt;
    }

    auto text = std::string{};
    auto buffer = std::array<char, 8192>{};
    auto size = std::size_t{};
    do
    {
        size = std::fread(buffer.data(), 1, buffer.size(), file.get());
        text.append(buffer.data(), size);
    } while (size == buffer.size());

    if (std::ferror(file.get()) != 0)
    {
        return std::nullopt;
    }

    return text;
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

void FileUtils::AppendText(const std::filesystem::path& path, std::string_view text)
{
    if (!path.parent_path().empty())
    {
        std::filesystem::create_directories(path.parent_path());
    }

    auto file = std::ofstream{path, std::ios::binary | std::ios::app};
    file << text;
    file.flush();
    if (!file)
    {
        throw std::runtime_error{std::format("can't write {}", path.string())};
    }
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
