#include "pch.hpp"
#include "TempFolder.hpp"

TempFolder::TempFolder(std::string_view prefix)
    : m_path{std::filesystem::temp_directory_path() / std::format("{}-{}", prefix, std::chrono::steady_clock::now().time_since_epoch().count())}
{
    std::filesystem::create_directories(m_path);
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
