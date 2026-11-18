#pragma once

#include "Game/GameClient.hpp"

class ReportingStatus
{
public:
    ReportingStatus() = delete;

    [[nodiscard]] static std::string_view Name(ClientStatus_e status);
};
