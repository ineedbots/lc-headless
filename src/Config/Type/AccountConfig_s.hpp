#pragma once

#include "ConfigDurationJson.hpp"
#include "ProxySettings_s.hpp"
#include "ServerSettings_s.hpp"

#include <nlohmann/json.hpp>

struct AccountSettings_s
{
    std::string username;
    std::string password;
};

NLOHMANN_DEFINE_TYPE_NON_INTRUSIVE_WITH_DEFAULT(AccountSettings_s, username, password)

struct ScriptConfig_s
{
    std::string file;
    // A define_bot script reads only the object under its name, so one file can keep the settings of several.
    std::string settings = "{}";
    // Zero turns reports off.
    std::chrono::minutes progressReportMinutes{0};
};

// One account file. A server or proxy section replaces client.jsonc's for this account.
struct AccountConfig_s
{
    std::string name;
    // Where a define_bot script's default settings are added; empty for one made in code.
    std::filesystem::path file;
    AccountSettings_s credentials;
    bool enabled = true;
    std::optional<ServerSettings_s> server;
    std::optional<ProxySettings_s> proxy;
    std::optional<ScriptConfig_s> script;
    // Zero idles until interrupted.
    std::chrono::seconds idleSeconds{0};
    bool randomEvents = true;
    // Zero turns the stall guard off.
    std::chrono::minutes stallMinutes{10};
    // Turns run back on once energy reaches runEnergyMin, as rs2b0t's run manager does.
    bool runAuto = true;
    s32 runEnergyMin = 20;
};

namespace ConfigJsonDetail
{
    inline constexpr auto TYPE_ERROR_ID = 302;

    template <typename TSection>
    std::optional<TSection> ReadSection(const nlohmann::json& account, std::string_view key)
    {
        const auto section = account.find(key);
        if (section == account.end() || section->is_null())
        {
            return std::nullopt;
        }

        if (!section->is_object())
        {
            throw nlohmann::json::type_error::create(TYPE_ERROR_ID, "must be an object", &*section);
        }

        return section->get<TSection>();
    }
}

inline void from_json(const nlohmann::json& value, ScriptConfig_s& script)
{
    script.file = value.value("file", std::string{});
    script.progressReportMinutes = std::chrono::minutes{value.value("progressReportMinutes", s64{0})};

    const auto settings = value.find("settings");
    if (settings == value.end())
    {
        return;
    }

    if (!settings->is_object())
    {
        throw nlohmann::json::type_error::create(ConfigJsonDetail::TYPE_ERROR_ID, "must be an object", &*settings);
    }

    script.settings = settings->dump();
}

inline void from_json(const nlohmann::json& value, AccountConfig_s& account)
{
    value.get_to(account.credentials);
    account.enabled = value.value("enabled", account.enabled);
    account.idleSeconds = value.value("idleSeconds", account.idleSeconds);
    account.randomEvents = value.value("randomEvents", account.randomEvents);
    account.stallMinutes = value.value("stallMinutes", account.stallMinutes);
    account.runAuto = value.value("runAuto", account.runAuto);
    account.runEnergyMin = value.value("runEnergyMin", account.runEnergyMin);

    account.server = ConfigJsonDetail::ReadSection<ServerSettings_s>(value, "server");
    account.proxy = ConfigJsonDetail::ReadSection<ProxySettings_s>(value, "proxy");

    const auto script = value.find("script");
    if (script == value.end() || script->is_null())
    {
        return;
    }

    if (!script->is_object())
    {
        throw nlohmann::json::type_error::create(ConfigJsonDetail::TYPE_ERROR_ID, "must be an object", &*script);
    }

    account.script = script->get<ScriptConfig_s>();
}
