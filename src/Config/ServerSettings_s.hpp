#pragma once

struct ServerSettings_s
{
    std::string url;
    std::string origin;
    std::string tlsCaFile = "SYSTEM";
};
