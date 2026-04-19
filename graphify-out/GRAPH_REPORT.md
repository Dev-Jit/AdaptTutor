# Graph Report - C:\Users\Jitendra Pandit\Downloads\AdaptTutor  (2026-04-19)

## Corpus Check
- 15 files · ~39,496 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 245 nodes · 692 edges · 31 communities detected
- Extraction: 43% EXTRACTED · 57% INFERRED · 0% AMBIGUOUS · INFERRED: 392 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]

## God Nodes (most connected - your core abstractions)
1. `WatcherState` - 61 edges
2. `SmartSummaryPanel` - 60 edges
3. `QuizMePanel` - 55 edges
4. `WindowWatcher` - 54 edges
5. `ExplainDifferentlyPanel` - 54 edges
6. `FlashcardGeneratorPanel` - 46 edges
7. `ClipboardMonitor` - 41 edges
8. `UiTheme` - 37 edges
9. `OverlayManager` - 28 edges
10. `_LauncherCircle` - 18 edges

## Surprising Connections (you probably didn't know these)
- `UiTheme` --uses--> `Parse model output into simple / analogy / technical strings.`  [INFERRED]
  C:\Users\Jitendra Pandit\Downloads\AdaptTutor\adapttutor\theme.py → C:\Users\Jitendra Pandit\Downloads\AdaptTutor\adapttutor\features\explain_differently.py
- `UiTheme` --uses--> `Concept input, Submit → three cards (Simple / Analogy / Technical), follow-up fi`  [INFERRED]
  C:\Users\Jitendra Pandit\Downloads\AdaptTutor\adapttutor\theme.py → C:\Users\Jitendra Pandit\Downloads\AdaptTutor\adapttutor\features\explain_differently.py
- `True while Explain / Summary is waiting on the model for the open bubble.` --uses--> `UiTheme`  [INFERRED]
  C:\Users\Jitendra Pandit\Downloads\AdaptTutor\adapttutor\features\instant_explain.py → C:\Users\Jitendra Pandit\Downloads\AdaptTutor\adapttutor\theme.py
- `Instant Explain bubble at cursor. Main-thread only.     Edge cases: 1–4 words →` --uses--> `UiTheme`  [INFERRED]
  C:\Users\Jitendra Pandit\Downloads\AdaptTutor\adapttutor\features\instant_explain.py → C:\Users\Jitendra Pandit\Downloads\AdaptTutor\adapttutor\theme.py
- `ClipboardMonitor` --uses--> `OverlayState`  [INFERRED]
  C:\Users\Jitendra Pandit\Downloads\AdaptTutor\adapttutor\clipboard_monitor.py → C:\Users\Jitendra Pandit\Downloads\AdaptTutor\adapttutor\overlay.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.08
Nodes (26): _get_windows_work_area(), parse_explain_json(), Parse model output into simple / analogy / technical strings., _get_windows_work_area(), parse_flashcards_json(), _strip_json_fence(), _get_windows_work_area(), parse_quiz_question_json() (+18 more)

### Community 1 - "Community 1"
Cohesion: 0.15
Nodes (8): main(), AdaptTutor entry point:      1. Build the overlay (hidden root Tk, launcher topl, OverlayManager, OverlayState, parse_summary_response(), Split model output into TL;DR body, Key Points block, Key Terms block., ask(), Call Groq (Llama 3.3 70B) in a background thread so the Tk UI never blocks.

### Community 2 - "Community 2"
Cohesion: 0.12
Nodes (8): _display_filename(), _title_looks_like_pdf(), apply_topmost(), configure_ttk_notebook(), style_button(), style_entry(), style_text_editable(), style_text_readonly()

### Community 3 - "Community 3"
Cohesion: 0.1
Nodes (2): extract_window(), Open a PDF at filepath, extract plain text from a window of pages centered on

### Community 4 - "Community 4"
Cohesion: 0.18
Nodes (16): Source like Smart Summary; Generate → JSON cards; edit/delete; Copy as CSV (Anki, Returns (left, top, right, bottom) of the Windows work area (excluding taskbar)., Right-side feature panel: shows Thinking... then AI response (non-blocking via t, Right-side feature panel: shows Thinking... then AI response (non-blocking via t, Returns (left, top, right, bottom) of the Windows work area (excluding taskbar)., Returns (left, top, right, bottom) of the Windows work area (excluding taskbar)., mix in [0..1]: 1 => original, 0 => white., mix in [0..1]: 1 => original, 0 => white. (+8 more)

### Community 5 - "Community 5"
Cohesion: 0.18
Nodes (15): FlashcardGeneratorPanel, Source like Smart Summary; Generate → JSON cards; edit/delete; Copy as CSV (Anki, Same branching as the cursor bubble (without the >500 two-step offer)., Menu path for Instant Explain: paste or load from clipboard, then Explain / Summ, Instant Explain bubble at cursor. Main-thread only.     Edge cases: 1–4 words →, Right-side feature panel: shows Thinking... then AI response (non-blocking via t, Right-side feature panel: shows Thinking... then AI response (non-blocking via t, Returns (left, top, right, bottom) of the Windows work area (excluding taskbar). (+7 more)

### Community 6 - "Community 6"
Cohesion: 0.18
Nodes (12): ClipboardMonitor, Polls the clipboard every 500ms. When text changes, word count is in [5, 500],, Right-side feature panel: shows Thinking... then AI response (non-blocking via t, Right-side feature panel: shows Thinking... then AI response (non-blocking via t, Right-side feature panel: shows Thinking... then AI response (non-blocking via t, Returns (left, top, right, bottom) of the Windows work area (excluding taskbar)., mix in [0..1]: 1 => original, 0 => white., Start daemon background threads before the Tk main loop.         WindowWatcher a (+4 more)

### Community 7 - "Community 7"
Cohesion: 0.16
Nodes (4): configure_bubble_host(), _get_windows_work_area(), _LauncherCircle, Returns (left, top, right, bottom) of the Windows work area (excluding taskbar).

### Community 8 - "Community 8"
Cohesion: 0.21
Nodes (8): _word_count(), bubble_llm_pending(), _dismiss_bubble(), dismiss_if_open(), True while Explain / Summary is waiting on the model for the open bubble., Instant Explain bubble at cursor. Main-thread only.     Edge cases: 1–4 words →, show_bubble(), _word_count()

### Community 9 - "Community 9"
Cohesion: 0.25
Nodes (2): _MenuWindow, _PillButton

### Community 10 - "Community 10"
Cohesion: 0.2
Nodes (7): ExplainDifferentlyPanel, Concept input, Submit → three cards (Simple / Analogy / Technical), follow-up fi, Right-side feature panel: shows Thinking... then AI response (non-blocking via t, Right-side feature panel: shows Thinking... then AI response (non-blocking via t, Returns (left, top, right, bottom) of the Windows work area (excluding taskbar)., Returns (left, top, right, bottom) of the Windows work area (excluding taskbar)., mix in [0..1]: 1 => original, 0 => white.

### Community 11 - "Community 11"
Cohesion: 0.25
Nodes (6): Returns (left, top, right, bottom) of the Windows work area (excluding taskbar)., Returns (left, top, right, bottom) of the Windows work area (excluding taskbar)., mix in [0..1]: 1 => original, 0 => white., mix in [0..1]: 1 => original, 0 => white., Smart Summary: Current Page vs Paste Text, Generate, structured output, Copy., SmartSummaryPanel

### Community 12 - "Community 12"
Cohesion: 0.5
Nodes (2): _FeaturePanel, Right-side feature panel: shows Thinking... then AI response (non-blocking via t

### Community 13 - "Community 13"
Cohesion: 1.0
Nodes (2): _point_in_window(), Hit-test in screen coordinates. Do not rely on winfo_rootx/width alone for     o

### Community 14 - "Community 14"
Cohesion: 1.0
Nodes (2): mix in [0..1]: 1 => original, 0 => white., _tint_color()

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (1): Feature panels (Smart Summary, etc.).

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (0): 

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Call Google Gemini in a background thread so the Tk UI never blocks.      The HT

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Call Google Gemini in a background thread so the Tk UI never blocks.      The HT

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Call Google Gemini in a background thread so the Tk UI never blocks.     Invokes

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Native apps: e.g. 'Document1.docx - Word', 'Chapter3.pdf - Adobe Acrobat'.     M

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Parse model output into simple / analogy / technical strings.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Concept input, Submit → three cards (Simple / Analogy / Technical), follow-up fi

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Instant Explain bubble at cursor. Main-thread only.     Edge cases: 1–4 words →

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Call once from the overlay with a Tk window used as parent for the bubble Toplev

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Show the Instant Explain bubble near the cursor. Must run on the Tk main thread.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Optional cleanup when app stops.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Call Google Gemini in a background thread so the Tk UI never blocks.     Invokes

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Call Google Gemini in a background thread so the Tk UI never blocks.     Invokes

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Call OpenAI Chat Completions (ChatGPT) in a background thread so the Tk UI never

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Call Claude in a background thread so the Tk UI never blocks.     Invokes on_com

## Knowledge Gaps
- **28 isolated node(s):** `Polls the clipboard every 500ms. When text changes, word count is in [5, 500],`, `Open a PDF at filepath, extract plain text from a window of pages centered on`, `Windows 10/11: AppsUseLightTheme registry value. Else default to light.`, `Call Groq (Llama 3.3 70B) in a background thread so the Tk UI never blocks.`, `Substring match on extensions / terms (browsers and generic study strings).` (+23 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 13`** (2 nodes): `_point_in_window()`, `Hit-test in screen coordinates. Do not rely on winfo_rootx/width alone for     o`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 14`** (2 nodes): `mix in [0..1]: 1 => original, 0 => white.`, `_tint_color()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (2 nodes): `__init__.py`, `Feature panels (Smart Summary, etc.).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (1 nodes): `Call Google Gemini in a background thread so the Tk UI never blocks.      The HT`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `Call Google Gemini in a background thread so the Tk UI never blocks.      The HT`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Call Google Gemini in a background thread so the Tk UI never blocks.     Invokes`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Native apps: e.g. 'Document1.docx - Word', 'Chapter3.pdf - Adobe Acrobat'.     M`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Parse model output into simple / analogy / technical strings.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Concept input, Submit → three cards (Simple / Analogy / Technical), follow-up fi`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Instant Explain bubble at cursor. Main-thread only.     Edge cases: 1–4 words →`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Call once from the overlay with a Tk window used as parent for the bubble Toplev`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Show the Instant Explain bubble near the cursor. Must run on the Tk main thread.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Optional cleanup when app stops.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Call Google Gemini in a background thread so the Tk UI never blocks.     Invokes`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Call Google Gemini in a background thread so the Tk UI never blocks.     Invokes`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Call OpenAI Chat Completions (ChatGPT) in a background thread so the Tk UI never`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Call Claude in a background thread so the Tk UI never blocks.     Invokes on_com`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `QuizMePanel` connect `Community 6` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 7`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 13`, `Community 14`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Why does `SmartSummaryPanel` connect `Community 11` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 12`, `Community 13`, `Community 14`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Why does `WatcherState` connect `Community 4` to `Community 0`, `Community 1`, `Community 5`, `Community 6`, `Community 7`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 13`, `Community 14`?**
  _High betweenness centrality (0.118) - this node is a cross-community bridge._
- **Are the 58 inferred relationships involving `WatcherState` (e.g. with `OverlayState` and `OverlayManager`) actually correct?**
  _`WatcherState` has 58 INFERRED edges - model-reasoned connections that need verification._
- **Are the 46 inferred relationships involving `SmartSummaryPanel` (e.g. with `OverlayState` and `OverlayManager`) actually correct?**
  _`SmartSummaryPanel` has 46 INFERRED edges - model-reasoned connections that need verification._
- **Are the 40 inferred relationships involving `QuizMePanel` (e.g. with `OverlayState` and `OverlayManager`) actually correct?**
  _`QuizMePanel` has 40 INFERRED edges - model-reasoned connections that need verification._
- **Are the 49 inferred relationships involving `WindowWatcher` (e.g. with `OverlayState` and `OverlayManager`) actually correct?**
  _`WindowWatcher` has 49 INFERRED edges - model-reasoned connections that need verification._