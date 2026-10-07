#include "pch.hpp"
#include "Application.hpp"

#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"
#include "Io/WebSocketClient.hpp"
#include "Io/Packet.hpp"

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

    auto out = Packet(std::vector<u8>(5000));
    auto in = Packet(std::vector<u8>(5000));
    auto loginout = Packet(std::vector<u8>(5000));

    out.P1(14);
    out.P1(0); // loginServer, unused in 2004scape
    socket.Send({out.GetData().data(), out.GetPos()});

    // 8 throwaway bytes
    socket.WaitAvailable(8);
    socket.Read({in.GetData().data() + in.GetPos(), 8});
    m_logger->Info("garb {}", in.G8());

    socket.WaitAvailable(1);
    socket.Read({in.GetData().data() + in.GetPos(), 1});
    // 0 is creds, 1 is try again later, 2 is logged in
    m_logger->Info("res {}", in.G1());

    // assume 0
    socket.WaitAvailable(8);
    socket.Read({in.GetData().data() + in.GetPos(), 8});
    auto loginSeed = in.G8();
    m_logger->Info("loginSeed {}", loginSeed);

    std::random_device random;
    std::array<s32, 4> seed = { static_cast<s32>(random()), static_cast<s32>(random()), static_cast<s32>(loginSeed >> 32), static_cast<s32>(loginSeed) };

    out.SetPos(0);
    out.P1(10);
    for (auto s : seed) out.P4(s);
    out.P4(1337);
    out.PJStr(m_config->account.username);
    out.PJStr(m_config->account.password);
    out.RsaEnc(m_config->login.rsaModulus, m_config->login.rsaExponent);

    loginout.SetPos(0);
    loginout.P1(16);
    loginout.P1(0); // to be filled out below
    loginout.P1(0xFF);
    loginout.P2(m_config->login.revision);
    loginout.P1(m_config->login.lowMemory ? 1 : 0);
    for (auto c : m_config->login.crcs) loginout.P4(c);
    loginout.PData({out.GetData().data(), out.GetPos()});

    auto loginPacketSize = loginout.GetPos();
    loginout.SetPos(1); // here
    loginout.P1(static_cast<u8>(loginPacketSize - 1 - 1)); // opcode and self
    loginout.SetPos(loginPacketSize);

    // set up randoms
    out.SetRandom(std::make_unique<Isaac>(seed));

    for (auto& s : seed) s += 50;
    in.SetRandom(std::make_unique<Isaac>(seed));

    socket.Send({loginout.GetData().data(), loginout.GetPos()}); // send login

    in.SetPos(0);
    socket.WaitAvailable(1);
    socket.Read({in.GetData().data() + in.GetPos(), 1});
    m_logger->Info("res {}", in.G1());
    // 2 is login

    socket.WaitAvailable(1);
    socket.Read({in.GetData().data() + in.GetPos(), 1});
    m_logger->Info("staff {}", in.G1());

    socket.WaitAvailable(1);
    socket.Read({in.GetData().data() + in.GetPos(), 1});
    m_logger->Info("mouse tracking {}", in.G1());

    while (true)
    {
        std::this_thread::sleep_for(1s);
        // TODO: handle game packets

        // no timeout op
        out.SetPos(0);
        out.P1Enc(181);
        socket.Send({out.GetData().data(), out.GetPos()});
    }

    // iterface button op
    out.SetPos(0);
    out.P1Enc(86);
    out.P2(m_config->client.logoutComponent);
    socket.Send({out.GetData().data(), out.GetPos()});

    std::this_thread::sleep_for(1s);

    // doesn't flush out buffer
    socket.Stop();
    return EXIT_SUCCESS;
}
