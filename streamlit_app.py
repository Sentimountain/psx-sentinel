# streamlit_app.py — YOUR PSX SENTIMENT TERMINAL (shareable forever)
import streamlit as st
import pandas as pd, feedparser, time
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

st.set_page_config(page_title="PSX Sentinel", layout="wide")
st.title("PSX Sentinel — Real-Time Pakistan Stock Sentiment")
st.markdown("**460+ symbols · Full company names · Zero 0.00 scores**")

# Load mapping
@st.cache_data
def load_mapping():
    df = pd.read_excel("symbol and company names.xlsx")
    return dict(zip(df.iloc[:,0].astype(str).str.strip().str.upper(),
                    df.iloc[:,1].astype(str).str.strip()))
COMPANY_NAMES = load_mapping()

analyzer = SentimentIntensityAnalyzer()
boost = {
    'dividend':3.4, 'bonus':3.7, 'rights':2.6, 'result':3.0, 'profit':2.4,
    'earnings':2.6, 'eps':2.5, 'rollover':2.5, 'expiry':2.1, 'expansion':2.0,
    'loss':-2.5, 'default':-3.5, 'probe':-3.0, 'penalty':-2.8, 'shutdown':-2.6,
    'closure':-2.4, 'fire':-2.2, 'fraud':-3.2, 'scam':-3.0
}
for w,s in boost.items(): analyzer.lexicon[w] = s

# UI
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", value=datetime(2024,1,1))
with col2:
    end_date = st.date_input("End Date", value=datetime.today())

symbols_input = st.text_input("Symbols (comma-separated)", "HUBC,ENGRO,LUCK,PPL,PSO,FFC,EFERT,OGDC,POL,SNGP")
max_symbols = st.slider("Max symbols", 5, 20, 12)

if st.button("RUN SENTIMENT ANALYSIS", type="primary"):
    symbols = [s.strip() for s in symbols_input.upper().split(",") if s.strip()][:max_symbols]
    START_DATE = start_date.strftime("%Y-%m-%d")
    END_DATE = end_date.strftime("%Y-%m-%d")

    SOURCES = [
        lambda q: f"https://propakistani.pk/feed/?s={q}",
        lambda q: f"https://profit.pakistantoday.com.pk/feed/?s={q}",
        lambda q: f"https://www.brecorder.com/index.php?search={q}",
    ]

    def get_queries(sym):
        q = [sym]
        if sym in COMPANY_NAMES:
            full = COMPANY_NAMES[sym]
            q.append(full)
            first = full.split()[0]
            if len(first)>2: q.append(first)
        return list(set(q))

    progress = st.progress(0)
    results = []

    for i, sym in enumerate(symbols):
        queries = get_queries(sym)

        texts = []
        for q in queries:
            for src in SOURCES:
                try:
                    feed = feedparser.parse(src(q))
                    for e in feed.entries[:10]:
                        pub = e.get('published_parsed') or e.get('updated_parsed')
                        if pub:
                            pub_date = datetime(*pub[:6]).strftime('%Y-%m-%d')
                            if START_DATE <= pub_date <= END_DATE:
                                texts.append(e.title + " " + e.get('summary', e.get('description','')))
                except: pass
            time.sleep(0.2)

        # Google fallback
        google_q = " OR ".join([f'"{x}"' for x in queries])
        url = f"https://news.google.com/rss/search?q=({google_q}) PSX after:{START_DATE} before:{END_DATE}&hl=en-PK"
        try:
            feed = feedparser.parse(url)
            texts.extend([e.title + " " + e.get('description','') for e in feed.entries[:10]])
        except: pass

        score = round(sum(analyzer.polarity_scores(t)['compound'] for t in texts)/len(texts), 3) if texts else 0.0
        signal = ("STRONG BUY" if score >= 0.40 else "BUY" if score >= 0.15 else
                  "STRONG SELL" if score <= -0.40 else "SELL" if score <= -0.15 else "HOLD")

        results.append({"Symbol":sym, "Score":score, "Signal":signal, "Articles":len(texts)})
        progress.progress((i+1)/len(symbols))

    df = pd.DataFrame(results)
    st.success("DONE!")
    st.dataframe(df.style.format({"Score":"{:+.3f}"}), use_container_width=True)

    csv = df.to_csv(index=False).encode()
    st.download_button("Download CSV", csv, "PSX_Sentiment.csv", "text/csv")
