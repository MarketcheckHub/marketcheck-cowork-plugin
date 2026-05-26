---
name: dealership_group_enum
description: The 471-entry dealership_group_name enum that get_sold_summary validates against. Source-of-truth bundle for resolve_group_name.py.
type: reference
---

# `dealership_group_name` enum (471 entries)

**Source:** `mcp_server_tool_docs/get_sold_summary.md:73` — extracted by the build process and re-verified character-for-character.

**Format:** one name per line inside the fenced code block below. **Not** comma-separated. The reason: at least one canonical name (`Americas Car-mart, Inc.`) contains a literal comma, which would break naive comma-split parsing.

`scripts/resolve_group_name.py` reads this file via `splitlines()`, ignoring everything outside the fenced code block and skipping blank lines.

## Punctuation / casing quirks (the ones that bite)

- `Carmax` — single token, NOT "CarMax". Case-sensitive against the enum.
- `Carvana` — present.
- `AutoNation Inc.` — trailing period.
- `Group 1 Automotive Inc.` — leading digit + trailing period.
- `Lithia Motors Inc.`, `Penske Automotive Group Inc.`, `Sonic Automotive Inc.`, `Holman Automotive Group Inc.` — trailing period.
- `Asbury Automotive Group` — **no** trailing period (unlike most siblings).
- `#1 Cochran Automotive Group` — leading `#`.
- `Hall | Mileone Autogroup` — literal pipe character `|`.
- `Demontrond Auto Group's` — trailing apostrophe-s.
- `Americas Car-mart, Inc.` — embedded comma; reason for one-per-line format.
- `Hi-country Auto Group`, `Lyon-waugh Auto Group`, `Reedman-Toll Auto Group`, `Tuttle-Click Automotive Group`, `Titus-will Automotive Group` — hyphens with mixed case.
- `Dwayne Lane's Auto Family`, `Jeff D'ambrosio Chrysler Dodge Jeep Ram Downingtown`, `Morrie's Automotive Group`, `Nouri/shaver Automotive Group`, `O'steen Automotive Group`, `Rosatti/Plaza Auto Group`, `Groupe Spinelli's` — apostrophes and slashes.
- `DARCARS Automotive Group`, `DCH Auto Group`, `DICK HANNAH DEALERSHIPS`, `LAcarGuy Dealership Group`, `LaFontaine Automotive Group`, `ONE Automotive Group`, `RFJ Auto Partners Holdings Inc.`, `RML Automotive` — unusual capitalization preserved verbatim.

`get_sold_summary` rejects any value not in this enum and returns a >10 KB error string listing every valid name. The skill's resolution layer enforces enum membership BEFORE the call, so this error path is never hit in practice.

## The 471 canonical names

```
#1 Cochran Automotive Group
Abeloff Auto Group
Acra Automotive Group
Alan Jay Automotive Network
Allen Samuels Auto Group
All American Auto Group
All Roads
Alpha Auto Group
Alsop Auto Group
Americas Car-mart, Inc.
Ancira Enterprises
Anderson Automotive Group
Andy Mohr Automotive
Apple Automotive Group
Applewood Auto Group
Apple Used Autos
Arrigo Auto Group
Asbury Automotive Group
Atlantic Auto Group
AutoFair Automotive Group
AutoFocus Inc.
Autoinc Family Of Dealerships
Autoiq Dealership Network
Automotive Group
AutoNation Inc.
Autopark Mississauga
Autocanada
Auto Ranch Group
Autosaver Group
Awin Group Of Dealerships
Bacon Auto Country Inc.
Bailey Auto Group
Bakhtiari Auto Group
Balise Motor Sales Co.
Barnes Crossing Auto Group
Basil Family Dealerships
Baumann Auto Group
Baxter Auto Group
Bayird Dodge Chrysler Jeep Ram Of Kennett
Bayside Auto Group
Bayway Auto Group Inc.
Beaver County Auto
Bergeys
Berge Auto Group
Bergstrom Automotive
Berkshire Hathaway Automotive
Bernardi Auto Group
Bertera Auto Group
Betten Baker Auto Group
Bill Kay Auto Group
Bill Marsh Auto Group
Birchwood
Blaise Alexander Family Dealerships
Blasius Auto Group
Bob Baker Auto Group
Bob Johnson Auto Group
Bob Loquercio Auto Group
Bob Moore Auto Group
Bob Rohrman Auto Group
Bob Thomas Dealership
Bobby Rahal Automotive Group
Bommarito Automotive Group
Bomnin Automotive Group
Boucher Group Inc.
Bowers Automotive Group
Braman Dealerships
Brandon Steven Motors
Brinson Auto Group
Bronco Motors Family Of Dealerships
Brunswick Auto Mart
Burt Watson Auto Group
Butler Auto Group
Bycolonial Automotive
Byers Automotive Group
Calgary Motor Dealers Association
Canada One Auto Group
Capital Automotive Group
Capitol Expressway Auto Mall
Cardinale Automotive Group
Carlock Automotive Group
Carmax
Car Pros Automotive Group
Carr Auto Group
Carson Automotive Group
Carter Auto Family
Carter Cadillac
Carter Myers Automotive
Carvana
Casey
Castle Automotive Group
Cavender Auto Family
Centennial Auto Group
Central TX Autos
Chapman Automotive Group
Chapman Az
Chrysler Ca
Ciocca Dealerships
Clay Cooley Auto Group
Coad Family Of Dealerships
Coggin Automotive Group
Cole Automotive Group
Continental Motors Group
Cooper Auto Group
Coral Springs Auto Mall
Corwin Automotive Group
Coughlin Automotive
Courtesy Automotive Group
Cowell Auto Group
Crain Automotive Team
Criswell Automotive
Crossroads Cars
Crown Auto Group
Curry Automotive
DARCARS Automotive Group
DCH Auto Group
David Wilson Automotive Group
Davis Auto Group
Del Grande Dealer Group
Delaney Auto Group
Della Automotive Group
Demontrond Auto Group's
Dennis & Co. Auto Group
Dennis Dillon Automotive
Dick Smith Automotive Group
DICK HANNAH DEALERSHIPS
Dilawri Group
Dimmitt Automotive Group
Dobbs Family Automotive
Dolan Auto Group
Don Davis Auto Group
Downtown Autogroup
Dueck Auto Group
Dutch Miller
Dwayne Lane's Auto Family
Earnhardt Auto Centers
Ed Bozarth Inc.
Ed Morse Automotive Group
Ed Napleton Automotive Group
Ed Voyles Automotive Group
Elder Automotive Group
Empire Automotive Group
Envision Motors
Evans Dealer Group
Executive Auto Group
FRL Automotive
Fairfield Auto Group
Faulkner Automotive Group
Fayetteville Automall
Feldman Automotive Group
Ferman Automotive Group
Fields Auto Group
Findlay Automotive Group
Firelands Auto Group
Fitzgerald Auto Malls
Fletcher Auto Group
Fletcher Jones California
Foundation Auto Colorado
Fox Motors
Fred Beans Automotive Group
Friendship Automotive
Fusz Automotive Network
Future Automotive Group
Gain Group
Galpin Motors Inc.
Ganley Auto Group
Garber Management Group
Garcia Automotive Group
Gates Automotive Group
Gee Automotive Cos.
Georgica Auto Holdings
Germain Automotive Group
Germain Motor Co.
Gettel Automotive
Gilchrist Automotive
Giles Automotive
Gillman Cos.
Global Auto Mall
Glockner Family Of Dealerships
Go Yeomans
Goldstein Auto Group
Golling Automotive Group
Goodwin Motor Group
Graham Automall
Great Lakes Auto Group
Green Family Stores Inc.
Greenway Automotive
Grieco Automotive Group
Groupe Park Avenue
Groupe Spinelli's
Group 1 Automotive Inc.
Gunn Automotive Group
Gurley Leep Automotive
Hall | Mileone Autogroup
Hare Auto Group
Harnish Auto Family
Harris Auto Group
Harte Auto Group
Headquarter Automotive
Healey Brothers Automotive Group
Heartland Automotive
Heiser Automotive Group
Hendrick Automotive Group
Herb Chambers Cos.
Hertrich Family of Auto Dealerships
Hi-country Auto Group
Hiester Automotive Group
Hight Auto Group
Hiley Automotive Group
Hoffman Auto Group
Holiday Auto Group
Holler Classic Automotive Group
Holman Automotive Group Inc.
Hudson Auto Group
Huffines Auto Dealerships
Humberview Motorsports
Huston Automotive Group
Hutchinson Automotive Group
Ide Family Of Dealerships
Idea Auto Group
Island Auto Group
Jeff D'ambrosio Chrysler Dodge Jeep Ram Downingtown
Jeff Schmitt Auto Group
Jeff Wyler Automotive Family Inc.
Jim Butler Auto Group
Jim Ellis Automotive Group
Jim Koons Automotive Cos.
Jim Pattison Auto Group
Jim Shorkey Auto Group
Jimclick Automative Team
John Eagle Auto Group
John Elway Dealerships
Johnson Automotive
Joseph Auto Group
Kaizen Automotive Group
Kahlig Auto Group
Karl Auto Group
Keating Auto Group
Keeler Motor Car Company
Keffer Auto Group
Kelley Automotive Group
Kelly Automotive Group
Ken Ganley Automotive Group
Ken Garff Automotive Group
Kendall Auto Group
Kenwood Dealer Group Inc.
Kerry Automotive Group
Key Auto Group
Keyes Automotive Group
Khoury Group
Knight Automotive Group
Kocourek Automotive
Kody Holdings
Kot Auto Group
Krause Auto
Krause Auto Group
Kunes Auto Group
Kunes Country Auto Group
LAcarGuy Dealership Group
LaFontaine Automotive Group
Larry H. Miller Dealerships
Lasco Auto Group
Laurel Auto Group
Lally Auto Group
Lee Auto Malls
Legacy Automotive Group
Leggat Chevrolet Cadillac Buick Gmc Limited
Leith Cars
Lewis Automotive Group
Lia Auto Group
Lithia Motors Inc.
Lorensen Auto Group
Lupient Automotive Group
Luther Automotive Group
Lyon-waugh Auto Group
Mac Haik Auto Group
Mackey Auto Group
Maguire Family Of Dealerships
Malloy Automotive Group
Martin Management Group
Mathews Group
Matt Blatt
Matthews Auto Group
Maverick Motor Group
McCombs Automotive
McLarty Automotive Group
Mcgovern Automotive Group
Mckenna Cars
Mike Anderson Auto Group
Mike Maroone Colorado
Mike Shaw Automotive
Mileone Autogroup
Mills Automotive Group
Montrose Auto Group
Moore Automotive Team
Morgan Auto Group
Morris Group
Morrie's Automotive Group
Muller Auto Group
Mullinax Ford
Murgado Automotive Group
Murray Auto Group
Myers Automotive Group
Navarre Auto Group
Neil Huffman Automotive Group
New Country Motor Car Group
New Roads Automotive Group
Niello Company
Nielsen Automotive Group
Noarus Auto Group
Norm Reeves Auto Group
North Coast Auto Mall
North Hills Select
Nouri/shaver Automotive Group
O'steen Automotive Group
ONE Automotive Group
Olympic Auto Group
One Automotive
Open Road Auto Group
Openroad Dealership
Oremor Automotive Group
Orr Auto Group
Ourisman Automotive Group
Page Auto Group
Palladino Auto Group
Paramount Automotive
Passport Auto Group
Pearson Signature Dealerships
Pecheles Automotive
Pellegrino Chrysler Jeep
Peltier Auto Group
Penske Automotive Group Inc.
Performance Automotive Network
Performance Protection Dealer
Perrysburg Auto Mall
Peterson Auto Group
Phaeton Automotive Group
Phil Long Dealerships
Phil Smith Automotive Group
Piazza Auto Group
Piercey Automotive Group
Plattner Automotive Group
Plattners Punta Gorda Auto Max
Poage Auto Group
Pohanka Automotive Group
Potamkin Automotive
Power Auto Group
Premier Automotive
Preston Automotive Group
Prestige Automotive Group
Prestige Group
Price Family Dealerships
Principle Auto
Priority Auto Group
Purdy Group
Puyallup Cars
Quirk Auto Group
RFJ Auto Partners Holdings Inc.
RML Automotive
Rafih Auto Group
Rairdon Automotive Group
Rallye Motor Company
Rallye Motors Auto Group
Ramsey Auto Group
Ray Catena Motor Car Corp.
Ray Skillman Auto Group
Rds Automotive Group
Reedman-Toll Auto Group
Respect Auto Group
Revolution Auto Group
Ricart
Richardson Auto Group
Rick Case Automotive Group
Ridings Auto Group
Right Drive
Riverside Auto Group
Roimotors Auto Group
Romano Auto Dealerships
Romeo Auto Group
Ron Marhofer Auto Family
Rosatti/Plaza Auto Group
Rosenthal Automotive Organization
Ross Auto Group
Rrr Automotive Group
Rusnak Auto Group
Russ Darrow Group Inc.
Safford Automotive Group
Sames Automotive Group
Sam Pack Automotive Group
Sandy Sansing Automotive
Sansone Auto Network
Sarchione Chevrolet
Schomp Automotive Group
Schumacher Chevrolet Auto Group
Serpentini Auto Group
Serra Automotive Group
Serra Automotive Inc.
Servco Pacific Inc.
Seth Wadley Auto Group
Shaker Automotive Group
Sheehy Auto Stores
Shelly Automotive Group
Shottenkirk Automotive Group
Shults Auto Group
Sid Dillon
Sierra Auto Group
Simmons-rockwell
Simpson Automotive Group
Sloane Automotive Group
Solomon Auto Group
Sonic Automotive Inc.
Sport Durst Automotive Group
Springs Automotive Group Platte Ave
Stanley Auto Group
Stead Automotive Group
Steele Auto Group
Step One Automotive Group
Stewart Management Group Inc.
Suburban Collection
Sullivan Automotive Group
Summit Automotive
Sunset Automotive Group
Sunwise Auto Group
Superior Automotive Group
Sutherlin Automotive Group
Svg Auto Group
Swickard Auto Group
Szott Auto Group
Tasca Automotive Group
Taylor Automotive Family
Ted Moore Auto Group
The Casey Auto Group
The Jim Whetstone Auto Group
The Wyant Group
Thigpen Automotive Group
Thomas Automotive
Tim Dahle Auto Group
Tim Short Auto Group
Timbrook Automotive
Titus-will Automotive Group
Tricor Automotive Group Inc
Trotman Auto Group
Tuttle-Click Automotive Group
Uftring Automall
Upstate Auto Group
Us 24 Auto Group
Usa Automotive
Valenti Family Of Dealerships
Valley Auto Group
Van Horn Automotive Group
Vickar Automotive Group
Victory Automotive Group
Vip Automotive Group
Voss Auto Network
Walser Automotive Group
Weimer Auto Group
Weins Auto Group
West-Herr Automotive Group Inc.
White Family Dealerships
Wilde Automotive Group
Winter Auto Group
Wood Automotive Group
Woodhouse Auto Family
World Auto Group
World Car Auto Group
World Class Automotive Group
Yark Automotive Group Inc.
Young Automotive Group
Zanchin Auto Group
Zeigler Auto Group
Zimbrick
Zt Motors Group
```
