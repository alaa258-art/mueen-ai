import streamlit as st
import pandas as pd
from openai import OpenAI

st.set_page_config(page_title="MUEEN AI V2 | مُعين", page_icon="🎓", layout="wide")
st.markdown("<style>.main{direction:rtl} h1,h2,h3,p,label,div[data-testid='stMarkdownContainer']{text-align:right}</style>", unsafe_allow_html=True)

def api_key():
    try: return st.secrets.get("OPENAI_API_KEY", "")
    except Exception: return ""

def generate_plan(client, model, subject, grade, skill, mastery, language, notes):
    prompt=f"""أنت مساعد تعليمي للمعلم. اكتب خطة علاجية عملية.
المادة: {subject}; الصف: {grade}; المهارة: {skill}; متوسط الإتقان: {mastery:.1f}%;
لغة المخرجات: {language}; ملاحظات المعلم: {notes or 'لا توجد'}.
قدّم شرحًا موجزًا، مثالًا محلولًا، نشاطًا مدته 10 دقائق، 5 أسئلة متابعة مع الإجابات،
معيارًا واضحًا للإتقان وخطوة بديلة إذا لم يتحسن الأداء. لا تفترض أسبابًا غير مثبتة،
ولا تقدم تشخيصًا نفسيًا أو طبيًا، واجعل المعلم صاحب القرار."""
    response=client.responses.create(model=model, input=prompt)
    return response.output_text

st.title("🎓 مُعين | MUEEN AI")
st.subheader("وكيل دعم التعلم الذكي — النسخة الثانية")
st.caption("تحليل شفاف للدرجات + إنشاء خطط وأنشطة عبر OpenAI API.")
st.warning("استخدم بيانات تجريبية أو مجهولة الهوية فقط، وراجع المحتوى الناتج قبل استخدامه مع الطلاب.")

with st.sidebar:
    st.header("إعدادات التحليل")
    subject=st.selectbox("المادة",["الحوسبة","الرياضيات","العلوم","اللغة العربية","اللغة الإنجليزية"])
    grade=st.selectbox("الصف",["الخامس","السادس","السابع","الثامن","التاسع"])
    threshold=st.slider("حد الإتقان (%)",50,90,70,5)
    language=st.selectbox("لغة الخطة",["العربية","English"])
    model=st.text_input("اسم نموذج API",value="gpt-4.1-mini")

key=api_key()
if key: st.success("تم العثور على مفتاح API في إعدادات الأسرار. لن نعرض المفتاح داخل التطبيق.")
else: st.info("لم يتم إعداد مفتاح API بعد. التحليل الأساسي يعمل، لكن إنشاء الخطة بالذكاء الاصطناعي يتطلب إعداد المفتاح.")

demo=pd.DataFrame([
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
st.markdown("### 1) بيانات التقييم")
st.write("الأعمدة المطلوبة في CSV: `Student`, `Skill`, `Score`, `MaxScore`.")
uploaded=st.file_uploader("ارفع ملف CSV",type=["csv"])
use_demo=st.checkbox("استخدام البيانات النموذجية",value=True)
data=None
if uploaded:
    try: data=pd.read_csv(uploaded)
    except Exception as e: st.error(f"تعذر قراءة الملف: {e}")
elif use_demo: data=demo.copy()

if data is not None:
    required={"Student","Skill","Score","MaxScore"}
    if not required.issubset(data.columns):
        st.error("الأعمدة المطلوبة: Student, Skill, Score, MaxScore"); data=None
    else:
        data["Score"]=pd.to_numeric(data["Score"],errors="coerce")
        data["MaxScore"]=pd.to_numeric(data["MaxScore"],errors="coerce")
        data=data.dropna(subset=["Student","Skill","Score","MaxScore"])
        data=data[(data["MaxScore"]>0)&(data["Score"]>=0)&(data["Score"]<=data["MaxScore"])]

if data is not None and not data.empty:
    st.dataframe(data,use_container_width=True,hide_index=True)
    data["MasteryPct"]=(data["Score"]/data["MaxScore"]*100).round(1)
    summary=data.groupby("Skill",as_index=False).agg(AverageMastery=("MasteryPct","mean"),Responses=("Student","count"))
    summary["AverageMastery"]=summary["AverageMastery"].round(1)
    summary["Status"]=summary["AverageMastery"].apply(lambda x:"متقنة مبدئيًا" if x>=threshold else "تحتاج إلى دعم")
    st.markdown("### 2) تحليل المهارات")
    st.dataframe(summary.rename(columns={"Skill":"المهارة","AverageMastery":"متوسط الإتقان (%)","Responses":"عدد الإجابات","Status":"الحالة"}),use_container_width=True,hide_index=True)

    st.markdown("### 3) إنشاء خطة علاجية مخصصة")
    weak=summary[summary["AverageMastery"]<threshold]["Skill"].tolist()
    options=weak or summary["Skill"].tolist()
    skill=st.selectbox("اختر المهارة",options)
    mastery=float(summary.loc[summary["Skill"]==skill,"AverageMastery"].iloc[0])
    notes=st.text_area("ملاحظات المعلم (اختياري)",placeholder="مثال: يخلط الطلاب بين ترتيب الخطوات وشرط القرار.")
    if st.button("✨ أنشئ خطة بالذكاء الاصطناعي",type="primary",use_container_width=True):
        if not key:
            st.error("أضف OPENAI_API_KEY إلى إعدادات Secrets في Streamlit أولًا.")
        else:
            try:
                with st.spinner("يتم إنشاء الخطة..."):
                    result=generate_plan(OpenAI(api_key=key),model,subject,grade,skill,mastery,language,notes)
                st.session_state["last_plan"]=result
                st.session_state["last_skill"]=skill
            except Exception as e:
                st.error("تعذر إنشاء الخطة. تحقق من المفتاح والفوترة وإتاحة النموذج.")
                st.code(str(e)[:1000])
    if st.session_state.get("last_plan"):
        st.markdown("#### خطة المهارة: "+st.session_state.get("last_skill",""))
        st.markdown(st.session_state["last_plan"])
        st.download_button("تنزيل الخطة TXT",st.session_state["last_plan"],"mueen_learning_plan.txt","text/plain")

    st.markdown("### 4) مقارنة نتائج قبل التدخل وبعده")
    c1,c2=st.columns(2)
    with c1: before=st.number_input("قبل التدخل (%)",0.0,100.0,float(summary["AverageMastery"].mean()),1.0)
    with c2: after=st.number_input("بعد التدخل (%)",0.0,100.0,min(100.0,float(summary["AverageMastery"].mean())+10),1.0)
    st.metric("التغير في متوسط الإتقان",f"{after-before:+.1f} نقطة مئوية")
    st.caption("المقارنة وصفية ولا تثبت وحدها أن التدخل سبب التحسن.")
    out=summary.rename(columns={"Skill":"المهارة","AverageMastery":"متوسط الإتقان (%)","Responses":"عدد الإجابات","Status":"الحالة"})
    st.download_button("تنزيل تقرير المهارات CSV",out.to_csv(index=False).encode("utf-8-sig"),"mueen_skill_report.csv","text/csv")
else: st.warning("ارفع ملف CSV صالحًا أو فعّل البيانات النموذجية.")

with st.expander("🔐 ربط مفتاح OpenAI API بأمان — خطوة بخطوة"):
    st.markdown("""
1. افتح [OpenAI API Keys](https://platform.openai.com/api-keys) وأنشئ مفتاحًا.
2. تحقق من الفوترة والحدود في [إعدادات الفوترة](https://platform.openai.com/settings/organization/billing/overview). اشتراك ChatGPT لا يتضمن تلقائيًا رصيد API.
3. افتح [Streamlit Community Cloud](https://share.streamlit.io/) وسجّل الدخول.
4. افتح قائمة التطبيق ثم **Settings → Secrets**.
5. أضف السطر التالي مع استبدال النص بمفتاحك الحقيقي:

```toml
OPENAI_API_KEY = "ضع_مفتاحك_الحقيقي_هنا"
```

6. احفظ، ثم أعد تحميل التطبيق.
7. تأكد من ظهور رسالة العثور على المفتاح، ثم جرّب زر إنشاء الخطة.

لا تضع المفتاح في `app.py` أو GitHub، ولا ترسله في المحادثة أو صورة. إذا انكشف، ألغِه وأنشئ آخر.
""")
st.divider()
st.caption("MUEEN AI V2 نموذج تجريبي. قد تتضمن المخرجات أخطاء؛ راجعها قبل استخدامها. لا ترفع بيانات تعريفية للطلاب.")
