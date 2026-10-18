#pragma once

// A key and a self-signed certificate made at run time, for a TLS test server. The certificate names only
// DNS:localhost, so connecting to 127.0.0.1 with it tests the name check.
struct TestCertificate_s
{
    static constexpr auto HOST = "localhost";

    std::string certificatePem;
    std::string privateKeyPem;
};

class TestCertificate
{
public:
    TestCertificate() = delete;

    // Made once and shared, because generating an RSA key takes a while.
    [[nodiscard]] static const TestCertificate_s& Get();
};
