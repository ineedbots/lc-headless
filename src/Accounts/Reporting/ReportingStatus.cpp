#include "pch.hpp"
#include "ReportingStatus.hpp"

#include "Game/GameClient.hpp"

std::string_view ReportingStatus::Name(ClientStatus_e status)
{
    switch (status)
    {
    case ClientStatus_e::Disconnected:
        return "disconnected";
    case ClientStatus_e::Connecting:
        return "connecting";
    case ClientStatus_e::InGame:
        return "ingame";
    case ClientStatus_e::LoggingOut:
        return "logging out";
    case ClientStatus_e::LoggedOut:
        return "logged out";
    }

    return "unknown";
}
