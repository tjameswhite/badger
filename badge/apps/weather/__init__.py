"""
Current weather for where you are, from Open-Meteo.

Location comes from your IP address unless WEATHER_LOCATION is set in
secrets.py. Open-Meteo and the geolocation services need no key or account.
The network details come from secrets.py.

Controls:
* Select = Fetch again now
* Up / Down = Cycle units (F + mph, C + mph, C + km/h)
"""

import os
import sys

APP_DIR = "/system/apps/weather"
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

import gc

import requests
from badgeware import State

import missing_details

MISSING = missing_details.missing("WIFI_SSID")
if not MISSING:
    import wifi

badge.mode(HIRES | VSYNC)
screen.antialias = image.X2

WIDTH, HEIGHT = 320, 240
PAD = 12

REFRESH_EVERY = 10 * 60_000     # Open-Meteo updates its current values every 15 min
RETRY_AFTER = 30_000
REQUEST_TIMEOUT = 10
WIFI_TIMEOUT = 10
WIFI_RETRIES = 100000           # keep trying; the page reports progress
USER_AGENT = "badger-weather/1.0"

FORECAST = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
            "&current=temperature_2m,apparent_temperature,relative_humidity_2m,"
            "weather_code,wind_speed_10m,is_day"
            "&daily=temperature_2m_max,temperature_2m_min"
            "&timezone=auto&forecast_days=1")
WTTR = "https://wttr.in/%s,%s?format=j2"   # fallback when Open-Meteo is down
GEOCODE ="https://geocoding-api.open-meteo.com/v1/search?count=1&name=%s"
IP_LOOKUPS = (
    # (url, latitude key, longitude key, city key, country key)
    ("https://ipapi.co/json/", "latitude", "longitude", "city", "country_code"),
    ("https://ipwho.is/", "latitude", "longitude", "city", "country_code"),
)

background = color.rgb(13, 17, 23)
white = color.rgb(235, 245, 255)
muted = color.rgb(120, 130, 140)
phosphor = color.rgb(211, 250, 55)
blue = color.rgb(48, 148, 255)
warning = color.rgb(255, 125, 120)
sun_yellow = color.rgb(255, 200, 60)
cloud_grey = color.rgb(200, 210, 220)
rain_blue = color.rgb(90, 170, 255)
storm_purple = color.rgb(190, 150, 255)
night_blue = color.rgb(170, 190, 255)
transparent = color.rgb(0, 0, 0, 0)

small_font = font.nope          # 13px
label_font = font.smart         # 16px
condition_font = font.ziplock   # 21px
big_font = font.ignore          # 28px, doubled for the temperature

# Glyphs in the built-in weather icon font, which is 16px tall.
ICON_SUN = "2"
ICON_MOON = "*"
ICON_PARTLY = "3"
ICON_CLOUD = "&"
ICON_FOG = "<"
ICON_RAIN = "/"
ICON_SNOW = "1"
ICON_STORM = "7"
ICON_DROP = ":"
ICON_WIND = ">"

CONDITIONS = {
    0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Freezing fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    56: "Freezing drizzle", 57: "Freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light showers", 81: "Showers", 82: "Heavy showers",
    85: "Snow showers", 86: "Snow showers",
    95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm",
}

# F + mph, C + mph, C + km/h, cycled with up and down
UNIT_MODES = (("F", "mph"), ("C", "mph"), ("C", "km/h"))

prefs = {"units": -1}           # -1 until chosen: picked from the country
State.load("weather", prefs)

location = None                 # {"lat", "lon", "name", "country"}
weather = None                  # the last good reading
fetched_at = None               # ticks when it arrived
next_fetch = 0
fault = None                    # what went wrong last, shown until a success
pending = None                  # a blocking step to run after its page is drawn
connect_started = False

_scaled = {}                    # (text, font, scale, colour key) -> image


# --- secrets ---------------------------------------------------------------

def weather_location_setting():
    """WEATHER_LOCATION from secrets.py, or None."""
    for path in ("/", "/system"):
        if path not in sys.path:
            sys.path.append(path)
    try:
        import secrets
        return getattr(secrets, "WEATHER_LOCATION", None)
    except ImportError:
        return None


# --- network ---------------------------------------------------------------

def quote(text):
    """Percent-encode for a query string."""
    out = []
    for byte in str(text).encode("utf-8"):
        ch = chr(byte)
        if ch.isalpha() or ch.isdigit() or ch in "-_.~":
            out.append(ch)
        else:
            out.append("%%%02X" % byte)
    return "".join(out)


def get_json(url):
    response = requests.get(url, timeout=REQUEST_TIMEOUT,
                            headers={"User-Agent": USER_AGENT})
    try:
        if response.status_code != 200:
            raise OSError("HTTP %d from %s" % (response.status_code, url.split("/")[2]))
        return response.json()
    finally:
        response.close()
        gc.collect()


def geocode(city, country=None):
    url = GEOCODE % quote(city)
    if country:
        url += "&countryCode=" + quote(country)
    results = get_json(url).get("results")
    if not results:
        raise ValueError("No place called %s" % city)
    found = results[0]
    return {"lat": found["latitude"], "lon": found["longitude"],
            "name": found["name"], "country": found.get("country_code", country)}


def from_setting(setting):
    """Turn WEATHER_LOCATION into a location.

    Accepts a city string ("Paris"), a city tuple (("London", "GB")), a
    coordinate tuple ((lat, lon, name, country)), or a dict with either
    "city" (and optional "country") or "lat"/"lon" (and optional "name",
    "country").
    """
    if isinstance(setting, str):
        return geocode(setting)
    if isinstance(setting, dict):
        if "city" in setting:
            return geocode(setting["city"], setting.get("country"))
        return {"lat": setting["lat"], "lon": setting["lon"],
                "name": setting.get("name", "Custom"),
                "country": setting.get("country")}
    if isinstance(setting, (tuple, list)) and setting:
        if isinstance(setting[0], (int, float)):
            return {"lat": setting[0], "lon": setting[1],
                    "name": setting[2] if len(setting) > 2 else "Custom",
                    "country": setting[3] if len(setting) > 3 else None}
        return geocode(setting[0], setting[1] if len(setting) > 1 else None)
    raise ValueError("WEATHER_LOCATION must be a string, tuple or dict")


def from_ip():
    """Ask each IP geolocation service in turn."""
    reason = None
    for url, lat, lon, city, country in IP_LOOKUPS:
        try:
            found = get_json(url)
            if found.get(lat) is None:
                raise ValueError("no position in reply")
            return {"lat": found[lat], "lon": found[lon],
                    "name": found.get(city) or "Here",
                    "country": found.get(country)}
        except (OSError, ValueError, KeyError, TypeError) as error:
            reason = error
    raise OSError("Can't find location: %s" % reason)


def locate():
    global location
    setting = weather_location_setting()
    location = from_setting(setting) if setting else from_ip()
    if prefs["units"] < 0:
        prefs["units"] = 0 if location.get("country") == "US" else 2
        State.save("weather", prefs)


def from_open_meteo():
    reply = get_json(FORECAST % (location["lat"], location["lon"]))
    current = reply["current"]
    daily = reply.get("daily", {})
    code = current["weather_code"]
    return {
        "temp": current["temperature_2m"],
        "feels": current.get("apparent_temperature"),
        "humidity": current["relative_humidity_2m"],
        "wind": current["wind_speed_10m"],
        "code": code,
        "condition": CONDITIONS.get(code, "Unknown"),
        "day": current.get("is_day", 1),
        "high": (daily.get("temperature_2m_max") or [None])[0],
        "low": (daily.get("temperature_2m_min") or [None])[0],
    }


# wttr.in reports World Weather Online codes; each maps to the WMO code
# whose icon fits
WWO_FOG = (143, 248, 260)
WWO_STORM = (200, 386, 389, 392, 395)
WWO_SNOW = (179, 182, 185, 227, 230, 317, 320, 323, 326, 329, 332, 335, 338,
            350, 362, 365, 368, 371, 374, 377)


def wmo_from_wwo(code):
    if code == 113:
        return 0
    if code == 116:
        return 2
    if code in (119, 122):
        return 3
    if code in WWO_FOG:
        return 45
    if code in WWO_STORM:
        return 95
    if code in WWO_SNOW:
        return 73
    return 63


def from_wttr():
    reply = get_json(WTTR % (location["lat"], location["lon"]))
    current = reply["current_condition"][0]
    today = reply["weather"][0]
    code = int(current["weatherCode"])
    return {
        "temp": float(current["temp_C"]),
        "feels": float(current["FeelsLikeC"]),
        "humidity": float(current["humidity"]),
        "wind": float(current["windspeedKmph"]),
        "code": wmo_from_wwo(code),
        "condition": current["weatherDesc"][0]["value"],
        "day": 1,
        "high": float(today["maxtempC"]),
        "low": float(today["mintempC"]),
    }


SOURCES = (from_open_meteo, from_wttr)
source = 0                      # the one that last worked is tried first


def fetch_weather():
    """Try each source, starting with the one that worked last time."""
    global weather, fetched_at, source
    reason = None
    for offset in range(len(SOURCES)):
        index = (source + offset) % len(SOURCES)
        try:
            weather = SOURCES[index]()
            source = index
            fetched_at = badge.ticks
            return
        except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
            reason = error
    raise OSError("No weather service answered: %s" % reason)


def run_pending():
    """Run the blocking step whose page was drawn last frame."""
    global pending, fault, next_fetch
    step, pending = pending, None
    try:
        if location is None:
            locate()
        step()
        fault = None
        next_fetch = badge.ticks + REFRESH_EVERY
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        fault = str(error) or type(error).__name__
        next_fetch = badge.ticks + RETRY_AFTER


# --- units and conditions --------------------------------------------------

def units_index():
    return prefs["units"] if prefs["units"] >= 0 else 2


def units():
    return UNIT_MODES[units_index()]


def temperature(celsius):
    if celsius is None:
        return "--"
    if units()[0] == "F":
        celsius = celsius * 9 / 5 + 32
    return "%d" % round(celsius)


def wind_speed(kmh):
    if units()[1] == "mph":
        kmh = kmh / 1.609344
    return "%d %s" % (round(kmh), units()[1])


def icon_for(code, day):
    """The weather font glyph and its colour."""
    if code in (0, 1):
        return (ICON_SUN, sun_yellow) if day else (ICON_MOON, night_blue)
    if code == 2:
        return (ICON_PARTLY, sun_yellow) if day else (ICON_CLOUD, cloud_grey)
    if code == 3:
        return ICON_CLOUD, cloud_grey
    if code in (45, 48):
        return ICON_FOG, cloud_grey
    if 71 <= code <= 77 or code in (85, 86):
        return ICON_SNOW, white
    if code >= 95:
        return ICON_STORM, storm_purple
    if 51 <= code <= 82:
        return ICON_RAIN, rain_blue
    return ICON_CLOUD, muted


# --- drawing ---------------------------------------------------------------

def scaled(text, typeface, scale, pen):
    """`text` rendered once into a small image, for blitting `scale` times larger.

    The fonts are bitmaps, so this is how the icon and temperature get big
    without going soft. Images are cached by what they show.
    """
    key = (text, typeface.name, id(pen))
    if key not in _scaled:
        if len(_scaled) > 8:
            _scaled.clear()
        screen.font = typeface
        width, height = screen.measure_text(text)
        picture = image(int(width) + 1, int(height))
        picture.antialias = image.OFF
        picture.pen = transparent
        picture.clear()
        picture.font = typeface
        picture.pen = pen
        picture.text(text, 0, 0)
        _scaled[key] = picture
    picture = _scaled[key]
    return picture, picture.width * scale, picture.height * scale


def blit_scaled(text, typeface, scale, pen, x, y):
    picture, width, height = scaled(text, typeface, scale, pen)
    screen.blit(picture, rect(int(x), int(y), width, height))
    return width, height


def text_width(text, typeface):
    screen.font = typeface
    return screen.measure_text(text)[0]


def right_text(text, typeface, pen, right, y):
    screen.font = typeface
    screen.pen = pen
    screen.text(text, right - text_width(text, typeface), y)


def ago(ms):
    minutes = ms // 60_000
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return "%dm ago" % minutes
    return "%dh ago" % (minutes // 60)


def draw_header():
    screen.font = label_font
    screen.pen = phosphor
    name = location["name"] if location else "Weather"
    screen.text(name, PAD, 8)

    if fetched_at is not None:
        right_text(ago(badge.ticks - fetched_at), small_font, muted, WIDTH - PAD, 10)

    screen.pen = color.rgb(255, 255, 255, 30)
    screen.rectangle(PAD, 30, WIDTH - PAD * 2, 1)


def draw_footer():
    screen.font = small_font
    screen.pen = muted
    screen.text("SELECT refresh", PAD, HEIGHT - 20)
    right_text("UP/DOWN %s / %s" % units(), small_font, muted, WIDTH - PAD, HEIGHT - 20)


def draw_weather():
    glyph, tint = icon_for(weather["code"], weather["day"])
    blit_scaled(glyph, font.weather, 5, tint, PAD + 4, 44)

    # temperature, doubled, with the unit beside it at normal size
    temp = temperature(weather["temp"])
    temp_w, _ = scaled(temp, big_font, 2, white)[1:]
    unit_w = text_width("°" + units()[0], label_font)
    right = WIDTH - PAD
    x = right - unit_w - 4 - temp_w
    blit_scaled(temp, big_font, 2, white, x, 40)
    screen.font = label_font
    screen.pen = muted
    screen.text("°" + units()[0], right - unit_w, 46)

    details = "feels %s°   H %s°  L %s°" % (temperature(weather["feels"]),
                                             temperature(weather["high"]),
                                             temperature(weather["low"]))
    right_text(details, small_font, muted, right, 104)

    screen.font = condition_font
    screen.pen = phosphor
    screen.text(weather["condition"], rect(PAD, 130, WIDTH - PAD * 2, 26))

    # humidity and wind, each with its icon
    y = 172
    screen.font = font.weather
    screen.pen = blue
    screen.text(ICON_DROP, PAD, y)
    screen.font = label_font
    screen.pen = white
    screen.text("%d%%" % round(weather["humidity"]), PAD + 22, y)

    wind = wind_speed(weather["wind"])
    wind_x = WIDTH / 2
    screen.font = font.weather
    screen.pen = blue
    screen.text(ICON_WIND, wind_x, y)
    screen.font = label_font
    screen.pen = white
    screen.text(wind, wind_x + 22, y)


def spinner(y):
    turned = badge.ticks / 1200 * 360
    screen.pen = color.rgb(255, 255, 255, 40)
    screen.shape(shape.arc(WIDTH / 2, y, 12, 15, 0, 360))
    screen.pen = phosphor
    screen.shape(shape.arc(WIDTH / 2, y, 12, 15, turned, turned + 90))


def draw_message(heading, saying, tone=muted, spinning=False):
    screen.font = condition_font
    screen.pen = white
    width = text_width(heading, condition_font)
    screen.text(heading, (WIDTH - width) / 2, 70)
    screen.font = label_font
    screen.pen = tone
    screen.text(saying, rect(PAD * 2, 104, WIDTH - PAD * 4, 70), align=image.CENTER)
    if spinning:
        spinner(190)


def clear():
    screen.pen = background
    screen.rectangle(0, 0, WIDTH, HEIGHT)


# --- loop ------------------------------------------------------------------

def update():
    global pending, next_fetch, connect_started

    clear()

    if MISSING:
        missing_details.show(MISSING, clear)
        return

    if not connect_started:
        wifi.connect(timeout=WIFI_TIMEOUT, retries=WIFI_RETRIES)
        connect_started = True

    if not wifi.is_connected():
        code, saying = wifi.status()
        wifi.connect()
        draw_header()
        if code < 0:
            draw_message("Can't connect", saying + "\n\nStill trying...", warning, True)
        else:
            draw_message("Connecting to Wi-Fi", saying, muted, True)
        return

    # the step drawn on the last frame runs now, so its page stays up while
    # the request blocks
    if pending:
        run_pending()

    if badge.pressed(BUTTON_SELECT):
        next_fetch = 0
    if badge.pressed(BUTTON_UP) or badge.pressed(BUTTON_DOWN):
        step = 1 if badge.pressed(BUTTON_DOWN) else -1
        prefs["units"] = (units_index() + step) % len(UNIT_MODES)
        State.save("weather", prefs)

    if badge.ticks >= next_fetch and pending is None:
        pending = fetch_weather

    draw_header()
    if weather:
        draw_weather()
        if fault:
            screen.font = small_font
            screen.pen = warning
            screen.text(fault, rect(PAD, HEIGHT - 40, WIDTH - PAD * 2, 16))
        elif pending:
            screen.font = small_font
            screen.pen = muted
            screen.text("updating...", PAD, HEIGHT - 40)
    elif pending:
        doing = "Finding you" if location is None else "Fetching weather"
        draw_message(doing, location["name"] if location else "Looking up your location",
                     muted, True)
    elif fault:
        draw_message("Weather error", fault + "\n\nSELECT to retry", warning)
    draw_footer()


run(update)
