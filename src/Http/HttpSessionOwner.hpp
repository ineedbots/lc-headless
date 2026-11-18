#pragma once

#include "Type/HttpSessionContext_s.hpp"
#include "Websockets/AsioWebSocketSession.hpp"

class HttpSessionOwner
{
public:
    virtual ~HttpSessionOwner() = default;

    virtual const HttpSessionContext_s& GetContext() const = 0;
    virtual void RegisterRequest(u64 request, u64 session) = 0;
    virtual void RetireRequest(u64 request) = 0;
    virtual void RetireSession(u64 session) = 0;
    virtual void UpgradeSession(u64 session, std::unique_ptr<AsioWebSocketSession> upgraded) = 0;
    virtual void StartOperation() = 0;
    virtual void FinishOperation() = 0;
};
