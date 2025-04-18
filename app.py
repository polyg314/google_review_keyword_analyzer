import streamlit as st
from utils import extract_data_id_from_url, fetch_reviews_by_data_id, analyze_keyword_mentions
import re

st.set_page_config(page_title="Google Review Keyword Analyzer")
st.title("🗺️ Google Review Keyword Analyzer")


def password_gate():
    def check_password():
        if st.session_state["password_input"] == st.secrets["app_password"]:
            st.session_state["authenticated"] = True
        else:
            st.session_state["authenticated"] = False
            st.error("❌ Incorrect password")

    if "authenticated" not in st.session_state:
        st.text_input("Enter password:", type="password", on_change=check_password, key="password_input")
        return False
    elif not st.session_state["authenticated"]:
        st.text_input("Enter password:", type="password", on_change=check_password, key="password_input")
        return False
    else:
        return True
    

if password_gate():
        
    st.info(
        "Paste a full **[Google Maps business listing URL](https://www.google.com/maps)** "
        "(from address bar).\n\n"
        "👉 To get a valid URL:\n"
        "1. Open [Google Maps](https://www.google.com/maps)\n"
        "2. Click the business name to go to its full page\n"
        "3. Copy the URL from the address bar"
    )

    # ---- INPUTS ----
    maps_url = st.text_input("🔗 Google Maps URL")
    max_reviews = st.number_input("🔢 Max Number of Reviews", min_value=10, max_value=200, value=100, step=10)
    sort_by = st.selectbox("📤 Sort Reviews By", ["newestFirst", "qualityScore", "ratingHigh", "ratingLow"], index=0)

    # ---- STATE INIT ----
    st.session_state.setdefault("reviews", [])
    st.session_state.setdefault("data_id", None)
    st.session_state.setdefault("last_fetch_params", {})
    st.session_state.setdefault("reviews_ready", False)
    st.session_state.setdefault("analysis_ready", False)
    st.session_state.setdefault("last_keywords", "")
    st.session_state.setdefault("trigger_analysis", False)

    # ---- STEP 1: Fetch Reviews ----
    if st.button("📦 Fetch Reviews"):
        if not maps_url:
            st.error("❌ Please enter a valid Google Maps URL.")
        else:
            current_params = {"maps_url": maps_url, "max_reviews": max_reviews, "sort_by": sort_by}

            if current_params != st.session_state.last_fetch_params:
                st.session_state.reviews = []
                st.session_state.reviews_ready = False
                st.session_state.analysis_ready = False

            with st.spinner("🔗 Extracting data ID from URL..."):
                data_id = extract_data_id_from_url(maps_url)

            if not data_id:
                st.error("❌ Could not extract a valid `data_id` from the URL.")
            else:
                with st.spinner(f"📦 Fetching up to {max_reviews} reviews from SerpAPI..."):
                    try:
                        reviews = fetch_reviews_by_data_id(data_id, max_reviews=max_reviews, sort_by=sort_by)
                        st.session_state.reviews = reviews
                        st.session_state.data_id = data_id
                        st.session_state.last_fetch_params = current_params
                        st.session_state.reviews_ready = True
                        st.session_state.analysis_ready = True
                        st.success(f"✅ Retrieved {len(reviews)} reviews!")
                    except Exception as e:
                        st.error(f"❌ Error fetching reviews: {e}")
                        st.session_state.reviews_ready = False
                        st.session_state.reviews = []
                        st.session_state.analysis_ready = False

    # ---- STEP 2: Analyze Keywords ----
    current_params = {"maps_url": maps_url, "max_reviews": max_reviews, "sort_by": sort_by}
    if (
        st.session_state.reviews_ready
        and st.session_state.reviews
        and st.session_state.last_fetch_params == current_params
    ):
        st.text_input("🔑 Comma-separated Keywords to Analyze", 
                    value=st.session_state.last_keywords,
                    key="keyword_input")

        if st.session_state.analysis_ready:
            if st.button("🧠 Analyze Keywords"):
                st.session_state.last_keywords = st.session_state.keyword_input
                st.session_state.trigger_analysis = True

    # ---- RUN ANALYSIS ----
    if st.session_state.trigger_analysis:
        stats = analyze_keyword_mentions(
            st.session_state.reviews,
            st.session_state.last_keywords
        )
        st.session_state.trigger_analysis = False  # reset

        st.markdown("### 📊 Reviews with Keywords (Raw %):")
        for kw in stats['keyword_counts']:
            st.write(f"- {kw}: {stats['keyword_counts'][kw]} ({stats['raw_percentages'][kw]:.1f}%)")

        st.markdown("### 📊 Reviews with Keywords (Normalized to non-empty reviews):")
        for kw in stats['keyword_counts']:
            st.write(f"- {kw}: {stats['normalized_percentages'][kw]:.1f}%")

        st.markdown("### 📈 Summary:")
        st.write(f"Total reviews: {stats['total']}")
        st.write(f"Reviews with no text: {stats['empty_count']} ({stats['empty_percentage']:.1f}%)")
        st.write(f"Non-empty reviews: {stats['non_empty']}")
        st.write(f"% of all reviews mentioning any keyword: {stats['raw_any_percentage']:.1f}%")
        st.write(f"% of non-empty reviews mentioning any keyword: {stats['norm_any_percentage']:.1f}%")

        # ---- Display Highlighted Reviews ----
        with st.expander("📄 Show Reviews"):
            with st.container():
                highlight_keywords = [
                    kw.strip().lower() for kw in st.session_state.last_keywords.split(",") if kw.strip()
                ]

                for i, r in enumerate(st.session_state.reviews):
                    text = r.get("snippet", "(no text)")
                    if text:
                        for kw in highlight_keywords:
                            if kw:
                                pattern = re.compile(rf'\b({re.escape(kw)})\b', re.IGNORECASE)
                                text = pattern.sub(r"<mark>\1</mark>", text)

                    st.markdown(
                        f"**Review {i + 1}** — ⭐️ {r.get('rating', 'N/A')}<br>{text}",
                        unsafe_allow_html=True
                    )

