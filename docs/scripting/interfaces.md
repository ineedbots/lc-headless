# Interfaces, dialogues and make menus

- [`chat_dialog`](#chat_dialog): dialogue pages, options and make menus in the chat box
- [`MakeProduct`](#makeproduct)
- [`modals`](#modals): the main interface, such as the bank or a shop
- [`interfaces`](#interfaces): any interface, component by component
- [`Component`](#component)

Each is found by its shape and what it offers, not by interface ids, so it works across revisions.

## `chat_dialog`

The chat box. Matching is by part of the text, without regard to case, as rs2b0t's is.

```python
while chat_dialog.can_continue():
    yield from chat_dialog.continue_()
yield from chat_dialog.choose_option('Yes')
yield from chat_dialog.make_x('Long Bow', 27)
```

Each method marked **Wait** gives `True` once the server has opened, closed or changed an interface in answer, and `False` when it didn't answer within 3 seconds, or there was nothing to click.

### Dialogue

| Method | Gives or does |
|---|---|
| `chat_dialog.is_open()` | A chat box interface is open |
| `chat_dialog.can_continue()` | A "Click here to continue" is showing and hasn't been clicked. The game sends one click per page, and so does this |
| `chat_dialog.continue_()` | **Wait.** Clicks it, and waits for the next page or the end. The trailing underscore is because `continue` is a keyword |
| `chat_dialog.texts()` | The chat box's lines, such as the speaker's name and what they say, without colour tags |
| `chat_dialog.options()` | The choices on offer, as the player reads them |
| `chat_dialog.choose_option(text=None)` | **Wait.** Chooses the first option containing `text`, or the first option when `text` is `None` |

### Make menus

A make menu is a stack of buttons over each product, one button per amount, such as fletching's "Make 1" to "Make X", the furnace's "Smelt 1 Bronze" or the tanner's "Tan all". A stack in the chat box is found first, else one in the main interface.

| Method | Gives or does |
|---|---|
| `chat_dialog.is_make_menu()` | A make menu is open |
| `chat_dialog.products()` | Its products, as [`MakeProduct`](#makeproduct)s |
| `chat_dialog.make_products()` | Its products' names |
| `chat_dialog.make(name=None)` | **Wait.** Clicks the button that makes the most without asking, on the first product whose name (or item's name) contains `name`, or the first product: "All" where there's one, otherwise the largest count |
| `chat_dialog.make_one(name=None)` | **Wait.** Clicks its "1" button |
| `chat_dialog.make_x(name, count)` | **Wait.** Clicks its "X" button, waits up to 5 seconds for the count dialog, and answers it with `count`. Gives `True` once the answer is sent |
| `chat_dialog.answer_count(count)` | Answers an open "Enter amount" dialog, rs2b0t's `actions.answerCountDialog`. `False` when none is open |

A product's name is the text the player reads on its buttons, without line breaks or colour tags, such as "Oak Long Bow" or "Soft leather: 1 gp". A product with no text is named by the item drawn over it, and failing that by what follows the amount in its buttons' options.

### Make panels

Some make screens, such as the anvil and gold jewellery, are inventories whose options make things.

| Method | Gives or does |
|---|---|
| `chat_dialog.is_main_make_panel()` | Such a panel is open |
| `chat_dialog.main_make_products()` | Its products' names, slot by slot |
| `chat_dialog.make_from_panel(name, op=None)` | **Wait.** Uses option `op`, such as `'Make 5'`, or the first option, on the product whose name contains `name`. Waits up to 5 seconds |
| `chat_dialog.make_from_panel_max(name)` | **Wait.** Uses the option that makes the most |

## `MakeProduct`

One product of a make menu.

| Member | Meaning |
|---|---|
| `name` | Its name, as above |
| `item` | The item id drawn over it, or `None` |
| `item_name` | That item's name, or `None` |
| `amounts` | What its buttons make: counts, plus [`MAKE_X`](constants.md#dialogues) (-1) for the button that asks and `MAKE_ALL` (0) for one that makes all |
| `button(amount)` | The component id of the button that makes `amount`, or `None` |
| `largest()` | The button `make()` uses: `MAKE_ALL`'s, else the largest count's, else `None` |

```python
for product in chat_dialog.products():
    log(product.name, product.amounts)
```

## `modals`

The main interface: the bank, a shop, the anvil, a quest journal.

| Method | Gives or does |
|---|---|
| `modals.main()` | Its id, or -1 |
| `modals.is_open()` | Whether there is one |
| `modals.close()` | **Wait.** Closes the open interfaces and waits up to 3 seconds for it to go. `True` when it went, or when none was open |
| `modals.close_if_open()` | **Wait.** The same, only when one is open. Gives `None` |

## `interfaces`

The game's interfaces as the player sees them: the cache's components, with what the server has set on them (text, colour, hiding, position, the item shown) in place of the cache's. It's what the facades above are built on, and it reaches any interface they don't cover.

```python
interfaces.click_text('Accept')
options = [c.text for c in interfaces.find(button='ok', root=reader.chat_modal())]
```

| Method | Gives or does |
|---|---|
| `interfaces.component(id)` | A [`Component`](#component), or `None` for an id the cache doesn't have |
| `interfaces.root(id)` | Every component of an interface, from its root down, in drawing order |
| `interfaces.open()` | The ids of the open interfaces: the main, side and chat modals, the overlay, and each tab's |
| `interfaces.tab(n)` | The interface in side tab `n`, 0 to 14, or -1. Tab 0 is combat, 2 quests, 5 prayer, 6 magic |
| `interfaces.find(text=None, button=None, root=None)` | Visible components with that text (whole, without regard to case) and button type, where each is given, in every open interface or only in `root`'s |
| `interfaces.click(id)` | Clicks the component as its button type says (see below). `False` when it isn't visible; a component that isn't a button raises `ValueError` |
| `interfaces.click_text(text, root=None)` | Clicks the button under the visible text, as a player clicking the words would. Trade's "Accept", for one, is a label over an unlabelled button. `False` when there's no such text, or no button under it |

What a click sends, by button type:

| `button` | Click |
|---|---|
| `'ok'`, `'toggle'`, `'select'` | A button press |
| `'continue'` | Continues the dialogue |
| `'close'` | Closes the interface |
| `'target'`, `None` | Raises `ValueError`. Cast spells with the [spell functions](game.md#casting-spells) |

An id the cache doesn't have also raises `ValueError`.

## `Component`

A snapshot of one interface component.

| Field | Meaning |
|---|---|
| `id` | Its id |
| `root` | The interface it belongs to |
| `layer` | The layer it sits in, or `None` for a root |
| `type` | `'layer'`, `'inv'`, `'rect'`, `'text'`, `'graphic'`, `'model'` or `'invtext'` |
| `button` | `None`, `'ok'`, `'target'`, `'close'`, `'toggle'`, `'select'` or `'continue'` |
| `button_text` | Its menu option, such as "Use Special Attack" |
| `text` | Its text as shown |
| `colour` | Its text colour, as RGB |
| `hidden` | Whether it's hidden itself |
| `visible` | Whether it's in an open interface, with nothing above it hidden |
| `options` | An inventory's five options, `None` where empty; `None` for other types |
| `target_verb`, `target_name` | A spell button's, such as "Cast on" and "Wind strike" |
| `x`, `y` | Its position from its interface's top-left corner |
| `width`, `height` | Its size |
| `children` | The ids of its children |
| `item` | The item the server set it to show, such as a make menu's product, or `None` |
| `varp`, `value` | For a Select or Toggle button, the varp its condition reads and the value it compares with, which is what clicking it sets; else `None` |

`component.click()` clicks it, as `interfaces.click(component.id)`.

To move an item within an interface inventory, use [`InvItem.move_to(slot)`](items.md#invitem).
