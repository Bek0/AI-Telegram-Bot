# file: app.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

# =======
# إعداد الاتصال بقاعدة البيانات
# =======
DATABASE_URL = "mssql+pyodbc://@B515R\\SQLEXPRESS/manager?driver=ODBC+Driver+17+for+SQL+Server"
engine = create_engine(DATABASE_URL)

# =======
# دوال مساعدة
# =======
def get_all_tables():
    """جلب أسماء جميع الجداول في قاعدة البيانات"""
    query = text("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
    with engine.connect() as conn:
        result = conn.execute(query)
        tables = [row[0] for row in result.fetchall()]
    return tables

def fetch_table_data(table_name: str):
    """جلب بيانات جدول معين"""
    with engine.connect() as conn:
        query = text(f"SELECT * FROM [{table_name}]")
        df = pd.read_sql(query, conn)
    return df

# =======
# Streamlit App
# =======
st.set_page_config(page_title="Database Dashboard", layout="wide")

st.title("📊 لوحة عرض بيانات قاعدة البيانات")

# تحديث تلقائي
st_autorefresh = st.experimental_get_query_params().get("autorefresh", [5])[0]
st_autorefresh = int(st_autorefresh)
st.write(f"آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.experimental_rerun_interval = st_autorefresh * 1000

# =======
# جلب وعرض كل الجداول
# =======
try:
    tables = get_all_tables()
    st.success(f"تم العثور على {len(tables)} جدول في قاعدة البيانات.")

    for table in tables:
        st.subheader(f"📄 {table}")
        try:
            df = fetch_table_data(table)
            st.write(f"عدد الصفوف: {len(df)}")
            st.dataframe(df)
        except Exception as e:
            st.error(f"⚠️ فشل في قراءة الجدول '{table}': {e}")

except Exception as e:
    st.error(f"❌ خطأ في جلب قائمة الجداول: {e}")

# =======
# عرض إحصائيات عامة
# =======
if st.checkbox("عرض إحصائيات عامة"):
    st.subheader("📊 إحصائيات عامة")
    stats = {}
    for t in tables:
        try:
            df_t = fetch_table_data(t)
            stats[t] = len(df_t)
        except:
            stats[t] = "Error"
    st.table(pd.DataFrame.from_dict(stats, orient="index", columns=["عدد الصفوف"]))
