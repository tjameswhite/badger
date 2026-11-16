# GitHub Universe Badge

This repository now targets the **GitHub Universe 2026 badge**. The current
badge filesystem lives in [`badge/`](./badge/) and is intended to be copied to
the badge's `/system` partition.

The Universe 2025 sources remain available in [`badge25/`](./badge25/) for
people using the previous badge.

## Repository layout

| Path | Purpose |
| --- | --- |
| [`badge/`](./badge/) | Universe 2026 `/system` files and apps |
| [`badge25/`](./badge25/) | Archived Universe 2025 files, docs, simulator, and apps |
| [`hardware/`](./hardware/) | Universe 2026 schematic and hardware/GPIO reference |
| [`eink/`](./eink/) | Earlier e-ink badge resources |
| [`ir-beacon/`](./ir-beacon/) | IR beacon utilities and protocol experiments |

The legacy simulator and Badgeware API documentation are under `badge25/`.
They do not model the 2026 graphics and input APIs.

## Examples

The [apps](./badge/apps/) folder contains all the applications that ship on the badge along
with others from the stock Pimoroni Tufty 2350 badge the GitHub Universe badge is based on. It 
also contains a number of community submitted applications for you to experiment with.

### Universe 2026 apps (`badge/apps/`)

Each app folder has a `README.md` with usage and requirements.

| App | Summary |
| --- | --- |
| [30 Minutes to Alpha Centauri](./badge/apps/30_minutes_to_alpha_centauri/) | Pilot a cargo ship through obstacles to complete a space delivery. |
| [AutoX](./badge/apps/autox/) | Measure cornering, braking and acceleration forces and log autocross runs. |
| [Badge](./badge/apps/badge/) | Display your GitHub profile and contribution graph (Wi-Fi). |
| [Bee Amazed](./badge/apps/bee_amazed/) | Guide a bee through mazes that get harder each level. |
| [Brattal](./badge/apps/brattal/) | A two-lane arcade shooter. |
| [Camera](./badge/apps/camera/) | Live viewfinder and shutter for a Wi-Fi ESP32-CAM, with photo review. |
| [Clock](./badge/apps/clock/) | Show the time in selectable styles and time zones (Wi-Fi/NTP). |
| [Commits](./badge/apps/commits/) | Break GitHub-colored bricks with a paddle. |
| [Contacts](./badge/apps/contacts/) | Exchange contact cards with nearby badges over the badge link. |
| [Copilot](./badge/apps/Copilot/) | Monitor GitHub Copilot coding sessions with an animated Agent Buddy. |
| [Demos](./badge/apps/demos/) | Graphics demos of shapes, text, sprites and display effects. |
| [Extend-a-Squirrel](./badge/apps/extend_a_squirrel/) | Snake-style game with a growing squirrel. |
| [Flappy Mona](./badge/apps/flappy_mona/) | Flap Mona through the gaps; best score is saved. |
| [Gallery](./badge/apps/gallery/) | Browse images with a thumbnail carousel. |
| [Ghost Signal](./badge/apps/ghost_signal/) | Match a moving wave pattern as accurately as possible. |
| [Hydrate](./badge/apps/hydrate/) | Track water intake against a daily goal. |
| [Input Test](./badge/apps/input_test/) | Test touch controls, buttons and motion input. |
| [ISS](./badge/apps/iss/) | Track the International Space Station on a live world map (Wi-Fi). |
| [Life](./badge/apps/life/) | Conway's Game of Life. |
| [Mass Storage](./badge/apps/mass_storage/) | Restart the badge as a USB drive to manage its files. |
| [Menu](./badge/apps/menu/) | The home screen launcher for every installed app. |
| [Merge Conflict](./badge/apps/merge_conflict/) | Short two-player games, including badge-link play. |
| [Mona Paint](./badge/apps/mona_paint/) | Tilt-aware paint program with drawing tools and undo. |
| [Mona Pet](./badge/apps/mona_pet/) | Virtual pet with feeding, cleaning and matching games. |
| [Monapet](./badge/apps/monapet/) | Care for your very own Mona. |
| [Pong](./badge/apps/pong/) | Badge-link multiplayer Pong. |
| [Quest](./badge/apps/quest/) | Universe badge quest: exchange IR beacons and collect progress. |
| [Rogue](./badge/apps/rogue/) | Turn-based dungeon crawler. |
| [Sense](./badge/apps/sense/) | Live temperature, humidity, pressure, light and motion readings. |
| [Settings](./badge/apps/settings/) | Edit Wi-Fi, GitHub username, contact name and backlight settings. |
| [Show](./badge/apps/show/) | Start the firmware's Sparkle light show. |
| [Sketchy Sketch](./badge/apps/sketchy_sketch/) | Draw by moving a cursor with the directional controls. |
| [Snake](./badge/apps/snake/) | A continuously moving snake game. |
| [Snarky Sciuridae](./badge/apps/snarky_sciuridae/) | Care for your very own squirrel. |
| [Startup](./badge/apps/startup/) | Boot animation shown before the menu. |
| [System](./badge/apps/system/) | Time, battery status and Wi-Fi clock sync. |
| [Tennis](./badge/apps/tennis/) | Pong-style game against a computer paddle. |
| [Tomato](./badge/apps/tomato/) | Pomodoro timer. |

### Universe 2025 apps (`badge25/apps/`)

These use the 2025 Badgeware API and run on the 2025 badge or the
[simulator](./badge25/README.md#testing-apps-with-the-simulator).

| App | Summary |
| --- | --- |
| [badge](./badge25/apps/badge/) | GitHub profile, avatar and contribution graph (Wi-Fi). |
| [commits](./badge25/apps/commits/) | Break GitHub-colored bricks with a paddle. |
| [copilot-loop](./badge25/apps/copilot-loop/) | Looping Copilot animation. |
| [crypto](./badge25/apps/crypto/) | Cryptocurrency prices (Wi-Fi). |
| [files](./badge25/apps/files/) | Browse the filesystem and view text files. |
| [flappy](./badge25/apps/flappy/) | Flappy-style game with Mona. |
| [gallery](./badge25/apps/gallery/) | Browse PNG images. |
| [gitris](./badge25/apps/gitris/) | GitHub-themed falling-block puzzle game. |
| [hello](./badge25/apps/hello/) | Minimal "hello world" starter app. |
| [invaders](./badge25/apps/invaders/) | Space-invaders-style shooter. |
| [jezzball](./badge25/apps/jezzball/) | Trap bouncing balls with dividers to claim territory. |
| [life](./badge25/apps/life/) | Conway's Game of Life with color palettes. |
| [menu](./badge25/apps/menu/) | Launcher that auto-discovers installed apps. |
| [monapet](./badge25/apps/monapet/) | Virtual pet Mona. |
| [quest](./badge25/apps/quest/) | Universe 2025 IR beacon quest. |
| [sensor_dashboard](./badge25/apps/sensor_dashboard/) | Temperature, humidity, dew point, VOC and NOx from external Qw/ST sensors. |
| [sketch](./badge25/apps/sketch/) | Drawing app with a dial-controlled cursor. |
| [snake](./badge25/apps/snake/) | Classic Snake with score tracking. |
| [startup](./badge25/apps/startup/) | Boot animation. |
| [stocks](./badge25/apps/stocks/) | Stock prices (Wi-Fi). |
| [weather](./badge25/apps/weather/) | Current weather for your location via Open-Meteo (Wi-Fi). |
| [wifi](./badge25/apps/wifi/) | Wi-Fi connection status. |
| [wled](./badge25/apps/wled/) | Control WLED devices such as the Universe 2025 Octolamp (Wi-Fi). |

## Pimoroni and Badgeware resources

- [Tufty 2350 product page and specifications](https://shop.pimoroni.com/products/tufty-2350)
- [`pimoroni/tufty2350`](https://github.com/pimoroni/tufty2350) firmware,
  board definitions, modules, and examples
- [`pimoroni/badgeware-docs`](https://github.com/pimoroni/badgeware-docs)
  Badgeware documentation and examples
- [`pimoroni/badgeware-simulator`](https://github.com/pimoroni/badgeware-simulator)
  desktop Badgeware Simulator
- [`pimoroni/badgeware-web-simulator`](https://github.com/pimoroni/badgeware-web-simulator)
  browser-based Badgeware Simulator

These upstream simulators and documents are useful references for the Tufty
and Badgeware ecosystem, but they do not model GitHub's custom 2026
accelerometer, IR, capacitive controls, or firmware APIs exactly. Test those
features on a Universe 2026 badge.

## Universe 2026 badge

The 2026 badge is a custom derivative of Pimoroni's
[Tufty 2350](https://shop.pimoroni.com/products/tufty-2350), part of the
[Badger, Tufty, and Blinky digital badge crew](https://badgewa.re/). It
retains Tufty's RP2350B, 320x240 colour LCD, 8 MB PSRAM, 16 MB flash, wireless
module, battery, case lighting, light sensor, and Qw/ST expansion connector.

The GitHub Universe version extends that platform with hardware designed for
interactive games and badge-to-badge experiences:

- An onboard LSM6DS3TR-C accelerometer and gyroscope.
- IR transmit and receive hardware.
- Eight capacitive touch controls: a directional pad plus Select, Back, Menu,
  and Home pads.
- Five physical front controls that work with the touch controls through the
  firmware's orientation-aware logical input API.

The firmware automatically handles screen orientation and exposes logical
input actions. Apps should use `BUTTON_UP`, `BUTTON_DOWN`, `BUTTON_LEFT`,
`BUTTON_RIGHT`, `BUTTON_SELECT`, `BUTTON_BACK`, `BUTTON_MENU`, and
`BUTTON_HOME` with `badge.pressed()`, `badge.held()`, and `badge.released()`.
Do not hard-code a physical control based on which end of the badge is
currently uppermost.

See the complete [Universe 2026 hardware reference](./hardware/README.md) for
the RP2350 GPIO map and onboard peripheral connections. See the
[USB serial and MicroPython REPL guide](./hardware/USB_SERIAL.md) to inspect a
connected badge and copy files or apps.

## Skills for building 2026 apps

The [`hyb26-skill`](./.github/skills/hyb26-skill/SKILL.md) Copilot skill helps
you create, check, debug, and install apps on your badge from macOS, Linux, or
Windows. Copilot picks it up automatically in this repository. It covers
`mpremote` and the REPL, switching the badge into USB Disk Mode from your
computer, enabling custom `icon.png` menu icons on stock badges, and the
[badger.github.io simulator](https://badger.github.io/editor). See its
[README](./.github/skills/hyb26-skill/README.md) to install it for other
projects.

## Creating a 2026 app

Apps are directories under `badge/apps/`:

```text
badge/apps/my_app/
├── __init__.py
├── icon.png
└── assets/
```

`icon.png` should be a 24x24 PNG. A minimal application is:

```python
import os
import sys

APP_DIR = "/system/apps/my_app"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

screen.font = font.nope


def update():
    screen.pen = color.rgb(20, 24, 28)
    screen.rectangle(screen.clip)

    screen.pen = color.rgb(255, 255, 255)
    screen.text("Hello Universe!", 10, 10)

    if badge.pressed(BUTTON_SELECT):
        print("Selected")


run(update)
```

The runtime supplies commonly used graphics and badge objects as globals,
including `badge`, `screen`, `image`, `font`, `color`, `shape`, `brush`,
`vec2`, `rect`, `mat3`, `run`, button constants, mode constants, and filesystem
helpers. Inspect the apps in [`badge/apps/`](./badge/apps/) for working
patterns.

### Badge Simulator canvas

If you use the GitHub Copilot app, this repository includes a **Badge
Simulator** canvas that loads automatically. Ask Copilot to "open the Badge
Simulator for my_app": your app runs on a 3D badge beside the chat and reloads
every time you save. **Deploy** asks Copilot to install it on a connected badge.
See [`.github/extensions/badge-simulator/`](./.github/extensions/badge-simulator/README.md).

### Input and orientation

```python
if badge.pressed(BUTTON_SELECT):
    activate()

if badge.held(BUTTON_LEFT):
    x -= speed * (badge.ticks_delta / 1000)

if badge.released(BUTTON_BACK):
    close_panel()

if badge.touched(BUTTON_MENU):
    show_touch_feedback()

direction = badge.direction()
upside_down = badge.upside_down()
```

Use `badge.ticks_delta` for frame-rate-independent animation and movement.
Use `screen.width` and `screen.height` instead of assuming a resolution.
The default logical mode used by most included apps is 160x120; apps that need
the full display can request `badge.mode(HIRES | VSYNC)`, which provides a
320x240 drawing surface.

### Graphics

```python
sprite = image.load("assets/sprite.png")
sheet = image.load("assets/characters.png").spritesheet(7, 2)

screen.pen = color.rgb(73, 219, 255)
screen.shape(shape.rectangle(0, 0, screen.width, screen.height))
screen.blit(sprite, vec2(10, 10))
screen.blit(sheet.sprite(0, 0), rect(40, 20, 32, 32))
```

Set `screen.pen` before drawing. Fonts are available through the `font`
namespace, for example `font.nope`, `font.sins`, `font.ark`, and
`font.ziplock`.

### Persistent state

```python
from badgeware import State

state = {"highscore": 0}
State.load("my_app", state)

# Save after a meaningful state change.
State.save("my_app", state)
```

Persistent state is stored outside `/system`; do not commit runtime state or
real Wi-Fi credentials.

## Installing files on a badge

Copy the contents of `badge/` to `/system/` on the Universe 2026 badge. To
install a single app, copy its complete directory to
`/system/apps/<app_name>/`. The menu discovers directories containing
`__init__.py` or `__init__.mpy`.

The normal MicroPython REPL mounts `/system` read-only. Use USB mass-storage
mode for persistent deployment; `mpremote mount badge` is useful for transient
hardware tests without copying. See
[`hardware/USB_SERIAL.md`](./hardware/USB_SERIAL.md) for the tested workflow.

The Wi-Fi template is [`badge/secrets.py`](./badge/secrets.py). Keep committed
values empty and configure credentials only on the device.

## Contributing

We welcome contributions! If you've created a new app or improved an existing
one, please consider submitting a pull request.

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). New development should target the
2026 runtime under `badge/`; only compatibility fixes for the older hardware
should be made under `badge25/`.
