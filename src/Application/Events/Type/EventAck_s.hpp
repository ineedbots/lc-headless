#pragma once

struct EventAck_s
{
    s32 version = 1;
    std::string type = "ack";
    std::string id;
    std::string action;
    std::string instance;
    u64 sequence = 0;
};
