#include "pch.hpp"
#include "Socks5Handshake.hpp"

#include "../Utils/Endian.hpp"

namespace
{
    constexpr auto RESERVED = u8{0x00};
    constexpr auto IPV4_SIZE = std::size_t{4};
    constexpr auto IPV6_SIZE = std::size_t{16};
    constexpr auto PORT_SIZE = std::size_t{2};
    constexpr auto MAX_IPV4_PART = 255;

    // RFC 1928 §6, by reply code.
    constexpr auto REPLY_MEANINGS = std::array{
        "general SOCKS server failure"sv,
        "connection not allowed by ruleset"sv,
        "network unreachable"sv,
        "host unreachable"sv,
        "connection refused"sv,
        "TTL expired"sv,
        "command not supported"sv,
        "address type not supported"sv,
    };

    // Four decimal parts of 0 to 255, and nothing else.
    std::optional<std::array<u8, IPV4_SIZE>> ParseIpv4(std::string_view host)
    {
        auto address = std::array<u8, IPV4_SIZE>{};
        const auto* position = host.data();
        const auto* const end = host.data() + host.size();
        for (auto part = std::size_t{0}; part < IPV4_SIZE; ++part)
        {
            if (part > 0)
            {
                if (position == end || *position != '.')
                {
                    return std::nullopt;
                }

                ++position;
            }

            auto value = 0;
            const auto [next, error] = std::from_chars(position, end, value);
            if (error != std::errc{} || value < 0 || value > MAX_IPV4_PART)
            {
                return std::nullopt;
            }

            address[part] = static_cast<u8>(value);
            position = next;
        }

        if (position != end)
        {
            return std::nullopt;
        }

        return address;
    }

    void AppendField(std::vector<u8>& message, std::string_view field, std::string_view name)
    {
        if (field.empty() || field.size() > Socks5Handshake::MAX_FIELD_LENGTH)
        {
            throw std::invalid_argument{std::format("the {} must be 1 to {} bytes", name, Socks5Handshake::MAX_FIELD_LENGTH)};
        }

        message.push_back(static_cast<u8>(field.size()));
        message.insert(message.end(), field.begin(), field.end());
    }

    void AppendPort(std::vector<u8>& message, u16 port)
    {
        const auto stored = Endian::ToBig(port);
        const auto bytes = std::bit_cast<std::array<u8, PORT_SIZE>>(stored);
        message.insert(message.end(), bytes.begin(), bytes.end());
    }

    void CheckVersion(u8 version)
    {
        if (version != Socks5Handshake::VERSION)
        {
            throw std::runtime_error{std::format("not a SOCKS5 proxy (version {})", version)};
        }
    }
}

std::vector<u8> Socks5Handshake::BuildGreeting(bool withPassword)
{
    if (withPassword)
    {
        return {VERSION, 2, static_cast<u8>(Socks5Method_e::NoAuthentication), static_cast<u8>(Socks5Method_e::UsernamePassword)};
    }

    return {VERSION, 1, static_cast<u8>(Socks5Method_e::NoAuthentication)};
}

Socks5Method_e Socks5Handshake::ParseMethodReply(std::span<const u8, METHOD_REPLY_SIZE> reply, bool withPassword)
{
    CheckVersion(reply[0]);

    const auto method = reply[1];
    if (method == NO_ACCEPTABLE_METHOD)
    {
        if (withPassword)
        {
            throw std::runtime_error{"accepts none of the offered authentication methods"};
        }

        throw std::runtime_error{"accepts none of the offered authentication methods; it may need a username and password"};
    }

    if (method == static_cast<u8>(Socks5Method_e::NoAuthentication))
    {
        return Socks5Method_e::NoAuthentication;
    }

    if (method == static_cast<u8>(Socks5Method_e::UsernamePassword) && withPassword)
    {
        return Socks5Method_e::UsernamePassword;
    }

    throw std::runtime_error{"chose an authentication method that wasn't offered"};
}

std::vector<u8> Socks5Handshake::BuildPasswordRequest(std::string_view username, std::string_view password)
{
    auto request = std::vector<u8>{PASSWORD_VERSION};
    AppendField(request, username, "username");
    AppendField(request, password, "password");
    return request;
}

void Socks5Handshake::ParsePasswordReply(std::span<const u8, PASSWORD_REPLY_SIZE> reply)
{
    if (reply[1] != SUCCEEDED)
    {
        throw std::runtime_error{"rejected the username or password"};
    }
}

std::vector<u8> Socks5Handshake::BuildConnectRequest(std::string_view host, u16 port)
{
    auto request = std::vector<u8>{VERSION, CONNECT_COMMAND, RESERVED};
    if (const auto address = ParseIpv4(host))
    {
        request.push_back(static_cast<u8>(Socks5AddressType_e::Ipv4));
        request.insert(request.end(), address->begin(), address->end());
    }
    else
    {
        request.push_back(static_cast<u8>(Socks5AddressType_e::DomainName));
        AppendField(request, host, "host");
    }

    AppendPort(request, port);
    return request;
}

Socks5AddressType_e Socks5Handshake::ParseConnectReply(std::span<const u8, CONNECT_REPLY_SIZE> reply)
{
    CheckVersion(reply[0]);

    const auto code = reply[1];
    if (code != SUCCEEDED)
    {
        const auto meaning = code <= REPLY_MEANINGS.size() ? REPLY_MEANINGS[code - 1] : "unknown reply"sv;
        throw std::runtime_error{std::format("{} (reply {})", meaning, code)};
    }

    const auto type = reply[3];
    switch (static_cast<Socks5AddressType_e>(type))
    {
    case Socks5AddressType_e::Ipv4:
    case Socks5AddressType_e::DomainName:
    case Socks5AddressType_e::Ipv6:
        return static_cast<Socks5AddressType_e>(type);
    }

    throw std::runtime_error{std::format("replied with an unknown address type ({})", type)};
}

std::size_t Socks5Handshake::GetBoundAddressSize(Socks5AddressType_e type, u8 domainLength)
{
    switch (type)
    {
    case Socks5AddressType_e::Ipv4:
        return IPV4_SIZE + PORT_SIZE;
    case Socks5AddressType_e::Ipv6:
        return IPV6_SIZE + PORT_SIZE;
    case Socks5AddressType_e::DomainName:
        // The length byte itself has already been read.
        return std::size_t{domainLength} + PORT_SIZE;
    }

    assert(false && "Unknown Socks5AddressType_e");
    return 0;
}
