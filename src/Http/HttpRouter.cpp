#include "pch.hpp"
#include "HttpRouter.hpp"

#include "../Utils/StringUtils.hpp"
#include "Endpoints/ApplicationStatusEndpoint.hpp"
#include "Endpoints/ApplicationEventsEndpoint.hpp"
#include "Endpoints/ConsoleCommandsEndpoint.hpp"
#include "HttpResponses.hpp"
#include "HttpUrl.hpp"

namespace
{
    bool IsJson(std::string_view value)
    {
        value = value.substr(0, value.find(';'));
        return StringUtils::EqualsIgnoringCase(StringUtils::TrimEnd(value, " "), "application/json");
    }
}

HttpRouter::HttpRouter()
    : HttpRouter{{ConsoleCommandsEndpoint::Route(), ApplicationStatusEndpoint::Route(), ApplicationEventsEndpoint::Route()}}
{
}

HttpRouter::HttpRouter(std::vector<HttpRoute_s> routes)
{
    for (auto& route : routes)
    {
        if (!route.path.starts_with('/') || route.path.find_first_of("?#") != std::string::npos ||
            std::ranges::any_of(route.path, [](unsigned char c)
        {
            return c < 0x20 || c == 0x7f;
        }) ||
            !StringUtils::IsUtf8(route.path) || route.method.empty() || (!route.decode && !route.webSocket) || (route.decode && route.webSocket))
        {
            throw std::invalid_argument{"HTTP routes need a path template, method and decoder"};
        }

        auto node = std::size_t{0};
        auto names = std::vector<std::string>{};
        for (const auto segment : HttpUrl::Segments(route.path))
        {
            if (segment.find_first_of("{}") != std::string_view::npos)
            {
                if (!segment.starts_with('{') || !segment.ends_with('}'))
                {
                    throw std::invalid_argument{"Path parameters must occupy an entire segment"};
                }

                const auto name = segment.substr(1, segment.size() - 2);
                if (!StringUtils::IsIdentifierAscii(name) || std::ranges::find(names, name) != names.end())
                {
                    throw std::invalid_argument{"Path parameters need unique identifier names"};
                }

                names.emplace_back(name);

                if (!m_nodes[node].parameter)
                {
                    const auto child = m_nodes.size();
                    m_nodes.emplace_back();
                    m_nodes[node].parameter = child;
                }

                node = *m_nodes[node].parameter;
            }
            else
            {
                const auto literal = std::string{segment};
                const auto found = m_nodes[node].literals.find(literal);
                if (found == m_nodes[node].literals.end())
                {
                    const auto child = m_nodes.size();
                    m_nodes.emplace_back();
                    m_nodes[node].literals.emplace(literal, child);
                    node = child;
                }
                else
                {
                    node = found->second;
                }
            }
        }

        auto& methods = m_nodes[node].methods;
        if (std::ranges::find(methods, route.method, [](const auto& entry) -> const std::string&
        {
            return entry.route.method;
        }) != methods.end())
        {
            throw std::invalid_argument{std::format("Duplicate HTTP route pattern: {} {}", route.method, route.path)};
        }

        methods.push_back({std::move(route), std::move(names)});
    }
}

HttpRouter::MatchResult HttpRouter::Match(std::string_view method, std::string_view target, std::string_view contentType) const
{
    auto url = HttpUrl::Parse(target);
    if (!url)
    {
        return HttpResponses::Error(400, "invalid_target", "Malformed request path or query string", {}, true);
    }

    struct Candidate_s
    {
        std::size_t node;
        std::size_t segment;
        std::vector<std::string> values;
    };

    auto candidates = std::vector<Candidate_s>{{0, 0, {}}};
    while (!candidates.empty())
    {
        auto candidate = std::move(candidates.back());
        candidates.pop_back();

        const auto& node = m_nodes[candidate.node];
        if (candidate.segment == url->segments.size())
        {
            if (node.methods.empty())
            {
                continue;
            }

            const auto route = std::ranges::find(node.methods, method, [](const auto& entry) -> const std::string&
            {
                return entry.route.method;
            });
            if (route == node.methods.end())
            {
                auto response = HttpResponses::Error(405, "method_not_allowed", "Unsupported method", {}, true);
                for (const auto& entry : node.methods)
                {
                    if (!response.allow.empty())
                    {
                        response.allow += ", ";
                    }

                    response.allow += entry.route.method;
                }

                return response;
            }

            if (route->route.requiresJson && !IsJson(contentType))
            {
                return HttpResponses::Error(415, "content_type", "application/json required", {}, true);
            }

            auto matched = HttpRouteMatch_s{.route = route->route, .request = {.queryParameters = std::move(url->query)}};
            for (std::size_t i = 0; i < candidate.values.size(); ++i)
            {
                matched.request.pathParameters.emplace(route->parameterNames[i], std::move(candidate.values[i]));
            }

            return matched;
        }

        const auto& segment = url->segments[candidate.segment];
        if (node.parameter && !segment.empty())
        {
            auto values = candidate.values;
            values.push_back(segment);
            candidates.push_back({*node.parameter, candidate.segment + 1, std::move(values)});
        }

        const auto literal = node.literals.find(segment);
        if (literal != node.literals.end())
        {
            candidates.push_back({literal->second, candidate.segment + 1, std::move(candidate.values)});
        }
    }

    return HttpResponses::Error(404, "not_found", "Unknown endpoint", {}, true);
}
