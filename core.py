from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

COUNTRIES = tuple(country for country in """
Afghanistan
Albania
Algeria
Andorra
Angola
Antigua and Barbuda
Argentina
Armenia
Australia
Austria
Azerbaijan
Bahamas
Bahrain
Bangladesh
Barbados
Belarus
Belgium
Belize
Benin
Bhutan
Bolivia
Bosnia and Herzegovina
Botswana
Brazil
Brunei
Bulgaria
Burkina Faso
Burundi
Cabo Verde
Cambodia
Cameroon
Canada
Central African Republic
Chad
Chile
China
Colombia
Comoros
Costa Rica
Croatia
Cuba
Cyprus
Czechia
Democratic Republic of the Congo
Denmark
Djibouti
Dominica
Dominican Republic
Ecuador
Egypt
El Salvador
Equatorial Guinea
Eritrea
Estonia
Eswatini
Ethiopia
Fiji
Finland
France
Gabon
Gambia
Georgia
Germany
Ghana
Greece
Grenada
Guatemala
Guinea
Guinea-Bissau
Guyana
Haiti
Honduras
Hungary
Iceland
India
Indonesia
Iran
Iraq
Ireland
Israel
Italy
Ivory Coast
Jamaica
Japan
Jordan
Kazakhstan
Kenya
Kiribati
Kosovo
Kuwait
Kyrgyzstan
Laos
Latvia
Lebanon
Lesotho
Liberia
Libya
Liechtenstein
Lithuania
Luxembourg
Madagascar
Malawi
Malaysia
Maldives
Mali
Malta
Marshall Islands
Mauritania
Mauritius
Mexico
Micronesia
Moldova
Monaco
Mongolia
Montenegro
Morocco
Mozambique
Myanmar
Namibia
Nauru
Nepal
Netherlands
New Zealand
Nicaragua
Niger
Nigeria
North Korea
North Macedonia
Norway
Oman
Pakistan
Palau
Palestine
Panama
Papua New Guinea
Paraguay
Peru
Philippines
Poland
Portugal
Qatar
Republic of the Congo
Romania
Russia
Rwanda
Saint Kitts and Nevis
Saint Lucia
Saint Vincent and the Grenadines
Samoa
San Marino
Sao Tome and Principe
Saudi Arabia
Senegal
Serbia
Seychelles
Sierra Leone
Singapore
Slovakia
Slovenia
Solomon Islands
Somalia
South Africa
South Korea
South Sudan
Spain
Sri Lanka
Sudan
Suriname
Sweden
Switzerland
Syria
Taiwan
Tajikistan
Tanzania
Thailand
Timor-Leste
Togo
Tonga
Trinidad and Tobago
Tunisia
Turkey
Turkmenistan
Tuvalu
UAE
Uganda
Ukraine
United Kingdom
United States
Uruguay
Uzbekistan
Vanuatu
Vatican City
Venezuela
Vietnam
Yemen
Zambia
Zimbabwe
""".strip().splitlines())
GRADES = tuple(range(1, 13))
SUBJECTS = ("Math", "Science", "English", "Arabic", "French", "Reading", "Homework help")
LANGUAGES = ("Arabic", "English", "French")
PREFERRED_TIMEZONES = (
    "Asia/Damascus", "Asia/Dubai", "UTC", "Asia/Riyadh", "Asia/Beirut",
    "Asia/Amman", "Asia/Kuwait", "Asia/Qatar", "Africa/Cairo", "Europe/London",
    "Europe/Paris", "America/New_York", "America/Chicago", "America/Denver",
    "America/Los_Angeles", "Asia/Karachi", "Asia/Kolkata", "Asia/Singapore",
    "Australia/Sydney",
)
TIMEZONES = PREFERRED_TIMEZONES + tuple(sorted(available_timezones() - set(PREFERRED_TIMEZONES)))
TIMEZONE_LABELS = {
    "Asia/Damascus": "Syria — Damascus time",
    "Asia/Dubai": "UAE — Dubai time",
    "UTC": "UTC — Coordinated Universal Time",
    "Asia/Riyadh": "Saudi Arabia — Riyadh time",
    "Asia/Beirut": "Lebanon — Beirut time",
    "Asia/Amman": "Jordan — Amman time",
    "Asia/Kuwait": "Kuwait — Kuwait City time",
    "Asia/Qatar": "Qatar — Doha time",
    "Africa/Cairo": "Egypt — Cairo time",
    "Europe/London": "United Kingdom — London time",
    "Europe/Paris": "France — Paris time",
    "America/New_York": "USA — Eastern time",
    "America/Chicago": "USA — Central time",
    "America/Denver": "USA — Mountain time",
    "America/Los_Angeles": "USA — Pacific time",
    "Asia/Karachi": "Pakistan — Karachi time",
    "Asia/Kolkata": "India — Kolkata time",
    "Asia/Singapore": "Singapore time",
    "Australia/Sydney": "Australia — Sydney time",
}
WEEKDAYS = {name: index for index, name in enumerate(("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"))}


def public_name(value: str) -> str:
    parts = value.strip().split()
    if not parts:
        return "Tutor"
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[-1][0].upper()}."


def valid_timezone(value: str) -> str:
    timezone_name = str(value or "").strip()
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Choose a valid timezone.") from exc
    return timezone_name


def timezone_label(value: str) -> str:
    return TIMEZONE_LABELS.get(value, value.replace("_", " "))


def format_slot(slot: dict, timezone_name: str | None = None) -> str:
    timezone_name = timezone_name or str(slot.get("timezone") or "UTC")
    try:
        local_zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        local_zone, timezone_name = timezone.utc, "UTC"
    start = datetime.fromisoformat(str(slot["starts_at"]).replace("Z", "+00:00")).astimezone(local_zone)
    end = datetime.fromisoformat(str(slot["ends_at"]).replace("Z", "+00:00")).astimezone(local_zone)
    return f"{start:%A, %d %B %Y} · {start:%H:%M}–{end:%H:%M} · {timezone_label(timezone_name)}"


def valid_meeting_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Enter a complete, secure https lesson link.")
    return value


def visible_upcoming_requests(rows: list[dict], now: datetime | None = None) -> list[dict]:
    """Return active and future-cancelled lessons that still matter to the user."""
    current = now or datetime.now(timezone.utc)
    visible: list[dict] = []
    for row in rows:
        slot = row.get("availability_slots") or {}
        if isinstance(slot, list):
            slot = slot[0] if slot else {}
        try:
            ends_at = datetime.fromisoformat(str(slot["ends_at"]).replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            continue
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc)
        if ends_at > current and row.get("status") in {"requested", "confirmed", "cancelled"}:
            visible.append(row)
    def start_value(row: dict) -> str:
        slot = row.get("availability_slots") or {}
        if isinstance(slot, list):
            slot = slot[0] if slot else {}
        return str(slot.get("starts_at", ""))

    return sorted(visible, key=start_value)


def build_recurring_slots(tutor_id: str, first_date: date, weekdays: list[int], weeks: int, window_start: time, window_end: time, lesson_minutes: int, break_minutes: int, timezone_name: str) -> list[dict]:
    if not weekdays:
        raise ValueError("Choose at least one weekday.")
    if weeks not in range(1, 13):
        raise ValueError("Choose between 1 and 12 weeks.")
    if lesson_minutes not in (30, 45, 60) or break_minutes not in (0, 10, 15, 30):
        raise ValueError("Choose one of the available lesson and break lengths.")
    timezone_name = valid_timezone(timezone_name)
    if window_end <= window_start:
        raise ValueError("The end time must be after the start time.")
    local_zone = ZoneInfo(timezone_name)
    payload: list[dict] = []
    for offset in range(weeks * 7):
        slot_date = first_date + timedelta(days=offset)
        if slot_date.weekday() not in weekdays:
            continue
        cursor = datetime.combine(slot_date, window_start, tzinfo=local_zone)
        boundary = datetime.combine(slot_date, window_end, tzinfo=local_zone)
        while cursor + timedelta(minutes=lesson_minutes) <= boundary:
            ending = cursor + timedelta(minutes=lesson_minutes)
            payload.append({"tutor_id": tutor_id, "starts_at": cursor.astimezone(timezone.utc).isoformat(), "ends_at": ending.astimezone(timezone.utc).isoformat(), "timezone": timezone_name, "status": "open"})
            cursor = ending + timedelta(minutes=break_minutes)
    if not payload:
        raise ValueError("Those settings do not create any lesson times.")
    return payload
