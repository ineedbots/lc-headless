#include "pch.hpp"
#include "Application.hpp"

#include "Core/ConfigFile.hpp"
#include "Core/Logger.hpp"
#include "Io/Isaac.hpp"
#include "Io/Packet.hpp"
#include "Io/WebSocketClient.hpp"

namespace
{
    std::atomic<bool> keepRunning{true};

    void SignalHandler(int signalNum)
    {
        if (signalNum == SIGINT)
        {
            keepRunning = false;
        }
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

    const auto& server = m_config->server;
    auto socket = WebSocketClient{m_logger};
    socket.Connect({.url = server.url, .origin = server.origin, .tlsCaFile = server.tlsCaFile});
    socket.WaitOpen();

    const auto receive = [&socket](std::size_t count)
    {
        static auto inBuffer = std::array<u8, 1 << 16>{};
        assert(count < inBuffer.size() && "count exceeds inBuffer size");

        const auto bytes = std::span{inBuffer}.first(count);
        socket.WaitAvailable(count);
        socket.Read(bytes);
        return Packet{bytes};
    };

    auto out = Packet{};
    out.P1(14);
    out.P1(0); // loginServer, unused in 2004scape
    socket.Send(out.GetData());

    // 8 throwaway bytes
    m_logger->Info("garb {}", receive(8).G8());

    // 0 is creds, 1 is try again later, 2 is logged in
    m_logger->Info("res {}", receive(1).G1());

    // assume 0
    auto loginSeed = receive(8).G8();
    m_logger->Info("loginSeed {}", loginSeed);

    std::random_device random;
    std::array<s32, 4> seed = { static_cast<s32>(random()), static_cast<s32>(random()), static_cast<s32>(loginSeed >> 32), static_cast<s32>(loginSeed) };

    out = Packet{};
    out.P1(10);
    for (auto s : seed) out.P4(s);
    out.P4(1337);
    out.PJStr(m_config->account.username);
    out.PJStr(m_config->account.password);
    out.RsaEnc(m_config->login.rsaModulus, m_config->login.rsaExponent);

    auto loginout = Packet{};
    loginout.SetPos(0);
    loginout.P1(16);
    loginout.P1(0); // to be filled out below
    loginout.P1(0xFF);
    loginout.P2(m_config->login.revision);
    loginout.P1(m_config->login.lowMemory ? 1 : 0);
    for (auto c : m_config->login.crcs) loginout.P4(c);
    loginout.PData(out.GetData());

    auto loginPacketSize = loginout.GetPos();
    loginout.SetPos(1); // here
    loginout.P1(static_cast<u8>(loginPacketSize - 1 - 1)); // opcode and self
    loginout.SetPos(loginPacketSize);

    // set up randoms
    auto randomOut = Isaac{seed};

    for (auto& s : seed) s += 50;
    auto randomIn = Isaac{seed};

    socket.Send(loginout.GetData()); // send login

    m_logger->Info("res {}", receive(1).G1());
    // 2 is login

    m_logger->Info("staff {}", receive(1).G1());

    m_logger->Info("mouse tracking {}", receive(1).G1());

    enum ClientProt
    {
        NO_TIMEOUT = 181,
        IDLE_TIMER = 145,
        EVENT_MOUSE_CLICK = 224,
        EVENT_MOUSE_MOVE = 229,
        EVENT_APPLET_FOCUS = 149,
        EVENT_CAMERA_POSITION = 193,
        ANTICHEAT_OPLOGIC1 = 195,
        ANTICHEAT_OPLOGIC2 = 81,
        ANTICHEAT_OPLOGIC3 = 122,
        ANTICHEAT_OPLOGIC4 = 49,
        ANTICHEAT_OPLOGIC5 = 46,
        ANTICHEAT_OPLOGIC6 = 73,
        ANTICHEAT_OPLOGIC7 = 133,
        ANTICHEAT_OPLOGIC8 = 168,
        ANTICHEAT_OPLOGIC9 = 88,
        ANTICHEAT_CYCLELOGIC1 = 130,
        ANTICHEAT_CYCLELOGIC2 = 154,
        ANTICHEAT_CYCLELOGIC3 = 125,
        ANTICHEAT_CYCLELOGIC4 = 137,
        ANTICHEAT_CYCLELOGIC5 = 85,
        ANTICHEAT_CYCLELOGIC6 = 255,
        ANTICHEAT_CYCLELOGIC7 = 232,
        OPOBJ1 = 97,
        OPOBJ2 = 4,
        OPOBJ3 = 110,
        OPOBJ4 = 147,
        OPOBJ5 = 22,
        OPOBJT = 241,
        OPOBJU = 55,
        OPNPC1 = 252,
        OPNPC2 = 21,
        OPNPC3 = 178,
        OPNPC4 = 30,
        OPNPC5 = 247,
        OPNPCT = 108,
        OPNPCU = 160,
        OPLOC1 = 10,
        OPLOC2 = 45,
        OPLOC3 = 196,
        OPLOC4 = 53,
        OPLOC5 = 126,
        OPLOCT = 218,
        OPLOCU = 184,
        OPPLAYER1 = 220,
        OPPLAYER2 = 51,
        OPPLAYER3 = 13,
        OPPLAYER4 = 189,
        OPPLAYER5 = 69,
        OPPLAYERT = 138,
        OPPLAYERU = 16,
        OPHELD1 = 76,
        OPHELD2 = 177,
        OPHELD3 = 40,
        OPHELD4 = 191,
        OPHELD5 = 79,
        OPHELDT = 112,
        OPHELDU = 200,
        INV_BUTTON1 = 44,
        INV_BUTTON2 = 111,
        INV_BUTTON3 = 124,
        INV_BUTTON4 = 248,
        INV_BUTTON5 = 227,
        IF_BUTTON = 86,
        RESUME_PAUSEBUTTON = 166,
        CLOSE_MODAL = 93,
        RESUME_P_COUNTDIALOG = 180,
        TUT_CLICKSIDE = 146,
        MAP_BUILD_COMPLETE = 214,
        MOVE_OPCLICK = 67,
        SEND_SNAPSHOT = 94,
        MOVE_MINIMAPCLICK = 236,
        INV_BUTTOND = 253,
        IGNORELIST_DEL = 251,
        IGNORELIST_ADD = 192,
        IDK_SAVEDESIGN = 27,
        CHAT_SETMODE = 161,
        MESSAGE_PRIVATE = 107,
        FRIENDLIST_DEL = 203,
        FRIENDLIST_ADD = 235,
        CLIENT_CHEAT = 34,
        MESSAGE_PUBLIC = 156,
        MOVE_GAMECLICK = 234,
    };

    while (keepRunning.load())
    {
        std::this_thread::sleep_for(1s);

        out = Packet();
        out.P1Enc(randomOut, NO_TIMEOUT);
        socket.Send(out.GetData());

        while (socket.Pump() == WebSocketState_e::Open && socket.Available() > 0)
        {
            auto op = receive(1).G1Enc(randomIn);

            static const auto ServerOpNames = std::to_array<std::pair<u32, const char*>>({
                { 81, "IF_OPENCHAT" },
                { 55, "IF_OPENMAIN_SIDE" },
                { 23, "IF_CLOSE" },
                { 63, "IF_SETICON" },
                { 189, "IF_SHOWICON" },
                { 119, "IF_OPENMAIN" },
                { 252, "IF_OPENSIDE" },
                { 127, "IF_OPENOVERLAY" },
                { 160, "IF_SETCOLOUR" },
                { 138, "IF_SETHIDE" },
                { 18, "IF_SETOBJECT" },
                { 222, "IF_SETMODEL" },
                { 211, "IF_SETANIM" },
                { 30, "IF_SETPLAYERHEAD" },
                { 59, "IF_SETTEXT" },
                { 244, "IF_SETNPCHEAD" },
                { 79, "IF_SETPOSITION" },
                { 184, "IF_SETSCROLLPOS" },
                { 181, "TUT_FLASH" },
                { 12, "TUT_OPEN" },
                { 28, "UPDATE_INV_STOP_TRANSMIT" },
                { 107, "UPDATE_INV_FULL" },
                { 76, "UPDATE_INV_PARTIAL" },
                { 82, "CAM_LOOKAT" },
                { 208, "CAM_SHAKE" },
                { 73, "CAM_MOVETO" },
                { 133, "CAM_RESET" },
                { 65, "NPC_INFO" },
                { 188, "PLAYER_INFO" },
                { 235, "FRIENDLIST_LOADED" },
                { 196, "MESSAGE_GAME" },
                { 47, "UPDATE_IGNORELIST" },
                { 13, "CHAT_FILTER_SETTINGS" },
                { 243, "MESSAGE_PRIVATE" },
                { 168, "UPDATE_FRIENDLIST" },
                { 164, "UNSET_MAP_FLAG" },
                { 46, "UPDATE_RUNWEIGHT" },
                { 115, "HINT_ARROW" },
                { 204, "UPDATE_REBOOT_TIMER" },
                { 154, "UPDATE_STAT" },
                { 195, "UPDATE_RUNENERGY" },
                { 201, "RESET_ANIMS" },
                { 120, "UPDATE_PID" },
                { 253, "LAST_LOGIN_INFO" },
                { 121, "LOGOUT" },
                { 35, "P_COUNTDIALOG" },
                { 247, "SET_MULTIWAY" },
                { 21, "SET_PLAYER_OP" },
                { 136, "MINIMAP_TOGGLE" },
                { 219, "REBUILD_NORMAL" },
                { 75, "VARP_SMALL" },
                { 97, "VARP_LARGE" },
                { 172, "VARP_SYNC" },
                { 177, "SYNTH_SOUND" },
                { 187, "MIDI_SONG" },
                { 29, "MIDI_JINGLE" },
                { 155, "UPDATE_ZONE_PARTIAL_FOLLOWS" },
                { 144, "UPDATE_ZONE_FULL_FOLLOWS" },
                { 112, "UPDATE_ZONE_PARTIAL_ENCLOSED" },
                { 83, "P_LOCMERGE" },
                { 106, "LOC_ANIM" },
                { 71, "OBJ_DEL" },
                { 176, "OBJ_REVEAL" },
                { 90, "LOC_ADD_CHANGE" },
                { 87, "MAP_PROJANIM" },
                { 194, "LOC_DEL" },
                { 117, "OBJ_COUNT" },
                { 233, "MAP_ANIM" },
                { 60, "OBJ_ADD" },
            });
            auto itr = std::ranges::find_if(ServerOpNames, [op](const auto& a)
            {
                return a.first == op;
            });
            assert(itr != ServerOpNames.end() && "invalid op");
            m_logger->Info("op {}", itr->second);

            static const auto ServerProtSizes = std::to_array<s32>({
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                0, 0, 2, 3, 0, 0, 0, 0, 6, 0,
                0, -1, 0, 0, 0, 0, 0, 0, 2, 4,
                2, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                0, 0, 0, 0, 0, 0, 2, -2, 0, 0,
                0, 0, 0, 0, 0, 4, 0, 0, 0, -2,
                5, 0, 0, 3, 0, -2, 0, 0, 0, 0,
                0, 3, 0, 6, 0, 3, -2, 0, 0, 6,
                0, 2, 6, 14, 0, 0, 0, 15, 0, 0,
                4, 0, 0, 0, 0, 0, 0, 6, 0, 0,
                0, 0, 0, 0, 0, 0, 4, -2, 0, 0,
                0, 0, -2, 0, 0, 6, 0, 7, 0, 2,
                3, 0, 0, 0, 0, 0, 0, 2, 0, 0,
                0, 0, 0, 0, 0, 0, 1, 0, 3, 0,
                0, 0, 0, 0, 2, 0, 0, 0, 0, 0,
                0, 0, 0, 0, 6, 2, 0, 0, 0, 0,
                4, 0, 0, 0, 0, 0, 0, 0, 9, 0,
                0, 0, 0, 0, 0, 0, 7, 5, 0, 0,
                0, 1, 0, 0, 4, 0, 0, 2, -2, 1,
                0, 0, 0, 0, 2, 1, -1, 0, 0, 0,
                0, 0, 0, 0, 2, 0, 0, 0, 4, 0,
                0, 4, 0, 0, 0, 0, 0, 0, 0, 4,
                0, 0, 4, 0, 0, 0, 0, 0, 0, 0,
                0, 0, 0, 6, 0, 1, 0, 0, 0, 0,
                0, 0, 0, -1, 4, 0, 0, 1, 0, 0,
                0, 0, 2, 10, 0, 0,
            });

            auto opsize = ServerProtSizes.at(op);
            if (opsize == -1)
            {
                opsize = receive(1).G1();
            }

            if (opsize == -2)
            {
                opsize = receive(2).G2();
            }

            auto oppayload = receive(opsize);
            m_logger->Info("oppayload {}", oppayload.GetAvailable());
        }
    }

    out = Packet();
    out.P1Enc(randomOut, IF_BUTTON);
    out.P2(m_config->client.logoutComponent);
    socket.Send(out.GetData());

    std::this_thread::sleep_for(1s); // so it flushes the send buffer
    socket.Stop();
    return EXIT_SUCCESS;
}
