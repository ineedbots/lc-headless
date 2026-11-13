#include "pch.hpp"
#include "AccountLogoutEvent.hpp"

#include "../../../Accounts/Type/AccountLogout_s.hpp"
#include "../EventPayloadJson.hpp"

#include <nlohmann/json.hpp>

std::optional<std::size_t> AccountLogoutEvent::Measure(const AccountLogout_s&)
{
    return sizeof(AccountLogout_s);
}

nlohmann::json AccountLogoutEvent::Serialize(const AccountLogout_s& payload)
{
    return payload;
}
