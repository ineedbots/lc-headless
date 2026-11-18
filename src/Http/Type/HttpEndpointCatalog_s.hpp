#pragma once

#include "Http/HttpEndpointConcepts.hpp"
#include "HttpEndpointKind_e.hpp"
#include "HttpRoute_s.hpp"
#include "HttpResponse_s.hpp"
#include "Application/Requests/Type/CompletedApplicationRequest_s.hpp"

template <typename... Endpoints>
struct HttpEndpointCatalog_s
{
    static_assert(((HttpRestEndpoint<Endpoints> || HttpUpgradeEndpoint<Endpoints>) && ...), "HTTP entries must satisfy HttpRestEndpoint or HttpUpgradeEndpoint");

    static constexpr bool HasValidDefaults()
    {
        return (HasDefault<Endpoints>() && ...);
    }

    static std::vector<HttpRoute_s> Routes()
    {
        static_assert(HasValidDefaults(), "Each HTTP response type needs exactly one IS_DEFAULT_RESPONSE endpoint");
        return {Route<Endpoints>()...};
    }

    template <typename T>
    static HttpResponse_s Respond(const CompletedApplicationRequest_s& result, const T& payload)
    {
        static_assert(DefaultCount<T>() == 1, "HTTP fallback responses need exactly one IS_DEFAULT_RESPONSE endpoint for their response type");

        auto response = std::optional<HttpResponse_s>{};
        ([&]
        {
            if constexpr (IsDefaultFor<Endpoints, T>())
            {
                response = Endpoints::Respond(result, payload);
            }
        }(), ...);

        return std::move(*response);
    }

private:
    template <typename Endpoint, typename T>
    static constexpr bool IsDefaultFor()
    {
        if constexpr (HttpRestEndpoint<Endpoint>)
        {
            return std::is_same_v<T, typename Endpoint::ResponsePayload> && Endpoint::IS_DEFAULT_RESPONSE;
        }

        return false;
    }

    template <typename T>
    static constexpr std::size_t DefaultCount()
    {
        return (std::size_t{0} + ... + std::size_t{IsDefaultFor<Endpoints, T>()});
    }

    template <typename Endpoint>
    static constexpr bool HasDefault()
    {
        if constexpr (HttpRestEndpoint<Endpoint>)
        {
            return DefaultCount<typename Endpoint::ResponsePayload>() == 1;
        }

        return true;
    }

    template <typename Endpoint>
    static HttpRoute_s Route()
    {
        auto route = Endpoint::Route();
        if (route.webSocket != (Endpoint::KIND == HttpEndpointKind_e::WebSocketUpgrade))
        {
            throw std::invalid_argument{"HTTP endpoint kind does not match its route transport"};
        }

        if constexpr (HttpRestEndpoint<Endpoint>)
        {
            route.respond = [](const CompletedApplicationRequest_s& result) -> std::optional<HttpResponse_s>
            {
                if (const auto payload = std::get_if<typename Endpoint::ResponsePayload>(&result.payload))
                {
                    return Endpoint::Respond(result, *payload);
                }

                return {};
            };
        }

        return route;
    }
};
