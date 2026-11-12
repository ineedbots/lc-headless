#pragma once

#include "Type/HttpEndpointRequest_s.hpp"

struct HttpUrl_s
{
    std::vector<std::string> segments;
    std::unordered_map<std::string, std::vector<std::string>> query;
};

class HttpUrl
{
public:
    HttpUrl() = delete;
    [[nodiscard]] static std::optional<HttpUrl_s> Parse(std::string_view target);
    [[nodiscard]] static std::vector<std::string_view> Segments(std::string_view path);
    [[nodiscard]] static bool IsUtf8(std::string_view text);

private:
    static std::optional<std::string> Decode(std::string_view value, bool query);
};
