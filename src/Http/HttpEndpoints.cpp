#include "pch.hpp"
#include "HttpEndpoints.hpp"

#include "Type/HttpRoute_s.hpp"

std::vector<HttpRoute_s> HttpEndpoints::Routes()
{
    return Catalog::Routes();
}
