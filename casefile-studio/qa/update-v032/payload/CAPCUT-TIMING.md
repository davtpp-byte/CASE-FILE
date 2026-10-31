# The Last Timeline — CapCut timing intake

**Status:** Timing files imported into the existing project. **Actual narration audio is still missing.** This is a data/structure audit, not acoustic verification, factual clearance, footage acquisition, or a rendered documentary.

## What is loaded

| Item | Result |
|---|---|
| CapCut project | `draft_info.json`; native word-unit arrays read by a dedicated adapter |
| Caption export | `captions_continuous.srt.md`; recognized as SRT by its contents |
| Exported narration timeline | **15:03.533** (903.533333 seconds), 30 fps |
| Caption blocks | **390**; JSON and SRT text agree in every block |
| Supplied non-space timing units | **2,353**; some contain dates or several words |
| Guide starts | **43 proposals**, all on supplied unit boundaries in this episode |
| Start-word matching | 35 normalized lexical matches; **8 substitution candidates requiring review** |
| Script/transcript comparison | 111 difference spans, including formatting and apparent ASR differences—not 111 confirmed spoken errors |
| Current plan | 56 scenes, **all visual gaps**; 903.541667 seconds after padding the last output frame at 24 fps |
| Received audio/music/footage | **None**; a local MP3 path in a draft is not the audio file |

The imported script and footage guide are unchanged. No caption text was silently corrected. No permission, source-context, timing, or transcript review was automatically approved. The fictional sample is unchanged.

## Important timing distinctions

- CapCut word-unit times are **milliseconds relative to each text segment**; segment positions are **microseconds on the target timeline**. The adapter combines those clocks, not word counts.
- Some units cover an entire expression. The adapter retains those bounds and does not label their interior word starts exact. Derived positions without a supplied boundary remain **estimates** and require a manual review if used for a cut.
- All 390 JSON/SRT caption starts agree within **0.334 milliseconds** (millisecond subtitle rounding). **211 SRT caption ends extend** past native text-segment ends, by up to **0.733667 seconds**. These continuous-caption holds were preserved; they are not evidence of global audio drift.
- 156 provided unit ends exceed a frame-rounded native caption end by less than one 30-fps frame. Raw unit bounds are retained rather than clamped; this does not prove acoustic accuracy.
- The output is 24 fps. Visual cuts use the nearest output frame; imported SRT keeps its millisecond times. A 30-fps export does not make a 24-fps output sample-accurate.
- Turning captions **off only hides text**. The same imported clock still places the guide visuals. Empty caption intervals do not generate fallback text. The SRT sidecar preserves the original global blocks, not duplicates at every visual cut.

## Text differences that must be checked with the recording

The script spelling and CapCut transcript differ on names, including **Jevario/Javario**, **Jahmir/Jamir**, **Moore/more**, and several others. This audit does not establish which words were actually spoken or independently verify case facts.

A substantive example is caption **231**, around **08:50.8**:

- Script: **10:45 a.m.**
- Caption export: **10:00am**

Do not automatically replace one with the other. Check the actual audio and reporting. If captions need correction, upload a corrected SRT with the same starts; the CapCut word-unit clock is retained and text changes are flagged. If the recording itself changes, export fresh matching timings.

In **Episode setup → Finished narration**, expand **Review transcript differences (111)** to inspect the comparison. Cue-position review and transcript-difference review are separate; both remain unapproved and disabled until the actual recording is supplied.

## Next file needed

Upload **`Just after 3_30 p.m..mp3`**, or the exact final recording used for these exports (an equivalent WAV is also fine). The draft references this basename but does not embed audio. The supported CapCut adapter requires a single untrimmed narration segment at timeline zero, speed 1. Multiple tracks, speed changes, trimmed source starts, mismatched caption starts, and mismatched recording duration require corrected exports rather than a guessed offset/stretch. Matching duration alone does not prove the words align acoustically.

No AI key or CapCut login is needed to read these local exports. Actual authorized source footage and optional background music are separate inputs, still missing. Guide links have not been downloaded or licensed.

## Proposed guide starts — not producer approvals

These are **narration-timeline positions**, not source-video in/out points. A matched start-token is not proof that an entire phrase matches the recording. All 43 must still be checked against the actual voice; rows labeled **TEXT REVIEW** depend on substitutions.

| Cue | Proposed position | Guide source | Start-token status | At phrase |
|---|---|---|---|---|
| C01 | 00:00.167 | S03 | Provided boundary; normalized start-token match | Just after 3:30 p.m. on April 17, 2024 |
| C02 | 00:15.200 | S01 | TEXT REVIEW — substitution candidate | Jevario’s family had been looking forward to his eighth-grade graduation |
| C03 | 00:26.200 | S06 | Provided boundary; normalized start-token match | Police released video of Jevario walking with two other people |
| C04 | 00:44.633 | S13 | Provided boundary; normalized start-token match | Four days after police arrested fifteen-year-old Jahmir Moore, he escaped |
| C05 | 00:51.993 | S17 | Provided boundary; normalized start-token match | At trial, the accounts of what happened between the teenagers would differ |
| C06 | 01:26.400 | S02 | TEXT REVIEW — substitution candidate | Jevario Buie was fourteen and in the eighth grade |
| C07 | 02:11.460 | S03 | Provided boundary; normalized start-token match | After Jevario’s death, his grandparents shared memories of him |
| C08 | 02:19.367 | S05 | TEXT REVIEW — substitution candidate | Jahmir Moore was fifteen when Jevario was killed |
| C09 | 02:27.367 | S05 | Provided boundary; normalized start-token match | After the shooting, police said investigators found records |
| C10 | 02:48.167 | S17 | Provided boundary; normalized start-token match | Those were the competing accounts presented in court |
| C11 | 03:04.367 | S01 | Provided boundary; normalized start-token match | On Wednesday, April 17, 2024, the three teenagers traveled together |
| C12 | 03:22.900 | S05 | Provided boundary; normalized start-token match | Trial reporting said the three met at an abandoned building |
| C13 | 03:30.767 | S05 | Provided boundary; normalized start-token match | At 3:33 p.m., police said, Jevario and Moore were filmed |
| C14 | 03:58.467 | S03 | Provided boundary; normalized start-token match | They found Jevario near the railroad tracks between Busch Boulevard and Rome Avenue |
| C15 | 04:13.460 | S04 | Provided boundary; normalized start-token match | On April 22, Tampa police publicly appealed for information |
| C16 | 04:40.667 | S01 | Provided boundary; normalized start-token match | After a community vigil, they gathered on May 4 for his funeral |
| C17 | 04:56.467 | S06 | Provided boundary; normalized start-token match | On May 9, police released a short home surveillance video |
| C18 | 05:14.400 | S08 | Provided boundary; normalized start-token match | Alongside the video came a larger reward |
| C19 | 05:34.567 | S08 | Provided boundary; normalized start-token match | Among the community partners was Thaddeus M. Bullard |
| C20 | 06:04.833 | S06 | Provided boundary; normalized start-token match | Police said the footage showed Jevario walking with two other people |
| C21 | 06:09.360 | S05 | Provided boundary; normalized start-token match | Another view showed him with Moore near North Rome Avenue |
| C22 | 06:16.400 | S07 | Provided boundary; normalized start-token match | The recordings gave investigators a timeline |
| C23 | 06:47.200 | S05 | Provided boundary; normalized start-token match | Tampa police said their investigation drew on more than surveillance video |
| C24 | 07:18.700 | S17 | Provided boundary; normalized start-token match | Moore’s defense disputed the prosecution’s interpretation of the digital material |
| C25 | 07:34.233 | S05 | Provided boundary; normalized start-token match | On December 4, 2024, the Tampa Police Department |
| C26 | 07:54.833 | S05 | Provided boundary; normalized start-token match | In a police release, State Attorney Suzy Lopez said |
| C27 | 08:05.300 | S05 | TEXT REVIEW — substitution candidate | Jevario’s mother, Jasmine Baldwin, and grandfather, Michael Baldwin Sr., thanked investigators |
| C28 | 08:27.833 | S12 | Provided boundary; normalized start-token match | Four days after his arrest, Jahmir Moore was being held |
| C29 | 08:46.587 | S13 | Provided boundary; normalized start-token match | A nearby business provided video showing Moore running away from the facility |
| C30 | 08:56.000 | S14 | Provided boundary; normalized start-token match | Deputy Chief Ruth Cate described a response |
| C31 | 09:26.167 | S14 | TEXT REVIEW — substitution candidate | Messmer said detectives drew on information gathered |
| C32 | 09:52.433 | S15 | Provided boundary; normalized start-token match | Police announced an additional felony escape charge |
| C33 | 10:48.300 | S16 | Provided boundary; normalized start-token match | The next morning, Moore appeared in Hillsborough County Circuit Court |
| C34 | 11:13.633 | S17 | Provided boundary; normalized start-token match | On September 1, 2026, Moore was seventeen |
| C35 | 11:25.767 | S17 | Provided boundary; normalized start-token match | At trial, Assistant State Attorney Chinwe Fossett argued |
| C36 | 11:36.167 | S17 | Provided boundary; normalized start-token match | Defense attorney Sinardi offered another explanation |
| C37 | 11:59.367 | S17 | Provided boundary; normalized start-token match | A third teenager testified as a prosecution witness |
| C38 | 12:24.800 | S17 | Provided boundary; normalized start-token match | On September 3, 2026, the jury found Moore guilty of first-degree murder |
| C39 | 12:45.033 | S19 | Provided boundary; normalized start-token match | On October 16, 2026, Jahmir Moore returned to a Hillsborough County courtroom for sentencing |
| C40 | 13:56.033 | S19 | Provided boundary; normalized start-token match | Judge Goudie recognized the seriousness of the killing |
| C41 | 14:06.667 | S19 | TEXT REVIEW — substitution candidate | Goudie sentenced Moore to fifty-five years in prison for the murder |
| C42 | 14:37.667 | S01 | TEXT REVIEW — substitution candidate | Jevario’s family had looked forward to celebrating his eighth-grade graduation |
| C43 | 15:01.067 | S02 | TEXT REVIEW — substitution candidate | Jevario’s family now lives without him |

## Data handling

The application retains sanitized text, times, source filenames, and fingerprints. CapCut device identifiers, MAC addresses, absolute media paths, and the complete raw draft are not included in the saved project or release. Original uploaded files remain separate in the workspace.

**Verification:** 125 backend tests, including 33 native-timing regressions and synthetic caption-on/off renders. The synthetic renders retain identical decoded audio with captions on/off and preserve caption holds across cuts; they are not recordings of this case. Browser checks cover the actual 2.7 MB draft and `.srt.md`, caption visibility/clock independence, unresolved approvals, and mobile layout. Review the finished actual-case video only after actual media is supplied.
