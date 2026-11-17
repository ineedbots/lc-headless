#pragma once

#include <boost/asio/ip/tcp.hpp>
#include <boost/beast/core.hpp>
#include <boost/beast/websocket/teardown.hpp>

class AsioBufferedStream : public boost::beast::buffered_read_stream<boost::beast::tcp_stream, boost::beast::flat_buffer>
{
public:
    AsioBufferedStream(boost::asio::ip::tcp::socket socket, std::string_view buffered)
        : buffered_read_stream{std::move(socket)}
    {
        buffer() = boost::beast::flat_buffer{16384};
        buffer().commit(boost::asio::buffer_copy(buffer().prepare(buffered.size()), boost::asio::buffer(buffered)));
    }

    // Beast finds these customization points by ADL on the wrapped stream.
    friend void teardown(boost::beast::role_type role, AsioBufferedStream& stream, boost::system::error_code& error)
    {
        using boost::beast::websocket::teardown;
        teardown(role, stream.next_layer(), error);
    }

    template <class Handler>
    friend void async_teardown(boost::beast::role_type role, AsioBufferedStream& stream, Handler&& handler)
    {
        using boost::beast::websocket::async_teardown;
        async_teardown(role, stream.next_layer(), std::forward<Handler>(handler));
    }
};
