#include "pch.hpp"
#include "HttpRouter.hpp"
#include "Endpoints/ApplicationStatusEndpoint.hpp"
#include "Endpoints/ConsoleCommandsEndpoint.hpp"
#include "HttpResponses.hpp"

namespace
{
    bool IsJson(std::string_view value)
    {
        value = value.substr(0, value.find(';'));
        while (!value.empty() && value.back() == ' ')
        {
            value.remove_suffix(1);
        }
        auto lowered = std::string{value};
        std::ranges::transform(lowered, lowered.begin(), [](unsigned char c)
        {
            return static_cast<char>(std::tolower(c));
        });
        return lowered == "application/json";
    }
}

HttpRouter::HttpRouter()
    : HttpRouter{{ConsoleCommandsEndpoint::Route(), ApplicationStatusEndpoint::Route()}}
{
}

HttpRouter::HttpRouter(std::vector<HttpRoute_s> routes)
{
    for (auto& route : routes)
    {
        if (route.path.empty() || route.path.front() != '/' || route.path.find('?') != std::string::npos || route.method.empty() || !route.decode)
        {
            throw std::invalid_argument{"HTTP routes need an exact path, method and decoder"};
        }
        auto& methods = m_routes[route.path];
        if (std::ranges::find(methods, route.method, &HttpRoute_s::method) != methods.end())
        {
            throw std::invalid_argument{std::format("Duplicate HTTP route: {} {}", route.method, route.path)};
        }
        methods.push_back(std::move(route));
    }
}

HttpRouter::MatchResult HttpRouter::Match(std::string_view method, std::string_view target, std::string_view contentType) const
{
    if (target.find('?') != std::string_view::npos)
    {
        return HttpResponses::Error(400, "query_not_supported", "Query parameters are unsupported", {}, true);
    }
    const auto group = m_routes.find(std::string{target});
    if (group == m_routes.end())
    {
        return HttpResponses::Error(404, "not_found", "Unknown endpoint", {}, true);
    }
    const auto& methods = group->second;
    const auto route = std::ranges::find(methods, method, &HttpRoute_s::method);
    if (route == methods.end())
    {
        auto response = HttpResponses::Error(405, "method_not_allowed", "Unsupported method", {}, true);
        for (const auto& entry : methods)
        {
            if (!response.allow.empty())
            {
                response.allow += ", ";
            }
            response.allow += entry.method;
        }
        return response;
    }
    if (route->requiresJson && !IsJson(contentType))
    {
        return HttpResponses::Error(415, "content_type", "application/json required", {}, true);
    }
    return *route;
}
