#include "pch.hpp"
#include "ScriptCoverage.hpp"

#include <catch2/reporters/catch_reporter_event_listener.hpp>
#include <catch2/reporters/catch_reporter_registrars.hpp>

#ifdef _WIN32
#include <process.h>
#else
#include <unistd.h>
#endif

namespace
{
    class ScriptCoverageListener final : public Catch::EventListenerBase
    {
    public:
        using EventListenerBase::EventListenerBase;

        void testRunStarting(const Catch::TestRunInfo&) override
        {
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable : 4996)
#endif
            const auto* directory = std::getenv("RS2004_SCRIPT_COVERAGE_DIR");
#ifdef _MSC_VER
#pragma warning(pop)
#endif
            if (directory != nullptr && *directory != '\0')
            {
                m_directory = directory;
                m_coverage = std::make_unique<ScriptCoverage>(Stdlib::GetFiles());
            }
        }

        void testRunEnded(const Catch::TestRunStats&) override
        {
            if (!m_coverage)
            {
                return;
            }
            try
            {
                m_coverage->Stop();
#ifdef _WIN32
                const auto pid = _getpid();
#else
                const auto pid = getpid();
#endif
                const auto stamp = std::chrono::steady_clock::now().time_since_epoch().count();
                m_coverage->Write(m_directory / std::format("{}-{}.json", pid, stamp));
                if (m_coverage->Failed())
                {
                    throw std::runtime_error{"A script coverage trace could not be recorded"};
                }
            }
            catch (const std::exception& error)
            {
                std::fprintf(stderr, "Script coverage failed: %s\n", error.what());
                std::exit(EXIT_FAILURE);
            }
        }

    private:
        std::filesystem::path m_directory;
        std::unique_ptr<ScriptCoverage> m_coverage;
    };
}

CATCH_REGISTER_LISTENER(ScriptCoverageListener)
