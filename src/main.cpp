#include "pch.hpp"
#include "Application.hpp"

#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"

int main(int argc, char** argv)
{
    const auto logger = std::make_shared<Logger>();
    Logger::SetDefault(logger);
    try
    {
        const auto args = std::span{argv, static_cast<std::size_t>(argc)};
        auto app = Application{args.size() > 1 ? args[1] : ConfigFile::DEFAULT_PATH, logger};
        return app.Run();
    }
    catch (const std::exception& e)
    {
        logger->Error("Fatal error: {}", e.what());
        return EXIT_FAILURE;
    }
}
