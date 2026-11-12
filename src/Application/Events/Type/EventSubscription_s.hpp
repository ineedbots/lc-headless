#pragma once

struct EventSubscription_s
{
    std::string id;
    std::vector<std::string> events;
    std::vector<std::string> accounts;
};

struct EventCommand_s
{
    std::string action;
    EventSubscription_s subscription;
};

struct EventProtocolError_s
{
    std::string id;
    std::string code;
};
