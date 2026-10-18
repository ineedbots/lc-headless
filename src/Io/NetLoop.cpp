#include "pch.hpp"
#include "NetLoop.hpp"

#include "AsioNetLoop.hpp"

std::shared_ptr<NetLoop> NetLoop::Create()
{
    return std::make_shared<AsioNetLoop>();
}
