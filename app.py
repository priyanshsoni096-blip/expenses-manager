"""
app.py
Smart Expense Tracker — main Streamlit app.
Dark terminal theme. Sidebar: Dashboard / Add Expense / History / Analytics / Categories.

Run with:
    streamlit run app.py

Requires .streamlit/secrets.toml with a [firebase_service_account] section.
"""

import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

import streamlit.components.v1 as components

import categorizer
import storage
import voice_input
from streamlit_mic_recorder import mic_recorder

st.set_page_config(page_title="Smart Expense Tracker", page_icon="💰", layout="wide", initial_sidebar_state="expanded")

PAYMENT_MODES = ["Cash", "UPI", "Card", "Other"]

USER_NAME = "Priyansh"


def _initials(name: str) -> str:
    """Up to two initials for the sidebar avatar, derived rather than hardcoded
    so changing USER_NAME can't leave a stale monogram behind."""
    parts = [w for w in name.split() if w]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


@st.cache_data(ttl=30, show_spinner=False)
def get_categories():
    try:
        return storage.load_categories()
    except Exception:
        return storage.DEFAULT_CATEGORIES


categories_list = get_categories()
CATEGORY_COLORS = {c["name"]: c["color"] for c in categories_list}
CATEGORY_ICONS = {c["name"]: c["icon"] for c in categories_list}
CATEGORY_NAMES = [c["name"] for c in categories_list]

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    :root {
        --bg: #0B0E14; --surface: #12161F; --surface-2: #171C27; --border: #232A38;
        --text: #E6E9EF; --muted: #7C8494; --accent: #22C55E; --accent-soft: #16351F;
        --red: #F87171; --red-soft: #3A1A1A;
    }
    html { color-scheme: dark !important; }
    html, body, [class*="css"], .stApp, .stApp * {
        font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace !important;
    }
    .stApp { background-color: var(--bg); color: var(--text); }
    section[data-testid="stSidebar"] { background-color: var(--surface); border-right: 1px solid var(--border); }
    .brand-block { padding: 4px 4px 18px; border-bottom: 1px solid var(--border); margin-bottom: 14px; display:flex; align-items:flex-start; gap:10px; }
    .brand-icon { flex-shrink:0; width:38px; height:38px; border-radius:10px; border:1.5px solid var(--accent); display:flex; align-items:center; justify-content:center; color:var(--accent); font-weight:700; font-size:17px; }
    .brand-title { font-weight: 700; font-size: 14px; color: var(--text); line-height:1.35; letter-spacing: 0.03em; text-transform: uppercase; }
    .brand-sub { font-size: 9.5px; color: var(--accent); font-weight: 600; letter-spacing: 0.1em; margin-top:6px; }

    div.stButton button {
        background-color: var(--surface-2) !important; color: var(--text) !important;
        border: 1px solid var(--border) !important; border-radius: 8px !important;
        padding: 10px 14px !important; font-weight: 500 !important;
        font-family: 'JetBrains Mono', monospace !important; font-size: 12.5px !important;
        letter-spacing: 0.02em !important; width: 100% !important;
    }
    div.stButton button:focus, div.stButton button:focus-visible, div.stButton button:active {
        outline: none !important; box-shadow: none !important; background-color: var(--surface-2) !important;
    }
    div.stButton button[kind="primary"] { background-color: var(--accent) !important; color: #06170C !important; border: none !important; font-weight: 700 !important; }
    div.stButton button[kind="primary"] p { color: #06170C !important; }

    section[data-testid="stSidebar"] div.stButton button {
        background: transparent !important; color: var(--muted) !important; border: none !important;
        text-align: left !important; justify-content: flex-start !important; padding: 10px 12px !important; margin-bottom: 2px !important;
    }
    section[data-testid="stSidebar"] div.stButton button:focus, section[data-testid="stSidebar"] div.stButton button:active {
        background: transparent !important; outline: none !important; box-shadow: none !important;
    }
    /* Only apply hover backgrounds on devices with a real mouse — otherwise a tap on
       touch/trackpad leaves the highlight "stuck" since there's no mouse-leave event. */
    @media (hover: hover) and (pointer: fine) {
        div.stButton button:hover { background-color: #1D2330 !important; border-color: #2E3644 !important; }
        div.stButton button[kind="primary"]:hover { background-color: #1FAE55 !important; }
        section[data-testid="stSidebar"] div.stButton button:hover { background: var(--surface-2) !important; color: var(--text) !important; }
    }
    /* Tighten default Streamlit inter-widget spacing in sidebar (covers multiple Streamlit versions' class/testid naming) */
    section[data-testid="stSidebar"] div[class*="element-container"],
    section[data-testid="stSidebar"] div[data-testid*="Element"],
    section[data-testid="stSidebar"] [data-testid="stElementContainer"],
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div {
        margin-bottom: 0 !important; margin-top: 0 !important; padding: 0 !important; gap: 0 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] { gap: 0.2rem !important; }
    section[data-testid="stSidebar"] div.stButton { line-height: 1 !important; margin: 0 !important; }
    section[data-testid="stSidebar"] div.stButton button {
        min-height: unset !important; line-height: 1.3 !important; box-sizing: border-box !important;
    }
    section[data-testid="stSidebar"] div.stButton button p { margin: 0 !important; line-height: 1.3 !important; }
    section[data-testid="stSidebar"] [data-testid="stButton"] { margin: 0 !important; }
    /* Each nav row (active pill or button) is wrapped in its own st.container(key="navrow_*"),
       which gives a guaranteed, stable class hook — unlike guessing Streamlit's internal
       testids/classes, which has been unreliable across this build. Every row's OWN wrapper
       gets the same margin, so spacing is identical regardless of whether that row renders
       a plain div (active page) or a real button (inactive pages). */
    [class*="st-key-navrow_"] { margin: 0 0 3px 0 !important; padding: 0 !important; }
    [class*="st-key-navrow_"] > div { margin: 0 !important; padding: 0 !important; }
    [class*="st-key-navrow_"] div.stButton,
    [class*="st-key-navrow_"] div.stButton button { margin: 0 !important; }
    /* Make the nav rows fill the sidebar however wide the user drags it. The
       active row's green pill was stopping short of the divider above it,
       because Streamlit constrains its sidebar content wrapper and the button
       inherited that narrower width. Percentages, not fixed pixels, so this
       tracks any sidebar width. */
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { max-width: 100% !important; }
    section[data-testid="stSidebar"] [class*="st-key-navrow_"],
    section[data-testid="stSidebar"] [class*="st-key-navrow_"] > div,
    section[data-testid="stSidebar"] [class*="st-key-navrow_"] div.stButton,
    section[data-testid="stSidebar"] [class*="st-key-navrow_"] div.stButton button {
        width: 100% !important; max-width: 100% !important; box-sizing: border-box !important;
    }
    /* Now that the button fills the sidebar, its label block also stretches, and
       Streamlit centres button text - so the labels drifted to the middle while
       the ::before icons stayed pinned left. Shrink the label block to its
       content and left-align it, so text sits right next to its icon. */
    section[data-testid="stSidebar"] [class*="st-key-navrow_"] div.stButton button > div,
    section[data-testid="stSidebar"] [class*="st-key-navrow_"] div.stButton button p {
        width: auto !important; max-width: none !important;
        flex: 0 1 auto !important; text-align: left !important; margin: 0 !important;
    }
    /* Same technique for expense-table rows: each row is wrapped in its own
       st.container(key="exprow_*") so every row gets identical top/bottom
       spacing, regardless of Streamlit's own (apparently inconsistent)
       default margins on the first row of a block vs. later ones. */
    [class*="st-key-exprow_"] { margin: 0 !important; padding: 0 !important; }
    [class*="st-key-exprow_"] [data-testid="stElementContainer"] { margin: 0 !important; padding: 0 !important; }
    [class*="st-key-exprow_"] div.stButton button { min-height: unset !important; }
    /* --- Parsed-item row vertical alignment ----------------------------------
       The row-number badge and the delete button have no label above them,
       while Merchant/Amount/Category do. Two earlier attempts tried to centre
       everything against the row's full rendered height (align-items on an
       unverified "stHorizontalBlock" testid, then a height:100% cascade) -
       both assumed Streamlit would hand back a reliable, measurable row
       height to align against, and in practice the badge kept landing near
       the label instead of centred, on every rebuild. This version stops
       depending on Streamlit's real label's measured height at all: it
       forces every real widget label in this panel to one FIXED, CSS-owned
       height (min-height + margin-bottom below), and gives the badge/button
       an identical hidden spacer of that same fixed height. Both sides are
       now defined by us, in the same place, so they can't drift apart. */
    .st-key-parsed_items_panel [data-testid="stWidgetLabel"] {
        min-height: 20px !important; margin-bottom: 6px !important;
        display: flex !important; align-items: center !important;
    }
    .parsed-item-spacer { min-height: 20px; margin-bottom: 6px; visibility: hidden; }
    /* The badge and the delete button don't naturally end up the same
       height as the input row next to them - the badge is a tiny 22px
       circle and the button is sized by its own padding, so even with both
       starting at the same Y (the spacer above), a shorter/taller box means
       their visual centre still doesn't land on the input's centre. Giving
       both a shared fixed height and centring their content inside it (same
       fixed-and-shared idea as the spacer above) settles that. */
    .parsed-num-wrap { display: flex; align-items: center; justify-content: center; min-height: 38px; }
    .st-key-parsed_items_panel div.stButton { min-height: 38px; }
    .st-key-parsed_items_panel div.stButton button {
        height: 38px !important; display: flex !important; align-items: center !important;
        justify-content: center !important; padding: 0 !important;
    }

    /* Example chips: Devanagari glyphs are taller than Latin ones, so equal
       padding left the Hindi row visibly taller than the English row. A shared
       min-height with centred content makes both rows match. */
    .example-chip {
        background: var(--surface-2); border: 1px solid var(--border);
        border-radius: 8px; padding: 6px 10px; font-size: 10.5px;
        text-align: center; color: var(--muted); min-height: 34px;
        display: flex; align-items: center; justify-content: center;
        box-sizing: border-box;
    }

    /* The mic recorder is a custom component, i.e. a cross-document iframe, so
       its inner button genuinely cannot be themed from this stylesheet. Constrain
       and centre the iframe so it at least sits neatly inside its card instead of
       stretching the full width. */
    .st-key-mic_frame iframe { max-width: 320px !important; margin: 0 auto !important; display: block !important; }

    .st-key-type_input_box [data-testid="InputInstructions"] { display: none !important; }
    .st-key-example_chip_row div.stButton button { background: transparent !important; border: none !important; color: var(--muted) !important; font-size: 11.5px !important; font-weight: 500 !important; padding: 4px 2px !important; }
    .st-key-example_chip_row div.stButton button:hover { color: var(--accent) !important; text-decoration: underline; }
    .st-key-mic_frame { background: var(--surface-2) !important; border: 1px solid var(--border) !important; border-radius: 14px !important; padding: 20px !important; margin-bottom: 16px !important; }
    .pulse-ring-wrap { position: relative; width: 48px; height: 48px; margin: 0 auto; }
    .pulse-ring { position: absolute; top:0; left:0; width:48px; height:48px; border-radius:50%; border: 1.5px solid var(--accent); animation: pulse-out 2.4s ease-out infinite; opacity:0; }
    @keyframes pulse-out { 0% { transform: scale(1); opacity:.6; } 100% { transform: scale(1.9); opacity:0; } }

    .section-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; margin-bottom: 20px; }
    .section-card-title { font-size: 10.5px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); font-weight: 700; margin-bottom: 14px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
    .section-label { font-size: 10.5px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); font-weight: 700; margin: 4px 0 10px; }
    .page-title { font-size: 22px; font-weight: 700; color: var(--text); }
    .page-subtitle { font-size: 12.5px; color: var(--muted); margin-bottom: 20px; }
    .tip-box { background: var(--accent-soft); border: 1px solid #1F4A2C; border-radius: 8px; padding: 10px 16px; font-size: 11.5px; color: #86EFAC; margin-bottom: 20px; display:inline-flex; align-items:center; gap:8px; }
    .tip-box b { color: var(--accent); letter-spacing: 0.08em; }

    .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; width: 100%; box-sizing: border-box; min-height: 84px; }
    /* Stat cards are laid out with CSS GRID, not st.columns. st.columns
       auto-stacks to a single column below an internal Streamlit width
       threshold - which is why the 4 cards showed side-by-side on a wide
       local window but stacked vertically on the (narrower) deployed window,
       despite identical code/versions. auto-fit + minmax keeps them
       side-by-side and only wraps when there is genuinely no room, at any
       width, on any deploy. (The Quick Add / Monthly Budget row below still
       uses st.columns because those cards contain real interactive widgets
       that can't live inside an HTML grid; stacking those two on a narrow
       window is fine.) */
    .stat-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 14px; width: 100%;
    }
    /* Force every wrapper layer between the column and our card to actually stretch —
       Streamlit's own containers otherwise shrink-wrap to content, so a card with more
       text (e.g. Top Category) renders wider than one with less (e.g. This Month). */
    [data-testid="stColumn"], [data-testid="stColumn"] > div,
    [data-testid="stColumn"] [data-testid="stVerticalBlock"],
    [data-testid="stColumn"] [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stColumn"] [data-testid="stElementContainer"],
    [data-testid="stColumn"] [data-testid="stMarkdownContainer"] {
        width: 100% !important;
    }
    .stat-card-icon { font-size: 18px; }
    .stat-card-label { font-size: 10px; color: var(--muted); margin-top:6px; }
    .stat-card-value { font-size: 19px; font-weight:700; color: var(--text); margin-top:2px; }
    .stat-card-sub { font-size: 9.5px; color: var(--muted); margin-top:2px; }

    .parsed-card { background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; margin-top: 10px; margin-bottom: 10px; }
    .parsed-num { display:inline-flex; align-items:center; justify-content:center; width:22px; height:22px; border-radius:50%; background:var(--accent-soft); color:var(--accent); font-size:11px; font-weight:700; margin-right:8px; }

    .st-key-parsed_items_panel div[data-testid="stNumberInputStepUp"],
    .st-key-parsed_items_panel div[data-testid="stNumberInputStepDown"],
    .st-key-parsed_items_panel div[data-testid="stNumberInput"] button { display:none !important; }
    .st-key-parsed_items_panel div[data-baseweb="input"] input,
    .st-key-parsed_items_panel div[data-baseweb="input"] {
        background: transparent !important; border: none !important; padding-left: 0 !important;
    }
    .st-key-parsed_items_panel div[data-testid="stTextInput"] input { font-weight: 600 !important; font-size: 14px !important; }
    .st-key-parsed_items_panel div[data-testid="stNumberInput"] input { font-weight: 700 !important; font-size: 14px !important; color: var(--accent) !important; }
    .st-key-parsed_items_panel div[data-baseweb="input"]:focus-within { background: var(--surface-2) !important; border: 1px solid var(--accent) !important; border-radius: 6px !important; }
    .stamp-tag { display: inline-flex; align-items: center; gap: 5px; font-size: 10px; text-transform: uppercase; padding: 3px 9px; border-radius: 4px; font-weight: 600; border: 1px solid currentColor; }

    [class*="_editbtn"] button, [class*="_delbtn"] button,
    [class*="_save"] button, [class*="_cancel"] button {
        padding: 6px 0 !important; font-size: 13px !important; min-height: unset !important; line-height: 1.2 !important;
    }

    div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea, div[data-baseweb="select"] {
        background-color: var(--surface-2) !important; color: var(--text) !important; border: 1px solid var(--border) !important;
        border-radius: 8px !important; font-family: 'JetBrains Mono', monospace !important; padding: 10px 12px !important; font-size: 13px !important;
    }
    div[data-baseweb="input"]:focus-within, div[data-baseweb="textarea"]:focus-within { border-color: var(--accent) !important; box-shadow: 0 0 0 3px rgba(34,197,94,0.15) !important; }

    .st-key-hist_filter_date div[data-baseweb="select"],
    .st-key-hist_filter_cat div[data-baseweb="select"],
    .st-key-hist_filter_pay div[data-baseweb="select"],
    .st-key-hist_search_box div[data-baseweb="input"] { position: relative; }
    .st-key-hist_filter_date div[data-baseweb="select"] > div:first-child,
    .st-key-hist_filter_cat div[data-baseweb="select"] > div:first-child,
    .st-key-hist_filter_pay div[data-baseweb="select"] > div:first-child { padding-left: 34px !important; }
    .st-key-hist_search_box div[data-baseweb="input"] input { padding-left: 34px !important; }
    .st-key-hist_filter_date div[data-baseweb="select"]::before,
    .st-key-hist_filter_cat div[data-baseweb="select"]::before,
    .st-key-hist_filter_pay div[data-baseweb="select"]::before,
    .st-key-hist_search_box div[data-baseweb="input"]::before {
        position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
        font-size: 13px; z-index: 2; pointer-events: none;
    }
    .st-key-hist_filter_date div[data-baseweb="select"]::before { content: "📅"; }
    .st-key-hist_filter_cat div[data-baseweb="select"]::before { content: "📄"; }
    .st-key-hist_filter_pay div[data-baseweb="select"]::before { content: "💳"; }
    .st-key-hist_search_box div[data-baseweb="input"]::before { content: "🔍"; }

    .stProgress > div > div > div { background-color: var(--accent) !important; }
    .stProgress > div > div { background-color: var(--surface-2) !important; }

    .stTabs [data-baseweb="tab-list"] { gap: 20px; border-bottom: 1px solid var(--border); }
    .stTabs [data-baseweb="tab"] { color: var(--muted); font-family:'JetBrains Mono',monospace; font-size:12px; font-weight:600; }
    .stTabs [aria-selected="true"] { color: var(--accent) !important; }

    #MainMenu, footer { visibility: hidden; }
    header[data-testid="stHeader"] {
        background-color: var(--bg) !important; box-shadow: none !important;
        border: none !important; border-top: none !important; border-bottom: none !important;
    }
    header[data-testid="stHeader"]::before, header[data-testid="stHeader"]::after { display: none !important; content: none !important; }
    body::before, .stApp::before, #root::before { display: none !important; content: none !important; }
    [data-testid="stIconMaterial"] { font-family: 'Material Symbols Rounded' !important; }
    [data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"] {
        opacity: 1 !important; visibility: visible !important;
    }
    [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"],
    [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"] {
        color: var(--accent) !important;
    }
    div[data-testid="stToolbar"] { visibility: hidden; }
    input, textarea, select { color-scheme: dark !important; background-color: var(--surface-2) !important; color: var(--text) !important; }
    ::placeholder { color: var(--muted) !important; opacity: 1 !important; }

    /* --- Widget chrome ------------------------------------------------------
       Belt and braces. .streamlit/config.toml sets base = "dark", which is what
       actually makes Streamlit theme its own widgets correctly. These rules mean
       that if the config is ever missing, reset, or overwritten, labels stay
       readable and borders stay dark instead of the whole form going
       light-on-dark. */
    [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p,
    .stTextInput label, .stNumberInput label, .stSelectbox label,
    .stTextArea label, .stDateInput label, .stFileUploader label {
        color: var(--text) !important;
    }
    div[data-baseweb="input"], div[data-baseweb="textarea"],
    div[data-baseweb="select"] > div, div[data-baseweb="base-input"] {
        border-color: var(--border) !important;
    }
    div[data-baseweb="select"] svg { fill: var(--muted) !important; }
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {
        background-color: var(--surface-2) !important; color: var(--text) !important;
    }
    li[role="option"] { color: var(--text) !important; }
    li[role="option"]:hover, li[aria-selected="true"] { background-color: var(--accent-soft) !important; }

    /* --- Monthly Budget card ------------------------------------------------
       The figures used to be one markdown div with a nested <span> at a smaller
       font size, which left the two numbers sitting on mismatched baselines,
       and the "9% used  •  Rs X left" line used &nbsp; entities for spacing,
       which gave visibly uneven gaps either side of the bullet. Both are now
       flex rows: baseline alignment for the figures, an even gap for the meta
       line. */
    .budget-amounts { display: flex; align-items: baseline; gap: 8px; }
    .budget-spent { font-size: 18px; font-weight: 700; color: var(--text); }
    .budget-total { font-size: 12px; color: var(--muted); }
    .budget-meta { display: flex; align-items: center; gap: 10px; font-size: 11.5px; color: var(--text); margin-top: 0; }
    .budget-dot { color: var(--muted); }
    /* st.progress ships with generous vertical margins of its own, which left a
       visible gap between the bar and the "% used" line. Tighten both sides so
       the three elements read as one group. */
    .st-key-card_budget div[data-testid="stProgress"] { margin-top: 2px !important; margin-bottom: 2px !important; }
    .st-key-card_budget div[data-testid="stProgress"] > div { margin-bottom: 0 !important; }

    /* --- Cards --------------------------------------------------------------
       Drawn here rather than by st.container(border=True). Streamlit's own
       border comes from a version-dependent emotion class, and the configured
       theme base is "light", so it was never going to match this dark palette.
       Every card now carries an st-key-card_* class and takes its border,
       background, radius and padding from this stylesheet - deterministic, and
       it survives Streamlit upgrades.

       type_input_box and parsed_items_panel keep their original keys because
       other rules target them by name, so they are listed explicitly. */
    [class*="st-key-card_"],
    .st-key-type_input_box,
    .st-key-parsed_items_panel {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        padding: 18px 20px !important;
        margin-bottom: 16px !important;
        box-sizing: border-box !important;
    }
    /* Card content overflow fix. Streamlit pins a fixed pixel width on the
       inner wrappers (an HTML width="370" attribute on stElementContainer /
       stVerticalBlock and an inline style="width:370px" on stMarkdown and the
       widgets). That 370px is the COLUMN width, but the padded card content
       box is ~40px narrower - so the progress bar, dividers, inputs and
       buttons render 370px wide and spill PAST the card's right border,
       breaking the border visually. This showed up only on the deployed
       render (the deployed window fell into the width where Streamlit pins
       370px). Overriding those wrappers back to width:100% of the padded box
       keeps everything inside the border. Only vertical-stack wrappers are
       targeted (NOT stHorizontalBlock or stColumn) so multi-column rows keep
       their layout. */
    [class*="st-key-card_"] [data-testid="stElementContainer"],
    [class*="st-key-card_"] [data-testid="stVerticalBlock"],
    [class*="st-key-card_"] [data-testid="stMarkdown"],
    [class*="st-key-card_"] [data-testid="stMarkdownContainer"],
    [class*="st-key-card_"] div.stButton,
    [class*="st-key-card_"] [data-testid="stTextInput"],
    [class*="st-key-card_"] [data-testid="stTextArea"],
    [class*="st-key-card_"] [data-testid="stNumberInput"],
    [class*="st-key-card_"] [data-testid="stProgress"],
    .st-key-type_input_box [data-testid="stElementContainer"],
    .st-key-type_input_box [data-testid="stVerticalBlock"],
    .st-key-type_input_box [data-testid="stMarkdown"],
    .st-key-type_input_box [data-testid="stMarkdownContainer"],
    .st-key-type_input_box div.stButton,
    .st-key-type_input_box [data-testid="stTextInput"],
    .st-key-type_input_box [data-testid="stTextArea"],
    .st-key-parsed_items_panel [data-testid="stElementContainer"],
    .st-key-parsed_items_panel [data-testid="stVerticalBlock"],
    .st-key-parsed_items_panel [data-testid="stMarkdown"],
    .st-key-parsed_items_panel [data-testid="stMarkdownContainer"] {
        width: 100% !important; max-width: 100% !important; box-sizing: border-box !important;
    }
    /* Cards that sit side by side share a min-height, so the shorter one does
       not leave a ragged bottom edge on the row. This replaces the old trick of
       padding the Top Merchants list with blank rows, which produced those
       stray empty separator lines under the last merchant. */
    .st-key-card_quickadd, .st-key-card_budget { min-height: 198px !important; }
    .st-key-card_an_payment, .st-key-card_an_merchants { min-height: 322px !important; }

    /* --- Top Merchants rows -------------------------------------------------
       grid-template-columns: 1fr auto pins the amount to the right edge of the
       card and lets the name column absorb the slack. With min-width:0 a very
       long merchant name truncates instead of pushing the amount out of the
       card. A flex row with space-between could not guarantee either. */
    .merchant-row {
        display: grid; grid-template-columns: 1fr auto; align-items: center;
        gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--border);
        font-size: 12px;
    }
    .merchant-row:last-of-type { border-bottom: none; }
    .merchant-name { display: flex; align-items: center; gap: 9px; min-width: 0; }
    .merchant-name-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .merchant-amt { font-family: 'JetBrains Mono', monospace; white-space: nowrap; }
    .merchant-amt-pct { color: var(--muted); font-size: 10px; }

    /* --- Insight tiles -------------------------------------------------------
       Rendered as one CSS grid (see render_insight_tiles() in app.py), not
       st.columns - three separate History/Analytics/Categories copies each
       built their own st.columns(3) with slightly different per-tile HTML,
       and the gutters between them came out uneven since each copy sized its
       icon/label/value pieces independently instead of sharing one grid.
       A single grid with fixed column tracks guarantees every tile's icon,
       label, value and sub-line lines up to the same widths everywhere. */
    .insight-tile-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 22px; margin-bottom: 10px; }
    .insight-tile-head { display: flex; align-items: center; gap: 7px; }
    .insight-tile-icon { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; flex-shrink: 0; }
    .insight-tile-label { font-size: 10.5px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); font-weight: 700; }
    .insight-tile-value { font-size: 15px; font-weight: 700; color: var(--text); margin-top: 8px; }
    .insight-tile-sub { font-size: 10.5px; color: var(--muted); margin-top: 3px; }

    /* --- Insight rows ------------------------------------------------------
       Fixed-width icon slot so every line's text starts at the same x, whatever
       the emoji's advance width. */
    .insight-row { display: flex; align-items: flex-start; gap: 10px; font-size: 12px; color: var(--text); padding: 6px 0; }
    .insight-icon { display: inline-block; width: 18px; flex-shrink: 0; text-align: center; line-height: 1.45; }

    /* --- Chart card full-screen toggle ------------------------------------- */
    [class*="st-key-fsbtn_"] div.stButton button {
        background: transparent !important; border: 1px solid var(--border) !important;
        color: var(--muted) !important; padding: 2px 0 !important;
        min-height: 26px !important; height: 26px !important; font-size: 13px !important;
        border-radius: 6px !important; line-height: 1 !important;
    }
    @media (hover: hover) and (pointer: fine) {
        [class*="st-key-fsbtn_"] div.stButton button:hover {
            color: var(--accent) !important; border-color: var(--accent) !important;
            background: var(--accent-soft) !important;
        }
    }
    /* The toggle shares a row with the card title; pull it up onto the title's
       baseline so it reads as part of the header rather than a stray button. */
    [class*="st-key-fsbtn_"] { margin-top: -2px !important; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def get_expenses_df() -> pd.DataFrame:
    try:
        return storage.load_expenses()
    except Exception as e:
        st.error(f"Couldn't reach the database. Please check your connection and try again.\n\nDetails: {e}")
        return pd.DataFrame(columns=["id", "date", "raw_text", "merchant", "amount", "category", "source", "payment_mode", "account", "notes"])


df = get_expenses_df()
today = datetime.date.today()

NAV_ITEMS = [("🏠", "Dashboard"), ("➕", "Add Expense"), ("📄", "History"), ("📊", "Analytics"), ("🏷️", "Categories")]
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


def _scroll_to_top(nonce: str) -> None:
    """Scroll the main content area back to the top.

    Streamlit has no scroll API, so this injects a tiny script into a 0-height
    component and reaches into the parent document. Needed because buttons near
    the bottom of the page (e.g. Quick Actions -> Set Budget) change state near
    the TOP of the page, which previously looked like nothing had happened.

    `nonce` must differ between calls: an unchanged component is not re-rendered,
    so the script would never run a second time. Several selectors are tried
    because which element actually owns the scrollbar has moved around between
    Streamlit versions.
    """
    components.html(
        "<script>"
        f"/* {nonce} */"
        "const doc = window.parent.document;"
        "const targets = ["
        "  doc.querySelector('[data-testid=\"stMain\"]'),"
        "  doc.querySelector('section.main'),"
        "  doc.querySelector('[data-testid=\"stAppViewContainer\"]'),"
        "  doc.scrollingElement, doc.documentElement, doc.body];"
        "for (const t of targets) {"
        "  if (!t) continue;"
        "  try { t.scrollTo({top: 0, behavior: 'smooth'}); } catch (e) { t.scrollTop = 0; }"
        "}"
        "</script>",
        height=0,
    )


def card(name: str):
    """A bordered content card.

    Deliberately NOT st.container(border=True): that border is drawn by a
    version-dependent Streamlit emotion class and is themed from config.toml,
    whose base is "light" - so it could not match this dark palette and it
    stopped rendering entirely at one point. The container gets an
    st-key-card_<name> class instead and the border, background, radius and
    padding all come from CUSTOM_CSS, which this app controls.

    `name` must be unique per card on a page.
    """
    return st.container(key=f"card_{name}")


def chart_header(title: str, chart_id: str) -> bool:
    """Card title with a full-screen toggle pinned to the top-right.

    Shared by every page that renders a Plotly chart (Dashboard, Analytics,
    Categories), so expand/collapse behaves identically everywhere instead of
    each page reinventing it. `chart_id` only needs to be unique within the
    set of charts that can be full-screened together on one page render -
    IDs are namespaced per page (e.g. "an_category" vs "category") so two
    pages' charts never collide in st.session_state.fs_chart.

    Returns True if this chart is currently full-screen, so the caller knows
    whether to render it alone (full width) or as part of its normal layout.
    """
    st.session_state.setdefault("fs_chart", None)
    t_col, btn_col = st.columns([8, 1])
    with t_col:
        st.markdown(f'<div class="section-card-title">{title}</div>', unsafe_allow_html=True)
    with btn_col:
        is_fs = st.session_state.fs_chart == chart_id
        with st.container(key=f"fsbtn_{chart_id}"):
            if st.button(
                "✕" if is_fs else "⛶",
                key=f"fs_toggle_{chart_id}",
                help="Exit full screen" if is_fs else "Expand to full width",
            ):
                st.session_state.fs_chart = None if is_fs else chart_id
                st.rerun()
    return is_fs


def render_insight_tiles(tiles) -> None:
    """Renders a row of insight tiles (icon, label, value, optional sub-line).

    `tiles` is a list of (icon, color, label, value, sub) tuples. This is a
    single CSS grid, not st.columns - see the .insight-tile-grid comment in
    CUSTOM_CSS for why. Shared by History, Analytics and Categories so all
    three read from one grid definition instead of three near-duplicates
    that could each drift out of sync with each other.
    """
    cells = []
    for icon, color, label, value, sub in tiles:
        cells.append(
            '<div class="insight-tile">'
            '<div class="insight-tile-head">'
            f'<span class="insight-tile-icon" style="background:{color}22; color:{color};">{icon}</span>'
            f'<span class="insight-tile-label">{label}</span>'
            "</div>"
            f'<div class="insight-tile-value">{value}</div>'
            + (f'<div class="insight-tile-sub">{sub}</div>' if sub else "")
            + "</div>"
        )
    st.markdown(f'<div class="insight-tile-grid">{"".join(cells)}</div>', unsafe_allow_html=True)


def _nav_slug(label: str) -> str:
    """CSS-safe id for a nav label. Streamlit turns a container key into a class
    name verbatim, so a key containing a space ("navrow_Add Expense") becomes TWO
    classes and can't be targeted precisely. Slugify to keep one class per row."""
    return label.lower().replace(" ", "_")

with st.sidebar:
    st.markdown(
        '<div class="brand-block"><div class="brand-icon">₹</div>'
        '<div><div class="brand-title">Smart<br>Expense<br>Tracker</div>'
        '<div class="brand-sub">TRACK EVERY RUPEE</div></div></div>',
        unsafe_allow_html=True,
    )
    # --- Sidebar nav ---------------------------------------------------------
    # Every row is an st.button, including the active one, so all five rows are
    # the same element with the same box model. Previously the active row was a
    # markdown <div> and the rest were <button>s, which meant different padding
    # and different Streamlit wrapper margins: the highlighted row sat tighter
    # than its neighbours and its label started a few px further right.
    #
    # Icons are injected with CSS ::before at a FIXED width instead of being part
    # of the button label, because the emoji have different advance widths
    # (compare the narrow arrow of the plus sign to the wide house). With inline
    # icons the labels can never share a left edge.
    #
    # Every selector below is prefixed with section[data-testid="stSidebar"] on
    # purpose. The generic sidebar-button rules earlier in CUSTOM_CSS force a
    # transparent background on :hover/:focus/:active, and they all use
    # !important — so the active row's highlight only survives if these rules win
    # on specificity, which the prefix guarantees.
    _SB = 'section[data-testid="stSidebar"]'
    _active_slug = _nav_slug(st.session_state.page)
    _icon_rules = "".join(
        f'{_SB} [class*="st-key-navrow_{_nav_slug(lbl)}"] div.stButton button::before'
        f'{{ content: "{ic}"; }}'
        for ic, lbl in NAV_ITEMS
    )
    _active_sel = f'{_SB} [class*="st-key-navrow_{_active_slug}"] div.stButton button'
    st.markdown(
        "<style>"
        # Shared geometry for all five rows.
        f'{_SB} [class*="st-key-navrow_"] div.stButton button {{'
        "  display: flex !important; align-items: center !important;"
        "  justify-content: flex-start !important;"
        "  min-height: 40px !important; padding: 9px 12px !important;"
        "  border-radius: 6px !important; font-size: 13px !important;"
        "}"
        # Fixed-width icon column - this is what actually aligns the labels.
        f'{_SB} [class*="st-key-navrow_"] div.stButton button::before {{'
        "  display: inline-block; width: 20px; margin-right: 10px;"
        "  text-align: center; flex-shrink: 0; font-size: 14px; line-height: 1;"
        "}"
        + _icon_rules +
        # Active row. The accent bar is an inset box-shadow rather than a
        # border-left so it occupies no layout space and the label does not jump
        # 3px sideways when a row becomes active.
        f"{_active_sel}, {_active_sel}:hover, {_active_sel}:focus,"
        f" {_active_sel}:focus-visible, {_active_sel}:active {{"
        "  background: var(--accent-soft) !important;"
        "  color: var(--accent) !important; font-weight: 600 !important;"
        "  box-shadow: inset 3px 0 0 var(--accent) !important;"
        "}"
        f"{_active_sel} p, {_active_sel}:hover p, {_active_sel}:focus p {{"
        "  color: var(--accent) !important; font-weight: 600 !important;"
        "}"
        # Uniform vertical rhythm, plus a little air under the brand divider.
        f'{_SB} [class*="st-key-navrow_"] {{ margin: 0 0 4px 0 !important; }}'
        f'{_SB} [class*="st-key-navrow_{_nav_slug(NAV_ITEMS[0][1])}"] {{'
        "  margin-top: 6px !important;"
        "}"
        "</style>",
        unsafe_allow_html=True,
    )
    for icon, label in NAV_ITEMS:
        slug = _nav_slug(label)
        with st.container(key=f"navrow_{slug}"):
            if st.button(label, key=f"nav_{slug}") and st.session_state.page != label:
                st.session_state.page = label
                st.rerun()

    # --- Profile card --------------------------------------------------------
    # Pinned to the bottom of the sidebar with position:absolute + left/right
    # rather than position:fixed + a hardcoded width:220px. The old version was
    # measured against the viewport, not the sidebar, so dragging the sidebar
    # wider or narrower left the card at 220px - either floating short of the
    # edge or spilling over the main content.
    #
    # left/right instead of a width means the card always spans its container,
    # whatever that container's width happens to be. If a Streamlit wrapper ever
    # becomes the positioned ancestor instead of the sidebar itself, the card
    # stops being bottom-pinned but stays correctly sized - it degrades to
    # sitting in the flow rather than breaking the layout.
    st.markdown(
        "<style>"
        'section[data-testid="stSidebar"] { position: relative !important; }'
        ".st-key-sidebar_profile {"
        "  position: absolute !important; bottom: 16px !important;"
        "  left: 12px !important; right: 12px !important;"
        "  width: auto !important; box-sizing: border-box !important;"
        "}"
        ".sidebar-profile {"
        "  display: flex; align-items: center; gap: 10px;"
        "  padding: 10px 12px; background: var(--surface-2);"
        "  border: 1px solid var(--border); border-radius: 10px;"
        "  box-sizing: border-box; width: 100%; min-width: 0;"
        "}"
        ".sidebar-profile-avatar {"
        "  width: 32px; height: 32px; border-radius: 50%;"
        "  background: var(--accent-soft); color: var(--accent);"
        "  display: flex; align-items: center; justify-content: center;"
        "  font-weight: 700; font-size: 12px; flex-shrink: 0;"
        "}"
        # min-width:0 lets the text block shrink below its content width, which
        # is what allows the ellipsis to engage in a narrow sidebar.
        ".sidebar-profile-text { min-width: 0; overflow: hidden; }"
        ".sidebar-profile-name {"
        "  font-size: 12px; font-weight: 600; color: var(--text);"
        "  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
        "}"
        ".sidebar-profile-sub {"
        "  font-size: 10px; color: var(--muted);"
        "  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
        "}"
        # Very short viewports: unpin so the card can't sit on top of the nav.
        "@media (max-height: 520px) {"
        "  .st-key-sidebar_profile {"
        "    position: static !important; margin-top: 20px !important;"
        "  }"
        "}"
        "</style>",
        unsafe_allow_html=True,
    )
    with st.container(key="sidebar_profile"):
        st.markdown(
            '<div class="sidebar-profile">'
            f'<div class="sidebar-profile-avatar">{_initials(USER_NAME)}</div>'
            '<div class="sidebar-profile-text">'
            f'<div class="sidebar-profile-name" title="{USER_NAME}">{USER_NAME}</div>'
            '<div class="sidebar-profile-sub">View Profile</div>'
            "</div></div>",
            unsafe_allow_html=True,
        )

page = st.session_state.page
st.session_state.setdefault("fs_chart", None)


PAYMENT_ICONS = {"Cash": "💵", "UPI": "📱", "Card": "💳", "Other": "🔘"}

# One weight per COLUMN, and header and data rows both call st.columns() with
# this exact same list. Earlier this repo gave the header 6 columns (merging
# the pencil/trash slots into one) while data rows kept 7 separate columns -
# same total width, but 6 columns only have 5 gaps between them where 7
# columns have 6, so the two rows' column boundaries drifted apart by that
# extra gap, compounding column-over-column until Payment Mode/Action were
# visibly off. Keeping both rows on 6 columns everywhere removes the
# mismatch at the source instead of nudging text to paper over it. The two
# action buttons now share their one column via a CSS flex row (see
# ACTION_PAIR_CSS below) instead of being separate top-level columns.
_TABLE_COL_WEIGHTS = [1.3, 2.6, 1.6, 1.1, 1.2, 0.9]
_TABLE_HEADERS = ["Date", "Merchant", "Category", "Amount", "Payment Mode", "Action"]
_TABLE_HEADER_STYLES = [
    "text-align:left;", "text-align:left;", "text-align:left;",
    "text-align:left;", "text-align:left;",
    "text-align:center;",
]

# Puts the two buttons of an st.container(key=f"actionpair_...") side by
# side. A nested st.columns(2) inside an already-narrow column was tried
# first, but Streamlit auto-stacks nested columns vertically once the outer
# column gets this narrow, which is what bloated every row's height. Flexing
# the container's own children avoids nested columns entirely, so it stays
# side-by-side at any width.
#
# Two earlier attempts at the CSS both silently matched nothing: a child
# combinator (">") assuming stVerticalBlock was a direct child, then a plain
# descendant selector assuming it was a real ancestor either way. Rather than
# guess a third time which wrapper divs Streamlit inserts and in what order,
# this collapses ALL of the known wrapper testids (proven to exist in this
# app - see the stColumn/stVerticalBlock/stVerticalBlockBorderWrapper/
# stElementContainer chain the stat-card width fix already relies on)
# via display:contents, at any depth. That removes their boxes from layout
# entirely regardless of how they're nested, so the two real div.stButton
# elements end up as the direct, only flex items of the outer container -
# which is flexed by matching the key class itself, not a descendant of it,
# so it doesn't matter whether that class sits on the outermost wrapper or
# something deeper.
ACTION_PAIR_CSS = (
    "<style>"
    '[class*="st-key-actionpair_"] {'
    "  display: flex !important; flex-direction: row !important; gap: 6px !important;"
    # Every other cell in the row wraps its content in a div with
    # "padding:10px 0" (see c1-c5 above), which is what gives the row its
    # breathing room from the divider above and below. The action buttons
    # never got that padding - min-height:unset and the exprow rule that
    # zeroes stElementContainer's own margin/padding (below) strip it
    # entirely - so they sit flush against the line above them. Matching
    # padding here puts them on the same vertical footing as every other
    # column instead of looking un-padded specifically in this one slot.
    "  padding: 10px 0 !important;"
    "}"
    '[class*="st-key-actionpair_"] [data-testid="stVerticalBlockBorderWrapper"],'
    '[class*="st-key-actionpair_"] [data-testid="stVerticalBlock"],'
    '[class*="st-key-actionpair_"] [data-testid="stElementContainer"] {'
    "  display: contents !important;"
    "}"
    '[class*="st-key-actionpair_"] div.stButton { flex: 1 1 0 !important; }'
    "</style>"
)


def render_expense_table(df_slice, key_prefix):
    """Renders a header row plus one row per expense, with working edit (pencil)
    and delete (trash) actions. Shared by the Dashboard's Recent Expenses list
    and the History page's All Expenses table."""
    st.markdown(ACTION_PAIR_CSS, unsafe_allow_html=True)
    header_cols = st.columns(_TABLE_COL_WEIGHTS)
    for col, h, extra in zip(header_cols, _TABLE_HEADERS, _TABLE_HEADER_STYLES):
        col.markdown(
            '<div style="font-size:10px; color:var(--muted); text-transform:uppercase;'
            ' letter-spacing:0.05em; font-weight:700; padding-bottom:8px;'
            f' border-bottom:1px solid var(--border); {extra}">{h}</div>',
            unsafe_allow_html=True,
        )

    for idx, row in df_slice.iterrows():
        row_id = row.get("id", idx)
        edit_key = f"{key_prefix}_{row_id}"
        editing = st.session_state.get("editing_row") == edit_key

        with st.container(key=f"exprow_{edit_key}"):
            c1, c2, c3, c4, c5, c6 = st.columns(_TABLE_COL_WEIGHTS)
            date_str = row["date"].strftime("%d %b %Y") if pd.notnull(row["date"]) else "—"
            c1.markdown(f'<div style="padding:10px 0; font-size:12px;">📅&nbsp;{date_str}</div>', unsafe_allow_html=True)

            if editing:
                with c2:
                    new_merchant = st.text_input("Merchant", value=row["merchant"], key=f"{edit_key}_merchant", label_visibility="collapsed")
                with c3:
                    cat_idx = CATEGORY_NAMES.index(row["category"]) if row["category"] in CATEGORY_NAMES else len(CATEGORY_NAMES) - 1
                    new_cat = st.selectbox("Category", CATEGORY_NAMES, index=cat_idx, key=f"{edit_key}_cat", label_visibility="collapsed")
                with c4:
                    new_amount = st.number_input("Amount", value=float(row["amount"] or 0), key=f"{edit_key}_amt", label_visibility="collapsed", format="%.2f")
                with c5:
                    pm_idx = PAYMENT_MODES.index(row["payment_mode"]) if row.get("payment_mode") in PAYMENT_MODES else 0
                    new_pm = st.selectbox("Payment", PAYMENT_MODES, index=pm_idx, key=f"{edit_key}_pm", label_visibility="collapsed")
                with c6:
                    with st.container(key=f"actionpair_{edit_key}_edit"):
                        if st.button("✓", key=f"{edit_key}_save"):
                            try:
                                storage.update_expense(row["id"], {
                                    "merchant": new_merchant, "category": new_cat,
                                    "amount": new_amount, "payment_mode": new_pm,
                                })
                                st.session_state.editing_row = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"Couldn\'t save: {e}")
                        if st.button("✕", key=f"{edit_key}_cancel"):
                            st.session_state.editing_row = None
                            st.rerun()
            else:
                note = row.get("notes") or ""
                color = CATEGORY_COLORS.get(row["category"], "#9CA3AF")
                icon = CATEGORY_ICONS.get(row["category"], "•")
                pm_icon = PAYMENT_ICONS.get(row.get("payment_mode", "Cash"), "💵")
                note_html = f'<div style="font-size:10.5px; color:var(--muted); margin-top:2px; font-style:italic;">{note}</div>' if note else ""
                c2.markdown(f'<div style="padding:10px 0;"><div style="font-size:13px; font-weight:600;">{row["merchant"]}</div>{note_html}</div>', unsafe_allow_html=True)
                c3.markdown(f'<div style="padding:10px 0;"><span class="stamp-tag" style="color:{color};">{icon}&nbsp;{row["category"]}</span></div>', unsafe_allow_html=True)
                c4.markdown(f'<div style="padding:10px 0; font-family:monospace; font-weight:700; color:var(--accent);">₹{row["amount"]:,.2f}</div>', unsafe_allow_html=True)
                c5.markdown(f'<div style="padding:10px 0; font-size:12px;">{pm_icon}&nbsp;{row.get("payment_mode", "Cash")}</div>', unsafe_allow_html=True)
                with c6:
                    with st.container(key=f"actionpair_{edit_key}_view"):
                        if st.button("✏️", key=f"{edit_key}_editbtn"):
                            st.session_state.editing_row = edit_key
                            st.rerun()
                        if st.button("🗑️", key=f"{edit_key}_delbtn"):
                            try:
                                storage.delete_expense(row["id"])
                                st.rerun()
                            except Exception as e:
                                st.error(f"Couldn\'t delete: {e}")
            st.markdown('<div style="border-top:1px solid var(--border); margin:2px 0 4px;"></div>', unsafe_allow_html=True)


EXAMPLE_EN = "500 at McDonald's and 200 for shopping"
EXAMPLE_HI = "मैकडॉनल्ड्स में पांच सौ रुपये और शॉपिंग के लिए दो सौ रुपये"

# =============================================================================
# PAGE: DASHBOARD
# =============================================================================
if page == "Dashboard":
    hour = datetime.datetime.now().hour
    greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")
    st.markdown(f'<div class="page-title">{greeting}, {USER_NAME} 👋</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Here\'s your financial overview</div>', unsafe_allow_html=True)

    # Some controls live at the bottom of the page but act on the top of it.
    # Whoever sets this flag gets the viewport scrolled back up on the rerun.
    if st.session_state.pop("scroll_top", False):
        st.session_state.scroll_nonce = st.session_state.get("scroll_nonce", 0) + 1
        _scroll_to_top(str(st.session_state.scroll_nonce))

    month_df = df[(df["date"].dt.year == today.year) & (df["date"].dt.month == today.month)] if not df.empty else df
    total_spent = float(month_df["amount"].sum()) if not month_df.empty else 0.0
    txn_count = len(month_df)
    daily_avg = (total_spent / today.day) if today.day > 0 else 0.0
    if not month_df.empty:
        highest_row = month_df.loc[month_df["amount"].idxmax()]
        highest_amt = highest_row["amount"]
        highest_merchant = highest_row["merchant"]
        highest_date = highest_row["date"].strftime("%d %b") if pd.notnull(highest_row["date"]) else ""
    else:
        highest_amt, highest_merchant, highest_date = 0.0, "—", ""

    _stat_cards = [
        ("💳", "Total Spent", f"₹{total_spent:,.0f}", "This Month"),
        ("🔁", "Transactions", f"{txn_count}", "This Month"),
        ("📈", "Daily Average", f"₹{daily_avg:,.0f}", "This Month"),
        ("🔺", "Highest Expense", f"₹{highest_amt:,.0f}", f"{highest_merchant} • {highest_date}"),
    ]
    _stat_html = "".join(
        f'<div class="stat-card"><div class="stat-card-icon">{icon}</div>'
        f'<div class="stat-card-label">{label}</div>'
        f'<div class="stat-card-value">{value}</div>'
        f'<div class="stat-card-sub">{sub}</div></div>'
        for icon, label, value, sub in _stat_cards
    )
    st.markdown(f'<div class="stat-grid">{_stat_html}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    quick_col, budget_col = st.columns([2, 1])
    with quick_col:
        with card("quickadd"):
            st.markdown('<div class="section-card-title">Quick Add Expense</div>', unsafe_allow_html=True)
            if "dash_input_counter" not in st.session_state:
                st.session_state.dash_input_counter = 0
            qtext = st.text_input("quick add", placeholder="e.g. 500 at McDonald's", label_visibility="collapsed", key=f"dash_quick_{st.session_state.dash_input_counter}")
            if st.button("Add Expense", key="dash_quick_add", type="primary"):
                if qtext.strip():
                    try:
                        parsed_list = categorizer.parse_multiple_expenses(qtext)
                        # Only save items where an amount was actually detected — otherwise
                        # typing "lunch" with no number silently created a Rs 0 expense.
                        valid = [p for p in parsed_list if p["amount"] and p["amount"] > 0]
                        skipped = len(parsed_list) - len(valid)
                        if not valid:
                            st.warning("No amount detected — include a number, e.g. \"500 at McDonald's\".")
                        else:
                            for p in valid:
                                storage.save_expense({
                                    "raw_text": p["raw_text"], "merchant": p["merchant"],
                                    "amount": p["amount"], "category": p["category"], "source": "text",
                                })
                            st.session_state.dash_input_counter += 1
                            msg = f"Added {len(valid)} expense(s)!"
                            if skipped:
                                msg += f" ({skipped} skipped — no amount found.)"
                            st.success(msg)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Couldn't save: {e}")

    with budget_col:
        with card("budget"):
            st.markdown('<div class="section-card-title">Monthly Budget</div>', unsafe_allow_html=True)
            budget = storage.get_budget()
            if "dash_edit_budget" not in st.session_state:
                st.session_state.dash_edit_budget = budget <= 0

            if st.session_state.dash_edit_budget:
                new_budget = st.number_input("Budget amount (₹)", value=float(budget), min_value=0.0, step=500.0, key="dash_budget_input", label_visibility="collapsed")
                bsave_col, bcancel_col = st.columns(2)
                with bsave_col:
                    if st.button("✓ Save", key="dash_save_budget_btn", type="primary", use_container_width=True):
                        try:
                            storage.set_budget(new_budget)
                            st.session_state.dash_edit_budget = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Couldn't save budget: {e}")
                with bcancel_col:
                    if budget > 0 and st.button("✕ Cancel", key="dash_cancel_budget_btn", use_container_width=True):
                        st.session_state.dash_edit_budget = False
                        st.rerun()
            else:
                pct = min(total_spent / budget, 1.0) if budget > 0 else 0.0
                left = max(budget - total_spent, 0)
                st.markdown(
                    '<div class="budget-amounts">'
                    f'<span class="budget-spent">₹{total_spent:,.0f}</span>'
                    f'<span class="budget-total">/ ₹{budget:,.0f}</span>'
                    "</div>",
                    unsafe_allow_html=True,
                )
                st.progress(pct)
                st.markdown(
                    '<div class="budget-meta">'
                    f"<span>{pct * 100:.0f}% used</span>"
                    '<span class="budget-dot">•</span>'
                    f"<span>₹{left:,.0f} left</span>"
                    "</div>",
                    unsafe_allow_html=True,
                )
                if st.button("✏️ Edit Budget", key="dash_edit_budget_btn"):
                    st.session_state.dash_edit_budget = True
                    st.rerun()

    if not df.empty:
        cat_totals = storage.category_totals(month_df) if not month_df.empty else pd.Series(dtype=float)

        def _empty_note(msg: str = "No data this month.") -> None:
            st.markdown(
                '<div style="color:var(--muted); font-size:12px; padding:30px 0;'
                f' text-align:center;">{msg}</div>',
                unsafe_allow_html=True,
            )

        def _render_category_chart(height: int) -> None:
            if cat_totals.empty:
                _empty_note()
                return
            expanded = height >= 400
            colors = [CATEGORY_COLORS.get(c, "#9CA3AF") for c in cat_totals.index]
            centre_size = 15 if expanded is False else 24

            # Every size below is DERIVED from the data, never hardcoded, so a
            # long custom category name can't clip or overlap the legend.
            longest_label = max((len(str(c)) for c in cat_totals.index), default=0)
            # ~7.4px per character in JetBrains Mono at 12px, plus the swatch and
            # its padding; capped so one silly-long name can't eat the chart.
            legend_px = min(360, 52 + int(longest_label * 7.4))

            fig = go.Figure(data=[go.Pie(
                labels=cat_totals.index, values=cat_totals.values, hole=0.62,
                marker=dict(colors=colors, line=dict(color="#12161F", width=2)),
                textinfo="none",
                # sort=False keeps wedge order identical to cat_totals (already
                # sorted by spend), so the legend reads largest-first too.
                sort=False, direction="clockwise",
                hovertemplate="%{label}: ₹%{value:,.0f}<extra></extra>",
            )])

            # A legend is unreadable in the 220px card but useful once expanded.
            # It goes on the RIGHT, vertically: a horizontal legend put long
            # category names side by side and they overlapped and truncated
            # ("Bills & Utiliti/esTransport"). A vertical list cannot collide
            # however many categories exist.
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E6E9EF"), showlegend=expanded,
                legend=dict(
                    orientation="v", x=1.0, xanchor="left", y=0.5, yanchor="middle",
                    font=dict(size=12, color="#E6E9EF"),
                    itemsizing="constant", itemclick=False, itemdoubleclick=False,
                    bgcolor="rgba(0,0,0,0)",
                ),
                margin=dict(l=10, r=legend_px if expanded else 10, t=10, b=10),
                height=height,
                annotations=[dict(
                    text=f"₹{cat_totals.sum():,.0f}<br>"
                         "<span style='font-size:9px;color:#7C8494;'>TOTAL</span>",
                    x=0.5, y=0.5, font=dict(size=centre_size, color="#E6E9EF"),
                    showarrow=False, xref="paper", yref="paper",
                )],
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        def _render_trend_chart(height: int) -> None:
            if month_df.empty:
                _empty_note()
                return
            daily = month_df.groupby(month_df["date"].dt.day)["amount"].sum().sort_index()
            fig2 = go.Figure(data=[go.Scatter(
                x=daily.index, y=daily.values, mode="lines+markers",
                line=dict(color="#22C55E", width=2), marker=dict(size=5, color="#22C55E"),
                fill="tozeroy", fillcolor="rgba(34,197,94,0.10)",
                hovertemplate="Day %{x}: ₹%{y:,.0f}<extra></extra>",
            )])
            # dtick=1 / tickformat="d" stop Plotly inventing fractional day
            # numbers (9.2, 9.4 ...) when only a couple of days have data.
            # automargin + a left margin stop the rupee tick labels being clipped,
            # which is why the axis previously read "?000" and ".500".
            # Tick text was too dim and too small to read once expanded, so both
            # scale with the rendered height rather than being fixed.
            expanded = height >= 400
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#B4BCCB" if expanded else "#7C8494",
                          size=12 if expanded else 10),
                margin=dict(l=10, r=10, t=10, b=10), height=height,
                hoverlabel=dict(bgcolor="#171C27", bordercolor="#232A38",
                                font=dict(color="#E6E9EF", size=12)),
                xaxis=dict(
                    gridcolor="#232A38", showgrid=False, dtick=1, tickformat="d",
                    automargin=True, title=None,
                ),
                yaxis=dict(
                    gridcolor="#232A38", showgrid=True, automargin=True,
                    tickprefix="₹", separatethousands=True, rangemode="tozero",
                ),
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        CHART_SPECS = [
            ("category", "Spending by Category", _render_category_chart),
            ("trend", "Monthly Trend", _render_trend_chart),
        ]
        _fs = st.session_state.fs_chart

        if _fs in {cid for cid, _, _ in CHART_SPECS}:
            # Full screen: the chosen chart gets the whole row on its own.
            chart_id, title, renderer = next(c for c in CHART_SPECS if c[0] == _fs)
            with card(f"chart_{chart_id}"):
                chart_header(title, chart_id)
                renderer(560)
        else:
            for col, (chart_id, title, renderer) in zip(st.columns(2), CHART_SPECS):
                with col:
                    with card(f"chart_{chart_id}"):
                        chart_header(title, chart_id)
                        renderer(220)

        with card("recent"):
            st.markdown('<div class="section-card-title">Recent Expenses</div>', unsafe_allow_html=True)
            render_expense_table(df.head(5), "dash")

        # --- Insights (computed from real data) ---
        with card("dash_insights"):
            st.markdown('<div class="section-card-title">Insights For You</div>', unsafe_allow_html=True)
            # (icon, text) pairs rather than one pre-joined string, so the icon
            # can go in a fixed-width slot and every line's text starts level.
            insight_lines = []
            last_month = (today.replace(day=1) - datetime.timedelta(days=1))
            last_month_df = df[(df["date"].dt.year == last_month.year) & (df["date"].dt.month == last_month.month)]
            if not cat_totals.empty and not last_month_df.empty:
                last_cat_totals = storage.category_totals(last_month_df)
                top_cat = cat_totals.index[0]
                this_val = cat_totals.iloc[0]
                last_val = last_cat_totals.get(top_cat, 0)
                diff = this_val - last_val
                if diff > 0:
                    insight_lines.append(("📈", f"You spent ₹{diff:,.0f} more on {top_cat} compared to last month."))
                elif diff < 0:
                    insight_lines.append(("📉", f"You spent ₹{abs(diff):,.0f} less on {top_cat} compared to last month."))
            if not month_df.empty:
                weekday_totals = month_df.groupby(month_df["date"].dt.day_name())["amount"].sum()
                if not weekday_totals.empty:
                    top_day = weekday_totals.idxmax()
                    insight_lines.append(("📅", f"Your spending is highest on {top_day}s."))
            if not insight_lines:
                insight_lines.append(("💡", "Keep adding expenses to unlock personalized insights."))
            for icon, text in insight_lines:
                st.markdown(
                    '<div class="insight-row">'
                    f'<span class="insight-icon">{icon}</span><span>{text}</span>'
                    "</div>",
                    unsafe_allow_html=True,
                )

        # --- Quick Actions ---
        # Same technique as the sidebar nav: the icon is a CSS ::before at a fixed
        # width instead of part of the button label. With the emoji inline, four
        # centred labels of differing icon widths never lined up.
        QUICK_ACTIONS = [
            ("➕", "Add Expense", "add"),
            ("🎤", "Record Voice", "voice"),
            ("📊", "View Reports", "reports"),
            ("💰", "Set Budget", "budget"),
        ]
        with card("quickactions"):
            st.markdown('<div class="section-card-title">Quick Actions</div>', unsafe_allow_html=True)
            st.markdown(
                "<style>"
                '[class*="st-key-qarow_"] div.stButton button {'
                "  display: flex !important; align-items: center !important;"
                "  justify-content: flex-start !important; text-align: left !important;"
                "  padding: 10px 14px !important;"
                "}"
                '[class*="st-key-qarow_"] div.stButton button::before {'
                "  display: inline-block; width: 20px; margin-right: 10px;"
                "  text-align: center; flex-shrink: 0; font-size: 14px; line-height: 1;"
                "}"
                + "".join(
                    f'[class*="st-key-qarow_{slug}"] div.stButton button::before'
                    f'{{ content: "{icon}"; }}'
                    for icon, _, slug in QUICK_ACTIONS
                )
                + "</style>",
                unsafe_allow_html=True,
            )
            for col, (icon, label, slug) in zip(st.columns(4), QUICK_ACTIONS):
                with col:
                    with st.container(key=f"qarow_{slug}"):
                        if st.button(label, key=f"qa_{slug}"):
                            if slug == "add":
                                st.session_state.page = "Add Expense"
                                st.session_state.input_mode = "Type"
                            elif slug == "voice":
                                st.session_state.page = "Add Expense"
                                st.session_state.input_mode = "Speak"
                            elif slug == "reports":
                                st.session_state.page = "Analytics"
                            elif slug == "budget":
                                # The budget editor is at the top of this same
                                # page, so without the scroll the click looked
                                # like it had done nothing at all.
                                st.session_state.page = "Dashboard"
                                st.session_state.dash_edit_budget = True
                                st.session_state.scroll_top = True
                            st.rerun()
    else:
        st.markdown('<div class="section-card"><div style="color:var(--muted); font-size:13px;">No expenses yet — use Quick Add above or head to Add Expense.</div></div>', unsafe_allow_html=True)

# =============================================================================
# PAGE: ADD EXPENSE
# =============================================================================
elif page == "Add Expense":
    title_col, help_col = st.columns([4, 1])
    with title_col:
        st.markdown('<div class="page-title">Add Expense</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">Type, speak or upload — we\'ll take care of the rest</div>', unsafe_allow_html=True)
    with help_col:
        if "show_how_it_works" not in st.session_state:
            st.session_state.show_how_it_works = False
        if st.button("❓ How it works?", key="how_it_works_btn"):
            st.session_state.show_how_it_works = not st.session_state.show_how_it_works

    if st.session_state.get("show_how_it_works"):
        st.info(
            "**Type** a description like \"500 at McDonald's\" and hit Enter, or **Speak** it out loud — "
            "in English or Hindi, no need to pick which. You can describe several expenses in one go "
            "(\"500 at McDonald's and 200 for shopping\"), and each one shows up as its own editable card "
            "below before you save."
        )

    if "drafts" not in st.session_state:
        st.session_state.drafts = []
    if "input_mode" not in st.session_state:
        st.session_state.input_mode = "Type"
    if "input_key_counter" not in st.session_state:
        st.session_state.input_key_counter = 0

    # Both halves of the toggle are buttons, and the active one is restyled via
    # CSS. Previously the active half was a markdown <div> and the inactive half a
    # <button>: different box models meant the two sat at slightly different
    # heights with their labels on different baselines. Same fix, and same reason,
    # as the sidebar nav. Icons are ::before at a fixed width so both labels
    # centre identically despite the emoji having different advance widths.
    MODE_OPTIONS = [("⌨️", "Type"), ("🎤", "Speak")]
    _mode_active = st.session_state.input_mode.lower()
    st.markdown(
        "<style>"
        '[class*="st-key-moderow_"] div.stButton button {'
        "  display: flex !important; align-items: center !important;"
        "  justify-content: center !important; min-height: 44px !important;"
        "  font-size: 12.5px !important; font-weight: 600 !important;"
        "}"
        '[class*="st-key-moderow_"] div.stButton button::before {'
        "  display: inline-block; width: 18px; margin-right: 8px;"
        "  text-align: center; flex-shrink: 0; font-size: 14px; line-height: 1;"
        "}"
        + "".join(
            f'[class*="st-key-moderow_{lbl.lower()}"] div.stButton button::before'
            f'{{ content: "{ic}"; }}'
            for ic, lbl in MODE_OPTIONS
        )
        # Declared across every pseudo-class because the generic button rules in
        # CUSTOM_CSS force a surface-2 background on :focus/:active with
        # !important - the highlight would otherwise vanish on click.
        + f'[class*="st-key-moderow_{_mode_active}"] div.stButton button,'
          f'[class*="st-key-moderow_{_mode_active}"] div.stButton button:hover,'
          f'[class*="st-key-moderow_{_mode_active}"] div.stButton button:focus,'
          f'[class*="st-key-moderow_{_mode_active}"] div.stButton button:focus-visible,'
          f'[class*="st-key-moderow_{_mode_active}"] div.stButton button:active {{'
          "  background: var(--accent) !important; border-color: var(--accent) !important;"
          "  color: #06170C !important; font-weight: 700 !important;"
          "}"
        + f'[class*="st-key-moderow_{_mode_active}"] div.stButton button p {{'
          "  color: #06170C !important; font-weight: 700 !important;"
          "}"
        + "</style>",
        unsafe_allow_html=True,
    )
    for col, (icon, label) in zip(st.columns(2), MODE_OPTIONS):
        with col:
            with st.container(key=f"moderow_{label.lower()}"):
                if st.button(label, key=f"mode_{label.lower()}", use_container_width=True) \
                        and st.session_state.input_mode != label:
                    st.session_state.input_mode = label
                    st.rerun()

    parsed_text = None

    # A richer, varied set of tappable examples — 4 English + 4 Hindi
    QUICK_EXAMPLES_EN = ["500 at McDonald's", "200 for groceries", "Uber ride 150", "Netflix subscription 649"]
    QUICK_EXAMPLES_HI = ["500 मैकडॉनल्ड्स में", "200 किराना सामान के लिए", "उबर राइड 150", "नेटफ्लिक्स सब्स्क्रिप्शन 649"]

    if st.session_state.input_mode == "Type":
        with st.container(key="type_input_box"):
            st.markdown('<div style="font-size:12px; color:var(--muted); margin-bottom:8px;">Describe your expense (खर्च के बारे में बताएं)</div>', unsafe_allow_html=True)
            input_col, btn_col = st.columns([5, 1])
            with input_col:
                text_input = st.text_area("expense", placeholder="500 at McDonald's and 200 for shopping", label_visibility="collapsed", key=f"expense_text_{st.session_state.input_key_counter}", max_chars=300, height=110)
            with btn_col:
                st.markdown('<div style="height:2px;"></div>', unsafe_allow_html=True)
                st.button("↵ Enter", key="enter_btn", type="primary", use_container_width=True)
            # margin-top:-30px used to drag this up over the textarea, where it
            # could collide with the last line of typed text. It now sits below.
            st.markdown(
                '<div style="text-align:right; font-size:10px; color:var(--muted);'
                f' margin-top:2px; margin-right:8px;">{len(text_input)}/300</div>',
                unsafe_allow_html=True,
            )
            if text_input.strip():
                parsed_text = text_input

            st.markdown('<div style="font-size:11px; color:var(--muted); margin-top:14px; margin-bottom:6px;">Examples:</div>', unsafe_allow_html=True)
            with st.container(key="example_chip_row"):
                ex_cols = st.columns([3, 0.3, 3, 0.3, 2, 0.3, 3.4])
                for slot, i in enumerate([0, 2, 4, 6]):
                    with ex_cols[i]:
                        if st.button(QUICK_EXAMPLES_EN[slot], key=f"ex_en_{slot}"):
                            st.session_state[f"expense_text_{st.session_state.input_key_counter}"] = QUICK_EXAMPLES_EN[slot]; st.rerun()
                for sep in [1, 3, 5]:
                    with ex_cols[sep]:
                        st.markdown('<div style="text-align:center; color:var(--muted); padding-top:8px;">&middot;</div>', unsafe_allow_html=True)

    else:  # Speak mode
        with card("speak"):
            st.markdown('<div class="section-label" style="margin-bottom:4px;">1. Speak your expense</div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center; padding: 8px 0 4px;"><div class="pulse-ring-wrap"><div class="pulse-ring"></div><div class="pulse-ring" style="animation-delay:0.6s;"></div><div style="width:48px; height:48px; border-radius:50%; background:var(--accent-soft); border:1px solid #1F4A2C; display:flex; align-items:center; justify-content:center; font-size:20px; position:relative; z-index:2;">🎤</div></div><div style="font-size:13.5px; color:var(--text); font-weight:700; margin:14px 0 6px;">RECORD YOUR EXPENSE</div><div style="font-size:11.5px; color:var(--muted); line-height:1.6; margin-bottom:20px;">Tap to record, mention one or more expenses, tap again to stop.<br>Works in English or Hindi — no need to choose.</div></div>', unsafe_allow_html=True)
            with st.container(key="mic_frame"):
                audio = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="⏹ Stop Recording", format="wav", just_once=True, key="mic_input", use_container_width=True)

            st.markdown('<div style="font-size:11px; color:var(--muted); margin-top:14px; margin-bottom:6px;">Try saying something like:</div>', unsafe_allow_html=True)
            for row_examples, top_gap in ((QUICK_EXAMPLES_EN, "0"), (QUICK_EXAMPLES_HI, "6px")):
                for col, ex in zip(st.columns(4), row_examples):
                    col.markdown(
                        f'<div class="example-chip" style="margin-top:{top_gap};">{ex}</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown(
                '<div class="insight-row" style="font-size:11px; color:var(--muted); margin-top:14px;">'
                '<span class="insight-icon">ℹ️</span>'
                "<span>You can mention multiple expenses in one sentence.</span></div>",
                unsafe_allow_html=True,
            )

            if audio:
                with st.spinner("Listening..."):
                    transcribed, detected_lang, error = voice_input.transcribe_auto(audio)
                if error:
                    st.error(error)
                elif transcribed:
                    st.markdown(
                        '<div class="insight-row" style="background:var(--surface-2);'
                        ' border:1px solid var(--border); border-radius:8px;'
                        ' padding:12px 18px 16px 12px; margin-top:14px; margin-bottom:10px; font-size:12.5px;'
                        ' box-sizing:border-box; word-break:break-word;">'
                        '<span class="insight-icon">🎤</span>'
                        f'<span>"{transcribed}"'
                        f' <span style="color:var(--muted); font-size:10.5px;">({detected_lang})</span>'
                        "</span></div>",
                        unsafe_allow_html=True,
                    )
                    parsed_text = transcribed

    if parsed_text:
        st.session_state.drafts = categorizer.parse_multiple_expenses(parsed_text)
        st.session_state.draft_source = "voice" if st.session_state.input_mode == "Speak" else "text"
        st.session_state.input_key_counter += 1

    if st.session_state.drafts:
        preview_label = "2. Parsed Preview (Review & Confirm)" if st.session_state.get("draft_source") == "voice" else "AI Parsed Preview"
        st.markdown(f'<div style="display:flex; justify-content:space-between; align-items:center; margin-top:28px;"><span class="section-label" style="margin:0;">✨&nbsp;&nbsp;{preview_label}</span><span style="font-size:11px; color:var(--accent);">{len(st.session_state.drafts)} item(s) detected</span></div>', unsafe_allow_html=True)

        indices_to_remove = []
        with st.container(key="parsed_items_panel"):
            for i, draft in enumerate(st.session_state.drafts):
                if i > 0:
                    st.markdown('<div style="border-top:1px solid var(--border); margin:0 0 14px;"></div>', unsafe_allow_html=True)
                cat_color = CATEGORY_COLORS.get(draft["category"], "#9CA3AF")
                st.markdown(f'<style>.st-key-category_select_{i} div[data-baseweb="select"] > div {{ border-color: {cat_color} !important; color: {cat_color} !important; }}</style>', unsafe_allow_html=True)
                num_col, m_col, a_col, c_col, del_col = st.columns([0.4, 2, 1.3, 1.7, 0.5])
                with num_col:
                    st.markdown(
                        '<div class="parsed-item-spacer">.</div>'
                        f'<div class="parsed-num-wrap"><div class="parsed-num">{i + 1}</div></div>',
                        unsafe_allow_html=True,
                    )
                with m_col:
                    new_merchant = st.text_input("Merchant", value=draft["merchant"], key=f"merchant_{i}", label_visibility="visible")
                    draft["merchant"] = new_merchant
                with a_col:
                    new_amount = st.number_input("Amount", value=float(draft["amount"] or 0), key=f"amount_{i}", label_visibility="visible", format="%.2f")
                    draft["amount"] = new_amount
                with c_col:
                    default_idx = CATEGORY_NAMES.index(draft["category"]) if draft["category"] in CATEGORY_NAMES else len(CATEGORY_NAMES) - 1
                    new_cat = st.selectbox("Category", CATEGORY_NAMES, index=default_idx, key=f"category_select_{i}", label_visibility="visible")
                    draft["category"] = new_cat
                with del_col:
                    st.markdown('<div class="parsed-item-spacer">.</div>', unsafe_allow_html=True)
                    if st.button("🗑️", key=f"discard_btn_{i}", help="Remove this item"):
                        indices_to_remove.append(i)

        if indices_to_remove:
            st.session_state.drafts = [d for j, d in enumerate(st.session_state.drafts) if j not in indices_to_remove]
            st.rerun()

        if st.button("+ Add another item", key="add_item_btn"):
            st.session_state.drafts.append({"raw_text": "", "amount": 0, "merchant": "New Item", "category": "Other", "confidence": "low"})
            st.rerun()

        details_label = "3. Details (Optional)" if st.session_state.get("draft_source") == "voice" else "Details (Optional)"
        st.markdown(f'<div class="section-label" style="margin-top:20px;">{details_label}</div>', unsafe_allow_html=True)
        d_col1, d_col2, d_col3 = st.columns(3)
        with d_col1:
            expense_date = st.date_input("Date", value=today, key="expense_date")
        with d_col2:
            payment_mode = st.selectbox("Payment Mode", PAYMENT_MODES, key="payment_mode_select")
        with d_col3:
            account = st.text_input("Account", placeholder="Select account", key="account_input")

        notes = st.text_area("Notes", placeholder="Add a note (optional)", key="notes_input", max_chars=200)

        st.markdown('<div class="section-label" style="margin-top:10px;">Attachment (Optional)</div>', unsafe_allow_html=True)
        # The 5MB in this label was never enforced and never shown - Streamlit
        # displays its own server limit, which defaults to 200MB. The real limit
        # now lives in .streamlit/config.toml (maxUploadSize = 5) so the number
        # the user sees is the number that applies.
        uploaded_file = st.file_uploader("Upload receipt or bill", type=["png", "jpg", "jpeg", "pdf"], key="receipt_upload", label_visibility="collapsed")
        if uploaded_file:
            st.caption(f"📎 {uploaded_file.name} attached (stored as a note reference — automatic receipt scanning isn't built yet)")

        clear_col, save_col = st.columns([1, 2])
        with clear_col:
            if st.button("↺ Clear All", key="clear_all_btn"):
                st.session_state.drafts = []
                st.session_state.input_key_counter += 1
                st.rerun()
        with save_col:
            if st.button(f"✓ Save Expense ({len(st.session_state.drafts)} Items)", key="save_all_btn", type="primary"):
                blank = [i + 1 for i, d in enumerate(st.session_state.drafts)
                         if not d.get("amount") or float(d["amount"]) <= 0]
                if blank:
                    st.warning(
                        "Item(s) " + ", ".join(f"#{n}" for n in blank) +
                        " have no amount. Enter an amount above, or remove the item, then save."
                    )
                    st.stop()
                try:
                    for draft in st.session_state.drafts:
                        note_text = notes or ""
                        if uploaded_file:
                            note_text = (note_text + f" [attached: {uploaded_file.name}]").strip()
                        storage.save_expense({
                            "raw_text": draft["raw_text"], "merchant": draft["merchant"],
                            "amount": draft["amount"] or 0, "category": draft["category"],
                            "source": st.session_state.get("draft_source", "text"),
                            "date": expense_date.isoformat(), "payment_mode": payment_mode,
                            "account": account, "notes": note_text,
                        })
                    st.session_state.drafts = []
                    st.success("Saved!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Couldn't save — check your connection.\n\nDetails: {e}")

# =============================================================================
# PAGE: HISTORY
# =============================================================================
elif page == "History":
    title_col, help_col = st.columns([4, 1])
    with title_col:
        st.markdown('<div class="page-title">History</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">View, search and manage your past expenses</div>', unsafe_allow_html=True)
    with help_col:
        if "hist_how_it_works" not in st.session_state:
            st.session_state.hist_how_it_works = False
        if st.button("❓ How it works?", key="hist_how_it_works_btn"):
            st.session_state.hist_how_it_works = not st.session_state.hist_how_it_works
    if st.session_state.get("hist_how_it_works"):
        st.info(
            "Filter by date, category or payment mode, or search by merchant/note. "
            "Click **▾ Filters** for an amount range. Click ✏️ on any row to edit it in "
            "place, or 🗑️ to delete it."
        )

    f1, f2, f3 = st.columns(3)
    with f1:
        with st.container(key="hist_filter_date"):
            date_range = st.selectbox("Date Range", ["All time", "Last 7 days", "Last 30 days", "This month", "Custom"], key="hist_date")
    with f2:
        with st.container(key="hist_filter_cat"):
            category_filter = st.selectbox("Category", ["All Categories"] + CATEGORY_NAMES, key="hist_cat")
    with f3:
        with st.container(key="hist_filter_pay"):
            payment_filter = st.selectbox("Payment Mode", ["All"] + PAYMENT_MODES, key="hist_pay")

    custom_start, custom_end = None, None
    if date_range == "Custom":
        cd1, cd2 = st.columns(2)
        with cd1:
            custom_start = st.date_input("From", value=today - datetime.timedelta(days=30), key="hist_custom_start")
        with cd2:
            custom_end = st.date_input("To", value=today, key="hist_custom_end")

    search_col, filter_col, export_col = st.columns([3, 1, 1])
    with search_col:
        with st.container(key="hist_search_box"):
            search_query = st.text_input("Search", placeholder="Search merchant, note...", label_visibility="collapsed", key="hist_search")
    with filter_col:
        if "hist_show_adv" not in st.session_state:
            st.session_state.hist_show_adv = False
        if st.button("▾ Filters", key="hist_filters_btn", use_container_width=True):
            st.session_state.hist_show_adv = not st.session_state.hist_show_adv

    if st.session_state.hist_show_adv:
        amt_col1, amt_col2 = st.columns(2)
        with amt_col1:
            min_amt = st.number_input("Min Amount (₹)", value=0.0, min_value=0.0, step=100.0, key="hist_min_amt")
        with amt_col2:
            max_amt = st.number_input("Max Amount (₹)", value=0.0, min_value=0.0, step=100.0, key="hist_max_amt", help="0 = no upper limit")
    else:
        min_amt, max_amt = 0.0, 0.0

    filtered = df.copy()
    if not filtered.empty:
        if category_filter != "All Categories":
            filtered = filtered[filtered["category"] == category_filter]
        if payment_filter != "All":
            filtered = filtered[filtered["payment_mode"] == payment_filter]
        if date_range == "Last 7 days":
            filtered = filtered[filtered["date"] >= pd.Timestamp(today - datetime.timedelta(days=7))]
        elif date_range == "Last 30 days":
            filtered = filtered[filtered["date"] >= pd.Timestamp(today - datetime.timedelta(days=30))]
        elif date_range == "This month":
            filtered = filtered[(filtered["date"].dt.year == today.year) & (filtered["date"].dt.month == today.month)]
        elif date_range == "Custom" and custom_start and custom_end:
            filtered = filtered[(filtered["date"] >= pd.Timestamp(custom_start)) & (filtered["date"] < pd.Timestamp(custom_end) + pd.Timedelta(days=1))]
        if search_query.strip():
            q = search_query.strip().lower()
            filtered = filtered[filtered["merchant"].str.lower().str.contains(q, na=False) | filtered["notes"].str.lower().str.contains(q, na=False)]
        if min_amt > 0:
            filtered = filtered[filtered["amount"] >= min_amt]
        if max_amt > 0:
            filtered = filtered[filtered["amount"] <= max_amt]

    with export_col:
        if not filtered.empty:
            csv_data = filtered[["date", "merchant", "category", "amount", "payment_mode", "notes"]].to_csv(index=False)
            st.download_button("⬇ Export", data=csv_data, file_name=f"expenses_{today.isoformat()}.csv", mime="text/csv", key="export_csv_btn")

    total_exp = float(filtered["amount"].sum()) if not filtered.empty else 0.0
    this_month_exp = storage.month_total(filtered, today.year, today.month) if not filtered.empty else 0.0
    this_month_count = len(filtered[(filtered["date"].dt.year == today.year) & (filtered["date"].dt.month == today.month)]) if not filtered.empty else 0
    avg_exp = (total_exp / len(filtered)) if not filtered.empty else 0.0
    top_cat_series = storage.category_totals(filtered) if not filtered.empty else pd.Series(dtype=float)
    top_cat_name = top_cat_series.index[0] if not top_cat_series.empty else "—"
    top_cat_amt = top_cat_series.iloc[0] if not top_cat_series.empty else 0.0
    top_cat_pct = (top_cat_amt / total_exp * 100) if total_exp > 0 else 0
    top_cat_icon = CATEGORY_ICONS.get(top_cat_name, "•")
    top_cat_color = CATEGORY_COLORS.get(top_cat_name, "#9CA3AF")

    s1, s2, s3, s4 = st.columns(4)
    s1.markdown(f'<div class="stat-card"><div class="stat-card-label">Total Expenses</div><div class="stat-card-value">₹{total_exp:,.2f}</div><div class="stat-card-sub">{len(filtered)} Transactions</div></div>', unsafe_allow_html=True)
    s2.markdown(f'<div class="stat-card"><div class="stat-card-label">This Month</div><div class="stat-card-value">₹{this_month_exp:,.2f}</div><div class="stat-card-sub">{this_month_count} Transactions</div></div>', unsafe_allow_html=True)
    s3.markdown(f'<div class="stat-card"><div class="stat-card-label">Average</div><div class="stat-card-value">₹{avg_exp:,.2f}</div><div class="stat-card-sub">Per Transaction</div></div>', unsafe_allow_html=True)
    s4.markdown(
        f'<div class="stat-card"><div class="stat-card-label">Top Category</div>'
        f'<div style="display:flex; align-items:center; gap:6px; margin-top:4px;">'
        f'<span style="width:22px; height:22px; border-radius:50%; background:{top_cat_color}22; color:{top_cat_color}; display:flex; align-items:center; justify-content:center; font-size:11px;">{top_cat_icon}</span>'
        f'<span class="stat-card-value" style="margin-top:0;">{top_cat_name}</span></div>'
        f'<div class="stat-card-sub">₹{top_cat_amt:,.2f} ({top_cat_pct:.0f}%)</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    with card("allexpenses"):
        st.markdown(f'<div class="section-card-title">All Expenses ({len(filtered)})</div>', unsafe_allow_html=True)
        if filtered.empty:
            st.markdown('<div style="color:var(--muted); font-size:12.5px;">No transactions match this filter.</div>', unsafe_allow_html=True)
        else:
            PAGE_SIZE = 8
            if "hist_page_num" not in st.session_state:
                st.session_state.hist_page_num = 1
            total_pages = max((len(filtered) - 1) // PAGE_SIZE + 1, 1)
            st.session_state.hist_page_num = min(st.session_state.hist_page_num, total_pages)
            start = (st.session_state.hist_page_num - 1) * PAGE_SIZE
            page_slice = filtered.iloc[start:start + PAGE_SIZE]

            render_expense_table(page_slice, "hist")

            if total_pages > 1:
                nav_cols = st.columns([0.6] + [0.5] * total_pages + [0.6, 4])
                with nav_cols[0]:
                    if st.button("←", key="hist_prev", disabled=(st.session_state.hist_page_num <= 1), use_container_width=True):
                        st.session_state.hist_page_num -= 1; st.rerun()
                # Third instance of the same bug as the sidebar nav and the
                # Type/Speak toggle: the current page was a markdown <div> while
                # every other page was a <button>, so the highlighted number sat
                # at a different height from its neighbours. All buttons now.
                #
                # NOTE: [class~=] (exact whitespace-separated token) rather than
                # [class*=] (substring) here, because with substring matching an
                # active page 1 would also style pages 10-19.
                _pg = st.session_state.hist_page_num
                st.markdown(
                    "<style>"
                    f'[class~="st-key-pgrow_{_pg}"] div.stButton button,'
                    f'[class~="st-key-pgrow_{_pg}"] div.stButton button:hover,'
                    f'[class~="st-key-pgrow_{_pg}"] div.stButton button:focus,'
                    f'[class~="st-key-pgrow_{_pg}"] div.stButton button:focus-visible,'
                    f'[class~="st-key-pgrow_{_pg}"] div.stButton button:active {{'
                    "  background: var(--accent) !important;"
                    "  border-color: var(--accent) !important;"
                    "  color: #06170C !important; font-weight: 700 !important;"
                    "}"
                    f'[class~="st-key-pgrow_{_pg}"] div.stButton button p {{'
                    "  color: #06170C !important; font-weight: 700 !important;"
                    "}"
                    "</style>",
                    unsafe_allow_html=True,
                )
                for p in range(1, total_pages + 1):
                    with nav_cols[p]:
                        with st.container(key=f"pgrow_{p}"):
                            if st.button(str(p), key=f"hist_page_{p}", use_container_width=True) \
                                    and p != st.session_state.hist_page_num:
                                st.session_state.hist_page_num = p
                                st.rerun()
                with nav_cols[total_pages + 1]:
                    if st.button("→", key="hist_next", disabled=(st.session_state.hist_page_num >= total_pages), use_container_width=True):
                        st.session_state.hist_page_num += 1; st.rerun()
                with nav_cols[total_pages + 2]:
                    st.markdown(f'<div style="text-align:right; font-size:11px; color:var(--muted); padding-top:10px;">Showing {start + 1} to {min(start + PAGE_SIZE, len(filtered))} of {len(filtered)}</div>', unsafe_allow_html=True)

    if not filtered.empty:
        day_totals = filtered.groupby(filtered["date"].dt.date)["amount"].sum()
        most_spent_day = day_totals.idxmax()
        most_spent_amt = day_totals.max()
        highest_row = filtered.loc[filtered["amount"].idxmax()]
        top_m = storage.top_merchants(filtered, n=1)
        frequent_merchant = top_m.iloc[0]["merchant"] if not top_m.empty else "—"
        frequent_count = int(top_m.iloc[0]["count"]) if not top_m.empty else 0

        with card("hist_insights"):
            st.markdown('<div class="section-card-title">Insights</div>', unsafe_allow_html=True)
            render_insight_tiles([
                ("📅", "#A78BFA", "MOST SPENT DAY", most_spent_day.strftime("%d %b %Y"), f"You spent ₹{most_spent_amt:,.2f}"),
                ("📈", "#34D399", "HIGHEST EXPENSE", f"₹{highest_row['amount']:,.2f}", highest_row["merchant"]),
                ("🚗", "#60A5FA", "FREQUENT MERCHANT", frequent_merchant, f"{frequent_count} time(s)"),
            ])

        st.markdown('<div style="font-size:11px; color:var(--muted); margin-top:10px;">ℹ️ Keep tracking your expenses to get better insights.</div>', unsafe_allow_html=True)

# =============================================================================
# PAGE: ANALYTICS
# =============================================================================
elif page == "Analytics":
    st.markdown('<div class="page-title">Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Visualize your spending patterns and insights</div>', unsafe_allow_html=True)

    af1, af2, af3 = st.columns(3)
    with af1:
        a_date_range = st.selectbox("Date Range", ["All time", "Last 7 days", "Last 30 days", "This month"], key="an_date")
    with af2:
        a_category = st.selectbox("Category", ["All Categories"] + CATEGORY_NAMES, key="an_cat")
    with af3:
        a_payment = st.selectbox("Payment Mode", ["All"] + PAYMENT_MODES, key="an_pay")

    a_filtered = df.copy()
    if not a_filtered.empty:
        if a_category != "All Categories":
            a_filtered = a_filtered[a_filtered["category"] == a_category]
        if a_payment != "All":
            a_filtered = a_filtered[a_filtered["payment_mode"] == a_payment]
        if a_date_range == "Last 7 days":
            a_filtered = a_filtered[a_filtered["date"] >= pd.Timestamp(today - datetime.timedelta(days=7))]
        elif a_date_range == "Last 30 days":
            a_filtered = a_filtered[a_filtered["date"] >= pd.Timestamp(today - datetime.timedelta(days=30))]
        elif a_date_range == "This month":
            a_filtered = a_filtered[(a_filtered["date"].dt.year == today.year) & (a_filtered["date"].dt.month == today.month)]

    if not a_filtered.empty:
        csv_data = a_filtered[["date", "merchant", "category", "amount", "payment_mode", "notes"]].to_csv(index=False)
        st.download_button("⬇ Download Report", data=csv_data, file_name=f"analytics_{today.isoformat()}.csv", mime="text/csv", key="download_report_btn")

    if a_filtered.empty:
        st.markdown('<div class="section-card"><div style="color:var(--muted); font-size:13px;">No data for this filter.</div></div>', unsafe_allow_html=True)
    else:
        total_a = float(a_filtered["amount"].sum())
        this_month_a = storage.month_total(a_filtered, today.year, today.month)
        this_month_a_count = len(a_filtered[(a_filtered["date"].dt.year == today.year) & (a_filtered["date"].dt.month == today.month)])
        avg_a = total_a / len(a_filtered) if len(a_filtered) else 0
        highest_row = a_filtered.loc[a_filtered["amount"].idxmax()]

        s1, s2, s3, s4 = st.columns(4)
        s1.markdown(f'<div class="stat-card"><div class="stat-card-label">Total Expenses</div><div class="stat-card-value">₹{total_a:,.0f}</div><div class="stat-card-sub">{len(a_filtered)} Transactions</div></div>', unsafe_allow_html=True)
        s2.markdown(f'<div class="stat-card"><div class="stat-card-label">This Month</div><div class="stat-card-value">₹{this_month_a:,.0f}</div><div class="stat-card-sub">{this_month_a_count} Transactions</div></div>', unsafe_allow_html=True)
        s3.markdown(f'<div class="stat-card"><div class="stat-card-label">Average Per Day</div><div class="stat-card-value">₹{avg_a:,.0f}</div><div class="stat-card-sub">{len(a_filtered)} Transactions</div></div>', unsafe_allow_html=True)
        s4.markdown(f'<div class="stat-card"><div class="stat-card-label">Highest Expense</div><div class="stat-card-value">₹{highest_row["amount"]:,.0f}</div><div class="stat-card-sub">{highest_row["merchant"]}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        cat_totals_a = storage.category_totals(a_filtered)

        def _render_an_category(height: int) -> None:
            colors = [CATEGORY_COLORS.get(c, "#9CA3AF") for c in cat_totals_a.index]
            fig = go.Figure(data=[go.Pie(labels=cat_totals_a.index, values=cat_totals_a.values, hole=0.62, marker=dict(colors=colors, line=dict(color="#12161F", width=2)), textinfo="none", hovertemplate="%{label}: ₹%{value:,.0f}<extra></extra>")])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#E6E9EF"), showlegend=True, legend=dict(font=dict(size=10)), margin=dict(l=0,r=0,t=10,b=10), height=height,
                annotations=[dict(text=f"₹{cat_totals_a.sum():,.0f}<br><span style='font-size:9px;color:#7C8494;'>Total</span>", x=0.5, y=0.5, font=dict(size=15, color="#E6E9EF"), showarrow=False)])
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        def _render_an_time(height: int) -> None:
            daily_a = a_filtered.groupby(a_filtered["date"].dt.date)["amount"].sum().sort_index()
            fig2 = go.Figure(data=[go.Scatter(
                x=list(daily_a.index), y=daily_a.values, mode="lines+markers",
                line=dict(color="#22C55E", width=2), marker=dict(size=6, color="#22C55E"),
                hovertemplate="%{x|%d %b %Y}: ₹%{y:,.0f}<extra></extra>",
            )])
            # Without an explicit date tick spacing, a range of only a day or
            # two makes Plotly fall back to HOURLY ticks - the axis read
            # "00:00 06:00 12:00 18:00" with a single "Aug 9, 2026" caption
            # underneath. dtick is one day in milliseconds, which is the unit
            # Plotly expects on a date axis.
            ONE_DAY_MS = 86_400_000
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#B4BCCB", size=11),
                margin=dict(l=10, r=10, t=10, b=10), height=height,
                hoverlabel=dict(bgcolor="#171C27", bordercolor="#232A38",
                                font=dict(color="#E6E9EF", size=12)),
                xaxis=dict(
                    type="date", dtick=ONE_DAY_MS, tickformat="%d %b",
                    gridcolor="#232A38", showgrid=False, automargin=True, title=None,
                ),
                yaxis=dict(
                    gridcolor="#232A38", showgrid=True, automargin=True,
                    tickprefix="₹", separatethousands=True, rangemode="tozero",
                ),
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

        AN_TOP_CHARTS = [
            ("an_category", "Expenses by Category", _render_an_category),
            ("an_time", "Expenses Over Time", _render_an_time),
        ]
        _an_fs = st.session_state.fs_chart
        if _an_fs in {cid for cid, _, _ in AN_TOP_CHARTS}:
            # Full screen: the chosen chart gets the whole row on its own.
            chart_id, title, renderer = next(c for c in AN_TOP_CHARTS if c[0] == _an_fs)
            with card(chart_id):
                chart_header(title, chart_id)
                renderer(560)
        else:
            for col, (chart_id, title, renderer) in zip(st.columns(2), AN_TOP_CHARTS):
                with col:
                    with card(chart_id):
                        chart_header(title, chart_id)
                        renderer(260)

        def _render_an_payment(height: int) -> None:
            pm_totals = storage.payment_mode_totals(a_filtered)
            pm_colors = {"Cash": "#34D399", "UPI": "#60A5FA", "Card": "#A78BFA", "Other": "#F87171"}
            colors2 = [pm_colors.get(p, "#9CA3AF") for p in pm_totals.index]
            fig3 = go.Figure(data=[go.Pie(labels=pm_totals.index, values=pm_totals.values, hole=0.62, marker=dict(colors=colors2, line=dict(color="#12161F", width=2)), textinfo="none", hovertemplate="%{label}: ₹%{value:,.0f}<extra></extra>")])
            fig3.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#E6E9EF"), showlegend=True, legend=dict(font=dict(size=10)), margin=dict(l=0,r=0,t=10,b=10), height=height,
                annotations=[dict(text=f"₹{pm_totals.sum():,.0f}<br><span style='font-size:9px;color:#7C8494;'>Total</span>", x=0.5, y=0.5, font=dict(size=14, color="#E6E9EF"), showarrow=False)])
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

        def _render_an_merchants() -> None:
            st.markdown('<div class="section-card-title">Top Merchants</div>', unsafe_allow_html=True)
            top_m = storage.top_merchants(a_filtered, n=5)
            # Percentages are of the whole filtered spend, not just the spend
            # of the top five - otherwise the listed percentages always summed
            # to 100% however small a slice of total spending they represented.
            total_spend = float(a_filtered["amount"].sum())
            if top_m.empty:
                st.markdown(
                    '<div style="color:var(--muted); font-size:12px; padding:20px 0;">'
                    "No merchant data for this filter.</div>",
                    unsafe_allow_html=True,
                )
            for _, row in top_m.reset_index(drop=True).iterrows():
                pct = (row["amount"] / total_spend * 100) if total_spend > 0 else 0
                rank = int(row.name) + 1
                txns = int(row["count"])
                st.markdown(
                    '<div class="merchant-row">'
                    '<div class="merchant-name">'
                    f'<span class="parsed-num">{rank}</span>'
                    f'<span class="merchant-name-text">{row["merchant"]} ({txns}x)</span>'
                    "</div>"
                    f'<div class="merchant-amt">₹{row["amount"]:,.0f}'
                    f'<span class="merchant-amt-pct"> ({pct:.0f}%)</span></div>'
                    "</div>",
                    unsafe_allow_html=True,
                )

        if st.session_state.fs_chart == "an_payment":
            # Top Merchants isn't a chart, so it just steps aside for the row
            # while Payment Mode is full screen, the same way a paired chart
            # would - it comes back once the toggle is off.
            with card("an_payment"):
                chart_header("Payment Mode Distribution", "an_payment")
                _render_an_payment(560)
        else:
            pc1, pc2 = st.columns(2)
            with pc1:
                with card("an_payment"):
                    chart_header("Payment Mode Distribution", "an_payment")
                    _render_an_payment(240)
            with pc2:
                with card("an_merchants"):
                    _render_an_merchants()

        with card("an_insights"):
            st.markdown('<div class="section-card-title">Insights</div>', unsafe_allow_html=True)
            # top_m computed here too (not reused from _render_an_merchants,
            # whose copy is local to that function) - same query, needed by
            # the "Frequent Merchant" tile below.
            top_m = storage.top_merchants(a_filtered, n=5)
            # BUG FIX: this used df["date"].idxmax(), which is the row with the
            # LATEST date - not the day with the highest spend. With 9 Aug at
            # Rs 1,200 and 10 Aug at Rs 700 it reported 10 Aug. It now takes the
            # idxmax of the per-day TOTALS, which is what the label claims.
            daily_totals = a_filtered.groupby(a_filtered["date"].dt.date)["amount"].sum()
            if daily_totals.empty:
                most_spent_day, most_spent_sub = "—", ""
            else:
                peak = daily_totals.idxmax()
                most_spent_day = peak.strftime("%d %b %Y")
                most_spent_sub = f"₹{daily_totals.max():,.0f} across {int((a_filtered['date'].dt.date == peak).sum())} txns"

            highest_sub = str(highest_row["merchant"])
            # "Frequent" should mean most TRANSACTIONS, not the largest spend -
            # top_m is ordered by amount, so pick the max by count explicitly.
            if top_m.empty:
                frequent_merchant, frequent_sub = "—", ""
            else:
                freq_row = top_m.loc[top_m["count"].idxmax()]
                frequent_merchant = str(freq_row["merchant"])
                frequent_sub = f"{int(freq_row['count'])} transactions"

            render_insight_tiles([
                ("📅", "#A78BFA", "MOST SPENT DAY", most_spent_day, most_spent_sub),
                ("📈", "#34D399", "HIGHEST EXPENSE", f"₹{highest_row['amount']:,.0f}", highest_sub),
                ("🚗", "#60A5FA", "FREQUENT MERCHANT", frequent_merchant, frequent_sub),
            ])

# =============================================================================
# PAGE: CATEGORIES
# =============================================================================
elif page == "Categories":
    st.markdown('<div class="page-title">Categories</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Manage your expense categories</div>', unsafe_allow_html=True)

    cat_totals_all = storage.category_totals(df) if not df.empty else pd.Series(dtype=float)
    total_all = float(cat_totals_all.sum()) if not cat_totals_all.empty else 0.0
    top_cat = cat_totals_all.index[0] if not cat_totals_all.empty else "—"
    top_cat_amt_pct = (cat_totals_all.iloc[0] / total_all * 100) if not cat_totals_all.empty and total_all > 0 else 0
    avg_per_cat = (total_all / len(cat_totals_all)) if len(cat_totals_all) else 0
    uncategorized = df[df["category"].isin(["", None])] if not df.empty else pd.DataFrame()

    s1, s2, s3, s4 = st.columns(4)
    s1.markdown(f'<div class="stat-card"><div class="stat-card-label">Total Spent</div><div class="stat-card-value">₹{total_all:,.0f}</div><div class="stat-card-sub">{len(df)} Transactions</div></div>', unsafe_allow_html=True)
    s2.markdown(f'<div class="stat-card"><div class="stat-card-label">Top Category</div><div class="stat-card-value" style="font-size:15px;">{top_cat}</div><div class="stat-card-sub">{top_cat_amt_pct:.0f}%</div></div>', unsafe_allow_html=True)
    s3.markdown(f'<div class="stat-card"><div class="stat-card-label">Avg. Per Category</div><div class="stat-card-value">₹{avg_per_cat:,.0f}</div><div class="stat-card-sub">{len(cat_totals_all)} Categories</div></div>', unsafe_allow_html=True)
    s4.markdown(f'<div class="stat-card"><div class="stat-card-label">Uncategorized</div><div class="stat-card-value">₹0.00</div><div class="stat-card-sub">{len(uncategorized)} Transactions</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("+ Add Category"):
        nc1, nc2, nc3 = st.columns([2, 1, 1])
        with nc1:
            new_cat_name = st.text_input("Name", key="new_cat_name")
        with nc2:
            new_cat_icon = st.text_input("Icon (emoji)", value="🏷️", key="new_cat_icon")
        with nc3:
            new_cat_color = st.color_picker("Color", value="#9CA3AF", key="new_cat_color")
        if st.button("Add Category", key="add_cat_btn", type="primary"):
            if new_cat_name.strip():
                try:
                    storage.add_category(new_cat_name.strip(), new_cat_icon, new_cat_color)
                    get_categories.clear()
                    st.success(f"Added '{new_cat_name}'!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Couldn't add category: {e}")
            else:
                st.warning("Enter a category name first.")

    tab1, tab2 = st.tabs(["Category Breakdown", "Category Insights"])
    with tab1:
        with card("cat_list"):
            if cat_totals_all.empty:
                st.markdown('<div style="color:var(--muted); font-size:13px;">No expenses yet.</div>', unsafe_allow_html=True)
            else:
                is_fs = chart_header("Category Breakdown", "cat_breakdown")
                colors = [CATEGORY_COLORS.get(c, "#9CA3AF") for c in cat_totals_all.index]
                fig = go.Figure(data=[go.Pie(labels=cat_totals_all.index, values=cat_totals_all.values, hole=0.62, marker=dict(colors=colors, line=dict(color="#12161F", width=2)), textinfo="none", hovertemplate="%{label}: ₹%{value:,.0f}<extra></extra>")])
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#E6E9EF"), showlegend=True, legend=dict(font=dict(size=10)), margin=dict(l=0,r=0,t=10,b=10), height=560 if is_fs else 280,
                    annotations=[dict(text=f"₹{total_all:,.0f}<br><span style='font-size:9px;color:#7C8494;'>Total</span>", x=0.5, y=0.5, font=dict(size=16, color="#E6E9EF"), showarrow=False)])
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with tab2:
        with card("cat_insights"):
            if cat_totals_all.empty:
                st.markdown('<div style="color:var(--muted); font-size:13px;">Add expenses to see insights per category.</div>', unsafe_allow_html=True)
            else:
                for cat, amt in cat_totals_all.items():
                    cat_df = df[df["category"] == cat]
                    avg_txn = amt / len(cat_df) if len(cat_df) else 0
                    st.markdown(f'<div style="padding:8px 0; border-bottom:1px solid var(--border); font-size:12.5px;">{CATEGORY_ICONS.get(cat,"•")} <b>{cat}</b> — {len(cat_df)} transactions, avg ₹{avg_txn:,.0f} each</div>', unsafe_allow_html=True)

    with card("cat_search_card"):
        cat_search_col, _ = st.columns([2, 3])
        with cat_search_col:
            cat_search = st.text_input("Search category", placeholder="Search category...", label_visibility="collapsed", key="cat_search")
        st.markdown(f'<div class="section-card-title" style="margin-top:12px;">All Categories ({len(categories_list)})</div>', unsafe_allow_html=True)

        default_names = {c["name"] for c in storage.DEFAULT_CATEGORIES}
        for cat_obj in categories_list:
            name = cat_obj["name"]
            if cat_search.strip() and cat_search.strip().lower() not in name.lower():
                continue
            amt = cat_totals_all.get(name, 0.0)
            pct = (amt / total_all * 100) if total_all > 0 else 0
            txn_count = len(df[df["category"] == name]) if not df.empty else 0
            row_col1, row_col2, row_col3, row_col4, row_col5 = st.columns([2.5, 1.3, 1, 1, 0.7])
            row_col1.markdown(f'<div style="padding:8px 0;">{cat_obj.get("icon","•")} {name}</div>', unsafe_allow_html=True)
            row_col2.markdown(f'<div style="padding:8px 0; font-family:monospace;">₹{amt:,.0f}</div>', unsafe_allow_html=True)
            row_col3.markdown(f'<div style="padding:8px 0;">{pct:.0f}%</div>', unsafe_allow_html=True)
            row_col4.markdown(f'<div style="padding:8px 0;">{txn_count}</div>', unsafe_allow_html=True)
            with row_col5:
                is_default = name in default_names
                if not is_default and "id" in cat_obj:
                    if st.button("🗑️", key=f"del_cat_{cat_obj['id']}"):
                        try:
                            storage.delete_category(cat_obj["id"])
                            get_categories.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Couldn't delete: {e}")