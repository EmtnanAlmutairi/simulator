import streamlit as st
import yfinance as yf
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# ------------------ إعداد صفحة التطبيق ------------------
st.set_page_config(page_title="محفظتي السعودية", page_icon="💼", layout="wide")

# ------------------ تحميل رموز الأسهم من ملف CSV ------------------
try:
    df_symbols = pd.read_csv('saudi_stocks.csv')
    all_symbols = df_symbols['Symbol'].dropna().unique().tolist()
except Exception as e:
    st.error(f"فشل تحميل ملف الأسهم: {e}")
    all_symbols = []

# ------------------ إعداد قاعدة البيانات ------------------
conn = sqlite3.connect("wallet.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS portfolio (
    symbol TEXT PRIMARY KEY,
    shares INTEGER,
    avg_price REAL
)''')
c.execute('''CREATE TABLE IF NOT EXISTS cash (
    id INTEGER PRIMARY KEY,
    balance REAL
)''')
conn.commit()

def init_balance():
    c.execute("SELECT balance FROM cash WHERE id=1")
    if not c.fetchone():
        c.execute("INSERT INTO cash (id, balance) VALUES (1, 100000)")
        conn.commit()

init_balance()

def get_balance():
    c.execute("SELECT balance FROM cash WHERE id=1")
    return c.fetchone()[0]

def update_balance(new_balance):
    c.execute("UPDATE cash SET balance=? WHERE id=1", (new_balance,))
    conn.commit()

def get_portfolio():
    c.execute("SELECT * FROM portfolio")
    rows = c.fetchall()
    return pd.DataFrame(rows, columns=['symbol', 'shares', 'avg_price']) if rows else pd.DataFrame(columns=['symbol', 'shares', 'avg_price'])

def update_portfolio(symbol, shares, avg_price):
    if shares == 0:
        c.execute("DELETE FROM portfolio WHERE symbol=?", (symbol,))
    else:
        if c.execute("SELECT 1 FROM portfolio WHERE symbol=?", (symbol,)).fetchone():
            c.execute("UPDATE portfolio SET shares=?, avg_price=? WHERE symbol=?", (shares, avg_price, symbol))
        else:
            c.execute("INSERT INTO portfolio (symbol, shares, avg_price) VALUES (?, ?, ?)", (symbol, shares, avg_price))
    conn.commit()

# ------------------ جلب بيانات الأسهم ------------------
@st.cache_data(ttl=900)
def get_stock_info(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        name = info.get('longName', 'غير معروف')
        price = info.get('previousClose', None)
        if price is None:
            return None, None
        return name, price
    except:
        return None, None

@st.cache_data(ttl=900)
def get_price_history(symbol, period="3mo"):
    try:
        stock = yf.Ticker(symbol)
        return stock.history(period=period)
    except:
        return pd.DataFrame()

# ------------------ واجهة التطبيق ------------------
st.title("📈 محاكي محفظة الأسهم السعودية")
st.caption("تابع، اشترِ، وبِع أسهم السوق السعودي بطريقة تفاعلية")

tabs = st.tabs(["📋 قائمة الأسهم", "📊 الرسم البياني", "💼 محفظتي"])

# ------------------ تبويب الأسهم ------------------
with tabs[0]:
    st.header("📋 تفاصيل الأسهم")
    if not all_symbols:
        st.warning("لم يتم تحميل أي رموز أسهم من الملف.")
    else:
        invalid_symbols = []
        valid_count = 0
        for sym in all_symbols:
            name, price = get_stock_info(sym)
            if name and price:
                col1, col2 = st.columns([1, 3])
                col1.markdown(f"**{sym}**")
                col2.markdown(f"**{name}** — السعر: `{price:.2f} ريال`")
                valid_count += 1
            else:
                invalid_symbols.append(sym)
        if valid_count == 0:
            st.warning("لا توجد رموز صالحة للعرض.")
        elif invalid_symbols:
            st.info(f"⚠️ تم تجاهل {len(invalid_symbols)} رمز غير مدعوم: {', '.join(invalid_symbols)}")

# ------------------ تبويب الرسم البياني ------------------
with tabs[1]:
    st.header("📊 الرسم البياني للسعر")
    valid_symbols = [sym for sym in all_symbols if get_stock_info(sym)[1] is not None]

    if not valid_symbols:
        st.warning("لا توجد رموز أسهم صالحة للعرض.")
    else:
        symbol_chart = st.selectbox("اختر سهمًا", valid_symbols)
        hist = get_price_history(symbol_chart)
        if hist.empty:
            st.warning("لا توجد بيانات لهذا السهم.")
        else:
            st.line_chart(hist['Close'], use_container_width=True)

# ------------------ تبويب المحفظة ------------------
with tabs[2]:
    st.header("📊 محفظتي")
    balance = get_balance()
    st.success(f"💰 رصيدك الحالي: {balance:,.2f} ريال")

    portfolio = get_portfolio()
    if portfolio.empty:
        st.info("📭 المحفظة فارغة حالياً")
    else:
        data = []
        total_value = 0
        total_cost = 0

        for i, row in portfolio.iterrows():
            symbol = row['symbol']
            shares = row['shares']
            avg_price = row['avg_price']
            current_price = get_stock_info(symbol)[1]

            if current_price:
                market_value = shares * current_price
                cost_value = shares * avg_price
                profit_loss = market_value - cost_value
                profit_percent = ((market_value - cost_value) / cost_value) * 100 if cost_value else 0
                change_percent = ((current_price - avg_price) / avg_price) * 100 if avg_price else 0

                total_value += market_value
                total_cost += cost_value

                data.append({
                    "الرمز": symbol,
                    "عدد الأسهم": shares,
                    "سعر الشراء": avg_price,
                    "السعر الحالي": current_price,
                    "القيمة السوقية": market_value,
                    "الربح / الخسارة": profit_loss,
                    "الربح %": profit_percent,
                    "التغير %": change_percent,
                })

        df = pd.DataFrame(data)
        if not df.empty:
            subset_cols = ["الربح / الخسارة", "الربح %", "التغير %"]
            if all(col in df.columns for col in subset_cols):
                styled_df = df.style.applymap(lambda val: 'color: green' if val > 0 else 'color: red' if val < 0 else '', subset=subset_cols)
                st.dataframe(styled_df, use_container_width=True)
            else:
                st.error("❗ بعض الأعمدة المطلوبة غير موجودة في DataFrame.")

        st.markdown("### 📊 توزيع القيمة السوقية حسب الأسهم")
        st.bar_chart(df.set_index("الرمز")["القيمة السوقية"])

        st.markdown("### 🥧 توزيع المحفظة بالنسب المئوية")
        pie_df = df[["الرمز", "القيمة السوقية"]].set_index("الرمز")
        fig = pie_df.plot.pie(y="القيمة السوقية", autopct='%1.1f%%', figsize=(6, 6), legend=False, ylabel='').figure
        st.pyplot(fig)
