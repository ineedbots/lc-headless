#include "pch.hpp"
#include "CommandExecution.hpp"
bool CommandExecution::CanExecute() const
{
    return !abandoned && std::chrono::steady_clock::now() < deadline;
}
bool CommandExecution::IsComplete() const
{
    return dispatched && std::ranges::none_of(recipients, [](const auto& r)
    {
        return r.outcome == "pending";
    });
}
CommandRecipient::CommandRecipient(std::shared_ptr<CommandExecution> value, std::string account)
    : execution{std::move(value)}
    , m_index{execution->recipients.size()}
{
    execution->recipients.push_back({.account = std::move(account)});
}
CommandRecipient::~CommandRecipient()
{
    Finish("cancelled", "invocation_cancelled");
}
void CommandRecipient::Finish(std::string outcome, std::string error)
{
    auto& recipient = execution->recipients[m_index];
    if (recipient.outcome != "pending")
    {
        return;
    }
    recipient.outcome = std::move(outcome);
    recipient.errorCode = std::move(error);
}
