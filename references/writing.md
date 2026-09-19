# Trip Optimizer — Plan Writing Standard

Plans are read by a traveler on a phone, often on the road. Write like a travel
writer, not a database. Prose, not fragments. Every pick must earn its place.

## The standard (non-negotiable)

1. **Prose, never fragments.** A segment's `details` is one or more full
   paragraphs, not telegram shards. Bad: "St. Vitus Cathedral, Old Royal
   Palace, Golden Lane. Timed entry, arrive by 9am." Good: a paragraph that
   says what it is, why it matters, and how to do it well.

2. **Every stop gets its "why".** History, a story, a technical marvel, a
   human detail — the thing that makes the traveler *feel* something before
   they arrive. A sight without a reason is a checkbox; rewrite it or cut it.

3. **Have opinions. Say what to skip.** Explicitly name the famous thing
   nearby that is NOT worth it, with the reason (rebuilt concrete, 2-hour
   queue for a photo rock, tourist-menu trap). A plan that endorses everything
   equally endorses nothing.

4. **Deliberate trade-offs get a callout.** When you skip the obvious famous
   option for a better quieter one, say so in a `>` blockquote: what you gave
   up, what you gain, and the escape hatch if the traveler disagrees.

5. **Food is sensory.** Taste, texture, temperature, smell, sound — and what
   makes THIS kitchen different from the generic version. "Svíčková, tank
   Pilsner" is a menu; "the dumpling soaks up the cream sauce until it
   collapses" is a reason to go. Contrast across cities when the trip earns it
   (three cities, three breakfast noodles, three personalities).

6. **Alternatives, labeled.** Each day carries 1–3 named alternatives
   (A/B/C or "弹性选项"): a rainy-day swap, a higher-energy option, a
   food backup. The traveler should never be stranded by weather or mood.

7. **Days have arcs.** Each day gets a `theme` (a subtitle, e.g. "外滩、弄堂
   与梧桐树") and a `transition` — one or two sentences connecting it to the
   previous day. Multi-city trips especially: name the emotional gear-shift
   ("the first five days you're a traveler; from tomorrow you're a returnee").

8. **Specific times, real logistics.** Segments carry `start_time`/`end_time`
   (e.g. 8:30–11:30), not "morning". Hotels get name + address + why this
   one. Transit gets mode, duration, and the sensory detail of the ride
   (what you see out the window is part of the trip).

9. **Budget where money moves.** Per-day or per-segment cost estimates in the
   traveler's currency. No one should wonder what a day costs.

10. **行前准备与后勤须知 is mandatory, not optional.** Every plan opens
    with it, before Day 1, with these sections (adapted to the trip; omit
    only what genuinely does not apply, never out of laziness):
    - 签证与入境 — entry rules per passport, transit-visa traps (e.g. a
      route that breaks a transit-visa zone), where to apply and lead times.
    - 支付与通讯 — how money moves locally (cash vs card vs local wallets,
      where to exchange, DCC traps), SIM/eSIM options, VPN if the country
      blocks services, the 2–3 must-install local apps (maps, ride-hailing,
      train booking, restaurant reviews) with what each is for.
    - 交通预订 — intercity booking: which app/site, how far ahead, train
      numbers if known (with the caveat that timetables change), foreign-
      passport gotchas at ticket machines.
    - 天气与穿着 — season-specific weather, what to pack, and per-city
      rainy-day pivots (which indoor backup replaces which outdoor plan).
    - 行李与住宿须知 — luggage strategy for the trip's transit pattern,
      hotel booking notes (room config, adjoining rooms for groups).
    - 旅行保险 — recommended coverage for the trip type.

11. **Write for the traveler, not anyone.** Reference their constraints,
    their people, their stakes. A plan that could be for anyone feels like it
    was written for no one.

## Language

Match the trip's `request_language` throughout. Chinese-language plans use
Simplified Chinese and Chinese-native sources (大众点评, 小红书, 马蜂窝);
verify restaurant names against current sources — restaurant turnover is fast
and a dead name in a plan is a broken promise.
