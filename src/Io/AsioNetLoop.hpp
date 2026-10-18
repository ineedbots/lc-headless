#pragma once

#include "../Console/Logger.hpp"
#include "ConnectionOptions_s.hpp"
#include "Link.hpp"
#include "NetLoop.hpp"

#include <boost/asio/executor_work_guard.hpp>
#include <boost/asio/io_context.hpp>

class AsioNetLoop : public NetLoop
{
public:
    AsioNetLoop();

    [[nodiscard]] std::shared_ptr<Link> Open(const ConnectionOptions_s& options, std::shared_ptr<Logger> logger) override;
    void Poll() override;
    void Wait(Deadline deadline) override;
    void Settle(Clock::time_point deadline) override;
    void Wake() noexcept override;

    // AsioLink's constructor and destructor, so Settle knows when every link has finished.
    void AddLink();
    void RemoveLink() noexcept;

private:
    // The order matters. Destroying m_io destroys the handlers that keep lingering links alive, and each link counts
    // itself out of m_linkCount as it goes, so the count must outlive m_io. The work guard must go before m_io.
    std::size_t m_linkCount = 0;
    boost::asio::io_context m_io{1};
    boost::asio::executor_work_guard<boost::asio::io_context::executor_type> m_work;
};
