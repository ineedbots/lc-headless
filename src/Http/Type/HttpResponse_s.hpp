#pragma once

// Owned response data; the transport adds common headers and retains it through the write.
struct HttpResponse_s
{
    unsigned status;
    std::string body;
    bool close = false;
    std::string allow;
};
