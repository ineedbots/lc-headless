#include "pch.hpp"
#include "TestCertificate.hpp"

#include <openssl/bio.h>
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/rsa.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>

namespace
{
    constexpr auto KEY_BITS = 2048U;
    constexpr auto VALID_SECONDS = 24 * 60 * 60;

    struct KeyFreer_s
    {
        void operator()(EVP_PKEY* key) const noexcept
        {
            EVP_PKEY_free(key);
        }
    };

    struct X509Freer_s
    {
        void operator()(X509* certificate) const noexcept
        {
            X509_free(certificate);
        }
    };

    struct ExtensionFreer_s
    {
        void operator()(X509_EXTENSION* extension) const noexcept
        {
            X509_EXTENSION_free(extension);
        }
    };

    struct BioFreer_s
    {
        void operator()(BIO* bio) const noexcept
        {
            BIO_free(bio);
        }
    };

    using KeyPtr = std::unique_ptr<EVP_PKEY, KeyFreer_s>;
    using X509Ptr = std::unique_ptr<X509, X509Freer_s>;
    using ExtensionPtr = std::unique_ptr<X509_EXTENSION, ExtensionFreer_s>;
    using BioPtr = std::unique_ptr<BIO, BioFreer_s>;

    void Check(bool succeeded, std::string_view step)
    {
        if (!succeeded)
        {
            throw std::runtime_error{std::format("Making the test certificate failed: {}", step)};
        }
    }

    void AddExtension(X509* certificate, int nid, const char* value)
    {
        auto context = X509V3_CTX{};
        X509V3_set_ctx_nodb(&context);
        X509V3_set_ctx(&context, certificate, certificate, nullptr, nullptr, 0);

        const auto extension = ExtensionPtr{X509V3_EXT_conf_nid(nullptr, &context, nid, value)};
        Check(extension != nullptr, value);
        Check(X509_add_ext(certificate, extension.get(), -1) == 1, value);
    }

    template <typename TWrite>
    std::string ToPem(TWrite write)
    {
        const auto bio = BioPtr{BIO_new(BIO_s_mem())};
        Check(bio != nullptr && write(bio.get()) == 1, "writing PEM");

        char* data = nullptr;
        const auto size = BIO_get_mem_data(bio.get(), &data);
        return std::string{data, static_cast<std::size_t>(size)};
    }

    TestCertificate_s Make()
    {
        const auto key = KeyPtr{EVP_RSA_gen(KEY_BITS)};
        Check(key != nullptr, "the key");

        const auto certificate = X509Ptr{X509_new()};
        Check(certificate != nullptr, "the certificate");
        Check(X509_set_version(certificate.get(), X509_VERSION_3) == 1, "the version");
        Check(ASN1_INTEGER_set(X509_get_serialNumber(certificate.get()), 1) == 1, "the serial number");
        X509_gmtime_adj(X509_getm_notBefore(certificate.get()), 0);
        X509_gmtime_adj(X509_getm_notAfter(certificate.get()), VALID_SECONDS);
        Check(X509_set_pubkey(certificate.get(), key.get()) == 1, "the public key");

        auto* const name = X509_get_subject_name(certificate.get());
        const auto* const host = reinterpret_cast<const unsigned char*>(TestCertificate_s::HOST);
        Check(X509_NAME_add_entry_by_txt(name, "CN", MBSTRING_ASC, host, -1, -1, 0) == 1, "the name");
        Check(X509_set_issuer_name(certificate.get(), name) == 1, "the issuer");

        // A trust anchor and a server certificate at once, as `openssl req -x509` makes them.
        AddExtension(certificate.get(), NID_basic_constraints, "critical,CA:TRUE");
        AddExtension(certificate.get(), NID_subject_alt_name, "DNS:localhost");
        Check(X509_sign(certificate.get(), key.get(), EVP_sha256()) > 0, "signing");

        return {
            .certificatePem = ToPem([&](BIO* bio)
            {
                return PEM_write_bio_X509(bio, certificate.get());
            }),
            .privateKeyPem = ToPem([&](BIO* bio)
            {
                return PEM_write_bio_PrivateKey(bio, key.get(), nullptr, nullptr, 0, nullptr, nullptr);
            }),
        };
    }
}

const TestCertificate_s& TestCertificate::Get()
{
    static const auto certificate = Make();
    return certificate;
}
