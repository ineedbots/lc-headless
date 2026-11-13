#pragma once

#include "Application/Events/ApplicationEventPublisher.hpp"
#include "Application/Events/Type/ApplicationEvent_s.hpp"

class EventCapture : public ApplicationEventPublisher
{
public:
    explicit EventCapture(std::function<void(const ApplicationEvent_s&)> capture)
        : m_capture{std::move(capture)}
    {
    }

    using ApplicationEventPublisher::Publish;
    bool Publish(ApplicationEvent_s event) override
    {
        m_capture(event);
        return true;
    }

    bool IsStopping() const override
    {
        return false;
    }

protected:
    void RejectPublication() override
    {
        throw std::invalid_argument{"Invalid captured event"};
    }

private:
    std::function<void(const ApplicationEvent_s&)> m_capture;
};
