#include "pch.hpp"
#include "TempFolder.hpp"

namespace
{
    // ctest runs the tests in parallel processes, so a name from the clock can be taken by another process that
    // started in the same tick. A random name that create_directory reports as new belongs to this folder alone.
    std::filesystem::path MakeUniqueFolder(std::string_view prefix)
    {
        static auto random = std::mt19937_64{std::random_device{}()};

        const auto parent = std::filesystem::temp_directory_path();
        while (true)
        {
            auto path = parent / std::format("{}-{:016x}", prefix, random());
            if (std::filesystem::create_directory(path))
            {
                return path;
            }
        }
    }
}

TempFolder::TempFolder(std::string_view prefix)
    : m_path{MakeUniqueFolder(prefix)}
{
}

TempFolder::~TempFolder()
{
    auto ignored = std::error_code{};
    std::filesystem::remove_all(m_path, ignored);
}

const std::filesystem::path& TempFolder::GetPath() const
{
    return m_path;
}

void TempFolder::WriteFile(const std::filesystem::path& relativePath, std::string_view text) const
{
    const auto path = m_path / relativePath;
    std::filesystem::create_directories(path.parent_path());

    auto file = std::ofstream{path, std::ios::binary};
    if (!file)
    {
        throw std::runtime_error{std::format("Can't write {}", path.string())};
    }

    file << text;
}

void TempFolder::RewriteFile(const std::filesystem::path& relativePath, std::string_view text) const
{
    const auto path = m_path / relativePath;
    const auto before = std::filesystem::last_write_time(path);
    WriteFile(relativePath, text);
    std::filesystem::last_write_time(path, before + 1s);
}
