#include "pch.hpp"
#include "LoopbackPort.hpp"

#include "Io/NetSystem.hpp"

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
#endif

namespace
{
#ifdef _WIN32
    using NativeSocket = SOCKET;
    const auto INVALID_NATIVE_SOCKET = INVALID_SOCKET;

    void CloseNativeSocket(NativeSocket socket)
    {
        closesocket(socket);
    }

    // Without this, Windows lets the probe share a port that a server bound with SO_REUSEADDR.
    void RefuseToShareAddress(NativeSocket socket)
    {
        auto exclusive = BOOL{TRUE};
        setsockopt(socket, SOL_SOCKET, SO_EXCLUSIVEADDRUSE, reinterpret_cast<const char*>(&exclusive), sizeof(exclusive));
    }
#else
    using NativeSocket = int;
    const auto INVALID_NATIVE_SOCKET = -1;

    void CloseNativeSocket(NativeSocket socket)
    {
        close(socket);
    }

    // POSIX only shares a port with sockets that ask for it, and a listening one can't be shared anyway.
    void RefuseToShareAddress(NativeSocket)
    {
    }
#endif
}

bool LoopbackPort::IsFree(int port)
{
    const auto netSystem = NetSystem{};
    const auto probe = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (probe == INVALID_NATIVE_SOCKET)
    {
        return false;
    }

    RefuseToShareAddress(probe);
    auto address = sockaddr_in{};
    address.sin_family = AF_INET;
    address.sin_port = htons(static_cast<u16>(port));
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    const auto bound = bind(probe, reinterpret_cast<const sockaddr*>(&address), sizeof(address)) == 0;
    CloseNativeSocket(probe);
    return bound;
}
