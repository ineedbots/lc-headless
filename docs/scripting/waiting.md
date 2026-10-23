# Waiting: `execution`

Where rs2b0t writes `await`, a script writes `yield from`. The `execution` builtin holds the waits. Each one is a generator: `yield from` it inside `loop()`, `on_start()`, a task's `execute()`, or any generator they call, and it gives back its result.

```python
def loop():
    raw = inventory.first('Raw shrimps')
    fire = locs.query().name('Fire').within(3).nearest()
    if raw is None or fire is None:
        return 600
    raw.use_on(fire)
    cooked = yield from execution.delay_until(lambda: inventory.count('Shrimps') > 0, 5000)
    if not cooked:
        log('Nothing cooked')
```

Calling a wait without `yield from` does nothing: it only makes a generator object.

## Functions

### `execution.delay(ms)`

Waits at least `ms` milliseconds of wall-clock time. Gives `None`.

### `execution.delay_ticks(n)`

Waits `n` server ticks (about 600 ms each). `n` of 0 or less returns at once. Gives `None`.

### `execution.delay_until(cond, timeout_ms=6000)`

Calls `cond()` now and again after every update from the server (each pass that decoded a packet), until it's true or `timeout_ms` has passed.

- **Gives** `True` as soon as `cond()` is true, `False` at the timeout.
- `cond` should be cheap: it may run many times a tick.
- A change shows the pass after the packet that made it, not on a poll.

```python
opened = yield from execution.delay_until(lambda: bank.is_open(), 5000)
```

### `execution.delay_until_ticks(cond, max_ticks)`

As `delay_until`, but checks once a server tick, for at most `max_ticks` ticks. Gives `True` or `False`.

### `execution.note_progress()`

Not a wait. Tells the [stall guard](upkeep.md#the-stall-guard) the bot made progress it can't see for itself, such as a completed trade. It already counts a change of tile and any experience. Calling it every loop turns stall detection off in effect.

## `event_signal`

rs2b0t's `EventSignal`, a cooperative interrupt. Here the random event guardian takes over by dropping the bot's step at the next tick, so a long loop that would rather stop at a safe point (between hits, after a bank deposit) asks first:

```python
while fighting():
    if event_signal.pending():
        return                      # the guardian answers the event, and loop() starts afresh
    yield from execution.delay_ticks(1)
```

| Member | Does |
|---|---|
| `event_signal.pending()` | True while the guardian sees an event it will answer, checked once a tick, or while the bot's interrupt holds |
| `event_signal.set_interrupt(fn)` | The bot's own reason to stop, as a callable, such as `lambda: self.died`; `None` clears it. A [`ScriptActivity`](script-structure.md#running-a-bot-inside-another-scriptactivity)'s `stop()` clears it too |

What a step must keep across an interruption goes on an object, such as the bot, not in a generator's locals, since the generator is dropped.

## Yielding directly

A generator can `yield` these itself, which is what the functions above do:

| Yield | Resumes |
|---|---|
| An `int` ≥ 0 | After that many milliseconds of wall-clock time. A yielded 600 is 600 ms, not a tick |
| `execution.Update(timeout_ms=None)` | After the next pass that decoded a packet, or `timeout_ms` when given, whichever comes first |
| `execution.Ticks(count)` | After `count` more server ticks. `count` must be an `int` ≥ 1, or `ValueError` |

Yielding anything else, or a negative number, stops the script with `TypeError` or `ValueError`.

## Rules

- Hooks run as usual while `loop()` waits.
- The call timeout (`scripting.callTimeoutMs`, 1000 ms by default) applies to each stretch between two waits, not to the whole generator.
- Hooks, event subscribers and console command handlers can't wait. Set a flag there and act on it in `loop()`.
- When the random-event guardian or the stall guard takes over, the waiting generator is dropped and `loop()` starts afresh afterwards, so don't rely on code after a `yield from` always running.
- A reload with `--watch` starts the script over.

## Other waits

Many facade functions are waits too, and are marked **Wait** in this reference, such as `equipment.equip(name)`, `bank.withdraw_x(name, n)` and `traversal.walk_resilient(dest)`. They're used the same way:

```python
worn = yield from equipment.equip('Bronze sword')
```
