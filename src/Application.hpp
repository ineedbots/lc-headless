#pragma once

#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"

class Application
{
public:
    explicit Application(const std::filesystem::path& configPath, std::shared_ptr<Logger> logger = Logger::GetDefault());

    [[nodiscard]] int Run();

private:
    std::shared_ptr<Logger> m_logger;
    std::shared_ptr<const Config_s> m_config;
};
