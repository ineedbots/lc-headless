#pragma once

#include "AccountConfig_s.hpp"

// One file in the accounts folder.
class AccountFile
{
public:
    static constexpr auto EXTENSION = ".jsonc";

    AccountFile() = delete;

    // The account's name is the file's name without its extension.
    [[nodiscard]] static AccountConfig_s Load(const std::filesystem::path& path);
    [[nodiscard]] static AccountConfig_s Parse(std::string_view text, std::string name);
    // Keeps the file's comments and layout, and rewrites it only when a key is added. Returns the keys added.
    [[nodiscard]] static std::vector<std::string> AddScriptSettings(const std::filesystem::path& path, std::string_view botName, std::string_view settingsJson);
    // script.settings[name][key] = the value, keeping the file's comments and layout; rewritten only when it
    // changes.
    static void SetScriptSetting(const std::filesystem::path& path, std::string_view name, std::string_view key, std::string_view valueJson);
};
