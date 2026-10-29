#include "pch.hpp"
#include "EntryPoint.hpp"
#include "Application.hpp"
#include "CommandLine.hpp"

#include "../Console/Logger.hpp"

int ApplicationEntryPoint::Run(int argc, char** argv)
{
    const auto logger = std::make_shared<Logger>();
    Logger::SetDefault(logger);

    try
    {
        const auto args = std::span<char* const>{argv, static_cast<std::size_t>(argc)}.subspan(1);
        auto app = Application{CommandLine::Parse(args), logger};
        return app.Run();
    }
    catch (const std::exception& e)
    {
        logger->Error("Fatal error: {}", e.what());
        return EXIT_FAILURE;
    }
}
