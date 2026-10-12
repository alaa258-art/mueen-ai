import streamlit as st
import pandas as pd
from openai import OpenAI
from datetime import datetime

st.set_page_config(page_title="MUEEN AI V3 | مُعين", page_icon="🎓", layout="wide")
st.markdown("<style>.main{direction:rtl} h1,h2,h3,p,label,div[data-testid='stMarkdownContainer']{text-align:right}</style>", unsafe_allow_html=True)

def get_key():
    try: return st.secrets.get("OPENAI_API_KEY", "")
    except Exception: return ""

def ai(model, prompt):
    key=get_key()
    if not key: raise ValueError("لم يتم العثور على OPENAI_API_KEY في Streamlit Secrets.")
    return OpenAI(api_key=key).responses.create(model=model, input=prompt).output_text

def create_plan(model, subject, grade, skill, mastery, language, notes, group):
    prompt=f"""أنت وكيل دعم تعلم يساعد المعلم وليس بديلًا عنه. أنشئ خطة علاجية عملية باللغة {language}.
المادة: {subject}؛ الصف: {grade}؛ المهارة: {skill}؛ متوسط الإتقان: {mastery:.1f}%؛ الفئة: {group}؛ ملاحظات المعلم: {notes or 'لا توجد'}.
نظّم الإجابة: 1) تفسير حذر للنتيجة دون افتراض أسباب غير مثبتة. 2) هدف قابل للقياس. 3) شرح مبسط. 4) مثال محلول. 5) نشاط علاجي 10 دقائق. 6) خمسة أسئلة متابعة مع الإجابات. 7) معيار إتقان مقترح 80% أو وفق إعداد المعلم. 8) بديل إذا لم يتحقق الإتقان. 9) الخطوة التالية بعد التقييم البعدي. لا تشخّص طبيًا أو نفسيًا، واجعل المعلم صاحب القرار."""
    return ai(model,prompt)

def create_quiz(model, subject, grade, skill, language):
    prompt=f"أنشئ اختبار متابعة من 5 أسئلة للمهارة {skill} في مادة {subject} للصف {grade} باللغة {language}. نوّع بين الاختيار من متعدد والإجابة القصيرة. اعرض الأسئلة أولًا ثم مفتاح إجابة منفصل للمعلم، مع معيار تصحيح مختصر. لا تفترض معلومات عن طالب بعينه."
    return ai(model,prompt)

def decide(before, after, threshold):
    delta=after-before
    if after>=threshold: return "إتقان مبدئي: يمكن للمعلم التفكير في الانتقال إلى مهارة تالية أو نشاط إثرائي.",delta
    if delta>0: return "يوجد تحسن، لكن الإتقان المستهدف لم يتحقق بعد. يُقترح تدريب إضافي أو مثال جديد ثم إعادة التقييم.",delta
    return "لم يظهر تحسن في الدرجة المدخلة. راجع ملاءمة الأسئلة وطريقة التدريس، وجرّب نشاطًا بديلًا قبل إعادة التقييم.",delta

st.title("🎓 مُعين | MUEEN AI")
st.subheader("وكيل دعم التعلم الذكي — النسخة الثالثة")
st.caption("تحليل المهارات • خطط علاجية • اختبارات متابعة • توصية بالخطوة التالية")
st.warning("استخدم بيانات تجريبية أو مجهولة الهوية فقط، وراجع المخرجات قبل استخدامها مع الطلاب.")
with st.sidebar:
    st.header("إعدادات التحليل")
    subject=st.selectbox("المادة",["الحوسبة","الرياضيات","العلوم","اللغة العربية","اللغة الإنجليزية"])
    grade=st.selectbox("الصف",["الخامس","السادس","السابع","الثامن","التاسع"])
    threshold=st.slider("حد الإتقان (%)",50,100,80,5)
    language=st.selectbox("لغة المخرجات",["العربية","English"])
    model=st.text_input("اسم نموذج API",value="gpt-4.1-mini")
key=get_key()
if key: st.success("تم العثور على مفتاح API. لن نعرضه داخل التطبيق.")
else: st.info("أضف OPENAI_API_KEY إلى Settings → Secrets في Streamlit لتفعيل ميزات الذكاء الاصطناعي.")

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
st.markdown("### 1) بيانات التقييم القبلي")
st.write("أعمدة CSV المطلوبة: `Student`, `Skill`, `Score`, `MaxScore`.")
uploaded=st.file_uploader("ارفع ملف CSV",type=["csv"])
use_demo=st.checkbox("استخدام البيانات النموذجية",value=True)
data=None
if uploaded is not None:
    try: data=pd.read_csv(uploaded)
    except Exception as e: st.error(f"تعذر قراءة الملف: {e}")
elif use_demo: data=demo.copy()
if data is not None:
    required={"Student","Skill","Score","MaxScore"}
    if not required.issubset(data.columns): st.error("الأعمدة المطلوبة: Student, Skill, Score, MaxScore"); data=None
    else:
        data=data.copy(); data["Score"]=pd.to_numeric(data["Score"],errors="coerce"); data["MaxScore"]=pd.to_numeric(data["MaxScore"],errors="coerce")
        data=data.dropna(subset=["Student","Skill","Score","MaxScore"])
        data=data[(data["MaxScore"]>0)&(data["Score"]>=0)&(data["Score"]<=data["MaxScore"])]
if data is not None and not data.empty:
    st.dataframe(data,use_container_width=True,hide_index=True)
    data["MasteryPct"]=(data["Score"]/data["MaxScore"]*100).round(1)
    summary=data.groupby("Skill",as_index=False).agg(AverageMastery=("MasteryPct","mean"),Responses=("Student","count"))
    summary["AverageMastery"]=summary["AverageMastery"].round(1)
    summary["Status"]=summary["AverageMastery"].apply(lambda x:"متقنة مبدئيًا" if x>=threshold else "تحتاج إلى دعم")
    st.markdown("### 2) تحليل المهارات وتحديد الأولوية")
    view=summary.rename(columns={"Skill":"المهارة","AverageMastery":"متوسط الإتقان (%)","Responses":"عدد الإجابات","Status":"الحالة"})
    st.dataframe(view,use_container_width=True,hide_index=True)
    weak=summary[summary["AverageMastery"]<threshold]["Skill"].tolist(); options=weak or summary["Skill"].tolist()
    skill=st.selectbox("اختر المهارة المستهدفة",options)
    mastery=float(summary.loc[summary["Skill"]==skill,"AverageMastery"].iloc[0])
    st.metric("متوسط الإتقان القبلي للمهارة",f"{mastery:.1f}%")
    notes=st.text_area("ملاحظات المعلم (اختياري)",placeholder="مثال: يحتاج بعض الطلاب إلى مثال بصري لترتيب الخطوات.")
    group=st.selectbox("الفئة المستهدفة",["مجموعة دعم","مجموعة الصف","مجموعة إثراء"])
    st.markdown("### 3) إنشاء خطة علاجية")
    if st.button("✨ إنشاء خطة بالذكاء الاصطناعي",type="primary",use_container_width=True):
        try:
            with st.spinner("يُعد مُعين الخطة..."):
                st.session_state["last_plan"]=create_plan(model,subject,grade,skill,mastery,language,notes,group)
                st.session_state["last_skill"]=skill
        except Exception as e:
            st.error("تعذر إنشاء الخطة. تحقق من المفتاح والفوترة وإتاحة النموذج."); st.code(str(e)[:1000])
    if st.session_state.get("last_plan"):
        st.markdown("#### الخطة العلاجية: "+st.session_state.get("last_skill","")); st.markdown(st.session_state["last_plan"])
        st.download_button("تنزيل الخطة TXT",st.session_state["last_plan"],"mueen_learning_plan.txt","text/plain")
    st.markdown("### 4) إنشاء اختبار متابعة")
    if st.button("📝 إنشاء اختبار متابعة من 5 أسئلة",use_container_width=True):
        try:
            with st.spinner("يُنشئ مُعين الاختبار..."):
                st.session_state["last_quiz"]=create_quiz(model,subject,grade,skill,language)
                st.session_state["quiz_skill"]=skill
        except Exception as e:
            st.error("تعذر إنشاء الاختبار. تحقق من إعدادات API."); st.code(str(e)[:1000])
    if st.session_state.get("last_quiz"):
        st.markdown("#### اختبار المتابعة: "+st.session_state.get("quiz_skill","")); st.markdown(st.session_state["last_quiz"])
        st.download_button("تنزيل اختبار المتابعة TXT",st.session_state["last_quiz"],"mueen_followup_quiz.txt","text/plain")
    st.markdown("### 5) تسجيل نتيجة التقييم البعدي")
    st.caption("أدخل نتيجة التقييم بعد تنفيذ النشاط. سجل هذه النسخة مؤقت خلال الجلسة الحالية فقط.")
    c1,c2=st.columns(2)
    with c1: before=st.number_input("الإتقان القبلي (%)",0.0,100.0,float(mastery),1.0)
    with c2: after=st.number_input("الإتقان البعدي (%)",0.0,100.0,min(100.0,float(mastery)+10),1.0)
    if st.button("تحليل التحسن والخطوة التالية",use_container_width=True):
        recommendation,delta=decide(before,after,threshold)
        st.session_state["followup"]={"Date":datetime.now().strftime("%Y-%m-%d %H:%M"),"Subject":subject,"Grade":grade,"Skill":skill,"BeforePct":float(before),"AfterPct":float(after),"ChangePoints":float(delta),"MasteryThreshold":int(threshold),"SuggestedNextStep":recommendation}
    if st.session_state.get("followup"):
        result=st.session_state["followup"]
        st.metric("التغير في الإتقان",f"{result['ChangePoints']:+.1f} نقطة مئوية")
        if result["AfterPct"]>=result["MasteryThreshold"]: st.success(result["SuggestedNextStep"])
        elif result["ChangePoints"]>0: st.info(result["SuggestedNextStep"])
        else: st.warning(result["SuggestedNextStep"])
        st.caption("التوصية مساندة للمعلم وليست قرارًا آليًا نهائيًا.")
        st.download_button("تنزيل سجل المتابعة CSV",pd.DataFrame([result]).to_csv(index=False).encode("utf-8-sig"),"mueen_followup_record.csv","text/csv")
    st.markdown("### 6) تنزيل تقرير المهارات")
    st.download_button("تنزيل تقرير المهارات CSV",view.to_csv(index=False).encode("utf-8-sig"),"mueen_skill_report.csv","text/csv")
else: st.warning("ارفع ملف CSV صالحًا أو فعّل البيانات النموذجية.")
with st.expander("🔐 ربط مفتاح OpenAI API بأمان"):
    st.markdown("1. أنشئ مفتاحًا من [OpenAI API Keys](https://platform.openai.com/api-keys).\n2. افتح التطبيق في [Streamlit Community Cloud](https://share.streamlit.io/).\n3. ادخل Settings → Secrets وأضف `OPENAI_API_KEY = \"مفتاحك\"`.\n4. لا تضع المفتاح في الكود أو GitHub ولا تشاركه في المحادثة.")
st.divider()
st.caption("MUEEN AI V3 نموذج أولي. سجل المتابعة لا يُحفظ في قاعدة بيانات دائمة؛ نزّل CSV للاحتفاظ به. لا ترفع بيانات تعريفية للطلاب.")
