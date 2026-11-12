#pragma once

#include "ConsoleCapture.hpp"

struct CommandRecipient_s
{
    std::string account;
    std::string outcome = "pending";
    std::string errorCode;
};

class CommandExecution
{
public:
    explicit CommandExecution(std::size_t limit, std::chrono::steady_clock::time_point expires)
        : capture{limit}
        , deadline{expires}
    {
    }

    bool CanExecute() const;
    bool IsComplete() const;
    ConsoleCapture capture;
    std::chrono::steady_clock::time_point deadline;
    bool abandoned = false;
    bool started = false;
    bool dispatched = false;
    std::string errorCode;
    std::vector<CommandRecipient_s> recipients;
};

// A queue owns its token; destroying an invocation cancels it exactly once.
class CommandRecipient
{
public:
    CommandRecipient(std::shared_ptr<CommandExecution> execution, std::string account);
    ~CommandRecipient();
    CommandRecipient(const CommandRecipient&) = delete;
    CommandRecipient& operator=(const CommandRecipient&) = delete;
    void Finish(std::string outcome, std::string error = {});
    std::shared_ptr<CommandExecution> execution;

private:
    std::size_t m_index;
};
