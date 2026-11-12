#pragma once

struct HttpEndpointRequest_s
{
    std::unordered_map<std::string, std::string> pathParameters;
    std::unordered_map<std::string, std::vector<std::string>> queryParameters;
    std::string body;
};
