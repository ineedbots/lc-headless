#pragma once

#include <boost/asio/executor_work_guard.hpp>
#include <boost/asio/io_context.hpp>
#include <boost/asio/post.hpp>

// An io_context on a thread of its own, so a test server answers while the test's thread waits in a client, as a
// real server would. A server calls Stop first in its destructor, so nothing runs while its members go.
class ServerThread
{
public:
    ServerThread();
    ~ServerThread();

    ServerThread(const ServerThread&) = delete;
    ServerThread& operator=(const ServerThread&) = delete;

    [[nodiscard]] boost::asio::io_context& GetContext();
    // Stops the loop and joins the thread. Later calls do nothing.
    void Stop() noexcept;

    // Runs function on the server's thread and waits for its result.
    template <typename TFunction>
    std::invoke_result_t<TFunction> Invoke(TFunction function)
    {
        auto task = std::packaged_task<std::invoke_result_t<TFunction>()>{std::move(function)};
        auto result = task.get_future();
        boost::asio::post(m_io, [&task]
        {
            task();
        });

        return result.get();
    }

private:
    boost::asio::io_context m_io{1};
    boost::asio::executor_work_guard<boost::asio::io_context::executor_type> m_work;
    std::thread m_thread;
};
