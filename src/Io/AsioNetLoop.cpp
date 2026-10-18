#include "pch.hpp"
#include "AsioNetLoop.hpp"

#include "../Console/Logger.hpp"
#include "AsioLink.hpp"
#include "ConnectionOptions_s.hpp"
#include "Link.hpp"

#include <boost/asio/post.hpp>

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
    m_io.poll();
}

void AsioNetLoop::Wait(Deadline deadline)
{
    if (deadline)
    {
        m_io.run_one_until(*deadline);
    }
    else
    {
        m_io.run_one();
    }

    m_io.poll();
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
