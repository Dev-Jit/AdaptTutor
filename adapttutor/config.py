import os

# Groq API (used by tutor.py). Prefer environment variable GROQ_API_KEY.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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").strip()

STUDY_KEYWORDS = [
    ".pdf",
    ".docx",
    ".pptx",
    ".txt",
    ".xlsx",
    ".md",
    "word",
    "powerpoint",
    "acrobat",
    "foxit",
    "okular",
    "evince",
    "libreoffice",
    "lecture",
    "notes",
    "textbook",
    "chapter",
    "study",
    "exam",
    "assignment",
    "tutorial",
    "lesson",
    "course",
    "worksheet",
    "revision",
    "syllabus",
    "wikipedia",
]

# Native desktop apps often use: "<filename> - <AppName>". Match end of title (lowercased).
STUDY_APP_TITLE_SUFFIXES = [
    " - word",
    " - powerpoint",
    " - excel",
    " - acrobat",
    " - adobe acrobat",
    " - foxit reader",
    " - notepad",
    " - okular",
    " - evince",
]

LAUNCHER_SIZE = 56
LAUNCHER_BG = "#6C63FF"
LAUNCHER_BG_HOVER = "#7A72FF"

MENU_PILL_WIDTH = 200
MENU_PILL_HEIGHT = 40
MENU_PILL_RADIUS = 20
MENU_GAP = 10
MENU_ANIM_STEP_PX = 8
MENU_ANIM_TICK_MS = 12
MENU_STAGGER_MS = 50

PANEL_WIDTH = 360
PANEL_MAX_HEIGHT = 600
PANEL_PAD = 16

FEATURES = [
    ("Ask AI", "#FF8C42", "💬"),
    ("Explain Differently", "#00BFA5", "🔁"),
    ("Quiz Me", "#FF6B6B", "❓"),
    ("Smart Summary", "#FFA726", "🧠"),
    ("Flashcard Generator", "#42A5F5", "🗂️"),
]

