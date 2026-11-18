#pragma once

#include "Type/HttpEndpointKind_e.hpp"
#include "Type/HttpRoute_s.hpp"
#include "Type/HttpResponse_s.hpp"
#include "Application/Type/CompletedApplicationRequest_s.hpp"

template <typename T>
concept HttpRestEndpoint = requires(const CompletedApplicationRequest_s& result, const typename T::ResponsePayload& payload) {
    requires T::KIND == HttpEndpointKind_e::Rest;
    typename std::bool_constant<T::IS_DEFAULT_RESPONSE>;
    { T::Route() } -> std::same_as<HttpRoute_s>;
    { T::Respond(result, payload) } -> std::same_as<HttpResponse_s>;
};

template <typename T>
concept HttpUpgradeEndpoint = requires {
    requires T::KIND == HttpEndpointKind_e::WebSocketUpgrade;
    { T::Route() } -> std::same_as<HttpRoute_s>;
} && (!requires { typename T::ResponsePayload; });
