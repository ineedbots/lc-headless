# Registering operator HTTP endpoints and events

Operator APIs use explicit compile-time catalogs. Registration has no global
constructors, linker retention requirements, or ordering dependency. Adding files
under `src/` requires no CMake source-list edits.

## HTTP endpoints

`src/Http/HttpEndpoints.hpp` is the endpoint list. Each REST endpoint provides:

- `Payload`: the owned **result** type it serializes.
- `Route()`: method, path template, content-type policy and request decoder.
- `Respond(const CompletedApplicationRequest_s&, const Payload&)`: response encoding.

Add the endpoint to `HttpEndpoints::Catalog`. The catalog attaches its response
adapter to the route. Multiple endpoints can reuse an operation/result and encode
it differently. A matched route owns its adapter through deferred body reading
and completion. Raw `HttpRoute_s` registrations remain supported.

Upgrade endpoints provide only `Route()`, with `webSocket = true`; register them
in the same catalog. This selects the existing subscription protocol/session,
not a new arbitrary WebSocket protocol.

For a new application operation:

1. Add owned request and result types under `src/Application/Type/` (or their
   domain's `Type/` folder).
2. Add an operation class under `src/Application/Operations/`, with `Payload`
   naming the request, `Result` naming the result, and
   `Execute(const ApplicationRequestContext_s&, const shared_ptr<RequestControl_s>&,
   const Payload&)` returning `optional<Result>`.
3. Add the operation to `ApplicationOperations_s` in
   `src/Application/Type/ApplicationOperations_s.hpp`. Request/result variants
   and execution dispatch derive from that list.
4. Add the HTTP endpoint and its catalog entry as above. Validate and decode only
   in the endpoint; execute against the account facade only in the operation.

Returning a result completes an immediate operation. An empty optional is reserved
for the existing console-command completion lifecycle: the handler must install
`RequestControl_s::execution`, and the processor finalizes it after all recipients
finish. A new kind of deferred operation needs its own completion lifecycle before
using this path; an empty optional is not a general async job mechanism.

`AccountControl` is the narrow account facade available to application handlers.
`AccountRunner` implements it; add domain capabilities there when an operation
needs functionality beyond the existing command and status access. HTTP callbacks
never receive this facade. Existing request admission, deadlines, cancellation,
shutdown and runner safe points continue to govern every operation.

`HttpResponses::Complete` remains the fallback for raw routes and completions
without a route-compatible result, such as cancellation before execution. Its
serializer list also derives from the endpoint catalog; the first endpoint for a
result type defines the fallback encoding. Keep that ordering stable when adding
alternate encodings. Normal matched responses use their own endpoint adapter.

Test decoding/encoding and behavior at safe points. Transport tests should verify
that a route's custom response survives asynchronous completion. Keep public wire
contracts and examples in the relevant operator guides current.

## WebSocket application events

`src/Application/Events/Type/ApplicationEvents_s.hpp` is the event list. An event
definition under `Events/Definitions/` provides:

- `Payload`: its owned application value type.
- `NAME`: unique public subscription name.
- `SCOPE`: `EventScope_e::Account` or `EventScope_e::Global`.
- `RETAINS_LATEST`: whether subscriptions receive the latest value per account
  for account events, or one latest value per event type for global events.
- `MAX_SERIALIZED_BYTES`: the maximum **full event envelope**, including metadata.
- `Measure(const Payload&)`: bounded validation/accounting before copying; return
  an empty optional to reject the value. Include owned dynamic content and payload
  storage; the generic adapter adds envelope storage.
- `Serialize(const Payload&)`: payload JSON; the protocol supplies the envelope.

Add the definition to `ApplicationEvents_s`. Its payload variant, known-name
validation, name lookup, encoding and retention dispatch derive from that list.
Names, scopes and maximum envelope sizes are checked at compile time.

Emit from an account safe point using its optional shared publisher:

```cpp
if (m_options.events)
{
    m_options.events->Publish(m_account.name, AccountLogout_s{confirmed});
}
```

Publish a global event at an application safe point without an account:

```cpp
events->Publish(ApplicationStarted_s{});
```

The typed overloads require the definition's scope at compile time: account events
require an account argument, and global events accept only their payload. Owned
`ApplicationEvent_s` envelopes use an optional account; the bridge rejects a scope
mismatch, empty account name, or unknown account. Global envelopes serialize
`"account": null`; account envelopes retain their account-name string.

Subscriptions with an absent or empty account filter may receive both scopes,
subject to their event-name filter. A nonempty account filter excludes all global
events, including retained snapshots. A global-only subscription should omit the
account filter. Global events work even when no accounts are configured.

The typed publisher validates the borrowed payload before copying into the owned
journal. Producer callbacks with variable-sized inputs should use this overload.
The owned `Publish(ApplicationEvent_s)` overload remains available when ownership
already exists. All publications and subscription changes retain journal ordering;
no event-specific account option or application startup callback is needed.

`EventLimits` owns the shared listener/event resource limits. A retained event
reserves its declared maximum envelope size plus a separator per configured
account for account scope, or once per event type for global scope. Bridge construction rejects a catalog/account combination whose snapshot
plus framing/ack reserve exceeds the client outbox byte limit. Another retained
event therefore cannot silently invalidate the old one-event-per-account budget.
The serializer's actual envelope size is also checked at publication processing.

Test payload schema, bounds, account/event filtering, retention, ordering and the
producer's actual trigger. Existing logout and progress tests provide examples.

`application.started` is a retained global event with an empty object payload,
published once after the HTTP listener and accounts have initialized and before
the runner loop starts. Its envelope timestamp records publication time. A fresh
global subscription receives that original envelope in its snapshot; it does not
trigger another startup event.

Python scripts publish bounded live `script.event` values using
`publish_event(name, data=None)`. `ScriptPublishedEvent` owns the limits, JSON
validation and serializer, while the host supplies the account config identity.
See [script publication](../scripting/console-and-messages.md#operator-events).
