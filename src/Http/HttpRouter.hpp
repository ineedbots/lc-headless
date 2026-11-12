#pragma once

#include "HttpRouteMatch_s.hpp"

class HttpRouter
{
public:
    using MatchResult = std::variant<HttpRouteMatch_s, HttpResponse_s>;
    HttpRouter();
    explicit HttpRouter(std::vector<HttpRoute_s> routes);
    [[nodiscard]] MatchResult Match(std::string_view method, std::string_view target, std::string_view contentType) const;

private:
    struct RegisteredRoute_s
    {
        HttpRoute_s route;
        std::vector<std::string> parameterNames;
    };

    struct Node_s
    {
        std::unordered_map<std::string, std::size_t> literals;
        std::optional<std::size_t> parameter;
        std::vector<RegisteredRoute_s> methods;
    };

    std::vector<Node_s> m_nodes{1};
};
