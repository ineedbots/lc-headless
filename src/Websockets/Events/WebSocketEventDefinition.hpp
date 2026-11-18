#pragma once

#include "Type/EventScope_e.hpp"

#include <nlohmann/json.hpp>

template <typename T>
concept WebSocketEventDefinition = requires(const typename T::Payload& payload) {
    { T::NAME } -> std::convertible_to<std::string_view>;
    { T::SCOPE } -> std::same_as<const EventScope_e&>;
    typename std::bool_constant<T::RETAINS_LATEST>;
    typename std::integral_constant<std::size_t, T::MAX_ENVELOPE_BYTES>;
    { T::ValidateAndMeasureOwnedBytes(payload) } -> std::same_as<std::optional<std::size_t>>;
    { T::Serialize(payload) } -> std::same_as<nlohmann::json>;
};
