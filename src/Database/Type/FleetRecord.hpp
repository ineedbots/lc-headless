#pragma once

#include "FleetAccountDataLog_s.hpp"
#include "FleetBankLog_s.hpp"
#include "FleetEquipmentLog_s.hpp"
#include "FleetExperienceLog_s.hpp"
#include "FleetInventoryLog_s.hpp"

using FleetRecord = std::variant<FleetAccountDataLog_s, FleetExperienceLog_s, FleetBankLog_s, FleetInventoryLog_s, FleetEquipmentLog_s>;
