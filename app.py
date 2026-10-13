import streamlit as st
import pandas as pd
from openai import OpenAI
from datetime import datetime
from supabase import create_client

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



def get_supabase():
    """Server-side connection. Keep the Supabase secret key only in Streamlit Secrets."""
    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_SECRET_KEY", "")
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception:
        return None

def save_assessment_records(records):
    client = get_supabase()
    if client is None:
        raise ValueError("اتصال Supabase غير مُعد. راجع إعدادات Secrets.")
    client.table("assessment_records").insert(records).execute()

def save_student(student_code, grade, section):
    client = get_supabase()
    if client is None:
        raise ValueError("اتصال Supabase غير مُعد. راجع إعدادات Secrets.")
    # Insert a simple roster record. The table may contain repeated codes unless
    # the project has a unique constraint; no destructive upsert is performed.
    client.table("students").insert({
        "student_code": student_code,
        "grade": grade,
        "section": section
    }).execute()

def load_history(student_code):
    client = get_supabase()
    if client is None:
        raise ValueError("اتصال Supabase غير مُعد. راجع إعدادات Secrets.")
    response = (client.table("assessment_records")
                .select("student_code,skill,assessment_type,score,max_score,recommendation,created_at")
                .eq("student_code", student_code)
                .order("created_at", desc=True)
                .limit(200)
                .execute())
    return pd.DataFrame(response.data or [])

def decide(before, after, threshold):
    delta=after-before
    if after>=threshold: return "إتقان مبدئي: يمكن للمعلم التفكير في الانتقال إلى مهارة تالية أو نشاط إثرائي.",delta
    if delta>0: return "يوجد تحسن، لكن الإتقان المستهدف لم يتحقق بعد. يُقترح تدريب إضافي أو مثال جديد ثم إعادة التقييم.",delta
    return "لم يظهر تحسن في الدرجة المدخلة. راجع ملاءمة الأسئلة وطريقة التدريس، وجرّب نشاطًا بديلًا قبل إعادة التقييم.",delta

st.title("🎓 مُعين | MUEEN AI")
st.subheader("وكيل دعم التعلم الذكي — النسخة الثالثة")
st.caption("تحليل المهارات • خطط علاجية • اختبارات متابعة • حفظ النتائج واستعراض سجل المتابعة")
st.info("هذه نسخة تجريبية للمعلم. استخدم رموزًا تعليمية مستعارة بدل أسماء الطلاب، ولا تضع بيانات شخصية حساسة.")
st.warning("استخدم بيانات تجريبية أو مجهولة الهوية فقط، وراجع المخرجات قبل استخدامها مع الطلاب.")
with st.sidebar:
    st.header("إعدادات التحليل")
    subject=st.selectbox("المادة",["الحوسبة","الرياضيات","العلوم","اللغة العربية","اللغة الإنجليزية"])
    grade=st.selectbox("الصف",["الخامس","السادس","السابع","الثامن","التاسع"])
    threshold=st.slider("حد الإتقان (%)",50,100,80,5)
    language=st.selectbox("لغة المخرجات",["العربية","English"])
    model=st.text_input("اسم نموذج API",value="gpt-4.1-mini")
key=get_key()
db_client=get_supabase()
if db_client:
    st.sidebar.success("قاعدة بيانات Supabase متصلة")
else:
    st.sidebar.warning("قاعدة البيانات غير مفعّلة: أضف SUPABASE_URL وSUPABASE_SECRET_KEY في Streamlit Secrets.")
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
    st.markdown("### 2.1) إعداد سجل المجموعة")
    a1, a2, a3 = st.columns(3)
    with a1: student_code = st.text_input("رمز الطالب/المجموعة (مجهول الهوية)", value="DEMO-GROUP", help="استخدم رمزًا مستعارًا، لا تكتب اسم الطالب.")
    with a2: section = st.text_input("الشعبة", value="A")
    with a3: db_grade = st.selectbox("الصف للحفظ", ["الخامس","السادس","السابع","الثامن","التاسع"], index=["الخامس","السادس","السابع","الثامن","التاسع"].index(grade))
    if st.button("💾 حفظ نتائج التقييم القبلي في Supabase", use_container_width=True):
        try:
            save_student(student_code.strip(), db_grade, section.strip())
            records = [{
                "student_code": student_code.strip(),
                "skill": str(row["Skill"]),
                "assessment_type": "baseline",
                "score": float(row["AverageMastery"]),
                "max_score": 100.0,
                "recommendation": "متوسط الإتقان القبلي للمجموعة؛ الحالة: " + str(row["Status"])
            } for _, row in summary.iterrows()]
            save_assessment_records(records)
            st.success(f"تم حفظ {len(records)} سجلًا قبليًا بنجاح.")
        except Exception as e:
            st.error("تعذر حفظ النتائج. تأكد من إعداد Secrets وأسماء أعمدة الجداول.")
            st.caption(str(e)[:500])
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
        if st.button("☁️ حفظ التقييم البعدي والتوصية في Supabase", use_container_width=True):
            try:
                save_assessment_records([{
                    "student_code": student_code.strip(),
                    "skill": str(skill),
                    "assessment_type": "follow_up",
                    "score": float(result["AfterPct"]),
                    "max_score": 100.0,
                    "recommendation": str(result["SuggestedNextStep"]) + f" | القبلي: {result['BeforePct']}% | التغير: {result['ChangePoints']:+.1f} نقطة"
                }])
                st.success("تم حفظ نتيجة التقييم البعدي والتوصية في قاعدة البيانات.")
            except Exception as e:
                st.error("تعذر حفظ النتيجة. تأكد من إعداد Secrets وصلاحية الاتصال.")
                st.caption(str(e)[:500])
    st.markdown("### 6) سجل المتابعة المحفوظ")
    hist_code = st.text_input("رمز الطالب/المجموعة لعرض السجل", value=student_code, key="history_code")
    if st.button("عرض السجل من Supabase"):
        try:
            history = load_history(hist_code.strip())
            if history.empty:
                st.info("لا توجد سجلات لهذا الرمز حتى الآن.")
            else:
                st.dataframe(history, use_container_width=True, hide_index=True)
                st.download_button("تنزيل السجل المحفوظ CSV", history.to_csv(index=False).encode("utf-8-sig"), "mueen_saved_history.csv", "text/csv")
        except Exception as e:
            st.error("تعذر جلب السجل. تأكد من إعداد Secrets.")
            st.caption(str(e)[:500])
    st.markdown("### 7) تنزيل تقرير المهارات")
    st.download_button("تنزيل تقرير المهارات CSV",view.to_csv(index=False).encode("utf-8-sig"),"mueen_skill_report.csv","text/csv")
else: st.warning("ارفع ملف CSV صالحًا أو فعّل البيانات النموذجية.")
with st.expander("🔐 إعداد مفاتيح OpenAI وSupabase بأمان"):
    st.markdown("""1. احتفظ بمفتاح OpenAI في Streamlit → Settings → Secrets باسم `OPENAI_API_KEY`.
2. أضف `SUPABASE_URL` و`SUPABASE_SECRET_KEY` إلى Secrets في إعدادات تطبيق Streamlit.
3. مفتاح Supabase Secret يتجاوز RLS؛ لا تستخدمه إلا في تطبيق خاص موثوق من جهة الخادم، ولا تضعه في GitHub أو في الكود أو داخل واجهة التطبيق. لا تشاركه في المحادثة.
4. مفتاح `sb_publishable_...` وحده لن يسمح بالحفظ ما دامت سياسات RLS لا تسمح بالعمليات.
5. قبل فتح التطبيق لطلاب أو مستخدمين آخرين، استبدل وصول الخادم الإداري بتسجيل دخول وسياسات RLS دقيقة.""")
st.divider()
st.caption("MUEEN AI V3.1 — عند تفعيل Supabase تُحفظ النتائج القبلية والبعدية وتوصيات المتابعة في قاعدة البيانات. استخدم رموزًا مجهولة الهوية واختبر ببيانات تجريبية أولًا.")
