#pragma once

enum class Socks5Method_e : u8
{
    NoAuthentication = 0x00,
    UsernamePassword = 0x02,
};

enum class Socks5AddressType_e : u8
{
    Ipv4 = 0x01,
    DomainName = 0x03,
    Ipv6 = 0x04,
};

// The SOCKS5 messages (RFC 1928, and RFC 1929's username and password), built and parsed without any I/O. A parse
// failure throws std::runtime_error with a lowercase message that never names the credentials, because the caller
// puts it after "SOCKS5 proxy {host}:{port}: ".
class Socks5Handshake
{
public:
    static constexpr u8 VERSION = 0x05;
    static constexpr u8 PASSWORD_VERSION = 0x01;
    static constexpr u8 CONNECT_COMMAND = 0x01;
    static constexpr u8 NO_ACCEPTABLE_METHOD = 0xFF;
    static constexpr u8 SUCCEEDED = 0x00;
    static constexpr std::size_t METHOD_REPLY_SIZE = 2;
    static constexpr std::size_t PASSWORD_REPLY_SIZE = 2;
    static constexpr std::size_t CONNECT_REPLY_SIZE = 4;
    static constexpr std::size_t MAX_FIELD_LENGTH = 255;

    Socks5Handshake() = delete;

    // With a password it offers both methods, and accepts the proxy choosing none.
    [[nodiscard]] static std::vector<u8> BuildGreeting(bool withPassword);
    [[nodiscard]] static Socks5Method_e ParseMethodReply(std::span<const u8, METHOD_REPLY_SIZE> reply, bool withPassword);
    // Throws std::invalid_argument for an empty field or one longer than MAX_FIELD_LENGTH.
    [[nodiscard]] static std::vector<u8> BuildPasswordRequest(std::string_view username, std::string_view password);
    // Only the status is checked: some proxies answer with version 5 instead of 1.
    static void ParsePasswordReply(std::span<const u8, PASSWORD_REPLY_SIZE> reply);
    // An IPv4 literal goes as an address, and any other host as a name for the proxy to resolve.
    [[nodiscard]] static std::vector<u8> BuildConnectRequest(std::string_view host, u16 port);
    [[nodiscard]] static Socks5AddressType_e ParseConnectReply(std::span<const u8, CONNECT_REPLY_SIZE> reply);
    // The bound address and port after the reply. domainLength is the byte after the reply, read only for a name.
    [[nodiscard]] static std::size_t GetBoundAddressSize(Socks5AddressType_e type, u8 domainLength);
};
