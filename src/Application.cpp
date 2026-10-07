#include "pch.hpp"
#include "Application.hpp"

#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"
#include "Io/WebSocketClient.hpp"

Application::Application(const std::filesystem::path& configPath, std::shared_ptr<Logger> logger)
    : m_logger{std::move(logger)}
{
    assert(m_logger && "Application needs a logger");
    m_config = std::make_shared<const Config_s>(ConfigFile::Load(configPath, *m_logger));
    m_logger->SetLevel(m_config->client.logLevel);
    m_logger->Info("Config loaded from {}", configPath.string());
}

int Application::Run()
{
    const auto& server = m_config->server;
    auto socket = WebSocketClient{m_logger};
    socket.Connect({.url = server.url, .origin = server.origin, .tlsCaFile = server.tlsCaFile});
    socket.WaitOpen();

    // TODO: log in and run the game loop once the protocol is ported
    socket.Stop();
    return EXIT_SUCCESS;
}
