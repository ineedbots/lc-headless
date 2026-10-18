#include "pch.hpp"
#include "TrustStore.hpp"

#include <boost/asio/ssl/context.hpp>
#include <boost/asio/ssl/verify_mode.hpp>
#include <boost/system/system_error.hpp>
#include <openssl/err.h>
#include <openssl/ssl.h>
#include <openssl/x509.h>

#ifdef _WIN32
#include <windows.h>
#include <wincrypt.h>
#endif

namespace
{
#ifdef _WIN32
    struct StoreCloser_s
    {
        void operator()(HCERTSTORE store) const noexcept
        {
            CertCloseStore(store, 0);
        }
    };

    struct X509Freer_s
    {
        void operator()(X509* certificate) const noexcept
        {
            X509_free(certificate);
        }
    };

    using StorePtr = std::unique_ptr<void, StoreCloser_s>;
    using X509Ptr = std::unique_ptr<X509, X509Freer_s>;

    // OpenSSL's default paths are empty on Windows, so its roots come from the Windows store. Windows fetches some
    // roots only when its own certificate code first needs them, so one no program here has used may be missing.
    std::size_t LoadWindowsRoots(boost::asio::ssl::context& context)
    {
        constexpr auto FLAGS = DWORD{CERT_SYSTEM_STORE_CURRENT_USER | CERT_STORE_READONLY_FLAG | CERT_STORE_OPEN_EXISTING_FLAG};
        const auto store = StorePtr{CertOpenStore(CERT_STORE_PROV_SYSTEM_W, 0, 0, FLAGS, L"ROOT")};
        if (!store)
        {
            throw std::runtime_error{"couldn't open the Windows root certificate store"};
        }

        auto* const trusted = SSL_CTX_get_cert_store(context.native_handle());
        auto count = std::size_t{0};
        for (auto certificate = CertEnumCertificatesInStore(store.get(), nullptr); certificate != nullptr; certificate = CertEnumCertificatesInStore(store.get(), certificate))
        {
            const auto* bytes = static_cast<const unsigned char*>(certificate->pbCertEncoded);
            const auto x509 = X509Ptr{d2i_X509(nullptr, &bytes, static_cast<long>(certificate->cbCertEncoded))};
            if (x509 && X509_STORE_add_cert(trusted, x509.get()) == 1)
            {
                ++count;
            }
        }

        // A certificate the store already had leaves an error on OpenSSL's queue, where a later TLS failure would find it.
        ERR_clear_error();

        if (count == 0)
        {
            throw std::runtime_error{"found no root certificates in the Windows store"};
        }

        return count;
    }
#endif
}

void TrustStore::Configure(boost::asio::ssl::context& context, const std::string& caFile)
{
    if (caFile == NONE)
    {
        context.set_verify_mode(boost::asio::ssl::verify_none);
        return;
    }

    context.set_verify_mode(boost::asio::ssl::verify_peer);
    if (caFile == SYSTEM)
    {
        static_cast<void>(LoadSystemRoots(context));
        return;
    }

    try
    {
        context.load_verify_file(caFile);
    }
    catch (const boost::system::system_error& e)
    {
        throw std::runtime_error{std::format("couldn't load the CA file {}: {}", caFile, e.code().message())};
    }
}

std::size_t TrustStore::LoadSystemRoots(boost::asio::ssl::context& context)
{
#ifdef _WIN32
    return LoadWindowsRoots(context);
#else
    context.set_default_verify_paths();
    return 0;
#endif
}
