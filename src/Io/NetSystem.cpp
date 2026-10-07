#include "pch.hpp"
#include "NetSystem.hpp"

#include <ixwebsocket/IXNetSystem.h>

NetSystem::NetSystem()
{
    if (!ix::initNetSystem())
    {
        throw std::runtime_error{"Failed to initialize the network system"};
    }
}

NetSystem::~NetSystem()
{
    ix::uninitNetSystem();
}
