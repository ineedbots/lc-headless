#include "pch.hpp"
#include "ServerThread.hpp"

#include <boost/asio/executor_work_guard.hpp>
#include <boost/asio/io_context.hpp>

ServerThread::ServerThread()
    : m_work{boost::asio::make_work_guard(m_io)}
    , m_thread{[this]
      {
          m_io.run();
      }}
{
}

ServerThread::~ServerThread()
{
    Stop();
}

boost::asio::io_context& ServerThread::GetContext()
{
    return m_io;
}

void ServerThread::Stop() noexcept
{
    if (!m_thread.joinable())
    {
        return;
    }

    m_work.reset();
    m_io.stop();
    m_thread.join();
}
