# School display names and abbreviations (app-side, display only)

Built 2026-10-09 by `scripts/build_school_names.py` from the identity file `data/schools/schools.csv` (engine PR #17): the
full school name expands the NCAA short name (St. to State, Mich. to Michigan, ...) with overrides for names that are not a
simple expansion; the abbreviation is a 2-5 letter form for tight spaces (marks, line scores, lineup tabs), unique across the 307.
Nothing here reaches the engine: ids and saves keep the engine's teams. Table: `app/school_names.csv`.

- 307 schools; 209 abbreviations taken from common use; 98 chosen here (ticker style) for the owner to check.
- The abbreviation clashes were resolved with the school's own alternate form: Kennesaw St. KENN (Kansas St. keeps KSU), Wichita St. WICH
  (Washington St. keeps WSU), South Dakota St. SDST (San Diego St. keeps SDSU), San Francisco SF (South Fla. keeps USF), Saint Joseph's SJOE
  (St. John's keeps SJU), Northern Colo. UNCO (North Carolina keeps UNC), Tennessee Tech TNTC (Texas Tech keeps TTU), Jacksonville St. JVST
  (Jackson St. keeps JKST), Charleston So. CHSO, Louisiana ULL.

## Abbreviations to check (guessed)

| tid | School | Full name | Abbr |
|---|---|---|---|
| 2 | Air Force | Air Force | AF |
| 3 | Akron | Akron | AKR |
| 7 | Alcorn | Alcorn State | ALCN |
| 13 | Arkansas St. | Arkansas State | ARST |
| 18 | Ball St. | Ball State | BALL |
| 20 | Bellarmine | Bellarmine | BELL |
| 21 | Belmont | Belmont | BEL |
| 23 | Binghamton | Binghamton | BING |
| 26 | Bradley | Bradley | BRAD |
| 27 | Brown | Brown | BRWN |
| 28 | Bryant | Bryant | BRY |
| 29 | Bucknell | Bucknell | BUCK |
| 30 | Butler | Butler | BUT |
| 33 | Cal Poly | Cal Poly | CP |
| 37 | Campbell | Campbell | CAMP |
| 38 | Canisius | Canisius | CAN |
| 42 | Charleston So. | Charleston Southern | CHSO |
| 48 | Columbia | Columbia | COLU |
| 49 | Coppin St. | Coppin State | COPP |
| 50 | Cornell | Cornell | COR |
| 53 | Dartmouth | Dartmouth | DART |
| 54 | Davidson | Davidson | DAV |
| 55 | Dayton | Dayton | DAY |
| 56 | Delaware | Delaware | DEL |
| 65 | Evansville | Evansville | EVAN |
| 69 | Fairfield | Fairfield | FAIR |
| 74 | Fordham | Fordham | FOR |
| 80 | Georgetown | Georgetown | GTWN |
| 90 | Hofstra | Hofstra | HOF |
| 91 | Holy Cross | Holy Cross | HC |
| 95 | Illinois St. | Illinois State | ILST |
| 97 | Indiana St. | Indiana State | INST |
| 98 | Iona | Iona | IONA |
| 102 | Jacksonville St. | Jacksonville State | JVST |
| 106 | Kennesaw St. | Kennesaw State | KENN |
| 107 | Kent St. | Kent State | KENT |
| 113 | Lafayette | Lafayette | LAF |
| 114 | Lamar University | Lamar | LAM |
| 115 | Le Moyne | Le Moyne | LEM |
| 116 | Lehigh | Lehigh | LEH |
| 118 | Lindenwood | Lindenwood | LIN |
| 122 | Longwood | Longwood | LONG |
| 124 | Louisiana Tech | Louisiana Tech | LT |
| 126 | Maine | Maine | ME |
| 127 | Manhattan | Manhattan | MAN |
| 128 | Marist | Marist | MRST |
| 129 | Marshall | Marshall | MRSH |
| 134 | Mercer | Mercer | MER |
| 135 | Mercyhurst | Mercyhurst | MERC |
| 136 | Merrimack | Merrimack | MRMK |
| 138 | Miami (OH) | Miami (OH) | M-OH |
| 142 | Milwaukee | Milwaukee | MILW |
| 147 | Missouri St. | Missouri State | MOST |
| 148 | Monmouth | Monmouth | MONM |
| 149 | Morehead St. | Morehead State | MORE |
| 150 | Mount St. Mary's | Mount St. Mary's | MSM |
| 151 | Murray St. | Murray State | MUR |
| 161 | Niagara | Niagara | NIAG |
| 162 | Nicholls | Nicholls | NICH |
| 163 | Norfolk St. | Norfolk State | NSU |
| 169 | Northern Colo. | Northern Colorado | UNCO |
| 174 | Oakland | Oakland | OAK |
| 175 | Ohio | Ohio | OHIO |
| 180 | Ole Miss | Ole Miss | MISS |
| 185 | Pacific | Pacific | PAC |
| 188 | Pepperdine | Pepperdine | PEPP |
| 190 | Portland | Portland | PORT |
| 192 | Presbyterian | Presbyterian | PRES |
| 196 | Queens (NC) | Queens | QUNC |
| 197 | Quinnipiac | Quinnipiac | QUIN |
| 198 | Radford | Radford | RAD |
| 201 | Richmond | Richmond | RICH |
| 202 | Rider | Rider | RID |
| 207 | Sacred Heart | Sacred Heart | SHU |
| 208 | Saint Joseph's | Saint Joseph's | SJOE |
| 211 | Saint Peter's | Saint Peter's | SPU |
| 213 | Samford | Samford | SAM |
| 216 | San Francisco | San Francisco | SF |
| 219 | Seattle U | Seattle | SEA |
| 220 | Seton Hall | Seton Hall | HALL |
| 221 | Siena | Siena | SIE |
| 224 | South Dakota St. | South Dakota State | SDST |
| 232 | Southern U. | Southern | SOU |
| 238 | Stonehill | Stonehill | STON |
| 241 | Tarleton St. | Tarleton State | TAR |
| 243 | Tennessee Tech | Tennessee Tech | TNTC |
| 249 | The Citadel | The Citadel | CIT |
| 250 | Toledo | Toledo | TOL |
| 251 | Towson | Towson | TOW |
| 255 | UAlbany | Albany | ALB |
| 274 | USC Upstate | USC Upstate | UPST |
| 280 | Utah Tech | Utah Tech | UTU |
| 284 | Valparaiso | Valparaiso | VALP |
| 289 | Wagner | Wagner | WAG |
| 299 | Wichita St. | Wichita State | WICH |
| 301 | Winthrop | Winthrop | WIN |
| 302 | Wofford | Wofford | WOF |
| 303 | Wright St. | Wright State | WRST |

## Full names that differ from the identity file's short name

| Short (identity file) | Full (display) |
|---|---|
| A&M-Corpus Christi | Texas A&M-Corpus Christi |
| Alabama St. | Alabama State |
| Alcorn | Alcorn State |
| App State | Appalachian State |
| Arizona St. | Arizona State |
| Ark.-Pine Bluff | Arkansas-Pine Bluff |
| Arkansas St. | Arkansas State |
| Army West Point | Army |
| Ball St. | Ball State |
| CSU Bakersfield | Cal State Bakersfield |
| CSUN | Cal State Northridge |
| Cal St. Fullerton | Cal State Fullerton |
| Central Ark. | Central Arkansas |
| Central Conn. St. | Central Connecticut State |
| Central Mich. | Central Michigan |
| Charleston So. | Charleston Southern |
| Col. of Charleston | College of Charleston |
| Coppin St. | Coppin State |
| DBU | Dallas Baptist |
| Delaware St. | Delaware State |
| ETSU | East Tennessee State |
| Eastern Ill. | Eastern Illinois |
| Eastern Ky. | Eastern Kentucky |
| Eastern Mich. | Eastern Michigan |
| FDU | Fairleigh Dickinson |
| FGCU | Florida Gulf Coast |
| FIU | Florida International |
| Fla. Atlantic | Florida Atlantic |
| Florida St. | Florida State |
| Fresno St. | Fresno State |
| Ga. Southern | Georgia Southern |
| Georgia St. | Georgia State |
| Illinois St. | Illinois State |
| Indiana St. | Indiana State |
| Jackson St. | Jackson State |
| Jacksonville St. | Jacksonville State |
| Kansas St. | Kansas State |
| Kennesaw St. | Kennesaw State |
| Kent St. | Kent State |
| LIU | Long Island |
| LMU (CA) | Loyola Marymount |
| LSU New Orleans | New Orleans |
| Lamar University | Lamar |
| Long Beach St. | Long Beach State |
| Miami (FL) | Miami |
| Michigan St. | Michigan State |
| Middle Tenn. | Middle Tennessee |
| Mississippi St. | Mississippi State |
| Mississippi Val. | Mississippi Valley State |
| Missouri St. | Missouri State |
| Morehead St. | Morehead State |
| Murray St. | Murray State |
| N.C. A&T | North Carolina A&T |
| NIU | Northern Illinois |
| New Mexico St. | New Mexico State |
| Norfolk St. | Norfolk State |
| North Ala. | North Alabama |
| North Dakota St. | North Dakota State |
| Northern Colo. | Northern Colorado |
| Northern Ky. | Northern Kentucky |
| Northwestern St. | Northwestern State |
| Ohio St. | Ohio State |
| Oklahoma St. | Oklahoma State |
| Oregon St. | Oregon State |
| Penn St. | Penn State |
| Prairie View | Prairie View A&M |
| Queens (NC) | Queens |
| SFA | Stephen F. Austin |
| SIUE | SIU Edwardsville |
| Sacramento St. | Sacramento State |
| Saint Mary's (CA) | Saint Mary's |
| San Diego St. | San Diego State |
| San Jose St. | San Jose State |
| Seattle U | Seattle |
| South Dakota St. | South Dakota State |
| South Fla. | South Florida |
| Southeast Mo. St. | Southeast Missouri State |
| Southeastern La. | Southeastern Louisiana |
| Southern California | USC |
| Southern Ill. | Southern Illinois |
| Southern Ind. | Southern Indiana |
| Southern Miss. | Southern Miss |
| Southern U. | Southern |
| St. John's (NY) | St. John's |
| St. Thomas (MN) | St. Thomas |
| Tarleton St. | Tarleton State |
| Texas St. | Texas State |
| UAlbany | Albany |
| UIW | Incarnate Word |
| ULM | Louisiana-Monroe |
| UMES | Maryland Eastern Shore |
| UNCW | UNC Wilmington |
| Washington St. | Washington State |
| West Ga. | West Georgia |
| Western Caro. | Western Carolina |
| Western Ill. | Western Illinois |
| Western Ky. | Western Kentucky |
| Western Mich. | Western Michigan |
| Wichita St. | Wichita State |
| Wright St. | Wright State |
| Youngstown St. | Youngstown State |
