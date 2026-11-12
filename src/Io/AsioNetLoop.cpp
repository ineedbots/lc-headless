#include "pch.hpp"
#include "AsioNetLoop.hpp"

#include "../Http/HttpRouter.hpp"
#include "../Application/Events/ApplicationEventBridge.hpp"
#include "../Console/Logger.hpp"
#include "AsioLink.hpp"
#include "Type/ConnectionOptions_s.hpp"
#include "Link.hpp"

#include <boost/asio/post.hpp>
#include "../Console/ConsoleCapture.hpp"
#include "../Http/AsioHttpServer.hpp"

AsioNetLoop::AsioNetLoop()
    : m_work{boost::asio::make_work_guard(m_io)}
{
}

std::shared_ptr<Link> AsioNetLoop::Open(const ConnectionOptions_s& options, std::shared_ptr<Logger> logger)
{
    auto link = std::make_shared<AsioLink>(*this, m_io, options, std::move(logger));
    link->Start();
    return link;
}

void AsioNetLoop::Poll()
{
    const auto pause = ConsoleCaptureScope{nullptr};
    const auto until = Clock::now() + 2ms;
    for (auto count = 0; count < 64 && Clock::now() < until; ++count)
    {
        if (!m_io.poll_one())
        {
            break;
        }
    }
}

void AsioNetLoop::Wait(Deadline deadline)
{
    const auto capturePause = ConsoleCaptureScope{nullptr};

    if (deadline)
    {
        m_io.run_one_until(*deadline);
    }
    else
    {
        m_io.run_one();
    }

    const auto pause = ConsoleCaptureScope{nullptr};
    const auto until = Clock::now() + 2ms;
    for (auto count = 1; count < 64 && Clock::now() < until; ++count)
    {
        if (!m_io.poll_one())
        {
            break;
        }
    }
}

void AsioNetLoop::Settle(Clock::time_point deadline)
{
    while (m_linkCount > 0 && Clock::now() < deadline)
    {
        Wait(deadline);
    }
}

void AsioNetLoop::Wake() noexcept
{
    try
    {
        boost::asio::post(m_io, []
        {
        });
    }
    catch (const std::exception&)
    {
        // Only an allocation can fail here, and the waiting thread wakes at its own deadline anyway.
    }
}

void AsioNetLoop::AddLink()
{
    ++m_linkCount;
}

void AsioNetLoop::RemoveLink() noexcept
{
    assert(m_linkCount > 0 && "RemoveLink without AddLink");
    --m_linkCount;
}

std::unique_ptr<HttpServer> AsioNetLoop::ListenHttp(const HttpSettings_s& settings, std::shared_ptr<ApplicationRequestBridge> bridge, std::shared_ptr<ApplicationEventBridge> events)
{
    if (settings.host.empty())
    {
        return {};
    }

    return std::make_unique<AsioHttpServer>(m_io, settings, std::move(bridge), HttpRouter{}, std::move(events));
}
