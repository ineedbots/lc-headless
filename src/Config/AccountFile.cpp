#include "pch.hpp"
#include "AccountFile.hpp"

#include "../Utils/FileUtils.hpp"
#include "AccountConfig_s.hpp"
#include "ConfigJson.hpp"
#include "ConfigValidator.hpp"
#include "Error/ConfigError.hpp"
#include "JsoncEditor.hpp"

namespace
{
    std::string ReadFile(const std::filesystem::path& path)
    {
        auto text = FileUtils::ReadText(path);
        if (!text)
        {
            throw ConfigError{std::format("Failed to read account file {}", path.string())};
        }

        return std::move(*text);
    }
}

AccountConfig_s AccountFile::Load(const std::filesystem::path& path)
{
    if (!std::filesystem::exists(path))
    {
        throw ConfigError{std::format("{}: account file not found", path.string())};
    }

    const auto text = ReadFile(path);
    try
    {
        auto account = Parse(text, path.stem().string());
        account.file = path;
        return account;
    }
    catch (const ConfigError& e)
    {
        throw ConfigError{std::format("{}: {}", path.string(), e.what())};
    }
}

AccountConfig_s AccountFile::Parse(std::string_view text, std::string name)
{
    auto account = ConfigJson::ParseAccount(text);
    account.name = std::move(name);
    ConfigValidator::ValidateAccount(account);
    return account;
}

std::vector<std::string> AccountFile::AddScriptSettings(const std::filesystem::path& path, std::string_view botName, std::string_view settingsJson)
{
    const auto text = ReadFile(path);
    auto edit = JsoncEdit_s{};
    try
    {
        ConfigJson::CheckObject(text);

        const auto keys = std::array{std::string{"script"}, std::string{"settings"}, std::string{botName}};
        edit = JsoncEditor::AddMissing(text, keys, settingsJson);
    }
    catch (const ConfigError& e)
    {
        throw ConfigError{std::format("{}: {}", path.string(), e.what())};
    }

    if (!edit.added.empty())
    {
        FileUtils::ReplaceFile(path, edit.text);
    }

    return std::move(edit.added);
}
