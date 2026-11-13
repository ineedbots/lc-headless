#pragma once

#include "../Console/CommandExecution.hpp"
#include "Type/AccountStatus_s.hpp"

// Application operations use this facade without depending on network ownership.
class AccountControl
{
public:
    virtual ~AccountControl() = default;
    virtual void HandleCommand(std::string_view line, std::shared_ptr<CommandExecution> execution = {}) = 0;
    virtual std::size_t GetAccountCount() const = 0;
    virtual AccountStatus_s GetAccountStatus(std::size_t index) const = 0;
};
