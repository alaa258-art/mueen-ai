import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="MUEEN AI | مُعين", page_icon="🎓", layout="wide")

st.markdown("""
<style>
.main {direction: rtl;}
h1, h2, h3, p, label, div[data-testid="stMarkdownContainer"] {text-align: right;}
[data-testid="stDataFrame"] {direction: rtl;}
</style>
""", unsafe_allow_html=True)

st.title("🎓 مُعين | MUEEN AI")
st.subheader("وكيل دعم التعلم الذكي — النسخة التجريبية الأولى")
st.info("هذه نسخة أولية تعتمد على قواعد تحليل واضحة، وليست بعدُ وكيل ذكاء اصطناعي متصلًا بنموذج لغوي. استخدم بيانات تجريبية أو مجهولة الهوية فقط.")

with st.sidebar:
    st.header("إعدادات التحليل")
    subject = st.selectbox("المادة", ["الحوسبة", "الرياضيات", "العلوم", "اللغة العربية", "اللغة الإنجليزية"])
    grade = st.selectbox("الصف", ["الخامس", "السادس", "السابع", "الثامن", "التاسع"])
    threshold = st.slider("حد الإتقان (%)", min_value=50, max_value=90, value=70, step=5)
    st.caption("يمكن تغيير حد الإتقان حسب سياسة المدرسة.")

st.markdown("### 1) أدخل بيانات التقييم")
st.write("يمكنك رفع ملف CSV أو تجربة البيانات النموذجية. الأعمدة المطلوبة: `Student` و `Skill` و `Score` و `MaxScore`.")

demo = pd.DataFrame([
    {"Student":"طالب 1","Skill":"فهم مفهوم الخوارزمية","Score":4,"MaxScore":5},
    {"Student":"طالب 1","Skill":"ترتيب خطوات الحل","Score":2,"MaxScore":5},
    {"Student":"طالب 1","Skill":"قراءة المخطط الانسيابي","Score":3,"MaxScore":5},
    {"Student":"طالب 2","Skill":"فهم مفهوم الخوارزمية","Score":5,"MaxScore":5},
    {"Student":"طالب 2","Skill":"ترتيب خطوات الحل","Score":3,"MaxScore":5},
    {"Student":"طالب 2","Skill":"قراءة المخطط الانسيابي","Score":2,"MaxScore":5},
    {"Student":"طالب 3","Skill":"فهم مفهوم الخوارزمية","Score":3,"MaxScore":5},
    {"Student":"طالب 3","Skill":"ترتيب خطوات الحل","Score":1,"MaxScore":5},
    {"Student":"طالب 3","Skill":"قراءة المخطط الانسيابي","Score":2,"MaxScore":5},
])

col1, col2 = st.columns([1, 1])
with col1:
    uploaded = st.file_uploader("ارفع ملف CSV", type=["csv"])
with col2:
    use_demo = st.checkbox("استخدام البيانات النموذجية", value=True)

data = None
if uploaded is not None:
    try:
        data = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"تعذر قراءة الملف: {e}")
elif use_demo:
    data = demo.copy()

if data is not None:
    required = {"Student", "Skill", "Score", "MaxScore"}
    if not required.issubset(set(data.columns)):
        st.error("الملف لا يحتوي على الأعمدة المطلوبة. تأكد من وجود: Student, Skill, Score, MaxScore.")
        data = None
    else:
        data["Score"] = pd.to_numeric(data["Score"], errors="coerce")
        data["MaxScore"] = pd.to_numeric(data["MaxScore"], errors="coerce")
        data = data.dropna(subset=["Student", "Skill", "Score", "MaxScore"])
        data = data[(data["MaxScore"] > 0) & (data["Score"] >= 0) & (data["Score"] <= data["MaxScore"])]

if data is not None and not data.empty:
    st.dataframe(data, use_container_width=True, hide_index=True)
    data["MasteryPct"] = (data["Score"] / data["MaxScore"] * 100).round(1)

    st.markdown("### 2) تحليل المهارات")
    summary = data.groupby("Skill", as_index=False).agg(
        AverageMastery=("MasteryPct", "mean"),
        Responses=("Student", "count")
    )
    summary["AverageMastery"] = summary["AverageMastery"].round(1)
    summary["Status"] = summary["AverageMastery"].apply(lambda x: "متقنة مبدئيًا" if x >= threshold else "تحتاج إلى دعم")
    st.dataframe(summary.rename(columns={
        "Skill":"المهارة", "AverageMastery":"متوسط الإتقان (%)",
        "Responses":"عدد الإجابات", "Status":"الحالة"
    }), use_container_width=True, hide_index=True)

    needs_support = summary[summary["AverageMastery"] < threshold].sort_values("AverageMastery")
    st.markdown("### 3) خطة دعم مقترحة")
    if needs_support.empty:
        st.success("المهارات المعروضة بلغت حد الإتقان المحدد. جرّب أسئلة إثرائية أو تحقق من الاحتفاظ بالتعلم لاحقًا.")
    else:
        for _, row in needs_support.iterrows():
            skill = row["Skill"]
            pct = row["AverageMastery"]
            if "ترتيب" in skill or "خطوات" in skill or "خوارزمية" in skill:
                activity = "قدّم مثالًا محلولًا، ثم اطلب من الطلاب ترتيب 4–6 خطوات مبعثرة، ثم اطلب منهم شرح سبب الترتيب."
            elif "مخطط" in skill or "رسم" in skill:
                activity = "اعرض مخططًا بسيطًا ناقصًا، واطلب إكماله، ثم مطابقة كل رمز بوظيفته."
            elif "رياض" in subject:
                activity = "قسّم المهارة إلى خطوات قصيرة، واعرض مثالًا محلولًا ثم سؤالًا مشابهًا وسؤالًا مستقلًا."
            else:
                activity = "قدّم شرحًا قصيرًا بمثال، ثم نشاطًا موجهًا، ثم سؤالًا مستقلًا للتحقق من الفهم."
            st.warning(f"**{skill} — متوسط الإتقان {pct:.1f}%**")
            st.write(f"**الإجراء المقترح:** {activity}")
            st.write("**التحقق:** أنشئ اختبار متابعة من 3–5 أسئلة مرتبطة بالمهارة، وقارن النتيجة بحد الإتقان.")

    st.markdown("### 4) مقارنة اختبار المتابعة")
    st.write("أدخل متوسط الإتقان قبل التدخل وبعده. هذه مقارنة وصفية ولا تثبت وحدها أن التدخل سبب التحسن.")
    c1, c2 = st.columns(2)
    with c1:
        before = st.number_input("قبل التدخل (%)", min_value=0.0, max_value=100.0, value=float(summary["AverageMastery"].mean()), step=1.0)
    with c2:
        after = st.number_input("بعد التدخل (%)", min_value=0.0, max_value=100.0, value=min(100.0, float(summary["AverageMastery"].mean()) + 10), step=1.0)
    delta = after - before
    st.metric("التغير في متوسط الإتقان", f"{delta:+.1f} نقطة مئوية")
    if delta > 0:
        st.success("النتيجة ارتفعت في البيانات المدخلة. تحقق من ثبات المهارة باستخدام أسئلة جديدة مماثلة.")
    elif delta < 0:
        st.error("النتيجة انخفضت. راجع ملاءمة النشاط وصعوبة الاختبار، وفكّر في دعم إضافي.")
    else:
        st.info("لم يتغير المتوسط. قد يحتاج الطالب إلى استراتيجية مختلفة أو وقت إضافي.")

    report = summary.rename(columns={
        "Skill":"المهارة", "AverageMastery":"متوسط الإتقان (%)",
        "Responses":"عدد الإجابات", "Status":"الحالة"
    })
    csv_bytes = report.to_csv(index=False).encode("utf-8-sig")
    st.download_button("تنزيل تقرير تحليل المهارات (CSV)", data=csv_bytes, file_name="mueen_skill_report.csv", mime="text/csv")
else:
    st.warning("ارفع ملف CSV صالحًا أو فعّل البيانات النموذجية لعرض التحليل.")

st.divider()
st.caption("MUEEN AI V1 — نموذج تجريبي. لا تستخدمه لاتخاذ قرارات عالية الأثر بشأن الطلاب دون مراجعة بشرية. احمِ خصوصية الطلاب واستخدم بيانات مجهولة الهوية.")
