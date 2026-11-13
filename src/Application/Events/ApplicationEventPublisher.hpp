#pragma once

#include "Type/ApplicationEvent_s.hpp"
#include "EventProtocol.hpp"
#include "EventLimits.hpp"

class ApplicationEventPublisher
{
public:
    virtual ~ApplicationEventPublisher() = default;

    template <typename T>
    bool Publish(std::string_view account, const T& payload)
    {
        if (IsStopping())
        {
            return false;
        }
        if (account.size() > EventLimits::MAX_ACCOUNT_BYTES || !EventProtocol::Measure(payload))
        {
            RejectPublication();
            return false;
        }
        return Publish({std::string{account}, payload});
    }

    virtual bool Publish(ApplicationEvent_s event) = 0;
    virtual bool IsStopping() const = 0;

protected:
    virtual void RejectPublication() = 0;
};
