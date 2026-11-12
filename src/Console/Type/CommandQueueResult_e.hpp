#pragma once

enum class CommandQueueResult_e : u8
{
    Accepted,
    Unavailable,
    UnknownCommand,
    QueueFull,
};
