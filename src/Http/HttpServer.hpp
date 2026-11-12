#pragma once
#include "../Application/ApplicationRequestBridge.hpp"
class HttpServer
{
public:
    virtual ~HttpServer() = default;
    virtual void Deliver(std::vector<CompletedApplicationRequest_s> results) = 0;
    virtual void Service() = 0;
    virtual void Stop() = 0;
    virtual void Close() = 0;
    virtual bool IsDrained() const = 0;
    virtual u16 GetPort() const = 0;
};
