#include "pch.hpp"
#include "Application.hpp"

#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"

// Usage: rs2004-headless [client.jsonc] [--account accounts/name.jsonc]
int main(int argc, char** argv)
{
    const auto logger = std::make_shared<Logger>();
    Logger::SetDefault(logger);
    try
    {
        auto configPath = std::filesystem::path{ConfigFile::DEFAULT_PATH};
        auto accountPath = std::optional<std::filesystem::path>{};
        const auto args = std::span{argv, static_cast<std::size_t>(argc)}.subspan(1);
        for (std::size_t i = 0; i < args.size(); ++i)
        {
            if (args[i] != Application::ACCOUNT_OPTION)
            {
                configPath = args[i];
                continue;
            }

            if (i + 1 >= args.size())
            {
                throw std::invalid_argument{std::format("{} needs an account file path", Application::ACCOUNT_OPTION)};
            }

            accountPath = args[++i];
        }

        auto app = Application{configPath, accountPath, logger};
        return app.Run();
    }
    catch (const std::exception& e)
    {
        logger->Error("Fatal error: {}", e.what());
        return EXIT_FAILURE;
    }
}
