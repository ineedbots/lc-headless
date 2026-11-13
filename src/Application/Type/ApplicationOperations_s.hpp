#pragma once

#include "OperationCatalog_s.hpp"
#include "../Operations/ConsoleCommandOperation.hpp"
#include "../Operations/ApplicationStatusOperation.hpp"

using ApplicationOperations_s = OperationCatalog_s<ConsoleCommandOperation, ApplicationStatusOperation>;
using ApplicationRequestPayload = ApplicationOperations_s::Payload;
