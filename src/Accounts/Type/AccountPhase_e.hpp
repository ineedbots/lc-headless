#pragma once

enum class AccountPhase_e : u8
{
    Pending,
    Active,
    RelogLogout,
    RelogWait,
    Stopping,
    Finished,
};
