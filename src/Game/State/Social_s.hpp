#pragma once

enum class MessageType_e : u8
{
    Game,
    Public,
    Say,
    Private,
    TradeRequest,
    DuelRequest,
};

struct ChatMessage_s
{
    u64 sequence = 0;
    u64 tick = 0;
    MessageType_e type = MessageType_e::Game;
    std::string sender;
    u64 sender37 = 0;
    u8 rights = 0;
    std::string text;
};

struct Friend_s
{
    u64 name37 = 0;
    std::string name;
    u8 world = 0;
};

struct Social_s
{
    u8 friendServerStatus = 0;
    u8 publicMode = 0;
    u8 privateMode = 0;
    u8 tradeMode = 0;
    std::vector<Friend_s> friends;
    std::vector<u64> ignores;
};
