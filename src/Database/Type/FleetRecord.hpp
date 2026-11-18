#pragma once

#include "../../Accounts/Reporting/Type/FleetAccountDataLog_s.hpp"
#include "../../Accounts/Reporting/Type/FleetBankLog_s.hpp"
#include "../../Accounts/Reporting/Type/FleetEquipmentLog_s.hpp"
#include "../../Accounts/Reporting/Type/FleetExperienceLog_s.hpp"
#include "../../Accounts/Reporting/Type/FleetInventoryLog_s.hpp"

using FleetRecord = std::variant<FleetAccountDataLog_s, FleetExperienceLog_s, FleetBankLog_s, FleetInventoryLog_s, FleetEquipmentLog_s>;
