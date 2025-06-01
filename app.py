import streamlit as st
import yfinance as yf
import sqlite3
import pandas as pd

# ------------------ رموز الأسهم السعودية ------------------
all_symbols = [
    "2010.SR", "2222.SR", "1120.SR", "7010.SR", "1050.SR", "2020.SR",
    "8230.SR", "1211.SR", "2280.SR", "4003.SR", "1810.SR", "6010.SR",
    "1180.SR", "4300.SR", "3002.SR", "8231.SR", "8010.SR"
]

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

# ------------------ البيانات من yfinance ------------------
@st.cache_data(ttl=900)
def get_stock_info(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        name = info.get('longName', 'غير معروف')
        price = info.get('previousClose', None)
        return name, price
    except:
        return "غير معروف", None

@st.cache_data(ttl=900)
def get_price_history(symbol, period="3mo"):
    try:
        stock = yf.Ticker(symbol)
        return stock.history(period=period)
    except:
        return pd.DataFrame()

# ------------------ واجهة Streamlit ------------------
st.set_page_config(page_title="محفظتي السعودية", page_icon="💼", layout="wide")
st.title("📈 محاكي محفظة الأسهم السعودية")
st.caption("تابع، اشترِ، وبِع أسهم السوق السعودي بطريقة تفاعلية")

tabs = st.tabs(["📋 قائمة الأسهم", "📊 الرسم البياني", "💼 محفظتي"])

# ------------------ تبويب الأسهم ------------------
with tabs[0]:
    st.header("📋 تفاصيل الأسهم")
    for sym in all_symbols:
        name, price = get_stock_info(sym)
        col1, col2 = st.columns([1, 3])
        col1.markdown(f"**{sym}**")
        col2.markdown(f"**{name}** — السعر: `{price if price else 'غير متوفر'} ريال`")

# ------------------ تبويب الرسم البياني ------------------
with tabs[1]:
    st.header("📊 الرسم البياني للسعر")
    symbol_chart = st.selectbox("اختر سهمًا", all_symbols)
    hist = get_price_history(symbol_chart)
    if hist.empty:
        st.warning("لا توجد بيانات لهذا السهم.")
    else:
        st.line_chart(hist['Close'], use_container_width=True)

# ------------------ تبويب المحفظة ------------------
with tabs[2]:
    st.header("📊 محفظتي")

    # ✅ الرصيد الحالي
    balance = get_balance()
    st.success(f"💰 رصيدك الحالي: {balance:,.2f} ريال")

    # ✅ بيانات المحفظة
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

            # ✅ جلب السعر الحالي
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

        # ✅ بطاقات إحصائيات
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📦 عدد الشركات", f"{len(df)}")
        col2.metric("📉 تكلفة الشراء", f"{total_cost:,.2f} ريال")
        col3.metric("📈 القيمة السوقية", f"{total_value:,.2f} ريال")
        profit_total = total_value - total_cost
        col4.metric("💹 الربح / الخسارة", f"{profit_total:,.2f} ريال", delta=f"{(profit_total / total_cost) * 100:.2f}%" if total_cost else "0%")

        # ✅ تنسيق ألوان الجدول
        def colorize(val):
            if isinstance(val, (int, float)):
                if val > 0:
                    return 'color: green'
                elif val < 0:
                    return 'color: red'
            return ''

        styled_df = df.style.applymap(colorize, subset=["الربح / الخسارة", "الربح %", "التغير %"])
        st.markdown("### 🧾 تفاصيل المحفظة")
        st.dataframe(styled_df, use_container_width=True)

        # ✅ رسم بياني شريطي للقيمة السوقية
        st.markdown("### 📊 توزيع القيمة السوقية حسب الأسهم")
        st.bar_chart(df.set_index("الرمز")["القيمة السوقية"])

        # ✅ رسم بياني دائري
        st.markdown("### 🥧 توزيع المحفظة بالنسب المئوية")
        pie_df = df[["الرمز", "القيمة السوقية"]].set_index("الرمز")
        fig = pie_df.plot.pie(
            y="القيمة السوقية",
            autopct='%1.1f%%',
            figsize=(6, 6),
            legend=False,
            ylabel=''
        ).figure
        st.pyplot(fig)
