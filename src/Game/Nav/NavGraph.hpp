#pragma once

#include "../Map/WalkMap.hpp"

struct NavPoint_s
{
    s32 x = 0;
    s32 z = 0;
    s32 level = 0;

    bool operator==(const NavPoint_s&) const = default;
};

struct NavRect_s
{
    s32 minX = 0;
    s32 maxX = 0;
    s32 minZ = 0;
    s32 maxZ = 0;
    // Every level when empty.
    std::optional<s32> level;

    [[nodiscard]] bool Contains(s32 x, s32 z, s32 tileLevel) const;
};

// What an account has, for an edge's requirements: rs2b0t's WorldState. Names are lower-case; a quest's
// status is "not_started", "started", "complete" or "unknown".
struct NavState_s
{
    bool members = false;
    std::unordered_map<std::string, s32> skills;
    std::unordered_map<std::string, s32> items;
    std::unordered_map<std::string, s32> worn;
    std::unordered_map<std::string, std::string> quests;
    s32 freeSlots = 0;
    bool entranaRestrictedGear = false;
    std::optional<bool> canSlashWeb;
};

// rs2b0t's TransportRequires: what an edge needs to be planned.
struct NavRequires_s
{
    struct Amount_s
    {
        std::string name;
        s32 count = 0;
    };

    struct Quest_s
    {
        std::string quest;
        std::string minStatus;
        std::string maxStatus;
    };

    bool members = false;
    std::optional<s32> freeSlots;
    std::vector<Amount_s> skills;
    std::vector<Amount_s> items;
    std::vector<Amount_s> worn;
    std::optional<Amount_s> currency;
    // A quest whose completion waives the items and currency, such as Prince Ali Rescue for the Al Kharid toll.
    std::string questWaivesItems;
    std::vector<Quest_s> quests;
    bool forbidEntranaRestricted = false;
    bool slashTool = false;

    // Whether anything here gates the edge.
    [[nodiscard]] bool IsGated() const;
    // nullopt when the state meets it, else why not. An unknown quest status fails closed.
    [[nodiscard]] std::optional<std::string> Check(const NavState_s& state) const;
};

// A move other than a step: a door, stairs, a ship and so on, with what the walker does to make it.
struct NavEdge_s
{
    std::string kind;
    NavPoint_s from;
    NavPoint_s to;
    s32 cost = 0;
    std::string locName;
    std::string action;
    s32 locX = 0;
    s32 locZ = 0;
    std::optional<s32> locId;
    std::optional<s32> openLocId;
    std::optional<s32> toLevel;
    // Where a long hop lands: ships, portals, shortcuts and the rest.
    std::optional<std::pair<s32, s32>> toTile;
    bool acceptAnyLanding = false;
    std::optional<NavRequires_s> requirement;
    std::string teleportId;
};

// A spell or jewellery teleport, which leaves from wherever you are.
struct NavTeleport_s
{
    std::string id;
    std::string family;
    std::string label;
    NavPoint_s to;
    s32 cost = 0;
    std::optional<NavRequires_s> requirement;
    // The deepest wilderness level it works from, or nullopt for anywhere.
    std::optional<s32> maxWildernessLevel;
    // Backpack item name parts that can make it, for jewellery.
    std::vector<std::string> itemNameMatch;
};

// rs2b0t's walker graph: its doors, stairs, ships and other transports, compiled to edges by
// tools/nav/export_rs2b0t.ts, and its teleports. Edges whose ends WalkMap can't stand on are left out, as
// rs2b0t's PathFinder leaves them out. Loaded once and shared read-only by every account.
class NavGraph
{
public:
    // Reads edges.json and teleports.json from the folder. Throws std::runtime_error naming the file that's
    // missing or malformed.
    NavGraph(const WalkMap& map, const std::filesystem::path& directory);
    // From JSON text, for tests.
    NavGraph(const WalkMap& map, std::string_view edgesJson, std::string_view teleportsJson);

    [[nodiscard]] static u32 GetNodeId(s32 x, s32 z, s32 level);
    [[nodiscard]] std::span<const NavEdge_s* const> GetEdgesFrom(u32 node) const;
    [[nodiscard]] std::span<const NavTeleport_s> GetTeleports() const;
    // Whether any edge spans more tiles than it costs, which makes the straight-line distance an
    // overestimate.
    [[nodiscard]] bool HasLongEdges() const;
    [[nodiscard]] std::size_t GetEdgeCount() const;
    [[nodiscard]] std::size_t GetDoorCount() const;

private:
    void Load(const WalkMap& map, std::string_view edgesJson, std::string_view teleportsJson);

    std::vector<NavEdge_s> m_edges;
    std::unordered_map<u32, std::vector<const NavEdge_s*>> m_from;
    std::vector<NavTeleport_s> m_teleports;
    bool m_longEdges = false;
    std::size_t m_doors = 0;
};

// The world's walking and the graph over it, built once at startup, with the data the stdlib's walker reads
// as JSON: crossings.json (tolls, ships and other special crossings), banks.json and danger_zones.json.
struct Navigation_s
{
    static constexpr std::array<std::string_view, 3> DATA_FILES = {"crossings", "banks", "danger_zones"};

    Navigation_s(const GameCache_s& cache, const std::filesystem::path& directory);
    // From the graph's JSON text, without the data files, for tests.
    Navigation_s(const GameCache_s& cache, std::string_view edgesJson, std::string_view teleportsJson);

    // A data file's JSON, by name without ".json", or nullopt for one it doesn't have.
    [[nodiscard]] std::optional<std::string_view> GetData(std::string_view name) const;

    WalkMap map;
    NavGraph graph;
    std::unordered_map<std::string, std::string> data;
};
