#pragma once

struct EventError_s
{
    s32 version = 1;
    std::string type = "error";
    std::optional<std::string> id;
    std::string code;
};
