#include "pch.hpp"
#include "Application.hpp"

#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"
#include "Game/GameClient.hpp"
#include "Game/State/GameState_s.hpp"
#include "Game/State/Npc_s.hpp"
#include "Game/Tile_s.hpp"

namespace
{
    using Clock = std::chrono::steady_clock;

    constexpr auto PUMP_WAIT = 100ms;
    constexpr auto SUMMARY_INTERVAL = 10s;
    constexpr auto LOGOUT_TIMEOUT = 10s;
    constexpr auto HITPOINTS_STAT = std::size_t{3};
    constexpr auto NEAREST_NPC_COUNT = std::size_t{5};

    std::atomic<bool> keepRunning{true};

    void SignalHandler(int signalNum)
    {
        if (signalNum == SIGINT)
        {
            keepRunning = false;
        }
    }

    std::string DescribeNearestNpcs(const GameState_s& state)
    {
        auto npcs = std::vector<const Npc_s*>{};
        for (const auto& npc : state.npcs)
        {
            npcs.push_back(&npc);
        }

        const auto& here = state.localPlayer.tile;
        std::ranges::sort(npcs, {}, [&here](const Npc_s* npc)
        {
            return npc->tile.GetDistance(here);
        });

        auto text = std::string{};
        for (const auto* const npc : npcs | std::views::take(NEAREST_NPC_COUNT))
        {
            if (!text.empty())
            {
                text += ", ";
            }

            std::format_to(std::back_inserter(text), "#{} type {} at {} tiles", npc->index, npc->type, npc->tile.GetDistance(here));
        }

        return text.empty() ? "none" : text;
    }

    void LogSummary(Logger& logger, const GameState_s& state)
    {
        const auto& tile = state.localPlayer.tile;
        const auto& hitpoints = state.stats[HITPOINTS_STAT];
        logger.Info("Tick {}: player {} at ({}, {}, {}), hitpoints {}/{}, run energy {}%, weight {} kg",
                    state.tick, state.pid, tile.x, tile.z, tile.level, hitpoints.level, hitpoints.baseLevel, state.runEnergy, state.runWeight);
        logger.Info("In view: {} players, {} NPCs, {} ground items, {} changed locs; {} inventories, {} varps",
                    state.players.size(), state.npcs.size(), state.groundItems.size(), state.locChanges.size(), state.inventories.size(), state.varps.size());
        logger.Info("Nearest NPCs: {}", DescribeNearestNpcs(state));

        const auto& interfaces = state.interfaces;
        logger.Info("Interfaces: main {}, side {}, chat {}, overlay {}", interfaces.mainModal, interfaces.sideModal, interfaces.chatModal, interfaces.overlay);
    }
}

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
    std::signal(SIGINT, SignalHandler);

    auto client = GameClient{m_config, m_logger};
    client.Login();

    auto nextSummary = Clock::now() + SUMMARY_INTERVAL;
    while (keepRunning.load() && client.IsInGame())
    {
        client.Pump(PUMP_WAIT);

        const auto now = Clock::now();
        if (now < nextSummary || !client.IsInGame())
        {
            continue;
        }

        LogSummary(*m_logger, client.GetState());
        nextSummary = now + SUMMARY_INTERVAL;
    }

    client.Logout(LOGOUT_TIMEOUT);
    return client.GetStatus() == ClientStatus_e::LoggedOut ? EXIT_SUCCESS : EXIT_FAILURE;
}
