"""
Q — Virtual Dining Assistant for ICB
Streamlit Chat Application powered by Claude via Portkey gateway

Run locally:   streamlit run app.py
Deploy:        Push to GitHub → connect to Streamlit Cloud (share.streamlit.io)
"""

import os
from typing import Optional
import anthropic
import streamlit as st

from menu_loader import load_menu, load_analytics
from system_prompt import build_system_prompt

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Q — ICB Dining Assistant",
    page_icon="🍺",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stChatMessage { border-radius: 12px; }
    .rx-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 16px;
        color: white;
    }
    .rx-header h2 { margin: 0; font-size: 1.4rem; color: #f5c518; }
    .rx-header p  { margin: 4px 0 0; font-size: 0.85rem; color: #ccc; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Constants ─────────────────────────────────────────────────────────────────
MENU_PATH     = os.path.join(os.path.dirname(__file__), "menu.json")
ANALYTICS_CSV = os.path.join(os.path.dirname(__file__), "menu_analytics.csv")
RX_NAME       = "ICB"
MODEL         = "claude-haiku-4-5-20251001"
MAX_TOKENS    = 600
TEMPERATURE   = 0.7

STARTER_SUGGESTIONS = [
    "What are the must-try dishes here?",
    "Recommend a good craft beer",
    "Suggest starters for sharing",
    "Plan a full meal for two",
    "What cocktails do you recommend?",
    "Any good vegetarian options?",
]


# ── Data loading (cached) ─────────────────────────────────────────────────────
@st.cache_resource
def get_menu_data(extra_scores: Optional[dict] = None):
    return load_menu(
        MENU_PATH,
        analytics_csv_path=ANALYTICS_CSV if os.path.exists(ANALYTICS_CSV) else None,
        popularity_scores=extra_scores,
    )


def make_client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    # Auto-load key from Streamlit Cloud secrets or env; fallback to manual input
    _secret_key = st.secrets.get("ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    if _secret_key:
        api_key_input = _secret_key
        st.success("✅ API key loaded", icon="🔑")
    else:
        api_key_input = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            help="Only needed locally — on Streamlit Cloud this is set as a secret.",
        )

    tester_name = st.text_input("Your name (optional)", placeholder="e.g. Rahul")

    st.divider()

    # Analytics status
    st.markdown("#### 📊 Popularity Data")
    if os.path.exists(ANALYTICS_CSV):
        st.success("✅ ICB analytics loaded (538 items)", icon="📈")
    else:
        st.warning("No analytics CSV found", icon="⚠️")

    uploaded_file = st.file_uploader(
        "Override with updated CSV/Excel",
        type=["xlsx", "csv"],
        help="CSV with columns: Item ID, No. of Times Ordered",
    )

    popularity_scores = None
    if uploaded_file is not None:
        try:
            import pandas as pd
            df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
            id_col    = next((c for c in df.columns if "id" in c.lower()), df.columns[0])
            score_col = next(
                (c for c in df.columns if any(k in c.lower() for k in ["times", "order", "score", "count"])),
                df.columns[-1],
            )
            popularity_scores = dict(zip(df[id_col].astype(str), df[score_col]))
            st.success(f"Override: {len(popularity_scores)} items")
        except Exception as e:
            st.error(f"Could not read file: {e}")

    st.divider()

    st.markdown("#### 🏪 Restaurant Info")
    st.markdown("**ICB — Independence Craft Brewery**")
    st.caption("Bengaluru | Multi-Cuisine | Bar & Restaurant")
    st.caption("⭐ 4.2/5 — Craft Beer · Cocktails · Food")

    st.divider()

    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown(
        "<div style='font-size:0.7rem;color:#666;margin-top:8px;'>Powered by Claude via Portkey · Internal testing</div>",
        unsafe_allow_html=True,
    )


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="rx-header">
        <h2>🍺 Q — Your Dining Companion</h2>
        <p>Powered by AI · {RX_NAME} · Bengaluru</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── Credential validation ─────────────────────────────────────────────────────
if not api_key_input:
    st.info("👈 Enter your **Anthropic API key** in the sidebar to start.", icon="🔑")
    st.stop()


# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []


# ── Starter suggestions ───────────────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown("**Try asking:**")
    cols = st.columns(2)
    for i, suggestion in enumerate(STARTER_SUGGESTIONS):
        with cols[i % 2]:
            if st.button(suggestion, key=f"s_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": suggestion})
                st.rerun()


# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    avatar = "🧑" if msg["role"] == "user" else "🍽️"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])


# ── Chat input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask Q about the menu, dishes, drinks…")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_input)

    menu_data     = get_menu_data(popularity_scores)
    system_prompt = build_system_prompt(menu_data, rx_name=RX_NAME)
    api_messages  = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

    client = make_client(api_key_input)

    with st.chat_message("assistant", avatar="🍽️"):
        placeholder   = st.empty()
        full_response = ""

        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                system=system_prompt,
                messages=api_messages,
            ) as stream:
                for chunk in stream.text_stream:
                    full_response += chunk
                    placeholder.markdown(full_response + "▌")

            placeholder.markdown(full_response)

        except anthropic.AuthenticationError:
            st.error("Authentication failed — check your Portkey API key and virtual key.")
            st.session_state.messages.pop()
            st.stop()

        except anthropic.RateLimitError:
            st.error("Rate limit reached. Please wait a moment and try again.")
            st.session_state.messages.pop()
            st.stop()

        except Exception as e:
            st.error(f"Something went wrong: {e}")
            st.session_state.messages.pop()
            st.stop()

    st.session_state.messages.append({"role": "assistant", "content": full_response})
