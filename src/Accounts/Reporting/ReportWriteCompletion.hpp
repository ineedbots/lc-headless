#pragma once

#include "Console/Logger.hpp"
#include "Websockets/Events/ApplicationEventPublisher.hpp"

class ReportWriteCompletion
{
public:
    ReportWriteCompletion() = delete;

    template <typename TWrite, typename TCommitted, typename TFailed>
    static void Poll(std::optional<TWrite>& pending, TCommitted committed, TFailed failed)
    {
        if (!pending || pending->completion.wait_for(0ms) != std::future_status::ready)
        {
            return;
        }

        auto write = std::move(*pending);
        pending.reset();

        try
        {
            write.completion.get();
        }
        catch (const std::exception& error)
        {
            failed(write, error);
            return;
        }

        committed(write);
    }

    template <typename TRecord>
    static void Publish(const std::shared_ptr<ApplicationEventPublisher>& events, Logger& logger, std::string_view account, const TRecord& record)
    {
        if (!events)
        {
            return;
        }

        try
        {
            events->Publish(account, record);
        }
        catch (const std::exception& error)
        {
            logger.Warning("The fleet record was saved, but its live event wasn't published: {}", error.what());
        }
    }
};
