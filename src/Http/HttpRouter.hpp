#pragma once
#include "HttpRoute_s.hpp"

class HttpRouter
{
public:
    using MatchResult = std::variant<HttpRoute_s, HttpResponse_s>;
    HttpRouter();
    explicit HttpRouter(std::vector<HttpRoute_s> routes);
    [[nodiscard]] MatchResult Match(std::string_view method, std::string_view target, std::string_view contentType) const;

private:
    std::unordered_map<std::string, std::vector<HttpRoute_s>> m_routes;
};
