# School identity: colors and ballparks

Built 2026-10-10 by `scripts/build_school_identity.py` into `app/school_identity.csv` (display only: the engine never reads it; its park factors are still the engine's own draw, not these ballparks).

Sources: colors from Wikipedia's `Module:College color/data` (the table every college sports infobox draws from; each row cites the school's brand guide, recorded as `color_source`), confidence B; ballpark, capacity and city from the program's Wikipedia baseball article infobox, confidence B; D when missing. www.ncaa.com was not used.

Rows: 307; both colors and a ballpark: 307; D rows: 0.

## D rows (check these)

None.

## Ballparks renamed recently (2023 or later)

Found by reading each ballpark's own Wikipedia article lead for "renamed" / "formerly" with a year of 2023 or later; a rename the article does not state in its lead is not caught, so the list is a lead, not a proof.

| School | Ballpark | Note |
|---|---|---|
| Michigan State | Jeff Ishbia Field at McLane Stadium | The field, formerly named after MSU baseball coach John Kobs, was renamed for Jeff Ishbia in September 2024, following a $10 million donation to the school from his son, Justin Ishbia, and daughter-in-law. |
| Oral Roberts | Chapman Park | In 2025, the venue was renovated and renamed Chapman Park following a donation from the Chapman Foundation. |
| Louisiana-Monroe | Lou St. Amant Field | The stadium was opened in 1983 and was known as Warhawk Field until 2023, when it was renamed for ULM head coach Lou St. |
| Youngstown State | 7 17 Credit Union Field at Eastwood | The stadium was formerly known as Cafaro Field from 1999 to 2003, and Eastwood Field from 2003 to 2026. |

## 2025 conference tournament venues (`app/conference_tournaments.csv`)

Shown only when the 2025 tournament article confirms the site; otherwise the app says "Conference tournament" with no venue.

| Conference | Venue | City | Confidence |
|---|---|---|---|
| ACC | Durham Bulls Athletic Park | Durham, North Carolina | B |
| ASUN | Melching Field at Conrad Park | DeLand, Florida | B |
| America East | Mahaney Diamond | Orono, Maine | B |
| Atlantic 10 | Capital One Park | Tysons, Virginia | B |
| Big 12 | Globe Life Field | Arlington, Texas | B |
| Big East | Prasco Park | Mason, Ohio | B |
| Big South | Truist Point | High Point, North Carolina | B |
| Big Ten | Charles Schwab Field Omaha | Omaha, Nebraska | B |
| Big West | Goodwin Field | Fullerton, CA | B |
| CAA | CofC Baseball Stadium at Patriots Point | Mount Pleasant, SC | B |
| CUSA | Liberty Baseball Stadium | Lynchburg, Virginia | B |
| Horizon | Nischwitz Stadium | Fairborn, Ohio | B |
| Ivy League | George H. W. Bush Field | New Haven, CT | B |
| MAAC | Clover Stadium | Pomona, New York | B |
| MAC | Crushers Stadium | Avon, Ohio | B |
| MVC | Duffy Bass Field | Normal, Illinois | B |
| Mountain West | Sloan Park | Mesa, Arizona | B |
| NEC | Heritage Financial Park | Wappingers Falls, New York | B |
| OVC | Mtn Dew Park | Marion, Illinois | B |
| Patriot | Fitton Field | Worcester, Massachusetts | B |
| SEC | Hoover Metropolitan Stadium | Hoover, AL | B |
| SWAC | Rickwood Field | Birmingham, Alabama | B |
| SoCon | Fluor Field at the West End | Greenville, SC | B |
| Southland | Husky Field | Houston, Texas | B |
| Summit League | Tal Anderson Field | Omaha, Nebraska | B |
| Sun Belt | Riverwalk Stadium | Montgomery, Alabama | B |
| The American | BayCare Ballpark | Clearwater, FL | B |
| WAC | Hohokam Stadium | Mesa, Arizona | B |
| WCC | Las Vegas Ballpark | Las Vegas, Nevada | B |
| DI Independent |  |  | D |

## Secondary colors

`primary` and `secondary` are the first two official colors as the brand guide lists them (white or black is often the official second color). `alt` is the first non-white, non-black color after the primary, which the app uses where a visible second color is needed (a dark primary on the dark background; two similar primaries on one scoreboard).
