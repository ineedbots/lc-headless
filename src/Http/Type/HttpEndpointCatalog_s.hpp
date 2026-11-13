#pragma once

#include "HttpRoute_s.hpp"
#include "HttpResponse_s.hpp"
#include "../../Application/Type/CompletedApplicationRequest_s.hpp"

template <typename... Endpoints>
struct HttpEndpointCatalog_s
{
    static std::vector<HttpRoute_s> Routes()
    {
        return {Route<Endpoints>()...};
    }

    // Compatibility for callers with a result but no matched route. The first
    // registered serializer for a result type supplies its default encoding.
    template <typename T>
    static HttpResponse_s Respond(const CompletedApplicationRequest_s& result, const T& payload)
    {
        static_assert((Handles<Endpoints, T>() || ...), "Application result needs an HTTP serializer");

        auto response = std::optional<HttpResponse_s>{};
        ([&]
        {
            if constexpr (Handles<Endpoints, T>())
            {
                if (!response)
                {
                    response = Endpoints::Respond(result, payload);
                }
            }
        }(), ...);

        return std::move(*response);
    }

private:
    template <typename Endpoint, typename T>
    static constexpr bool Handles()
    {
        if constexpr (requires { typename Endpoint::Payload; })
        {
            return std::is_same_v<T, typename Endpoint::Payload>;
        }

        return false;
    }

    template <typename Endpoint>
    static HttpRoute_s Route()
    {
        auto route = Endpoint::Route();
        if constexpr (requires { typename Endpoint::Payload; })
        {
            route.respond = [](const CompletedApplicationRequest_s& result) -> std::optional<HttpResponse_s>
            {
                if (const auto payload = std::get_if<typename Endpoint::Payload>(&result.payload))
                {
                    return Endpoint::Respond(result, *payload);
                }

                return {};
            };
        }

        return route;
    }
};
