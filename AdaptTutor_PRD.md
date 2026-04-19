# AdaptTutor — Product Requirements Document

## Overview

AdaptTutor is a desktop overlay application that acts as a personal AI tutor. It runs silently in the background, detects when the user opens study-related content, and surfaces contextual AI-powered help without requiring the user to switch apps or open a browser.

The app is built using Python with a Tkinter UI, integrated with the Claude API (claude-sonnet-4-20250514) for all AI functionality.

---

## Design Language

### The Launcher (Collapsed State)

- A circular floating button fixed to the **bottom-right corner** of the screen
- Size: 56x56px circle
- Always on top of all other windows (`-topmost True`)
- Background: deep indigo/purple (`#6C63FF`)
- Icon: a small graduation cap or sparkle symbol in white, centered
- Slight drop shadow for depth
- On hover: slightly brightens (10% lighter)
- On click: expands upward into the feature menu

### The Menu (Expanded State)

When the user clicks the circle, the menu opens **upward** from the circle — like a radial/vertical fan of feature buttons. Each feature is its own pill-shaped button that animates in with a smooth slide-up and fade-in effect, staggered one by one (50ms delay between each).

Menu layout (bottom to top order):

```
[Circle Button]           ← always visible, bottom right
    ↑
[Instant Explain]
[Explain Differently]
[Quiz Me]
[Smart Summary]
[Flashcard Generator]
[Pre-Exam Brief]
[Focus Timer]
```

Each pill button:
- Width: 200px, Height: 40px, border-radius: 20px
- White background with a colored left-border accent (unique color per feature)
- Feature icon (emoji or simple SVG) on the left
- Feature name text (14px, medium weight)
- On hover: subtle background tint matching the accent color
- On click outside menu: menu closes and collapses back to the circle

### Color Accents Per Feature

| Feature | Accent Color |
|---|---|
| Instant Explain | `#6C63FF` (indigo) |
| Explain Differently | `#00BFA5` (teal) |
| Quiz Me | `#FF6B6B` (coral) |
| Smart Summary | `#FFA726` (amber) |
| Flashcard Generator | `#42A5F5` (blue) |
| Pre-Exam Brief | `#AB47BC` (purple) |
| Focus Timer | `#66BB6A` (green) |

### The Panel (Feature Active State)

When a feature is selected, a panel slides in from the right side of the screen (or expands from the circle, anchored bottom-right). The circle remains visible and glowing to indicate AdaptTutor is active.

Panel specs:
- Width: 360px
- Height: auto, max 600px, scrollable if content overflows
- Background: white (light mode) / `#1E1E2E` (dark mode)
- Border-radius: 16px on top-left and bottom-left corners
- Soft border: `1px solid rgba(0,0,0,0.08)`
- Header bar: feature name + close (X) button
- Content area: scrollable, 16px padding

---

## Core Architecture

### Background Watcher (watcher.py)

- Runs as a daemon thread on app launch
- Polls the active window title every 3 seconds using `pygetwindow`
- Matches window title against a keyword list to detect study context
- On study content detected: notifies the overlay to show itself
- On non-study context: overlay minimizes to the circle only

Study keywords to detect:
```
pdf, .pptx, lecture, notes, textbook, youtube, coursera, udemy,
khan, chapter, study, exam, assignment, tutorial, slides, textbook,
classroom, lesson, course, module, worksheet
```

### Clipboard Monitor (clipboard_monitor.py)

- Separate daemon thread running alongside the watcher
- Polls clipboard / primary selection buffer every 500ms using `pyperclip` or `pygetwindow` accessibility APIs
- Detects newly selected text by comparing previous and current clipboard state
- Triggers Instant Explain only when:
  - Selected text is between 5 and 500 words
  - Mouse has been still for at least 1 second (use `pynput` to track mouse movement)
  - The active window is study-related (checks against watcher state)
- On trigger: spawns the Instant Explain bubble at cursor position

### Overlay Manager (overlay.py)

- Central controller for all UI windows
- Manages state: `collapsed`, `menu_open`, `feature_active`
- Handles transitions between states with animations
- Ensures only one feature panel is open at a time

---

## Features

---

### 1. Instant Explain

**Trigger:** User selects text on screen in any application. No button press required.

**Behavior:**
1. Clipboard monitor detects new text selection meeting size criteria
2. A small bubble window appears near the cursor (not in corner — at cursor position)
3. Bubble shows a preview of the selected text (truncated to 60 chars) and a prompt: "Explain this simply?"
4. Two buttons: `Explain it` and `Dismiss`
5. If no interaction within 4 seconds, bubble auto-dismisses
6. On `Explain it` click: bubble expands to show AI-generated simple explanation
7. Explanation is under 4 sentences, uses an analogy if possible
8. A `Go Deeper` button at the bottom opens the full feature panel for follow-up questions

**Bubble specs:**
- Width: 280px, height: auto
- Rounded corners: 12px
- Appears above the cursor with a small arrow pointer
- Always on top
- Drops shadow: `0 4px 20px rgba(0,0,0,0.15)`
- Smooth expand animation when showing explanation

**Claude prompt:**
```
Explain the following text in the simplest possible way, as if the reader 
is hearing this concept for the first time. Use a relatable real-world analogy 
if one exists. Keep the response to 3-4 sentences maximum. Do not use jargon.

Selected text: {selected_text}
```

**Edge cases:**
- Selection of 1-4 words → show dictionary-style definition instead
- Selection over 500 words → show "This is quite long — want a summary instead?" with a Summary button
- User presses Ctrl+C immediately after selecting → assume they wanted to copy, dismiss bubble silently

---

### 2. Explain Differently

**Trigger:** User clicks `Explain Differently` from the feature menu.

**Behavior:**
1. Feature panel opens
2. User types or pastes a concept they don't understand into a text input
3. AI returns three explanations simultaneously displayed as three cards:
   - **Simple** — ELI5, plain language, no jargon
   - **Analogy** — a relatable real-world comparison
   - **Technical** — precise explanation with correct terminology
4. User can click any card to expand it
5. Below the cards: a text field to ask a follow-up question about any of the explanations

**Panel layout:**
- Input box at top with placeholder: "Paste a concept or sentence you don't understand..."
- Submit button
- Three cards stacked vertically after response, each with a colored left border matching the mode
- Each card: mode label (bold, 12px), explanation text (14px)

**Claude prompt:**
```
A student doesn't understand the following concept. Provide three different 
explanations:

1. SIMPLE: Explain it in plain language a 12-year-old could understand. No jargon.
2. ANALOGY: Create a relatable real-world analogy that makes the concept click.
3. TECHNICAL: Explain it precisely using correct terminology for a student who 
   wants the accurate version.

Keep each explanation to 3-5 sentences.

Concept: {concept}
```

---

### 3. Quiz Me

**Trigger:** User clicks `Quiz Me` from the feature menu.

**Behavior:**
1. Feature panel opens
2. If a PDF is open, the app reads its content via the active window context. If not, user can paste text manually.
3. AI generates 1 question at a time (Socratic method — not a bulk list)
4. Question types cycle through: multiple choice, open-ended, fill-in-the-blank
5. User submits their answer
6. AI responds with:
   - Correct/incorrect indicator
   - If incorrect: a guiding hint, not the direct answer
   - A follow-up question that probes deeper on the same concept
7. After every 3 questions, a brief summary card shows: "You got X right. You seem to struggle with Y."
8. `Next Topic` button generates questions on a new section

**Panel layout:**
- Question card (large, centered, colored background per question type)
- Answer input (text field or radio buttons for MCQ)
- Submit button
- Response area below showing AI feedback
- Progress indicator: `Question 3 of this session`

**Claude prompt for question generation:**
```
You are a Socratic tutor. Based on the following study material, generate ONE 
question to test the student's understanding. 

Rules:
- Ask only one question at a time
- Vary between: multiple choice (provide 4 options labeled A-D), open-ended, 
  and fill-in-the-blank
- Target conceptual understanding, not memorisation
- Difficulty should be medium — not trivial, not postgraduate

Study material: {content}
Previous questions asked this session: {history}

Return your response as JSON:
{
  "type": "mcq" | "open" | "fill",
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],  // only for mcq
  "answer": "..."  // internal use only, do not display to user
}
```

**Claude prompt for answer evaluation:**
```
The student answered a quiz question. Evaluate their answer using the Socratic 
method — guide them toward understanding rather than just marking right or wrong.

Question: {question}
Correct answer: {answer}
Student's answer: {student_answer}

Respond with:
1. Whether they were correct (be encouraging either way)
2. If wrong: a guiding hint that nudges them without giving the answer directly
3. A short follow-up question that deepens understanding of this concept
```

---

### 4. Smart Summary

**Trigger:** User clicks `Smart Summary` from the feature menu.

**Behavior:**
1. Feature panel opens
2. User can either:
   - Paste text manually into the input area
   - Click `Use current page` to let the app read the active window's content (PDF text extraction via `pymupdf`)
3. AI generates a structured summary:
   - A 3-sentence TL;DR at the top
   - 4-6 key points as bullet points
   - 2-3 important terms defined simply
4. User can click any key point to expand it into a deeper explanation
5. `Copy Summary` button copies plain text to clipboard
6. `Save as Flashcards` button passes the key points to the Flashcard Generator

**Panel layout:**
- Source selector at top: `Paste text` tab | `Current page` tab
- Text input (visible only in Paste tab)
- Generate button
- Summary output: TL;DR section, Key Points section, Key Terms section
- Action buttons at bottom

**Claude prompt:**
```
Summarise the following study material for a student preparing for an exam.

Return your response in this exact structure:

TLDR: (3 sentences maximum — the absolute core of what this content says)

KEY POINTS:
- (most important idea)
- (second most important idea)
- ... (4-6 points total)

KEY TERMS:
- Term: simple one-sentence definition
- ... (2-3 terms)

Be concise. Every word should earn its place.

Content: {content}
```

---

### 5. Flashcard Generator

**Trigger:** User clicks `Flashcard Generator` from the feature menu.

**Behavior:**
1. Feature panel opens
2. User pastes content or clicks `Use current page`
3. AI generates a deck of flashcards (8-15 cards depending on content length)
4. Cards are displayed in a preview list: Front | Back
5. User can edit any card inline before exporting
6. User can delete cards they don't want
7. Export options:
   - `Copy as CSV` — copies in Anki-compatible format (Front, Back)
   - `Export as .txt` — saves to desktop as plain text

**Panel layout:**
- Source input at top (same as Smart Summary)
- Generate button
- Card list: each card shows front text and back text side by side
- Edit icon on each card (click to edit inline)
- Delete icon on each card
- Export buttons at bottom

**Card formats AI should generate:**
- Definition cards: term on front, definition on back
- Concept cards: question on front, explanation on back
- Fill-in cards: sentence with blank on front, missing word on back

**Claude prompt:**
```
Generate a set of flashcards from the following study material.

Rules:
- Create between 8 and 15 cards depending on content length
- Mix three types: definition cards, concept questions, and fill-in-the-blank
- Keep front of card concise (under 15 words)
- Keep back of card under 40 words
- Cover the most important concepts, not trivial details

Return as JSON array:
[
  { "front": "...", "back": "...", "type": "definition" | "concept" | "fill" },
  ...
]

Content: {content}
```

---

### 6. Pre-Exam Brief

**Trigger:** User clicks `Pre-Exam Brief` from the feature menu.

**Behavior:**
1. Feature panel opens
2. User pastes their study material (notes, PDF text, revision content)
3. User optionally types: "My exam is on {topic} and covers {scope}"
4. AI generates a pre-exam brief with:
   - The 5 most likely exam topics based on the material
   - The 3 concepts most commonly misunderstood in this subject
   - A rapid-fire recap: 10 key facts in plain bullet form
   - One "trick question" warning — a common exam trap with the correct answer
5. Brief is formatted for quick reading (not long paragraphs)
6. `Print / Copy` button at bottom

**Panel layout:**
- Input area: study material paste box + optional exam info text field
- Generate button
- Output: four clearly separated sections with icons and headers
- Print/Copy button

**Claude prompt:**
```
A student is about to sit an exam and has provided their study material. 
Generate a focused pre-exam brief designed to be read 30 minutes before the exam.

Structure your response exactly as follows:

TOP 5 LIKELY EXAM TOPICS:
1. ...
2. ...
(with a one-line explanation of why each is likely)

3 COMMONLY MISUNDERSTOOD CONCEPTS:
- Concept: what students usually get wrong vs what is actually correct

RAPID RECAP (10 key facts):
- ...
(one line each, the most important facts to remember)

WATCH OUT FOR:
One common exam trick or misconception in this subject, and the correct answer.

Study material: {content}
Exam context (if provided): {exam_context}
```

---

### 7. Focus Timer

**Trigger:** User clicks `Focus Timer` from the feature menu.

**Behavior:**
1. Feature panel opens showing the timer interface
2. Default session: 25 minutes study / 5 minutes break (Pomodoro)
3. User can adjust session length: 15, 25, 45, 60 minutes
4. On Start:
   - Timer counts down in the panel
   - The launcher circle shows a subtle pulsing ring to indicate an active session
   - At end of session: a soft notification sound + overlay message "Break time! 5 minutes."
5. Break timer counts down automatically
6. After break: prompts "Ready to continue?" with a Resume button
7. Session counter at top: "Session 3 of today"
8. On panel close during active session: timer continues, circle shows remaining time as an arc progress ring around it

**Panel layout:**
- Large countdown display (MM:SS) centered
- Session length selector (pill buttons: 15 / 25 / 45 / 60)
- Start / Pause / Reset buttons
- Session counter badge
- Motivational micro-message from AI after each completed session (short, one line)

**Motivational prompt (called after each completed session):**
```
Give a single short, encouraging message (under 12 words) to a student who 
just completed a study session. Keep it genuine, not clichéd. Vary the tone 
each time — sometimes matter-of-fact, sometimes warm, sometimes lightly humorous.
```

---

## File Structure

```
adapttutor/
├── main.py                  ← entry point, launches all threads + UI
├── watcher.py               ← background window title monitor
├── clipboard_monitor.py     ← text selection detection daemon
├── overlay.py               ← main UI controller, state management
├── features/
│   ├── instant_explain.py   ← bubble UI + logic
│   ├── explain_differently.py
│   ├── quiz_me.py
│   ├── smart_summary.py
│   ├── flashcard_generator.py
│   ├── pre_exam_brief.py
│   └── focus_timer.py
├── tutor.py                 ← Claude API wrapper, all prompt calls
├── pdf_reader.py            ← extracts text from open PDFs using pymupdf
├── config.py                ← API key, keywords, constants
├── assets/
│   ├── icon.png
│   └── sounds/
│       └── timer_end.wav
└── requirements.txt
```

---

## Dependencies

```
anthropic
pygetwindow
pyautogui
pynput
pyperclip
pymupdf
tkinter (standard library)
playsound
```

---

## Technical Constraints

- The UI must use `attributes("-topmost", True)` on all overlay windows so they appear above every other application
- All Claude API calls must be non-blocking — run in separate threads so the UI never freezes
- The launcher circle must persist even when no study content is detected — it is always visible in the bottom right corner
- PDF text extraction reads only the currently visible page to keep context within token limits
- All Claude prompts must include `max_tokens=600` to keep responses concise for the overlay format
- The app must handle the case where no active window title is detected gracefully (default to idle state)
- Dark mode detection: read the OS theme on launch and apply appropriate color variables

---

## Out of Scope (Not to Build)

- Progress tracker or analytics dashboard
- Weakness tracker or long-term memory between sessions
- Voice input or text-to-speech
- Cloud sync or user accounts
- Mobile version
- Browser extension version
