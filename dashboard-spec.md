# Health dashboard: handoff for Don (v0.1, work in progress)

**From:** Arnold (coach). **For:** Don (design). **Owner:** me, 41.
**Data:** `data.json` in this repo, published for viewing only. Times are local wall-clock times with no UTC offset. Use the `days` cycle as the unit and `cycle_start` as the x-axis.

## Design intent
- **Brand:** the Arnold Institute of Broscience, with rowing and swimming at its heart. It should feel motivating, not clinical.
- **Lungs:** frame the lung metrics as *levers you can pull*, like breathing rate, SpO2 and cardio fitness. Never track or message about this topic.
- **What comes first:** mobile first, and the first screen answers "how am I today, and what should I do?"

## v1 scope (small)
### Panel 1: Today card
- **Shows:** big recovery % with a green, yellow or red ring, RHR, HRV, and last sleep hours.
- **One-line coach call:** "row easy 30" if recovery is under 34%, "full plan" if it's 67% or more, and "plan as written" otherwise. Arnold writes the copy.
- **Reads:** the last element of `days` where `recovery_pct` isn't null, using `recovery_pct`, `rhr`, `hrv_ms`, `main_sleep_h`, `nap_h`, `total_sleep_h` and `cycle_start`.

### Panel 2: Road to 49 (hero motivator)
- **Shows:** a line chart of `rhr` per cycle, with a 7-cycle rolling average.
- **Lines and bands:** a horizontal goal line at **49**, plus a faint "personal best" marker (min `rhr`, currently 54).
- **Optional background:** shaded bands from `reference_bands.rhr.bands`. Label them "general reference".
- **Footer:** "X bpm to go", worked out as 7-cycle average − 49.

### Panel 3: Sleep, the big lever
- **Chart:** stacked bars per cycle, with `main_sleep_h` solid and `nap_h` lighter.
- **Overlay:** a dot for `recovery_pct` on a second axis, plus a 7 h target line.
- **Small stats:** `sleep_consistency_pct`, `sleep_eff_pct`, and a bedtime/wake strip (`bedtime` and `wake`, from `sleeps[]` `start`/`end`).
- **Insight chip (from my data):** read `insights.sleep_vs_recovery`. Show a bucket only when `show` is true (n ≥ 5). Default copy: "Longer main sleep, higher recovery (r = 0.80, 30 nights)", then the shown buckets, e.g. "4.5–6 h → 64% · under 3 h → 15%". Never show a bucket with n < 5 as a claim.

### Panel 4: Training log (rows and swims first)
- **Chart:** a weekly bar chart of minutes by sport (`workouts[].sport`, `minutes`, `date`), with rowing and swimming in hero colours and yoga and other activity muted.
- **Streak counter:** "30-minute rows" counts the sessions where `sport == "rowing"` and `minutes >= 30`. There's also a swims-this-week count.
- **Per-workout detail:** an HR zone bar from `zones_min`. For rows, add a **"steady check"** that is green if most minutes are in zones 1–2. WHOOP zones use **heart-rate reserve**, not % of max: with max 180 and RHR ~59, zone 1 ≈ 107–132 and zone 2 ≈ 132–144 bpm. Read `hr_zones` (the old `hr_zones_bpm_from_max_180` key is deprecated but now carries the corrected values). My one row so far was 18% in zones 1–2, mostly zones 3–4.

### Panel 5: Lung levers
- **Small multiples:** `resp_rate` (normal 12–20) and `spo2_pct` (WHOOP overnight, normal 95–100), each with its own 7-day average.
- **Later:** HRV can go here too as "engine".
- **Fingertip readings:** when `manual_logs.spo2_fingertip` has entries, overlay them as dots.
- **Tone:** "your lungs are getting stronger", about levers rather than problems.

### Today card: coach call and status override (v1)
- Read `status_active` (active entries from `manual_logs.status` covering today). If one exists, use `coach_copy.status[flag]` **instead of** the recovery-based call, and show its `note` as a small line.
- Otherwise: `recovery_pct` null → `coach_copy.pending`; < 34 → `red`; 34–66 → `amber`; ≥ 67 → `green`. Each entry has `title` and `body`.
- Current status (Oct 28): `recovery_day`, "Post-illness, no erg until seat soreness clears; swim easy."
- An ongoing cycle's recovery, RHR, HRV, SpO2, breathing rate and sleep are already final; only strain, steps and workouts are still accumulating. Put the "in progress" label on those, not on the recovery-side metrics.

## v1.1+ (later, once manual logging exists)
- **Blood pressure:** from the Omron cuff, `manual_logs.blood_pressure`, with morning and evening readings, 2 readings each, plotted as the average. Use a dual line for systolic and diastolic, with reference shading at 120/80 and 130/80 (general reference). Baseline week daily, then 2–3 days a week.
- **Body weight:** from `manual_logs.body_weight`. The WHOOP profile starts it at 85.3 kg. Show a weekly trend, not daily noise.
- **Erg metrics:** from `manual_logs.erg`. Track meters, average split per 500 m, stroke rate and average HR, plus a "same HR, faster split" chart. That's the aerobic fitness win.
- **Swim:** from `manual_logs.swim`. Track meters per session and the weekly total.
- **Bug/illness flag:** a skin temp more than +0.5 °C over baseline, together with resp rate more than +1.5 over baseline. In my data this matched Oct 24 and Oct 26.
- **Correlation corner:** "what moves your recovery", with simple bars of r values (main sleep, REM, prior-day strain), recomputed monthly.
- **Badges:** first row under 2:10/500 in zone 2, a 4-swim week, a 7-day sleep-consistency streak, and RHR 52/50/49 milestones.

## Data notes for building
- **Cycles:** sometimes 2 per calendar date, because I sleep in the afternoon or evening. Don't group by `date`; key on `cycle_start`.
- **Last cycle:** it may be `ongoing: true`, with partial sleep and steps. Mark it as "in progress".
- **Missing values:** `spo2_pct` can be null (Oct 26). The first cycle (Sep 27) has no recovery.
- **Notes:** `days[].note` holds Arnold's annotations (bug start, spikes). Show them as chart markers.
- **Manual log schemas:** these sit in `manual_logs._schema`. Arnold will fill the logs from my photos and messages.
- **Refresh:** pull from WHOOP (outside this repo), then `python3 build.py && ./run_all.sh`. `build.py` merges every WHOOP pull and `manual.json`; edit `manual.json` (status, logs, annotations, coach copy), never `data.json`.
- **Long cycles:** a cycle can run 30–41 h when I only nap between main sleeps (Sep 29 and Oct 11–13). Those carry an automatic `note`.
- **Consistency:** `sleep_consistency_pct` is null for the first three nights (WHOOP calibrating). Show a gap, not zero.

## Open questions for Don and me
1. What format: a single HTML file opened locally, or a PDF snapshot each Sunday?
2. Dark mode for 3 AM wake-ups?
3. Which hero metric should sit at the top: recovery or the Road to 49?

## v1.2: bands on every metric
Source of truth: `manual.json` → `reference_bands` (bands + sources) and `goals`; `build.py` adds each metric's live `current` and category to `data.json`. Don't hard-code bands in the page.

- `data.json.reference_bands.<metric>` for: `rhr, hrv, recovery, sleep_total, sleep_efficiency, sleep_consistency, sleep_performance, resp_rate, spo2_overnight, spo2_fingertip, skin_temp, blood_pressure, day_strain, weekly_cardio, steps, bmi, waist_to_height, vo2max, erg_2k, erg_split_500`.
  - `label, unit, group` (heart|recovery|sleep|lungs|activity|body|fitness), `better` (higher|lower|range|match_recovery).
  - `source.label`, `source.url`, optional `source.extra_urls`, optional `note`.
  - `bands[]`, lowest to highest value: `{min, max, label, tone}`. `min` is inclusive, `max` is exclusive, and `null` means open-ended. `tone` is good|ok|watch|flag and drives the colour.
    - `blood_pressure` bands use `sys_min/sys_max/dia_min/dia_max` plus a `rule` string (the worse of sys or dia wins).
    - `skin_temp` bands are my own baseline ± SD, rebuilt every run (`baseline.median_c, sd_c`), not population bands.
  - `current`: `{value, window, recent, recent_window, n, range, category, recent_category}`. `value` is null with `window: "not logged yet"` for manual metrics (BP, fingertip SpO2, waist, VO2max, erg). Show an "add a reading" prompt, not a zero.
    - Extras: `sleep_total.current.main_block_median_h/main_block_7avg_h`; `weekly_cardio.current.weeks[[monday, min]], this_week_so_far, weeks_meeting_150`.
  - `goal`: `{id, target, timeframe, status}` and `goal_status` (confirmed|proposed|ask).
- `data.json.goals.<id>`: `{metric, target, value, status, timeframe, milestones?, question?{q, options[]}, depends_on?}`.
- **Display:** on each metric card, a thin band bar with a dot for `current.value` and a hollow dot for `current.recent`, the category name, and the source label as a small "ⓘ" link. Mark goals by status: confirmed = solid, proposed = dashed "proposed", ask = "Arnie has a question" chip showing `question.q`.
- The RHR chart reads `reference_bands.rhr.bands`.
- `hr_zones_bpm_from_max_180` is still emitted only because dashboard.html reads `zone2_60_70pct` from it. Switch to `hr_zones.zone2_60_70pct` and build.py will drop the legacy key.
- `sleeps[].consistency_pct` is now null (with `consistency_note`) for the first 3 calibration main sleeps, matching `days[]`.

## v1.3: estimated VO2max (note for Don)
- Data: `data.json.vo2max_est`.
  - `headline` has `{value, low, high, basis}`.
  - `methods[]` has `{id, name, value, inputs, formula, see, source}`, and `sensitivity[]` holds the alternative versions.
  - `series[]` is per cycle: `{cycle_start, date, rhr_7avg, est}`. It uses Uth-Sorensen with WHOOP max HR and the rolling 7-cycle RHR.
  - `weekly[]` is `{week, rhr_mean, n, est, partial}`.
  - `lab[]` mirrors `manual_logs.vo2max_lab`.
  - `reference_bands.vo2max.current` has `basis` = "estimated" or "lab", plus `estimated`, `estimated_range` and `lab`.
- Chart: show the estimated VO2max as a **dashed** line (`series[].est`, or `weekly[]` with partial weeks hollow). Shade The Cooper Institute men 40-49 bands behind it from `reference_bands.vo2max.bands`, and add a faint ribbon for `headline.low`–`headline.high`. Label it "estimated", never just "VO2max".
- Lab result: once `vo2max_lab[]` has an entry, draw a solid marker (◆) at its date and value, labelled "lab", and use it for the category chip. Keep the estimate line so the two can be compared.
- Caption: "Estimate from resting HR, age, BMI and activity, typically ±5 ml/kg/min. A lab test is the real number."

## v1.4: data fixes from the numbers check (note for Don)
- **VO2max line = headline method.** `vo2max_est.series[].est` and `weekly[].est` are now the same 3-method blend as the headline (Uth–Sørensen, Jackson 1990, Jurca 2005); only resting HR varies, activity rating and BMI held at current values. The latest series point equals the headline (42.7). The heart-rate-only values moved to `est_hr_only` (label in `vo2max_est.hr_only.label`: "heart-rate method only (Uth-Sorensen)"); optional faint comparison line.
- **Sleep goal text:** "7+ hours a day, counting naps (7-day average)".
- **Sleep performance source** is labelled "WHOOP guidance, unofficial" (no WHOOP support page with the tiers could be opened).
- **Erg:** `erg_2k` and `erg_split_500` carry `role: "reference_only"` and no goal. New metric `reference_bands.row_steady` (group fitness, unit rows/week, no bands) carries the confirmed `row_min` goal; `current` has `weeks`, `this_week_so_far`, `total_banked`, `last_row`.
- **Blood pressure** now uses the standard layout: `bands` = systolic min/max/label/tone, `bands_diastolic` same layout, `bands_axis: "systolic"`. `current.value` = systolic (number), `current.value_diastolic`, `current.display` ("118/84"), `category` = worse of `category_systolic` / `category_diastolic`.
- **SpO2:** `spo2_overnight.note` = "Wrist sensor reads low; confirm with your fingertip reader." Goals split: `spo2` (overnight) and new `spo2_fingertip`.
- `hr_zones_bpm_from_max_180` removed from data.json (use `hr_zones`).
- Notes and labels are in second person.
