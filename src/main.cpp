#include "pch.hpp"
#include "Application.hpp"

#include "Core/Logger.hpp"

// Usage: Application::USAGE
int main(int argc, char** argv)
{
    const auto logger = std::make_shared<Logger>();
    Logger::SetDefault(logger);
    try
    {
        const auto args = std::span<char* const>{argv, static_cast<std::size_t>(argc)}.subspan(1);
        auto app = Application{Application::ParseCommandLine(args), logger};
        return app.Run();
    }
    catch (const std::exception& e)
    {
        logger->Error("Fatal error: {}", e.what());
        return EXIT_FAILURE;
    }
}
