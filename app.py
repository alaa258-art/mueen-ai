import streamlit as st
import pandas as pd
import json
import html
import re
from openai import OpenAI
from datetime import datetime
from supabase import create_client
st.markdown("""
<style>
/* الهوية البصرية لمنصة مُعين */
:root {
    --mueen-navy: #10243A;
    --mueen-teal: #087E8B;
    --mueen-bg: #F3F6FA;
    --mueen-gold: #D9A441;
}

/* خلفية التطبيق */
.stApp {
    background-color: var(--mueen-bg);
}

/* مساحة المحتوى */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 0.5rem !important;
}

/* العناوين */
h1, h2, h3 {
    color: var(--mueen-navy);
    font-weight: 700;
}

/* الأزرار */
.stButton > button,
.stDownloadButton > button {
    background-color: var(--mueen-teal);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.55rem 1rem;
    font-weight: 600;
    transition: all 0.2s ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    background-color: var(--mueen-navy);
    color: white;
    border: none;
}

/* حقول الإدخال */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea {
    border-radius: 8px;
}

/* القوائم المنسدلة */
.stSelectbox > div > div {
    border-radius: 8px;
}

/* البطاقات والتنبيهات */
div[data-testid="stMetric"],
div[data-testid="stAlert"] {
    border-radius: 12px;
}

/* تنسيق العربية الافتراضي */
.main {
    direction: rtl;
}

h1, h2, h3, p, label,
div[data-testid="stMarkdownContainer"] {
    text-align: right;
}

/* انتقالات مريحة */
button, input, textarea {
    transition: border-color 0.2s ease;
}
</style>
""", unsafe_allow_html=True)


def get_key():
    try: return st.secrets.get("OPENAI_API_KEY", "")
    except Exception: return ""

def ai(model, prompt):
    key=get_key()
    if not key: raise ValueError("لم يتم العثور على OPENAI_API_KEY في Streamlit Secrets.")
    return OpenAI(api_key=key).responses.create(model=model, input=prompt).output_text


def create_plan(model, subject, grade, skill, mastery, output_language, notes, group, threshold=80):
    """إنشاء خطة علاجية موجهة بالبيانات؛ يراجع المعلم مخرجاتها قبل التطبيق."""
    prompt = f"""أنت خبير تربوي مساعد للمعلم في منصة مُعين. أنشئ خطة علاجية عملية باللغة {output_language} فقط.

سياق المهمة:
- المادة المعتمدة لهذه الخطة: {subject}
- الصف: {grade}
- المهارة المستهدفة: {skill}
- متوسط الإتقان القبلي للمجموعة: {mastery:.1f}%
- حد الإتقان الذي حدده المعلم: {threshold}%
- الفئة: {group}
- ملاحظات المعلم: {notes or 'لا توجد ملاحظات إضافية'}

قواعد الدقة التربوية (إلزامية):
1. نسبة {mastery:.1f}% هي متوسط نتائج المجموعة في هذه المهارة، وليست نسبة الطلاب المتعثرين أو نسبة من أتقنوا المهارة. لا تقل «معظم الطلاب» أو «80% من الطلاب» دون بيانات تثبت ذلك.
2. فسّر النتيجة بوصفها مؤشرًا إلى الحاجة للتحقق والدعم، ولا تنسبها إلى سبب نفسي أو معرفي محدد دون دليل. يمكن اقتراح طرق تحقق للمعلم.
3. اكتب هدفًا سلوكيًا قابلًا للقياس يحدد أداء المتعلم، وأداة قياس (اختبار متابعة أو مهمة أداء)، والدرجة المستهدفة {threshold}%، ومدة زمنية مقترحة قابلة للتعديل. لا تدّعِ أن الهدف تحقق.
4. يجب أن يرتبط المثال المحلول والنشاط والأسئلة ارتباطًا مباشرًا بمادة «{subject}» ومهارة «{skill}» ومحتوى مناسب للصف «{grade}». إذا كانت المادة حوسبة والمهارة ترتيب خطوات الحل، استخدم خوارزمية حاسوبية بسيطة (مثل حفظ ملف أو رسم شكل في برنامج) مع تسلسل صحيح وخطوات قابلة للتنفيذ. لا تستخدم مثال إعداد الشاي أو الطعام.
5. قدم نشاطًا علاجيًا مدته 10 دقائق مع أدوات لازمة، وخطوات تنفيذ قصيرة، وطريقة ملاحظة أداء الطلاب، وتكييف مبسط عند الحاجة.
6. قدم خمسة أسئلة متنوعة لقياس المهارة المستهدفة، ثم الإجابة الصحيحة لكل سؤال. تأكد من أن الأسئلة والإجابات متسقة مع المثال والهدف.
7. حدد طريقة تصحيح قابلة للتطبيق: خمس فقرات متساوية = 20 درجة مئوية لكل فقرة؛ حد النجاح {threshold}%، مع بيان عدد الإجابات الصحيحة اللازم إذا كان الحد قابلًا للتحقيق بمضاعفات 20، وإلا وضح الحاجة إلى سلم تقدير أدق.
8. اقترح تدخلًا بديلًا عند عدم تحقق الإتقان، وخطوة متابعة بعد الاختبار البعدي، على أن يراجع المعلم القرار.
9. تجنب البيانات الشخصية، والتشخيص، والأحكام الجازمة، والمعلومات غير المستندة إلى المدخلات.

متطلبات الإخراج الضرورية للتصميم:
- اكتب باللغة العربية فقط إذا كانت اللغة العربية، أو الإنجليزية فقط إذا كانت English.
- استخدم العناوين التسعة التالية حرفيًا، كل عنوان في سطر مستقل دون ترقيم سابق له، ثم المحتوى تحته:
"""
    if output_language == "English":
        prompt += """Interpretation
Measurable objective
Simple explanation
Worked example
10-minute activity
Follow-up questions
Mastery criterion
Alternative support
Next steps
"""
    else:
        prompt += """تفسير النتيجة
الهدف القابل للقياس
الشرح المبسط
المثال المحلول
النشاط العلاجي
أسئلة المتابعة
معيار الإتقان
التدخل البديل
الخطوة التالية
"""
    prompt += """- اكتب الخطوات في أسطر منفصلة مرقمة 1. ثم 2. وهكذا؛ وضع كل سؤال وإجابته في سطرين واضحين.
- لا تستخدم جداول Markdown، ولا تضف عنوانًا عاشرًا أو مقدمة خارج الأقسام التسعة.
- اجعل كل قسم موجزًا ومباشرًا مع دقة تربوية عالية."""
    return ai(model, prompt)


def create_quiz(model, subject, grade, skill, output_language):
    prompt = f"""اكتب الاختبار كاملًا باللغة {output_language} فقط، بما في ذلك الأسئلة والتعليمات ومفتاح الإجابة.
إذا كانت اللغة English، فاكتب الاختبار كله باللغة الإنجليزية.
إذا كانت اللغة العربية، فاكتب الاختبار كله باللغة العربية.
أنشئ اختبار متابعة من 5 أسئلة للمهارة {skill} في مادة {subject} للصف {grade} باللغة {output_language}. نوّع بين الاختيار من متعدد والإجابة القصيرة. اعرض الأسئلة أولًا ثم مفتاح إجابة منفصل للمعلم، مع معيار تصحيح مختصر. لا تفترض معلومات عن طالب بعينه."""
    return ai(model, prompt)


def create_achievement_analysis(model, aggregate_json, threshold, output_language):
    """تحليل تعليمي من بيانات مجمعة فقط؛ لا ترسل رموز الطلاب أو سجلاتهم الفردية."""
    prompt = f"""اكتب التحليل كاملًا باللغة {output_language} فقط.
إذا كانت اللغة English، فاكتب العناوين والتحليل والتوصيات كلها باللغة الإنجليزية.
إذا كانت اللغة العربية، فاكتب العناوين والتحليل والتوصيات كلها باللغة العربية.
أنت محلل بيانات تعليمية مساعد للمعلم. حلل مؤشرات التحصيل التالية بحذر وباللغة {output_language}.
حد الإتقان المعتمد: {threshold}%.
بيانات مجمعة حسب المهارة ونوع التقييم فقط (لا تحتوي على أسماء أو رموز طلاب):
{aggregate_json}
التزم بالقواعد التالية:
1) استشهد بالأرقام الموجودة في البيانات فقط، ولا تخترع أعدادًا أو نسبًا.
2) ميّز بين الملاحظة المؤكدة والفرضية التي تحتاج تحققًا من المعلم.
3) لا تستنتج تحسنًا قبليًا/بعديًا إلا إذا كانت البيانات تعرض النوعين بوضوح، ولا تعتبر المتوسطات المجمعة دليلًا على تحسن الطالب الفردي.
4) اذكر أقوى المهارات وأبرز المهارات التي تحتاج دعمًا استنادًا إلى المتوسطات المعروضة وحد الإتقان.
5) اقترح ثلاث خطوات تعليمية عملية قابلة للتنفيذ، وخطوة تحقق لاحقة باستخدام اختبار متابعة.
6) لا تشخّص الطالب ولا تتخذ قرارًا آليًا بشأنه؛ اجعل التوصيات مساندة للمعلم.
7) إذا كانت البيانات قليلة أو غير كافية للمقارنة، صرّح بذلك بوضوح.
استخدم العناوين: ملخص المؤشرات، نقاط القوة، أولويات الدعم، خطوات مقترحة، حدود التحليل."""
    return ai(model, prompt)

    



def get_auth_client():
    """إنشاء اتصال Supabase باستخدام المفتاح العام فقط."""
    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_PUBLISHABLE_KEY", "")
        if not url or not key:
            return None
        return create_client(url, key)
    except Exception:
        return None


def clear_login():
    for key in ("mueen_access_token", "mueen_refresh_token", "mueen_school_id", "mueen_school_role"):
        st.session_state.pop(key, None)


def get_supabase():
    """إعادة إنشاء اتصال موثّق بجلسة المستخدم وتخزين أي رموز مجددة."""
    try:
        client = get_auth_client()
        access_token = st.session_state.get("mueen_access_token")
        refresh_token = st.session_state.get("mueen_refresh_token")
        if client is None or not access_token or not refresh_token:
            return None

        client.auth.set_session(access_token, refresh_token)
        session = client.auth.get_session()
        if session:
            st.session_state["mueen_access_token"] = session.access_token
            st.session_state["mueen_refresh_token"] = session.refresh_token
        return client
    except Exception:
        return None


def get_current_user_id(client):
    response = client.auth.get_user()
    user = getattr(response, "user", None)
    if not user:
        raise ValueError("تعذر التحقق من المستخدم. سجّل الدخول مجددًا.")
    return str(user.id)


def get_selected_school_id():
    school_id = st.session_state.get("mueen_school_id")
    if not school_id:
        raise ValueError("اختر المدرسة أولًا.")
    return school_id


def get_user_schools(client, user_id):
    """إرجاع المدارس التي للمستخدم عضوية نشطة فيها فقط."""
    memberships = (
        client.table("school_memberships")
        .select("school_id,role,is_active")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .execute()
    ).data or []
    role_by_school = {
        str(row["school_id"]): row["role"]
        for row in memberships
        if row.get("school_id") and row.get("role")
    }
    school_ids = list(role_by_school.keys())
    if not school_ids:
        return []

    schools = (
        client.table("schools")
        .select("id,name")
        .in_("id", school_ids)
        .execute()
    ).data or []

    result = []
    for school in schools:
        school_id = str(school.get("id", ""))
        if school_id in role_by_school:
            result.append({
                "id": school_id,
                "name": school.get("name") or "مدرسة دون اسم",
                "role": role_by_school[school_id],
            })
    return sorted(result, key=lambda item: item["name"])


def save_assessment_records(records):
    client = get_supabase()
    if client is None:
        raise ValueError("جلسة Supabase غير متاحة. سجّل الدخول مجددًا.")
    user_id = get_current_user_id(client)
    school_id = get_selected_school_id()

    prepared_records = []
    for record in records:
        item = dict(record)
        item["school_id"] = school_id
        item["created_by"] = user_id
        prepared_records.append(item)

    client.table("assessment_records").insert(prepared_records).execute()


def save_student(student_code, grade, section):
    """استخدم سجل الطالب الموجود في المدرسة بدل إنشاء سجل مكرر."""
    client = get_supabase()
    if client is None:
        raise ValueError("جلسة Supabase غير متاحة. سجّل الدخول مجددًا.")
    user_id = get_current_user_id(client)
    school_id = get_selected_school_id()

    # ابحث عن الطالب داخل المدرسة النشطة أولًا.
    existing = (
        client.table("students")
        .select("id,student_code,school_id")
        .eq("student_code", student_code)
        .eq("school_id", school_id)
        .limit(1)
        .execute()
    ).data or []

    if existing:
        # السجل موجود بالفعل؛ لا تعِد إدخاله حتى لا يحدث تعارض unique.
        return existing[0]

    # لا يوجد سجل مطابق في المدرسة النشطة، لذا أنشئه.
    # إذا كان الرمز مستخدمًا في مدرسة أخرى وكان student_code فريدًا عالميًا،
    # ستظهر رسالة تعارض؛ عندها يلزم مراجعة تصميم القيد في قاعدة البيانات.
    response = client.table("students").insert({
        "student_code": student_code,
        "grade": grade,
        "section": section,
        "school_id": school_id,
        "created_by": user_id,
    }).execute()
    return (response.data or [None])[0]


def load_history(student_code):
    client = get_supabase()
    if client is None:
        raise ValueError("جلسة Supabase غير متاحة. سجّل الدخول مجددًا.")
    school_id = get_selected_school_id()
    response = (
        client.table("assessment_records")
        .select("student_code,skill,assessment_type,score,max_score,recommendation,created_at")
        .eq("school_id", school_id)
        .eq("student_code", student_code)
        .order("created_at", desc=True)
        .limit(200)
        .execute()
    )
    return pd.DataFrame(response.data or [])


def load_all_history(limit=1000):
    """تحميل أحدث سجلات المدرسة المختارة؛ وتظل RLS هي طبقة الحماية الأساسية."""
    client = get_supabase()
    if client is None:
        raise ValueError("جلسة Supabase غير متاحة. سجّل الدخول مجددًا.")
    school_id = get_selected_school_id()
    response = (
        client.table("assessment_records")
                .select("student_code,skill,assessment_type,score,max_score,recommendation,created_at,section_id,subject_id")
        .eq("school_id", school_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return pd.DataFrame(response.data or [])

def decide(before, after, threshold):
    delta=after-before
    if after>=threshold: return "إتقان مبدئي: يمكن للمعلم التفكير في الانتقال إلى مهارة تالية أو نشاط إثرائي.",delta
    if delta>0: return "يوجد تحسن، لكن الإتقان المستهدف لم يتحقق بعد. يُقترح تدريب إضافي أو مثال جديد ثم إعادة التقييم.",delta
    return "لم يظهر تحسن في الدرجة المدخلة. راجع ملاءمة الأسئلة وطريقة التدريس، وجرّب نشاطًا بديلًا قبل إعادة التقييم.",delta



# MUEEN V5 — وظائف الوكيل المرتبطة بالجداول القائمة (دون جداول جديدة).
def mueen_v5_paired(baseline, followup, skill):
    """مقارنة الطالب نفسه والمهارة نفسها؛ لا تعتمد على متوسط مجموعتين مختلفتين."""
    required = {"Student", "Skill", "Score", "MaxScore"}
    if not required.issubset(baseline.columns) or not required.issubset(followup.columns):
        raise ValueError("الأعمدة المطلوبة: Student, Skill, Score, MaxScore")
    def clean(df):
        d = df.loc[df["Skill"].astype(str) == str(skill), list(required)].copy()
        d["Student"] = d["Student"].astype(str).str.strip()
        for col in ("Score", "MaxScore"):
            d[col] = pd.to_numeric(d[col], errors="coerce")
        d = d.dropna(subset=["Score", "MaxScore"])
        d = d[(d["Student"] != "") & (d["MaxScore"] > 0) & (d["Score"] >= 0) & (d["Score"] <= d["MaxScore"])]
        if d["Student"].duplicated().any():
            raise ValueError("يوجد أكثر من تقييم للطالب نفسه في المهارة؛ اختر تقييمًا واحدًا لكل طالب.")
        d["mastery"] = d["Score"] / d["MaxScore"] * 100
        return d[["Student", "mastery"]]
    before = clean(baseline).rename(columns={"mastery": "قبل"})
    after = clean(followup).rename(columns={"mastery": "بعد"})
    paired = before.merge(after, on="Student", how="inner", validate="one_to_one")
    if paired.empty:
        raise ValueError("لا توجد رموز طلاب مشتركة للمهارة المحددة بين الملفين.")
    paired["التغير"] = (paired["بعد"] - paired["قبل"]).round(2)
    return paired


def mueen_v5_save_plan(cycle, plan_title, strategy, criteria, student_id=None):
    client = get_supabase()
    if client is None:
        raise ValueError("انتهت جلسة Supabase.")
    school_id = get_selected_school_id()
    if school_id != cycle["school_id"]:
        raise ValueError("تغيرت المدرسة؛ أعد إنشاء الدورة.")
    role = str(st.session_state.get("mueen_school_role", "")).lower()
    if role not in ("principal", "coordinator"):
        raise PermissionError("سياسة قاعدة البيانات تسمح للمدير والمنسق فقط بحفظ الخطط حاليًا.")
    payload = {
        "school_id": school_id,
        "section_id": cycle.get("section_id"),
        "subject_id": cycle.get("subject_id"),
        "skill_id": cycle.get("skill_id"),
        "student_id": student_id,
        "plan_title": plan_title[:200],
        "learning_gap": f"{cycle['skill']} — متوسط قبلي {cycle['before']:.1f}%",
        "intervention_strategy": strategy,
        "success_criteria": criteria,
        "plan_status": "planned",
        "created_by": get_current_user_id(client),
    }
    response = client.table("intervention_plans").insert(payload).execute()
    if not response.data:
        raise ValueError("لم تُرجع قاعدة البيانات سجل الخطة.")
    return response.data[0]


def mueen_v5_save_followup(cycle, plan_id, decision, notes):
    client = get_supabase()
    if client is None:
        raise ValueError("انتهت جلسة Supabase.")
    if get_selected_school_id() != cycle["school_id"]:
        raise ValueError("تغيرت المدرسة؛ لا يمكن الحفظ.")
    if str(st.session_state.get("mueen_school_role", "")).lower() not in ("principal", "coordinator"):
        raise PermissionError("حفظ المتابعات متاح للمدير والمنسق حسب سياسات RLS الحالية.")
    payload = {
        "school_id": cycle["school_id"],
        "intervention_plan_id": plan_id,
        "followup_date": datetime.now().date().isoformat(),
        "activity_completed": "اختبار متابعة معتمد من المعلم",
        "teacher_notes": notes[:3000],
        "progress_percentage": float(decision["after"]),
        "next_action": decision["recommendation"],
        "recorded_by": get_current_user_id(client),
    }
    return client.table("intervention_followups").insert(payload).execute()


def mueen_v5_prior_interventions(school_id, subject_id=None, skill_id=None):
    client = get_supabase()
    if client is None:
        return []
    query = client.table("intervention_plans").select("id,plan_title,learning_gap,intervention_strategy,success_criteria,plan_status,created_at").eq("school_id", school_id)
    if subject_id:
        query = query.eq("subject_id", subject_id)
    if skill_id:
        query = query.eq("skill_id", skill_id)
    return query.order("created_at", desc=True).limit(20).execute().data or []


# MUEEN V5.1 — فحص تكامل آمن: قراءة فقط، دون كتابة أو حذف بيانات.

# V5.2 — اختبار كتابة حقيقي محدود بمدرسة تجريبية مستقلة.
def mueen_v52_write_probe():
    from uuid import uuid4
    from datetime import date
    results = []
    def add(name, status, detail):
        results.append({"الاختبار": name, "النتيجة": status, "التفاصيل": str(detail)})
    client = get_supabase()
    if client is None:
        add("الاتصال", "فشل", "لا توجد جلسة صالحة")
        return results
    school_id = str(get_selected_school_id())
    user_id = get_current_user_id(client)
    school_rows = client.table("schools").select("name").eq("id", school_id).limit(1).execute().data or []
    school_name = str(school_rows[0]["name"]) if school_rows else ""
    membership = (client.table("school_memberships").select("role")
                  .eq("school_id", school_id).eq("user_id", user_id)
                  .eq("is_active", True).limit(1).execute().data or [])
    role = str(membership[0]["role"]).lower() if membership else ""
    if not school_name.startswith("MUEEN_TEST_") or role not in ("principal", "coordinator"):
        add("شروط السلامة", "مرفوض",
            "يجب اختيار مدرسة اختبار مستقلة يبدأ اسمها حرفيًا بـ MUEEN_TEST_ وامتلاك دور مدير أو منسق.")
        return results

    token = "MUEEN_TEST_" + uuid4().hex
    plan_id = None
    followup_id = None
    try:
        payload = {
            "school_id": school_id, "plan_title": token,
            "learning_gap": "اختبار تقني فقط؛ لا يمثل طالبًا",
            "intervention_strategy": "اختبار كتابة واسترجاع",
            "success_criteria": "إمكانية استرجاع الخطة والمتابعة",
            "plan_status": "draft", "created_by": user_id
        }
        created = client.table("intervention_plans").insert(payload).execute().data or []
        if not created:
            raise RuntimeError("لم يرجع إدراج الخطة صفًا")
        plan_id = str(created[0]["id"])
        add("إدراج الخطة", "نجاح", f"معرّف الخطة التجريبية: {plan_id}")
        fetched = (client.table("intervention_plans").select("id,plan_title,school_id")
                   .eq("id", plan_id).eq("school_id", school_id).limit(1).execute().data or [])
        if not fetched or fetched[0].get("plan_title") != token:
            raise RuntimeError("لم يمكن استرجاع الخطة بنفس العلامة والمدرسة")
        add("استرجاع الخطة", "نجاح", "تطابقت علامة الاختبار ومعرّف المدرسة")
        followup = {
            "school_id": school_id, "intervention_plan_id": plan_id,
            "followup_date": date.today().isoformat(),
            "activity_completed": token, "teacher_notes": "اختبار تقني فقط",
            "progress_percentage": 10, "next_action": "لا إجراء — سجل تجريبي",
            "recorded_by": user_id
        }
        rows = client.table("intervention_followups").insert(followup).execute().data or []
        if not rows:
            raise RuntimeError("لم يرجع إدراج المتابعة صفًا")
        followup_id = str(rows[0]["id"])
        add("إدراج المتابعة", "نجاح", f"معرّف المتابعة: {followup_id}")
        fetched_followup = (client.table("intervention_followups")
                            .select("id,school_id,intervention_plan_id,activity_completed")
                            .eq("id", followup_id).eq("school_id", school_id).limit(1).execute().data or [])
        if (not fetched_followup or str(fetched_followup[0].get("intervention_plan_id")) != plan_id
                or fetched_followup[0].get("activity_completed") != token):
            raise RuntimeError("فشل التحقق من بيانات المتابعة المسترجعة")
        add("استرجاع المتابعة", "نجاح", "ارتباط المتابعة بالخطة والمدرسة صحيح")
    except Exception as exc:
        add("تنفيذ الاختبار", "فشل", type(exc).__name__ + ": " + str(exc)[:350])
    finally:
        if plan_id:
            add("التنظيف", "يتطلب إجراء", "سجلات اختبار محفوظة في مدرسة الاختبار؛ لا حذف تلقائي لعدم وجود سياسة DELETE.")
            add("معرّفات التنظيف", "معلومات", f"plan_id={plan_id}; followup_id={followup_id or 'لم يُنشأ'}")
    return results

def mueen_v51_integration_audit():
    results = []
    def record(test, ok, detail):
        results.append({"الاختبار": test, "النتيجة": "نجاح" if ok else "يحتاج مراجعة", "التفاصيل": str(detail)[:280]})

    client = get_supabase()
    if client is None:
        record("جلسة Supabase", False, "لا توجد جلسة مستخدم موثقة.")
        return results
    try:
        user_id = get_current_user_id(client)
        school_id = get_selected_school_id()
        memberships = (client.table("school_memberships")
                       .select("school_id,role,is_active")
                       .eq("school_id", school_id).eq("user_id", user_id)
                       .eq("is_active", True).limit(1).execute().data or [])
        role = str(memberships[0].get("role", "")).lower() if memberships else ""
        record("عضوية المدرسة النشطة", bool(memberships), f"عضوية نشطة: {bool(memberships)}؛ الدور: {role or 'غير معروف'}")
        if not memberships:
            return results
    except Exception as exc:
        record("التحقق من الهوية والعضوية", False, type(exc).__name__ + ": " + str(exc)[:170])
        return results

    for table, columns in [
        ("schools", "id,name"),
        ("academic_sections", "id,school_id"),
        ("academic_subjects", "id,school_id"),
        ("students", "id,school_id,student_code"),
        ("assessment_records", "id,school_id,student_code,skill,assessment_type,score,max_score"),
        ("intervention_plans", "id,school_id,plan_title"),
        ("intervention_followups", "id,school_id,intervention_plan_id"),
    ]:
        try:
            query = client.table(table).select(columns).eq("school_id", school_id).limit(50) if table != "schools" else client.table(table).select(columns).eq("id", school_id).limit(1)
            rows = query.execute().data or []
            scoped = all(str(row.get("school_id", school_id)) == str(school_id) for row in rows)
            record("قراءة " + table, scoped, f"{len(rows)} سجل ظاهر (حد القراءة 50). قد يكون الجدول فارغًا أو مقيدًا بـ RLS.")
        except Exception as exc:
            record("قراءة " + table, False, type(exc).__name__ + ": " + str(exc)[:170])

    try:
        before = pd.DataFrame([{"Student":"TEST-A","Skill":"مهارة اختبار","Score":40,"MaxScore":100}])
        after = pd.DataFrame([{"Student":"TEST-A","Skill":"مهارة اختبار","Score":50,"MaxScore":100}])
        matched = mueen_v5_paired(before, after, "مهارة اختبار")
        ok = len(matched) == 1 and abs(float(matched.iloc[0]["التغير"]) - 10) < 1e-8
        record("مطابقة التقييم القبلي والبعدي", ok, "تغير متوقع: +10 نقاط مئوية؛ بيانات محاكاة فقط.")
    except Exception as exc:
        record("مطابقة التقييم القبلي والبعدي", False, str(exc)[:180])
    try:
        recommendation, delta = decide(40, 50, 80)
        record("قرار الوكيل عند عدم بلوغ الإتقان", delta == 10 and "تحسن" in recommendation,
               f"التغير: {delta:+.0f}؛ {recommendation}")
        recommendation2, delta2 = decide(40, 85, 80)
        record("قرار الوكيل عند بلوغ الإتقان", delta2 == 45 and "إتقان" in recommendation2,
               f"التغير: {delta2:+.0f}؛ {recommendation2}")
    except Exception as exc:
        record("اختبار قرارات الوكيل", False, str(exc)[:180])

    record("صلاحية حفظ خطط التدخل", role in ("principal", "coordinator"),
           "صلاحية واجهة فقط؛ لم تُجرّب كتابة فعلية. الحماية النهائية لدى RLS.")
    record("الحفظ والاسترجاع الفعلي", False,
           "لم ينفذ: الفحص آمن للقراءة فقط؛ لا توجد سياسة حذف مضمونة لتنظيف السجلات التجريبية.")
    record("عزل البيانات بين مدرستين", False,
           "لم ينفذ: يلزم حساب اختبار ثانٍ ومدرسة ثانية للتحقق من منع الوصول عبر RLS.")
    return results

# بوابة تسجيل الدخول إلى مُعين AI - عربي / English
if "mueen_language" not in st.session_state:
    st.session_state["mueen_language"] = "العربية"

language = st.session_state["mueen_language"]
is_arabic = language == "العربية"

if not st.session_state.get("mueen_access_token"):

    # اختيار اللغة - مساحة علوية آمنة للعنوان
    st.markdown('<div style="height: 52px;"></div>', unsafe_allow_html=True)

    _, language_col = st.columns([3, 1])
    with language_col:
        selected_language = st.selectbox(
            "لغة الواجهة | Interface language",
            ["العربية", "English"],
            index=0 if is_arabic else 1,
            key="mueen_login_language"
        )

    if selected_language != st.session_state["mueen_language"]:
        st.session_state["mueen_language"] = selected_language
        st.rerun()

    language = st.session_state["mueen_language"]
    is_arabic = language == "العربية"

        # اتجاه الواجهة بحسب اللغة المختارة
    direction = "rtl" if is_arabic else "ltr"
    text_align = "right" if is_arabic else "left"

    st.markdown(
        f"""
        <style>
        .main {{
            direction: {direction};
        }}

        .main h1, .main h2, .main h3,
        .main p, .main label,
        .main div[data-testid="stMarkdownContainer"] {{
            text-align: {text_align};
        }}

        /* تقليل المسافات بين العناصر */
        div[data-testid="stVerticalBlock"] {{
            gap: 0.45rem !important;
        }}

        /* تقليل ارتفاع حقول الإدخال */
        div[data-testid="stTextInput"] input {{
            min-height: 38px !important;
            height: 38px !important;
        }}

        /* تقليل ارتفاع زر الدخول */
        div[data-testid="stButton"] button {{
            min-height: 40px !important;
            padding: 6px 14px !important;
        }}

        /* تقليل المسافة حول العناوين */
        h1, h2, h3 {{
            margin-top: 0.3rem !important;
            margin-bottom: 0.3rem !important;
        }}

        </style>
        """,
        unsafe_allow_html=True
    )
    # تصميم تسجيل الدخول فقط — لا يؤثر على الصفحات بعد تسجيل الدخول
        # ==========================================
    # MUEEN AI - PROFESSIONAL LOGIN DESIGN
    # ==========================================

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;600;700;800&display=swap');

    /* خلفية صفحة تسجيل الدخول */
    .stApp {
        background:
            radial-gradient(circle at 12% 18%, rgba(8,126,139,.10), transparent 32%),
            radial-gradient(circle at 88% 80%, rgba(217,164,65,.09), transparent 28%),
            linear-gradient(135deg, #F8FBFF 0%, #EDF5F9 55%, #F5F8FC 100%);
    }

    /* الخطوط */
    .stApp,
    .stApp input,
    .stApp button,
    .stApp label,
    .stApp p {
        font-family: 'Tajawal', 'Segoe UI', Arial, sans-serif !important;
    }

    /* مساحة الصفحة */
    .block-container {
        max-width: 820px !important;
        padding-top: 3rem !important;
        padding-bottom: 2rem !important;
    }

    /* بطاقة هوية مُعين */
    .mueen-login-hero {
        background: linear-gradient(125deg, #10243A 0%, #14536B 55%, #087E8B 100%);
        border-radius: 24px;
        padding: 38px 30px;
        margin: 12px 0 28px;
        text-align: center;
        border-bottom: 5px solid #D9A441;
        box-shadow: 0 18px 40px rgba(16,36,58,.18);
    }

    .mueen-login-hero .icon {
        font-size: 46px;
        margin-bottom: 12px;
    }

    .mueen-login-hero h1 {
        color: #FFFFFF !important;
        font-size: clamp(34px, 4vw, 48px) !important;
        font-weight: 800 !important;
        line-height: 1.5 !important;
        text-align: center !important;
        margin: 0 !important;
    }

    .mueen-login-hero p {
        color: #E7F7F8 !important;
        font-size: 20px !important;
        font-weight: 500 !important;
        text-align: center !important;
        margin-top: 8px !important;
    }

    /* عنوان تسجيل الدخول */
    .stApp h3 {
        color: #10243A !important;
        font-size: 29px !important;
        font-weight: 800 !important;
    }

    /* النصوص التوضيحية */
    .stCaptionContainer,
    [data-testid="stCaptionContainer"] {
        font-size: 16px !important;
        color: #526779 !important;
    }

    /* نموذج تسجيل الدخول */
    div[data-testid="stForm"] {
        background: #FFFFFF !important;
        border: 1px solid #DCE8EF !important;
        border-radius: 22px !important;
        padding: 32px !important;
        box-shadow: 0 14px 38px rgba(16,36,58,.10);
    }

    /* أسماء الحقول */
    div[data-testid="stForm"] label,
    div[data-testid="stForm"] label p {
        font-size: 18px !important;
        font-weight: 700 !important;
        color: #10243A !important;
    }

    /* حقول الإدخال */
    div[data-testid="stForm"] input {
        background: #F9FCFF !important;
        color: #10243A !important;
        -webkit-text-fill-color: #10243A !important;
        border: 1.5px solid #B9CDD9 !important;
        border-radius: 12px !important;
        min-height: 54px !important;
        font-size: 18px !important;
        padding: 12px 15px !important;
    }

    /* التركيز على الحقول */
    div[data-testid="stForm"] input:focus {
        border: 2px solid #087E8B !important;
        box-shadow: 0 0 0 4px rgba(8,126,139,.12) !important;
    }

    /* زر تسجيل الدخول */
    div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button {
        background: linear-gradient(100deg, #087E8B, #096578) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 12px !important;
        min-height: 55px !important;
        font-size: 19px !important;
        font-weight: 800 !important;
        box-shadow: 0 6px 18px rgba(8,126,139,.22);
        transition: all .2s ease;
    }

    div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button:hover {
        background: linear-gradient(100deg, #096578, #10243A) !important;
        transform: translateY(-1px);
    }

    /* اختيار اللغة */
    div[data-testid="stSelectbox"] label p {
        font-size: 16px !important;
        font-weight: 700 !important;
        color: #10243A !important;
    }

    /* تحسين عرض الهاتف */
    @media (max-width: 640px) {
        .block-container {
            padding: 1.5rem 1rem !important;
        }

        .mueen-login-hero {
            padding: 26px 16px;
            border-radius: 18px;
        }

        .mueen-login-hero h1 {
            font-size: 30px !important;
        }

        .mueen-login-hero p {
            font-size: 16px !important;
        }

        div[data-testid="stForm"] {
            padding: 20px !important;
        }
    }
    /* ==========================================
   MUEEN AI - COMPACT LOGIN PAGE
   ========================================== */

@media (min-width: 641px) {

    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }

    .mueen-login-hero {
        padding: 20px 30px !important;
        margin: 4px 0 12px !important;
    }

    .mueen-login-hero .icon {
        font-size: 34px !important;
        margin-bottom: 4px !important;
    }

    .mueen-login-hero h1 {
        font-size: 38px !important;
        line-height: 1.2 !important;
    }

    .mueen-login-hero p {
        font-size: 17px !important;
        margin-top: 4px !important;
    }

    .stApp h3 {
        font-size: 24px !important;
        margin-top: 4px !important;
        margin-bottom: 4px !important;
    }

    div[data-testid="stForm"] {
        padding: 20px !important;
    }

    div[data-testid="stForm"] input {
        min-height: 42px !important;
        height: 42px !important;
        padding: 8px 12px !important;
    }

    div[data-testid="stForm"] [data-testid="stFormSubmitButton"] button {
        min-height: 44px !important;
        font-size: 17px !important;
    }
}
    </style>
    """, unsafe_allow_html=True)

    # شاشة دخول مختصرة بهوية مُعين
        # شاشة دخول احترافية بهوية مُعين
    st.markdown(
        f"""
        <div class="mueen-login-hero" dir="{'rtl' if is_arabic else 'ltr'}">
            <div class="icon">🎓</div>
            <h1>مُعين | MUEEN AI</h1>
            <p>{
                "منصة الذكاء الاصطناعي لتحسين نواتج التعلم"
                if is_arabic
                else "AI-Powered Learning Improvement Platform"
            }</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader(
        "🔐 تسجيل الدخول" if is_arabic else "🔐 Sign In"
    )
    st.caption(
        "سجّل الدخول بحسابك المعتمد للوصول إلى المنصة."
        if is_arabic
        else "Sign in with your authorized account to access the platform."
    )

    auth_client = get_auth_client()

    if auth_client is None:
        st.error(
            "تعذر إعداد Supabase. تحقق من إعدادات الاتصال في Streamlit Secrets."
            if is_arabic
            else "Supabase could not be initialized. Check your Streamlit Secrets."
        )
        st.stop()

    with st.form("mueen_login_form"):
        email = st.text_input(
            "البريد الإلكتروني" if is_arabic else "Email address"
        )
        password = st.text_input(
            "كلمة المرور" if is_arabic else "Password",
            type="password"
        )
        submitted = st.form_submit_button(
            "تسجيل الدخول" if is_arabic else "Sign In",
            use_container_width=True
        )

    if submitted:
        if not email.strip() or not password:
            st.warning(
                "يرجى إدخال البريد الإلكتروني وكلمة المرور."
                if is_arabic
                else "Please enter your email address and password."
            )
        else:
            try:
                result = auth_client.auth.sign_in_with_password({
                    "email": email.strip(),
                    "password": password,
                })

                if result.session:
                    st.session_state["mueen_access_token"] = (
                        result.session.access_token
                    )
                    st.session_state["mueen_refresh_token"] = (
                        result.session.refresh_token
                    )
                    st.rerun()
                else:
                    st.error(
                        "لم يتم إنشاء جلسة تسجيل دخول."
                        if is_arabic
                        else "A sign-in session could not be created."
                    )

            except Exception:
                st.error(
                    "تعذر تسجيل الدخول. تحقق من بيانات الحساب وحالة الحساب."
                    if is_arabic
                    else "Sign-in failed. Check your credentials and account status."
                )

    st.markdown("---")
    st.caption(
        "منصة مُعين للتعلم الذكي | نسخة تجريبية للمعلمين"
        if is_arabic
        else "MUEEN AI Learning Platform | Teacher Trial Version"
    )

    st.stop()

# تحقق من الجلسة قبل عرض أي بيانات
session_client = get_supabase()
if session_client is None:
    clear_login()
    st.warning("انتهت جلسة الدخول أو تعذر التحقق منها. سجّل الدخول مجددًا.")
    st.stop()

try:
    current_user_id = get_current_user_id(session_client)
    user_schools = get_user_schools(session_client, current_user_id)
except Exception:
    st.error("تعذر تحميل المدارس المرتبطة بحسابك. تحقق من سياسات RLS واتصال Supabase.")
    st.stop()

if not user_schools:
    st.error("لا توجد مدرسة مرتبطة بحسابك بعضوية نشطة. اطلب من مسؤول النظام إضافتك إلى المدرسة.")
    if st.button("تسجيل الخروج"):
        try:
            session_client.auth.sign_out()
        except Exception:
            pass
        clear_login()
        st.rerun()
    st.stop()

saved_school_id = st.session_state.get("mueen_school_id")
valid_school_ids = [school["id"] for school in user_schools]
if saved_school_id not in valid_school_ids:
    saved_school_id = user_schools[0]["id"]
# MUEEN AI V3 — رأس مختصر مع إبقاء اختيار المدرسة والصلاحيات
st.markdown("""
<style>
.block-container {padding-top: 4.25rem !important; padding-bottom: 1rem !important;}
/* اترك مساحة أسفل شريط Streamlit العلوي حتى لا يختفي عنوان مُعين */
div[data-testid="stVerticalBlock"] {gap: .65rem;}
.mueen-v3-head {scroll-margin-top: 5rem;}
.mueen-v3-head {
    background: linear-gradient(110deg,#10243A,#087E8B);
    color: white; border-radius: 14px; padding: 13px 20px;
    border-bottom: 3px solid #D9A441;
}
.mueen-v3-head strong {font-size: 24px;}
.mueen-v3-head small {color: #E2F4F5;}
</style>
<div class="mueen-v3-head">
<strong>🎓 مُعين | MUEEN AI</strong><br>
<small>منصة دعم التعلم الذكي · مساحة العمل التعليمية</small>
</div>
""", unsafe_allow_html=True)

school_col, logout_col = st.columns([5, 1], vertical_alignment="bottom")
with school_col:
    selected_school = st.selectbox(
        "🏫 المدرسة النشطة",
        options=user_schools,
        index=next(i for i, school in enumerate(user_schools) if school["id"] == saved_school_id),
        format_func=lambda school: school["name"],
        key="mueen_school_selector",
    )
with logout_col:
    if st.button("🚪 خروج", key="mueen_logout", use_container_width=True):
        try:
            session_client.auth.sign_out()
        except Exception:
            pass
        clear_login()
        st.rerun()
st.session_state["mueen_school_id"] = selected_school["id"]
st.session_state["mueen_school_role"] = selected_school["role"]
# MUEEN AI — تنسيق مساحة العمل فقط، بعد نجاح تسجيل الدخول
st.markdown("""
<style>
/* عرض مناسب لشاشات العرض واللجان */
section.main .block-container,
[data-testid="stMainBlockContainer"] {
    max-width: 1480px !important;
    width: 100% !important;
    padding-left: clamp(1rem, 3vw, 3rem) !important;
    padding-right: clamp(1rem, 3vw, 3rem) !important;
    padding-top: 3.5rem !important;
}
/* مقروئية عامة للواجهة الداخلية */
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p,
[data-testid="stMain"] [data-testid="stWidgetLabel"] p {
    font-size: 16px !important;
    line-height: 1.75 !important;
}
[data-testid="stMain"] h1 {font-size: clamp(28px, 2.3vw, 38px) !important;}
[data-testid="stMain"] h2 {font-size: clamp(24px, 2vw, 31px) !important;}
[data-testid="stMain"] h3 {font-size: clamp(20px, 1.6vw, 26px) !important;}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    font-size: 15px !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] {min-width: 275px;}
/* تحسين بطاقات القياس بدون المساس بالبيانات */
[data-testid="stMetric"] {
    background: #fff;
    border: 1px solid #DFE8EF;
    border-radius: 16px;
    padding: 16px 18px;
    box-shadow: 0 5px 16px rgba(16,36,58,.05);
}
/* أزرار الانتقال لا تختصر العناوين */
[class*="st-key-mueen_quick_"] button {
    min-height: 56px !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    white-space: normal !important;
    overflow-wrap: anywhere !important;
    line-height: 1.4 !important;
    padding: 9px 12px !important;
}
@media (max-width: 800px) {
    [data-testid="stMainBlockContainer"] {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.caption(
    "🔒 بيانات المدرسة النشطة فقط · استخدم رموزًا مستعارة للطلاب "
    "وراجع نتائج الذكاء الاصطناعي قبل تطبيقها."
)

# MUEEN AI V5 — أزرار تنقل حقيقية (لا تعتمد على تنسيق التبويبات)
from contextlib import contextmanager

@contextmanager
def mueen_page(page_number):
    """إبقاء الحسابات المشتركة دون تغيير، مع إخفاء محتوى الصفحات الأخرى."""
    if st.session_state.get("mueen_active_page", 0) == page_number:
        with st.container():
            yield
    else:
        hidden_area = st.empty()
        try:
            with hidden_area.container():
                yield
        finally:
            hidden_area.empty()

st.markdown("""
<style>
.mueen-v5-title {
 background:linear-gradient(110deg,#10243A,#087E8B);
 color:white;border-radius:14px;padding:13px 20px;
 border-bottom:4px solid #D9A441;margin:0 0 10px;
}
.mueen-v5-title h2{color:white;margin:0;font-size:23px}
.mueen-v5-title p{color:#E7F4F5;margin:3px 0 0;font-size:14px}
/* الأزرار الفعلية في صفوف التنقل فقط */
div[data-testid="stHorizontalBlock"] .st-key-mueen_nav_0 button,
div[data-testid="stHorizontalBlock"] .st-key-mueen_nav_1 button,
div[data-testid="stHorizontalBlock"] .st-key-mueen_nav_2 button,
div[data-testid="stHorizontalBlock"] .st-key-mueen_nav_3 button,
div[data-testid="stHorizontalBlock"] .st-key-mueen_nav_4 button,
div[data-testid="stHorizontalBlock"] .st-key-mueen_nav_5 button,
div[data-testid="stHorizontalBlock"] .st-key-mueen_nav_6 button {
 min-height:74px!important;white-space:normal!important;
 border-radius:14px!important;font-size:16px!important;
 font-weight:800!important;color:white!important;
 box-shadow:0 4px 12px rgba(16,36,58,.12)!important;
}
.st-key-mueen_nav_0 button {background:#10243A!important}
.st-key-mueen_nav_1 button {background:#087E8B!important}
.st-key-mueen_nav_2 button {background:#2463A0!important}
.st-key-mueen_nav_3 button {background:#7553A6!important}
.st-key-mueen_nav_4 button {background:#A66A27!important}
.st-key-mueen_nav_5 button {background:#20806A!important}
.st-key-mueen_nav_6 button {background:#B45366!important}
.st-key-mueen_nav_0 button:hover,.st-key-mueen_nav_1 button:hover,
.st-key-mueen_nav_2 button:hover,.st-key-mueen_nav_3 button:hover,
.st-key-mueen_nav_4 button:hover,.st-key-mueen_nav_5 button:hover,
.st-key-mueen_nav_6 button:hover {filter:brightness(1.15);transform:translateY(-2px)}
</style>
""", unsafe_allow_html=True)

st.session_state.setdefault("mueen_active_page", 0)
nav_items = [
    ("🏠 الرئيسية", 0), ("📊 لوحة القيادة", 1),
    ("📈 التحسن والمهارات", 2), ("🧠 التحليل الذكي", 3),
    ("📄 التقرير التنفيذي", 4), ("📚 الخطط والاختبارات", 5),
    ("🏫 إدارة المدرسة", 6),
]
# V6: البطاقات الكبيرة للرئيسية فقط، والتنقل المختصر للصفحات الداخلية.
active_page = st.session_state["mueen_active_page"]
if active_page == 0:
    st.markdown("""<div class="mueen-v5-title"><h2>✨ مساحة عمل مُعين</h2>
    <p>اختر القسم من البطاقات الملونة للانتقال مباشرة إلى أدواته.</p></div>""",
    unsafe_allow_html=True)
    for row_items in (nav_items[:3], nav_items[3:6], nav_items[6:]):
        cols = st.columns(3)
        for col, (label, number) in zip(cols, row_items):
            with col:
                if st.button(label, key=f"mueen_nav_{number}", use_container_width=True):
                    st.session_state["mueen_active_page"] = number
                    st.rerun()
    st.caption("🏠 الصفحة الرئيسية · اختر بطاقة للانتقال إلى القسم المطلوب")
else:
    st.markdown("""
    <style>
    /* أزرار التنقل المختصرة، دون تغيير ألوان البطاقات الرئيسية */
    [class*="st-key-mueen_quick_"] button {
        min-height: 56px !important;
        padding: 9px 12px !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 9px !important;
        background: #FFFFFF !important;
        color: #10243A !important;
        white-space: normal !important;
    }
    [class*="st-key-mueen_quick_"] button[kind="primary"] {
        background: #087E8B !important;
        border-color: #087E8B !important;
        color: white !important;
    }
    [class*="st-key-mueen_quick_"] button:hover {
        border-color: #087E8B !important;
        color: #087E8B !important;
        background: #EDF8F8 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    # صفان بأسماء كاملة بدل سبعة أزرار ضيقة
    for nav_row in (nav_items[:4], nav_items[4:]):
        cols = st.columns(len(nav_row), gap="small")
        for col, (label, number) in zip(cols, nav_row):
            with col:
                if st.button(
                    label,
                    key=f"mueen_quick_{number}",
                    use_container_width=True,
                    type="primary" if number == active_page else "secondary",
                ):
                    st.session_state["mueen_active_page"] = number
                    st.rerun()
    st.caption("القسم الحالي: " + nav_items[active_page][0])

with mueen_page(0):
    st.info("مرحبًا بك في مُعين. اختر إحدى البطاقات الملونة أعلاه لفتح القسم المطلوب.")

with mueen_page(6):
    st.markdown("### 🧪 اختبار التكامل الشامل — V5.1")
    st.caption("فحص قراءة آمن على المدرسة المختارة؛ لا يُنشئ ولا يحذف أي سجل، ولا يرسل بيانات الطلاب إلى الذكاء الاصطناعي.")
    if st.button("🧪 تشغيل فحص التكامل الشامل", key="mueen_v51_run_audit", use_container_width=True):
        with st.spinner("فحص الصلاحيات والقراءة والحسابات دون تعديل البيانات..."):
            st.session_state["mueen_v51_audit"] = {
                "school_id": get_selected_school_id(),
                "rows": mueen_v51_integration_audit(),
            }
    report = st.session_state.get("mueen_v51_audit", {})
    if report.get("school_id") == get_selected_school_id() and report.get("rows"):
        audit_df = pd.DataFrame(report["rows"])
        st.dataframe(audit_df, hide_index=True, use_container_width=True)
        successes = int((audit_df["النتيجة"] == "نجاح").sum())
        st.info(f"نجح {successes} من أصل {len(audit_df)} فحصًا. الفحوص غير المنفذة ليست إخفاقًا مثبتًا، ولا تُعد نجاحًا.")
        st.download_button("📥 تنزيل تقرير الفحص CSV",
            audit_df.to_csv(index=False).encode("utf-8-sig"),
            "MUEEN_V5_1_integration_audit.csv", "text/csv",
            key="mueen_v51_audit_download")
        st.warning("هذا الفحص لا يثبت نجاح INSERT أو DELETE أو عزل RLS بين حسابين. لا تستخدم نتائج الاختبار دليلًا على نجاح الحفظ الفعلي.")

with mueen_page(6):

    st.markdown("### 🔐 V5.2 — اختبار الحفظ والاسترجاع الفعلي")
    st.caption("يُنشئ خطة ومتابعة تقنيتين دون ربطهما بأي طالب. متاح فقط داخل مدرسة اختبار يبدأ اسمها بـ MUEEN_TEST_.")
    st.warning("لا توجد سياسة DELETE للجداول حاليًا؛ ستبقى سجلات الاختبار في مدرسة الاختبار حتى تنظيفها إداريًا. لا تشغّل هذا الاختبار على مدرسة فعلية.")
    consent = st.checkbox("أؤكد أنني اخترت مدرسة اختبار مستقلة وأوافق على إبقاء السجلات التجريبية مؤقتًا", key="v52_consent")
    if st.button("🧪 اختبار الحفظ والاسترجاع الحقيقي", disabled=not consent, key="v52_write_test"):
        with st.spinner("جارٍ اختبار الكتابة والاسترجاع..."):
            st.session_state["v52_write_report"] = {"school": get_selected_school_id(), "rows": mueen_v52_write_probe()}
    report52 = st.session_state.get("v52_write_report", {})
    if report52.get("school") == get_selected_school_id() and report52.get("rows"):
        df52 = pd.DataFrame(report52["rows"])
        st.dataframe(df52, use_container_width=True, hide_index=True)
        st.download_button("تنزيل تقرير V5.2", df52.to_csv(index=False).encode("utf-8-sig"),
                           "MUEEN_V5_2_write_report.csv", "text/csv", key="v52_download")
    st.markdown("### 🛡️ اختبار عزل المدارس")
    st.info("اختبار عزل مدرستين لا يُعد مكتملًا دون حساب ثانٍ لا يملك عضوية في المدرسة المستهدفة. لا يثبت هذا الزر العزل عبر حساب واحد.")

    # =========================================================
    # إدارة الهيكل الأكاديمي - MUEEN AI
    # =========================================================
    st.markdown("## 🏫 إدارة الهيكل الأكاديمي")

    academic_role = st.session_state.get("mueen_school_role", "")
    academic_school_id = st.session_state.get("mueen_school_id")
    st.caption(f"فحص المدرسة المحددة: {academic_school_id}")
    academic_can_manage = academic_role in ("principal", "coordinator")

    with st.expander("فتح إدارة الصفوف والشعب والمواد", expanded=False):
        if not academic_can_manage:
            st.info("هذه الإدارة متاحة لمدير المدرسة والمنسق فقط.")
        else:
            academic_client = get_supabase()

            if academic_client is None:
                st.error("تعذر الاتصال بقاعدة البيانات. سجّل الدخول مجددًا.")
            else:
                academic_user_id = get_current_user_id(academic_client)

                academic_tabs = st.tabs([
                    "إضافة شعبة",
                    "إضافة مادة",
                    "ربط المواد بالشعب",
                    "عرض الهيكل"
                ])

                # -------------------------------------------------
                # 1) إضافة شعبة
                # -------------------------------------------------
                with academic_tabs[0]:
                    st.markdown("### إضافة صف وشعبة")

                    with st.form("mueen_add_academic_section"):
                        section_grade = st.selectbox(
                            "الصف",
                            options=[5, 6, 7, 8, 9, 10, 11, 12],
                            format_func=lambda x: f"الصف {x}"
                        )

                        if section_grade <= 8:
                            section_track = "none"
                            st.caption("الحلقة الثانية — لا يوجد مسار.")
                        else:
                            section_track = st.selectbox(
                                "المسار",
                                options=["general", "advanced"],
                                format_func=lambda x: (
                                    "عام" if x == "general" else "متقدم"
                                )
                            )

                        section_name = st.text_input(
                            "اسم الشعبة",
                            placeholder="مثال: A أو 9-1"
                        )

                        section_year = st.selectbox(
                            "السنة الدراسية",
                            options=["2026-2027", "2027-2028"]
                        )

                        section_submit = st.form_submit_button(
                            "حفظ الشعبة",
                            use_container_width=True
                        )

                    if section_submit:
                        if not section_name.strip():
                            st.error("أدخل اسم الشعبة أولًا.")
                        else:
                            try:
                                section_payload = {
                                    "school_id": academic_school_id,
                                    "grade_level": section_grade,
                                    "track": section_track,
                                    "section_name": section_name.strip(),
                                    "academic_year": section_year,
                                    "created_by": academic_user_id,
                                }

                                academic_client.table(
                                    "academic_sections"
                                ).insert(section_payload).execute()

                                st.success("تم حفظ الشعبة بنجاح.")
                                st.rerun()

                            except Exception as e:
                                st.error("تعذر حفظ الشعبة.")
                                st.caption(str(e)[:500])

                # -------------------------------------------------
                # 2) إضافة مادة
                # -------------------------------------------------
            
                with academic_tabs[1]:
                    st.markdown("### إضافة مادة دراسية")

                    with st.form("mueen_add_academic_subject"):
                        subject_grade = st.selectbox(
                            "الصف المرتبط بالمادة",
                            options=[5, 6, 7, 8, 9, 10, 11, 12],
                            format_func=lambda x: f"الصف {x}",
                            key="academic_subject_grade"
                        )

                        if subject_grade <= 8:
                            subject_track = "none"
                            st.caption("الحلقة الثانية — لا يوجد مسار.")
                        else:
                            subject_track = st.selectbox(
                                "مسار المادة",
                                options=["general", "advanced"],
                                format_func=lambda x: (
                                    "عام" if x == "general" else "متقدم"
                                ),
                                key="academic_subject_track"
                            )

                        subject_name = st.text_input(
                            "اسم المادة",
                            placeholder="مثال: الرياضيات",
                            key="academic_subject_name"
                        )

                        subject_year = st.selectbox(
                            "السنة الدراسية للمادة",
                            options=["2026-2027", "2027-2028"],
                            key="academic_subject_year"
                        )

                        subject_submit = st.form_submit_button(
                            "حفظ المادة",
                            use_container_width=True
                        )

                    if subject_submit:
                        if not subject_name.strip():
                            st.error("أدخل اسم المادة أولًا.")
                        else:
                            try:
                                existing_subject = (
                                    academic_client.table("academic_subjects")
                                    .select("id")
                                    .eq("school_id", academic_school_id)
                                    .eq("grade_level", subject_grade)
                                    .eq("track", subject_track)
                                    .eq("subject_name", subject_name.strip())
                                    .eq("academic_year", subject_year)
                                    .execute()
                                )

                                if existing_subject.data:
                                    st.warning(
                                        "هذه المادة مسجلة بالفعل لهذا الصف والمسار والسنة. "
                                        "يمكنك استخدامها من تبويب ربط المواد بالشعب."
                                    )
                                else:
                                    subject_payload = {
                                        "school_id": academic_school_id,
                                        "grade_level": subject_grade,
                                        "track": subject_track,
                                        "subject_name": subject_name.strip(),
                                        "academic_year": subject_year,
                                        "created_by": academic_user_id,
                                    }

                                    academic_client.table(
                                        "academic_subjects"
                                    ).insert(subject_payload).execute()

                                    st.success("تم حفظ المادة بنجاح.")
                                    st.rerun()

                            except Exception as e:
                                st.error("تعذر حفظ المادة.")
                                st.caption(str(e)[:500])

                # -------------------------------------------------
                # 3) ربط مادة بشعبة
                # -------------------------------------------------
                with academic_tabs[2]:
                    st.markdown("### ربط المواد بالشعب")

                    try:
                        sections_response = (
                            academic_client.table("academic_sections")
                            .select(
                                "id,grade_level,track,section_name,academic_year"
                            )
                            .eq("school_id", academic_school_id)
                            .order("grade_level")
                            .execute()
                        )

                        subjects_response = (
                            academic_client.table("academic_subjects")
                            .select(
                                "id,grade_level,track,subject_name,academic_year"
                            )
                            .eq("school_id", academic_school_id)
                            .order("grade_level")
                            .execute()
                        )

                        all_sections = sections_response.data or []
                        all_subjects = subjects_response.data or []
                        st.write("فحص تحميل الشعب:", len(all_sections))
                        st.write("فحص تحميل المواد:", len(all_subjects))

                        if all_sections:
                            st.write("أول شعبة محمّلة:", all_sections[0])

                        if all_subjects:
                            st.write("أول مادة محمّلة:", all_subjects[0])
                        with st.form("mueen_link_section_subject"):
                            chosen_section = st.selectbox(
                                "الشعبة",
                                options=all_sections,
                                format_func=lambda x: (
                                    f"الصف {x['grade_level']} - "
                                    f"{x['section_name']} | "
                                    f"{'عام' if x['track'] == 'general' else 'متقدم' if x['track'] == 'advanced' else 'بدون مسار'} | "
                                    f"{x['academic_year']}"
                                ) if all_sections else "لا توجد شعب محفوظة"
                            )

                            if all_sections:
                                compatible_subjects = [
                                    item for item in all_subjects
                                    if item["grade_level"] == chosen_section["grade_level"]
                                    and item["track"] == chosen_section["track"]
                                    and item["academic_year"] == chosen_section["academic_year"]
                                ]
                            else:
                                compatible_subjects = []

                            chosen_subject = st.selectbox(
                                "المادة",
                                options=compatible_subjects,
                                format_func=lambda x: x["subject_name"],
                                disabled=not compatible_subjects
                            )

                            link_submit = st.form_submit_button(
                                "ربط المادة بالشعبة",
                                use_container_width=True,
                                disabled=not all_sections or not compatible_subjects
                            )

                        if not all_sections:
                            st.info("أضف شعبة أولًا.")
                        elif not compatible_subjects:
                            st.info(
                                "لا توجد مواد مطابقة لهذه الشعبة. "
                                "أضف مادة للصف والمسار والسنة نفسها."
                            )

                    
                        if link_submit and all_sections and compatible_subjects:
                            try:
                                existing_link = (
                                    academic_client.table("section_subjects")
                                    .select("section_id")
                                    .eq("school_id", academic_school_id)
                                    .eq("section_id", chosen_section["id"])
                                    .eq("subject_id", chosen_subject["id"])
                                    .execute()
                                )

                                if existing_link.data:
                                    st.warning(
                                        "هذه المادة مرتبطة بهذه الشعبة بالفعل."
                                    )
                                else:
                                    link_payload = {
                                        "school_id": academic_school_id,
                                        "section_id": chosen_section["id"],
                                        "subject_id": chosen_subject["id"],
                                        "grade_level": chosen_section["grade_level"],
                                        "track": chosen_section["track"],
                                        "created_by": academic_user_id,
                                    }

                                
                                    academic_client.table(
                                        "section_subjects"
                                    ).insert(link_payload).execute()

                                    st.success("تم ربط المادة بالشعبة بنجاح.")
                                    st.rerun()

                            except Exception as e:
                                if getattr(e, "code", None) == "23505":
                                    st.warning(
                                        "هذه المادة مرتبطة بهذه الشعبة بالفعل."
                                    )
                                else:
                                    st.error("تعذر ربط المادة بالشعبة.")
                                    st.caption(str(e)[:500])

                    except Exception as e:
                        st.error("تعذر تحميل بيانات الشعب والمواد.")
                        st.caption(str(e)[:500])



                # -------------------------------------------------
                # 4) عرض الهيكل الأكاديمي
                # -------------------------------------------------
                with academic_tabs[3]:
                    st.markdown("### الشعب المسجلة")
                    try:
                        sections_view = (
                            academic_client.table("academic_sections")
                            .select(
                                "grade_level,track,section_name,academic_year"
                            )
                            .eq("school_id", academic_school_id)
                            .order("grade_level")
                            .execute()
                        )

                        sections_df = pd.DataFrame(sections_view.data or [])

                        if sections_df.empty:
                            st.info("لم تتم إضافة شعب حتى الآن.")
                        else:
                            sections_df["track"] = sections_df["track"].map({
                                "none": "بدون مسار",
                                "general": "عام",
                                "advanced": "متقدم",
                            }).fillna(sections_df["track"])

                            st.dataframe(
                                sections_df.rename(columns={
                                    "grade_level": "الصف",
                                    "track": "المسار",
                                    "section_name": "الشعبة",
                                    "academic_year": "السنة الدراسية",
                                }),
                                use_container_width=True,
                                hide_index=True
                            )

                        st.markdown("### المواد المسجلة")
                        subjects_view = (
                            academic_client.table("academic_subjects")
                            .select(
                                "grade_level,track,subject_name,academic_year"
                            )
                            .eq("school_id", academic_school_id)
                            .order("grade_level")
                            .execute()
                        )

                        subjects_df = pd.DataFrame(subjects_view.data or [])

                        if subjects_df.empty:
                            st.info("لم تتم إضافة مواد حتى الآن.")
                        else:
                            subjects_df["track"] = subjects_df["track"].map({
                                "none": "بدون مسار",
                                "general": "عام",
                                "advanced": "متقدم",
                            }).fillna(subjects_df["track"])

                            st.dataframe(
                                subjects_df.rename(columns={
                                    "grade_level": "الصف",
                                    "track": "المسار",
                                    "subject_name": "المادة",
                                    "academic_year": "السنة الدراسية",
                                }),
                                use_container_width=True,
                                hide_index=True
                            )

                    except Exception as e:
                        st.error("تعذر عرض الهيكل الأكاديمي.")
                        st.caption(str(e)[:500])

with st.sidebar:
    st.header("إعدادات التحليل")
    subject=st.selectbox("المادة",["الحوسبة","الرياضيات","العلوم","اللغة العربية","اللغة الإنجليزية"])
    grade=st.selectbox("الصف",["الخامس","السادس","السابع","الثامن","التاسع"])
    threshold=st.slider("حد الإتقان (%)",50,100,80,5)
    output_language = st.selectbox(
    "لغة المخرجات" if st.session_state.get("mueen_language", "العربية") == "العربية"
    else "Output Language",
    ["العربية", "English"],
    key="mueen_output_language"
)
    model=st.text_input("اسم نموذج API",value="gpt-4.1-mini")
key=get_key()
db_client=get_supabase()
if db_client:
    st.sidebar.success("قاعدة بيانات Supabase متصلة")
else:
    st.sidebar.warning("تعذر الاتصال بقاعدة البيانات عبر جلسة المستخدم. تحقق من SUPABASE_URL وSUPABASE_PUBLISHABLE_KEY.")
if key: st.sidebar.success("ميزات الذكاء الاصطناعي جاهزة")
else: st.sidebar.info("أضف OPENAI_API_KEY إلى Streamlit Secrets لتفعيل الذكاء الاصطناعي.")


with mueen_page(1):
    st.markdown("""
    <div style="
        background: linear-gradient(120deg, #10243A 0%, #17465B 65%, #087E8B 100%);
        padding: 24px 28px;
        border-radius: 16px;
        margin: 8px 0 20px 0;
        color: white;
        border: 1px solid rgba(255,255,255,0.12);
    ">
        <div style="font-size: 13px; color: #D9A441; font-weight: 700;
                    letter-spacing: 1px; margin-bottom: 8px;">
            MUEEN AI | مُعين
        </div>
        <div style="font-size: 27px; font-weight: 800; margin-bottom: 8px;">
            📊 لوحة القيادة التعليمية
        </div>
        <div style="font-size: 15px; color: #E4EDF4;">
            متابعة التحصيل الدراسي، وقياس الإتقان، وتحديد أولويات الدعم التعليمي
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.caption(
        "تعرض هذه اللوحة السجلات المحفوظة في Supabase للمدرسة النشطة فقط، "
        "ولا تخلط بينها وبين البيانات النموذجية غير المحفوظة."
    )

if db_client and st.session_state.get("mueen_active_page") in (1, 2, 3, 4):
    with mueen_page(1):
        refresh_clicked = st.button("🔄 تحديث لوحة المتابعة", use_container_width=True)
    if refresh_clicked:
        st.session_state["refresh_dashboard"] = datetime.now().isoformat()
    try:
        dashboard_df = load_all_history(limit=1000)
        if dashboard_df.empty:
            st.info("لا توجد سجلات محفوظة بعد. احفظ التقييم القبلي أو البعدي أولًا.")
        else:
            dashboard_df["score"] = pd.to_numeric(dashboard_df["score"], errors="coerce")
            dashboard_df["max_score"] = pd.to_numeric(dashboard_df["max_score"], errors="coerce")
            dashboard_df = dashboard_df.dropna(subset=["score", "max_score"])
            dashboard_df = dashboard_df[dashboard_df["max_score"] > 0].copy()
            dashboard_df["mastery_pct"] = (
                dashboard_df["score"] / dashboard_df["max_score"] * 100
            ).round(1)
            dashboard_df["assessment_type"] = dashboard_df["assessment_type"].fillna("").astype(str)
            dashboard_df["skill"] = dashboard_df["skill"].fillna("غير محدد").astype(str)
            dashboard_df["student_code"] = dashboard_df["student_code"].fillna("غير محدد").astype(str)

            # Filters apply only to the already school-scoped data returned by load_all_history.
           

            with mueen_page(1):
                st.markdown("### 🔎 تصفية التقارير")

                # فلتر الفترة الزمنية
                if "created_at" in dashboard_df.columns:
                    dashboard_df["created_at"] = pd.to_datetime(
                        dashboard_df["created_at"], errors="coerce", utc=True
                    )
                    dashboard_df = dashboard_df.dropna(subset=["created_at"])

                    date_options = {
                        "كل الفترات": None,
                        "آخر 7 أيام": 7,
                        "آخر 30 يومًا": 30,
                        "آخر 90 يومًا": 90,
                    }
                    selected_period = st.selectbox(
                        "الفترة الزمنية",
                        list(date_options.keys()),
                        key="dashboard_date_filter",
                    )
                    days = date_options[selected_period]

                    if days is not None:
                        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
                        dashboard_df = dashboard_df[
                            dashboard_df["created_at"] >= cutoff
                        ]
                else:
                    st.warning("لا يتوفر تاريخ إنشاء السجلات؛ تعذرت تصفية التقرير زمنيًا.")

                f1, f2, f3 = st.columns(3)
                with f1:
                    skill_options = ["كل المهارات"] + sorted(dashboard_df["skill"].unique().tolist())
                    selected_skill = st.selectbox("المهارة", skill_options, key="dashboard_skill_filter")
                with f2:
                    type_map = {
                        "كل أنواع التقييم": None,
                        "قبلي": ["baseline", "قبلي"],
                        "بعدي": ["follow_up", "followup", "بعدي"],
                    }
                    selected_type_label = st.selectbox(
                        "نوع التقييم", list(type_map.keys()), key="dashboard_type_filter"
                    )
                with f3:
                    student_options = ["كل الطلاب/المجموعات"] + sorted(dashboard_df["student_code"].unique().tolist())
                    selected_student = st.selectbox(
                        "رمز الطالب/المجموعة", student_options, key="dashboard_student_filter"
                    )
            filtered_df = dashboard_df.copy()
            if selected_skill != "كل المهارات":
                filtered_df = filtered_df[filtered_df["skill"] == selected_skill]
            selected_types = type_map[selected_type_label]
            if selected_types:
                filtered_df = filtered_df[
                    filtered_df["assessment_type"].str.lower().isin([x.lower() for x in selected_types])
                ]
            if selected_student != "كل الطلاب/المجموعات":
                filtered_df = filtered_df[filtered_df["student_code"] == selected_student]

            if filtered_df.empty:
                st.info("لا توجد سجلات تطابق عوامل التصفية المحددة.")
            else:
            
                baseline = filtered_df[
                    filtered_df["assessment_type"].str.lower().isin(["baseline", "قبلي"])
                ]
                followup = filtered_df[
                    filtered_df["assessment_type"].str.lower().isin(["follow_up", "followup", "بعدي"])
                ]

                avg_mastery = float(filtered_df["mastery_pct"].mean())
                students_n = int(filtered_df["student_code"].nunique())
                below_threshold_n = int(
                    (filtered_df["mastery_pct"] < threshold).sum()
                )

                baseline_avg = (
                    float(baseline["mastery_pct"].mean())
                    if not baseline.empty else None
                )
                followup_avg = (
                    float(followup["mastery_pct"].mean())
                    if not followup.empty else None
                )

            
                with mueen_page(1):
                    st.markdown("### 📊 المؤشرات الرئيسية")

                    m1, m2, m3, m4 = st.columns(4)

                    with m1:
                        st.metric(
                            "👥 طلاب/مجموعات",
                            students_n,
                            help="عدد الطلاب أو المجموعات الظاهرة ضمن الفلاتر الحالية."
                        )

                    with m2:
                        st.metric(
                            "📋 السجلات المعروضة",
                            int(len(filtered_df)),
                            help="عدد سجلات التقييم المطابقة للفلاتر الحالية."
                        )

                    with m3:
                        st.metric(
                            "🎯 متوسط جميع السجلات",
                            f"{avg_mastery:.1f}%",
                            help="متوسط الإتقان لجميع السجلات المعروضة."
                        )

                    with m4:
                        st.metric(
                            "⚠️ دون حد الإتقان",
                            below_threshold_n,
                            help="عدد السجلات التي تقل عن حد الإتقان المحدد."
                        )

                    st.markdown("### 📈 مقارنة الإتقان القبلي والبعدي")

                    m5, m6 = st.columns(2)

                    with m5:
                        st.metric(
                            "📝 متوسط الإتقان القبلي",
                            f"{baseline_avg:.1f}%" if baseline_avg is not None else "لا توجد بيانات"
                        )

                    with m6:
                        st.metric(
                            "✅ متوسط الإتقان البعدي",
                            f"{followup_avg:.1f}%" if followup_avg is not None else "لا توجد بيانات"
                        )

                    if baseline_avg is not None and followup_avg is not None:
                        st.caption(
                            "تنبيه: قد يعتمد متوسطا القبلي والبعدي على سجلات مختلفة؛ "
                            "لذلك لا يُعد الفرق بينهما مقياسًا مؤكدًا للتحسن الفردي."
                        )

            with mueen_page(2):
                st.markdown("### 📈 مقارنة التحسن الفعلي بين القبلي والبعدي")


                # نستخدم سجلات المدرسة والفترة المحددتين،
                # مع تجاهل فلتر نوع التقييم حتى تتوفر المرحلتان.
                comparison_source = dashboard_df.copy()

                if selected_skill != "كل المهارات":
                    comparison_source = comparison_source[
                        comparison_source["skill"] == selected_skill
                    ]

                if selected_student != "كل الطلاب/المجموعات":
                    comparison_source = comparison_source[
                        comparison_source["student_code"] == selected_student
                    ]

                comparison_source["type_norm"] = (
                    comparison_source["assessment_type"]
                    .astype(str).str.strip().str.lower()
                )

            
                # استبعاد السجلات غير المرتبطة بشعبة ومادة محددتين
                comparison_source = comparison_source.dropna(
                    subset=["section_id", "subject_id"]
                ).copy()

                baseline_rows = (
                    comparison_source[
                        comparison_source["type_norm"].isin(["baseline", "قبلي"])
                    ]
                    .sort_values("created_at")
                    .drop_duplicates(
                        ["student_code", "skill", "section_id", "subject_id"],
                        keep="last"
                    )
                    [[
                        "student_code", "skill", "section_id",
                        "subject_id", "mastery_pct"
                    ]]
                    .rename(columns={"mastery_pct": "القبلي (%)"})
                )

                followup_rows = (
                    comparison_source[
                        comparison_source["type_norm"].isin(
                            ["follow_up", "followup", "بعدي"]
                        )
                    ]
                    .sort_values("created_at")
                    .drop_duplicates(
                        ["student_code", "skill", "section_id", "subject_id"],
                        keep="last"
                    )
                    [[
                        "student_code", "skill", "section_id",
                        "subject_id", "mastery_pct"
                    ]]
                    .rename(columns={"mastery_pct": "البعدي (%)"})
                )

                comparison = baseline_rows.merge(
                    followup_rows,
                    on=["student_code", "skill", "section_id", "subject_id"],
                    how="inner"
                )

                if comparison.empty:
                    st.info(
                        "لا توجد بيانات قبلية وبعدية للطالب والمهارة نفسيهما "
                        "ضمن الفترة المحددة. احفظ التقييمين أولًا."
                    )
                else:
                    comparison["التغير (نقطة مئوية)"] = (
                        comparison["البعدي (%)"] - comparison["القبلي (%)"]
                    ).round(1)

                    comparison["حالة التحسن"] = comparison[
                        "التغير (نقطة مئوية)"
                    ].apply(
                        lambda x: (
                            "تحسن" if x > 0
                            else "دون تغير" if x == 0
                            else "تراجع"
                        )
                    )

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("عدد المقارنات", len(comparison))
                    c2.metric(
                        "متوسط التغير",
                        f"{comparison['التغير (نقطة مئوية)'].mean():+.1f}"
                        " نقطة مئوية"
                    )
                    c3.metric(
                        "حالات التحسن",
                        int((comparison["التغير (نقطة مئوية)"] > 0).sum())
                    )
                    c4.metric(
                        "حالات التراجع",
                        int((comparison["التغير (نقطة مئوية)"] < 0).sum())
                    )

                    st.markdown("#### 📊 توزيع حالات التحسن")

                    status_counts = (
                        comparison["حالة التحسن"]
                        .value_counts()
                        .reindex(
                            ["تحسن", "دون تغير", "تراجع"],
                            fill_value=0
                        )
                    )

                    chart_df = status_counts.rename_axis(
                        "حالة التحسن"
                    ).reset_index(name="عدد الحالات")

                    st.bar_chart(
                        chart_df,
                        x="حالة التحسن",
                        y="عدد الحالات",
                        use_container_width=True
                    )

                    display_comparison = comparison.rename(
                        columns={
                            "student_code": "رمز الطالب/المجموعة",
                            "skill": "المهارة"
                        }
                    )

                    st.dataframe(
                        display_comparison,
                        use_container_width=True,
                        hide_index=True
                    )

                    st.download_button(
                        "📥 تنزيل تقرير مقارنة التحسن CSV",
                        display_comparison.to_csv(
                            index=False
                        ).encode("utf-8-sig"),
                        "mueen_improvement_comparison.csv",
                        "text/csv",
                        key="download_improvement_comparison"
                    )

                    st.markdown("### 🎯 مؤشرات أثر التدخل العلاجي")

                    total_comparisons = len(comparison)
                    improved_n = int(
                        (comparison["التغير (نقطة مئوية)"] > 0).sum()
                    )
                    unchanged_n = int(
                        (comparison["التغير (نقطة مئوية)"] == 0).sum()
                    )
                    declined_n = int(
                        (comparison["التغير (نقطة مئوية)"] < 0).sum()
                    )

                    improvement_rate = (
                        improved_n / total_comparisons * 100
                        if total_comparisons > 0 else 0.0
                    )

                    avg_change = (
                        float(comparison["التغير (نقطة مئوية)"].mean())
                        if total_comparisons > 0 else 0.0
                    )

                    impact1, impact2, impact3 = st.columns(3)
                    impact1.metric(
                        "نسبة حالات التحسن",
                        f"{improvement_rate:.1f}%"
                    )
                    impact2.metric(
                        "متوسط التغير",
                        f"{avg_change:+.1f} نقطة مئوية"
                    )
                    impact3.metric(
                        "إجمالي المقارنات",
                        total_comparisons
                    )

                    impact4, impact5, impact6 = st.columns(3)
                    impact4.metric("حالات التحسن", improved_n)
                    impact5.metric("دون تغير", unchanged_n)
                    impact6.metric("حالات التراجع", declined_n)

                    st.caption(
                        "تعكس هذه المؤشرات المقارنات المتاحة فقط، "
                        "ولا تثبت وحدها أن التحسن ناتج عن التدخل العلاجي."
                    )

                    st.markdown("### 🏫 تقرير التحسن حسب الشعبة والمادة")

                    try:
                        report_client = get_supabase()
                        report_school_id = get_selected_school_id()

                        if report_client is None or not report_school_id:
                            st.warning("تعذر تحميل أسماء الشعب والمواد.")
                        elif comparison.empty:
                            st.info("لا توجد مقارنات متطابقة لإنشاء التقرير.")
                        else:
                            sections_response = (
                                report_client.table("academic_sections")
                                .select("id,grade_level,section_name,academic_year")
                                .eq("school_id", report_school_id)
                                .execute()
                            )

                            subjects_response = (
                                report_client.table("academic_subjects")
                                .select("id,subject_name,academic_year")
                                .eq("school_id", report_school_id)
                                .execute()
                            )

                            sections_df = pd.DataFrame(sections_response.data or [])
                            subjects_df = pd.DataFrame(subjects_response.data or [])

                            if sections_df.empty or subjects_df.empty:
                                st.warning("لا توجد بيانات كافية لأسماء الشعب والمواد.")
                            else:
                                sections_df = sections_df.rename(
                                    columns={
                                        "id": "section_id",
                                        "grade_level": "الصف",
                                        "section_name": "الشعبة",
                                        "academic_year": "السنة الدراسية",
                                    }
                                )

                                subjects_df = subjects_df.rename(
                                    columns={
                                        "id": "subject_id",
                                        "subject_name": "المادة",
                                        "academic_year": "السنة الدراسية",
                                    }
                                )

                                report_df = comparison.merge(
                                    sections_df[
                                        ["section_id", "الصف", "الشعبة", "السنة الدراسية"]
                                    ],
                                    on="section_id",
                                    how="left"
                                ).merge(
                                    subjects_df[
                                        ["subject_id", "المادة"]
                                    ],
                                    on="subject_id",
                                    how="left"
                                )

                                report_df = report_df.dropna(
                                    subset=["الصف", "الشعبة", "المادة"]
                                )

                                if report_df.empty:
                                    st.info("لم يتم العثور على أسماء مطابقة للشعب والمواد.")
                                else:
                                    report_summary = (
                                        report_df.groupby(
                                            ["الصف", "الشعبة", "المادة"],
                                            dropna=False
                                        )
                                        .agg(
                                            عدد_المقارنات=("التغير (نقطة مئوية)", "count"),
                                            متوسط_القبلي=("القبلي (%)", "mean"),
                                            متوسط_البعدي=("البعدي (%)", "mean"),
                                            متوسط_التغير=("التغير (نقطة مئوية)", "mean"),
                                            حالات_التحسن=(
                                                "التغير (نقطة مئوية)",
                                                lambda values: int((values > 0).sum())
                                            ),
                                            حالات_التراجع=(
                                                "التغير (نقطة مئوية)",
                                                lambda values: int((values < 0).sum())
                                            ),
                                        )
                                        .reset_index()
                                    )

                                    for column in [
                                        "متوسط_القبلي",
                                        "متوسط_البعدي",
                                        "متوسط_التغير",
                                    ]:
                                        report_summary[column] = report_summary[column].round(1)

                                    st.dataframe(
                                        report_summary,
                                        use_container_width=True,
                                        hide_index=True
                                    )

                                    st.download_button(
                                        "📥 تنزيل تقرير التحسن حسب الشعبة والمادة",
                                        report_summary.to_csv(
                                            index=False
                                        ).encode("utf-8-sig"),
                                        "mueen_section_subject_improvement.csv",
                                        "text/csv",
                                        key="download_section_subject_improvement"
                                    )

                    except Exception as e:
                            st.error("تعذر إنشاء تقرير التحسن حسب الشعبة والمادة.")
                            st.caption(str(e)[:500])


            with mueen_page(2):
                st.markdown("### 📊 مؤشرات الإتقان حسب المهارة")
                skill_summary = (
                    filtered_df.groupby(["skill", "assessment_type"], as_index=False)
                    .agg(متوسط_الإتقان=("mastery_pct", "mean"), عدد_السجلات=("student_code", "count"))
                )
                skill_summary["متوسط_الإتقان"] = skill_summary["متوسط_الإتقان"].round(1)
                st.bar_chart(
                    filtered_df.groupby("skill")["mastery_pct"].mean().sort_values(ascending=False)
                )
                st.dataframe(
                    skill_summary.rename(columns={
                        "skill": "المهارة",
                        "assessment_type": "نوع التقييم",
                        "متوسط_الإتقان": "متوسط الإتقان (%)",
                        "عدد_السجلات": "عدد السجلات",
                    }),
                    use_container_width=True,
                    hide_index=True,
                )

            with mueen_page(3):
                st.divider()
                st.markdown("## 🧠 لوحة التحليل الذكي للمهارات")

                # 1. تحليل مستوى الإتقان لكل مهارة
                analysis_df = filtered_df.copy()
                analysis_df["mastery_pct"] = pd.to_numeric(
                    analysis_df["mastery_pct"], errors="coerce"
                )
                analysis_df = analysis_df.dropna(
                    subset=["skill", "mastery_pct"]
                )

                if analysis_df.empty:
                    st.info("لا توجد بيانات كافية لتحليل المهارات.")
                else:
                    skill_analysis = (
                        analysis_df.groupby("skill", as_index=False)
                        .agg(
                            متوسط_الإتقان=("mastery_pct", "mean"),
                            عدد_السجلات=("mastery_pct", "count"),
                        )
                    )
                    skill_analysis["متوسط_الإتقان"] = (
                        skill_analysis["متوسط_الإتقان"].round(1)
                    )
                    skill_analysis["الفجوة عن الهدف"] = (
                        float(threshold) - skill_analysis["متوسط_الإتقان"]
                    ).round(1)

                    skill_analysis["حالة الإتقان"] = skill_analysis[
                        "متوسط_الإتقان"
                    ].apply(
                        lambda x: "تحتاج إلى دعم"
                        if x < threshold else "بلغت حد الإتقان"
                    )

                    # 2. المهارات الأقل إتقانًا
                    st.markdown("### 1️⃣ المهارات الأقل إتقانًا")
                    weakest = skill_analysis.sort_values(
                        "متوسط_الإتقان", ascending=True
                    )
                    st.dataframe(
                        weakest.rename(columns={
                            "skill": "المهارة",
                            "متوسط_الإتقان": "متوسط الإتقان (%)",
                            "عدد_السجلات": "عدد السجلات",
                        }),
                        use_container_width=True,
                        hide_index=True,
                    )

                    # 3. المهارات التي تقل عن حد الإتقان
                    st.markdown(
                        f"### 2️⃣ المهارات الأقل من حد الإتقان ({threshold}%)"
                    )
                    below_target = skill_analysis[
                        skill_analysis["متوسط_الإتقان"] < threshold
                    ].copy()

                    
                    # 4. تحليل التحسن حسب المهارة من المقارنات المتطابقة
                    st.markdown("### 3️⃣ المهارات التي تحسنت بعد التدخل")

                    skill_change = pd.DataFrame(
                        columns=[
                            "skill",
                            "متوسط_التغير",
                            "عدد_المقارنات",
                            "نتيجة التدخل",
                        ]
                    )

                    if "comparison" in locals() and not comparison.empty:
                        skill_change = (
                            comparison.groupby("skill", as_index=False)
                            .agg(
                                متوسط_التغير=("التغير (نقطة مئوية)", "mean"),
                                عدد_المقارنات=("التغير (نقطة مئوية)", "count"),
                            )
                        )

                        skill_change["متوسط_التغير"] = (
                            skill_change["متوسط_التغير"].round(1)
                        )

                        skill_change["نتيجة التدخل"] = skill_change[
                            "متوسط_التغير"
                        ].apply(
                            lambda x: "تحسن" if x > 0
                            else "دون تغير" if x == 0
                            else "تراجع"
                        )

                        st.dataframe(
                            skill_change.rename(columns={
                                "skill": "المهارة",
                                "متوسط_التغير": "متوسط التغير (نقطة مئوية)",
                                "عدد_المقارنات": "عدد المقارنات",
                            }),
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.info(
                            "لا توجد مقارنات قبلية وبعدية متطابقة "
                            "لتحديد المهارات التي تحسنت."
                        )


                    # 5. أولويات الخطط العلاجية
                    st.markdown("### 4️⃣ المهارات ذات الأولوية العلاجية")

                    priorities = below_target.copy()
                    if not priorities.empty:
                        priorities["الأولوية"] = priorities[
                            "متوسط_الإتقان"
                        ].apply(
                            lambda x: "عاجلة" if x < threshold - 20
                            else "مرتفعة" if x < threshold - 10
                            else "متوسطة"
                        )

                        priorities["الإجراء المقترح"] = priorities[
                            "الأولوية"
                        ].map({
                            "عاجلة": "إعادة تدريس المهارة وتقديم دعم مكثف",
                            "مرتفعة": "تنفيذ نشاط علاجي موجه ثم إعادة التقييم",
                            "متوسطة": "تدريب إضافي ومتابعة التقدم",
                        })

                        st.dataframe(
                            priorities.rename(columns={
                                "skill": "المهارة",
                                "متوسط_الإتقان": "متوسط الإتقان (%)",
                                "عدد_السجلات": "عدد السجلات",
                            })[
                                [
                                    "المهارة",
                                    "متوسط الإتقان (%)",
                                    "الأولوية",
                                    "الإجراء المقترح",
                                ]
                            ],
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.success(
                            "لا توجد مهارات دون حد الإتقان تحتاج إلى أولوية علاجية "
                            "وفق البيانات والفلاتر الحالية."
                        )

                    # 6. تنزيل تقرير موحد
                    report = skill_analysis.merge(
                        skill_change[
                            ["skill", "متوسط_التغير", "عدد_المقارنات"]
                        ] if "comparison" in locals() and not comparison.empty
                        else pd.DataFrame(columns=[
                            "skill", "متوسط_التغير", "عدد_المقارنات"
                        ]),
                        on="skill",
                        how="left",
                    )

                    st.download_button(
                        "📥 تنزيل تقرير التحليل الذكي للمهارات CSV",
                        report.to_csv(index=False).encode("utf-8-sig"),
                        "mueen_smart_skill_analysis.csv",
                        "text/csv",
                        key="download_smart_skill_analysis",
                    )

                    st.caption(
                        "تعتمد النتائج على السجلات والفلاتر الحالية. "
                        "الأولوية المقترحة مساندة للمعلم وليست قرارًا آليًا نهائيًا."
                    )

                st.markdown("### 🧠 التحليل الذكي للتحصيل الدراسي")
                st.caption("يُرسل إلى نموذج الذكاء الاصطناعي ملخص مجمّع حسب المهارة ونوع التقييم فقط، دون رموز الطلاب أو سجلاتهم الفردية.")
                
                if not skill_summary.empty:
                    st.markdown("#### 📚 ملخص المهارات الحالية")

                    skills_display = skill_summary[
                        ["skill", "متوسط_الإتقان", "عدد_السجلات"]
                    ].copy()

                    skills_display["متوسط_الإتقان"] = (
                        skills_display["متوسط_الإتقان"].round(1)
                    )

                    skills_display = skills_display.rename(
                        columns={
                            "skill": "المهارة",
                            "متوسط_الإتقان": "متوسط الإتقان (%)",
                            "عدد_السجلات": "عدد السجلات",
                        }
                    )

                    st.dataframe(
                        skills_display,
                        use_container_width=True,
                        hide_index=True,
                    )

                    st.bar_chart(
                        skills_display,
                        x="المهارة",
                        y="متوسط الإتقان (%)",
                        use_container_width=True,
                    )
                else:
                    st.info("لا توجد بيانات مهارات كافية لعرض الملخص.")

                if not key:
                    st.info("أضف OPENAI_API_KEY إلى Streamlit Secrets لتفعيل التحليل الذكي.")
                elif st.button("✨ إنشاء تحليل ذكي للمؤشرات الحالية", key="run_achievement_analysis", use_container_width=True):
                    try:
                        aggregate_for_ai = skill_summary[["skill", "assessment_type", "متوسط_الإتقان", "عدد_السجلات"]].copy()
                        aggregate_for_ai["متوسط_الإتقان"] = aggregate_for_ai["متوسط_الإتقان"].round(1)
                        aggregate_json = json.dumps(aggregate_for_ai.to_dict(orient="records"), ensure_ascii=False)
                        with st.spinner("يحلل مُعين المؤشرات المجمعة..."):
                            st.session_state["mueen_achievement_analysis"] = create_achievement_analysis(
                                model, aggregate_json, threshold, output_language
                            )
                        st.session_state["mueen_achievement_analysis_scope"] = {
                            "school_id": get_selected_school_id(),
                            "filters": [selected_period, selected_skill, selected_type_label, selected_student],
                        }
                    except Exception as e:
                        st.error("تعذر إنشاء التحليل الذكي. تحقق من إعدادات API وإتاحة النموذج.")
                        st.caption(str(e)[:500])
                analysis_scope = st.session_state.get("mueen_achievement_analysis_scope", {})
                if st.session_state.get("mueen_achievement_analysis") and analysis_scope.get("school_id") == get_selected_school_id() and analysis_scope.get("filters") == [selected_period, selected_skill, selected_type_label, selected_student]:
                    st.markdown(st.session_state["mueen_achievement_analysis"])
                    st.download_button(
                        "تنزيل التحليل الذكي TXT",
                        st.session_state["mueen_achievement_analysis"],
                        "mueen_achievement_analysis.txt",
                        "text/plain",
                        key="download_achievement_analysis",
                    )
                st.caption("راجع الاستنتاجات والتوصيات قبل تطبيقها؛ التحليل الذكي مساعد للمعلم وليس حكمًا نهائيًا على أداء الطلاب.")

            with mueen_page(2):
                if not baseline.empty and not followup.empty:
                    st.markdown("### 📈 مؤشرات التحسن: التقييم القبلي والبعدي")

                    base_latest = (
                        baseline.sort_values("created_at")
                        .drop_duplicates(["student_code", "skill"], keep="last")
                        [["student_code", "skill", "mastery_pct"]]
                        .rename(columns={"mastery_pct": "القبلي (%)"})
                    )

                    follow_latest = (
                        followup.sort_values("created_at")
                        .drop_duplicates(["student_code", "skill"], keep="last")
                        [["student_code", "skill", "mastery_pct"]]
                        .rename(columns={"mastery_pct": "البعدي (%)"})
                    )

                    comparison = base_latest.merge(
                        follow_latest,
                        on=["student_code", "skill"],
                        how="inner",
                    )

                    if not comparison.empty:
                        comparison["التغير (نقطة مئوية)"] = (
                            comparison["البعدي (%)"] - comparison["القبلي (%)"]
                        ).round(1)

                        comparison["الحالة"] = comparison[
                            "التغير (نقطة مئوية)"
                        ].apply(
                            lambda x: (
                                "متحسن" if x > 0
                                else "متراجع" if x < 0
                                else "ثابت"
                            )
                        )

                        comparison["مستوى البعدي"] = comparison[
                            "البعدي (%)"
                        ].apply(
                            lambda x: (
                                "بلغ حد الإتقان"
                                if x >= threshold
                                else "يحتاج إلى دعم"
                            )
                        )

                        avg_change = float(
                            comparison["التغير (نقطة مئوية)"].mean()
                        )
                        improved_n = int(
                            (comparison["الحالة"] == "متحسن").sum()
                        )
                        unchanged_n = int(
                            (comparison["الحالة"] == "ثابت").sum()
                        )
                        declined_n = int(
                            (comparison["الحالة"] == "متراجع").sum()
                        )
                        achieved_n = int(
                            (comparison["البعدي (%)"] >= threshold).sum()
                        )
                        support_n = int(
                            (comparison["البعدي (%)"] < threshold).sum()
                        )

                        st.caption(
                            "تُحسب المقارنة فقط للحالات التي لديها تقييم قبلي "
                            "وبعدي للطالب/المجموعة نفسها والمهارة نفسها."
                        )

                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("متوسط التحسن", f"{avg_change:+.1f} نقطة")
                        c2.metric("حالات متحسنة", improved_n)
                        c3.metric("حالات ثابتة", unchanged_n)
                        c4.metric("حالات متراجعة", declined_n)

                        c5, c6 = st.columns(2)
                        c5.metric("بلغت حد الإتقان", achieved_n)
                        c6.metric("تحتاج إلى دعم", support_n)

                        st.dataframe(
                            comparison.rename(
                                columns={
                                    "student_code": "رمز الطالب/المجموعة",
                                    "skill": "المهارة",
                                }
                            ),
                            use_container_width=True,
                            hide_index=True,
                        )

                        needs_support = comparison[
                            comparison["البعدي (%)"] < threshold
                        ]
                        if not needs_support.empty:
                            st.markdown("#### 🎯 حالات تحتاج إلى دعم إضافي")
                            st.dataframe(
                                needs_support[
                                    [
                                        "student_code",
                                        "skill",
                                        "القبلي (%)",
                                        "البعدي (%)",
                                        "التغير (نقطة مئوية)",
                                    ]
                                ].rename(
                                    columns={
                                        "student_code": "رمز الطالب/المجموعة",
                                        "skill": "المهارة",
                                    }
                                ),
                                use_container_width=True,
                                hide_index=True,
                            )
                    else:
                        st.info(
                            "لا توجد حالات لها تقييم قبلي وبعدي "
                            "للطالب/المجموعة نفسها والمهارة نفسها ضمن الفلاتر الحالية."
                        )
                else:
                    st.info(
                        "تحتاج مؤشرات التحسن إلى وجود تقييم قبلي وتقييم بعدي "
                        "ضمن الفلاتر الحالية."
                    )

            with mueen_page(4):
                # التقرير التنفيذي الذكي لمدير المدرسة
                st.markdown("## 🏫 التقرير التنفيذي الذكي لمدير المدرسة")
                st.caption(
                    "تقرير موجز لدعم القرارات التعليمية، "
                    "اعتمادًا على البيانات المعروضة والفلاتر الحالية."
                )

                if filtered_df.empty:
                    st.info("لا توجد بيانات كافية لإنشاء التقرير التنفيذي.")
                else:
                    report_df = filtered_df.copy()
                    report_df["mastery_pct"] = pd.to_numeric(
                        report_df["mastery_pct"], errors="coerce"
                    )
                    report_df = report_df.dropna(
                        subset=["skill", "mastery_pct"]
                    )

                    if report_df.empty:
                        st.info("لا توجد نتائج إتقان صالحة لإنشاء التقرير.")
                    else:
                        report_avg = float(report_df["mastery_pct"].mean())
                        report_skills = (
                            report_df.groupby("skill", as_index=False)
                            .agg(
                                متوسط_الإتقان=("mastery_pct", "mean"),
                                عدد_السجلات=("mastery_pct", "count"),
                            )
                        )
                        report_skills["متوسط_الإتقان"] = (
                            report_skills["متوسط_الإتقان"].round(1)
                        )
                        report_weak = report_skills[
                            report_skills["متوسط_الإتقان"] < threshold
                        ].sort_values("متوسط_الإتقان")

                        report_baseline = report_df[
                            report_df["assessment_type"].astype(str).str.lower()
                            .isin(["baseline", "قبلي"])
                        ]
                        report_followup = report_df[
                            report_df["assessment_type"].astype(str).str.lower()
                            .isin(["follow_up", "followup", "بعدي"])
                        ]

                        baseline_mean = (
                            float(report_baseline["mastery_pct"].mean())
                            if not report_baseline.empty else None
                        )
                        followup_mean = (
                            float(report_followup["mastery_pct"].mean())
                            if not report_followup.empty else None
                        )

                        r1, r2, r3 = st.columns(3)
                        r1.metric("متوسط الإتقان", f"{report_avg:.1f}%")
                        r2.metric("حد الإتقان المستهدف", f"{threshold}%")
                        r3.metric("مهارات دون الحد", len(report_weak))

                        st.markdown("### الملخص التنفيذي")
                        if report_avg >= threshold:
                            st.success(
                                "متوسط الإتقان العام بلغ حد الإتقان المستهدف "
                                "أو تجاوزه. يُنصح بالمحافظة على المستوى "
                                "ومعالجة أي مهارات منخفضة بصورة فردية."
                            )
                        else:
                            st.warning(
                                f"متوسط الإتقان العام {report_avg:.1f}%، "
                                f"وهو أقل من الهدف المحدد ({threshold}%). "
                                "تُوصى الأولوية بمراجعة المهارات الأقل إتقانًا "
                                "وتنفيذ تدخلات تعليمية موجهة."
                            )

                        st.markdown("### أبرز نقاط القوة")
                        strengths = report_skills[
                            report_skills["متوسط_الإتقان"] >= threshold
                        ].sort_values("متوسط_الإتقان", ascending=False)

                        if strengths.empty:
                            st.write(
                                "لم تبلغ أي مهارة حد الإتقان المستهدف "
                                "ضمن البيانات الحالية."
                            )
                        else:
                            for _, row in strengths.iterrows():
                                st.write(
                                    f"• {row['skill']}: "
                                    f"{row['متوسط_الإتقان']:.1f}%"
                                )

                        st.markdown("### أولويات الدعم")
                        if report_weak.empty:
                            st.write(
                                "لا توجد مهارات دون حد الإتقان "
                                "وفق البيانات والفلاتر الحالية."
                            )
                        else:
                            st.dataframe(
                                report_weak.rename(columns={
                                    "skill": "المهارة",
                                    "متوسط_الإتقان": "متوسط الإتقان (%)",
                                    "عدد_السجلات": "عدد السجلات",
                                }),
                                use_container_width=True,
                                hide_index=True,
                            )
                            st.write(
                                "التوصية: إعداد أنشطة علاجية للمهارات "
                                "الأقل إتقانًا، ثم إجراء تقييم متابعة "
                                "لقياس التقدم."
                            )

                        st.markdown("### مؤشرات التقييم القبلي والبعدي")
                        q1, q2 = st.columns(2)
                        q1.metric(
                            "متوسط التقييم القبلي",
                            f"{baseline_mean:.1f}%"
                            if baseline_mean is not None else "لا توجد بيانات"
                        )
                        q2.metric(
                            "متوسط التقييم البعدي",
                            f"{followup_mean:.1f}%"
                            if followup_mean is not None else "لا توجد بيانات"
                        )

                        if baseline_mean is not None and followup_mean is not None:
                            st.caption(
                                "تنبيه: الفرق بين المتوسطين العامين لا يثبت "
                                "تحسن الطلاب أنفسهم ما لم تُطابق سجلات الطالب "
                                "والمهارة بين التقييمين."
                            )

                        
                        # إنشاء تقرير HTML احترافي قابل للطباعة والحفظ PDF
                        from datetime import datetime
                        from zoneinfo import ZoneInfo

                        report_date = datetime.now(
                            ZoneInfo("Asia/Dubai")
                        ).strftime("%Y-%m-%d %H:%M")

                        active_school_name = html.escape(
                            str(selected_school.get("name", "المدرسة"))
                        )
                        # V6.5 - تحديد السنة الدراسية الحالية
                        report_now = datetime.now(ZoneInfo("Asia/Dubai"))

                        if report_now.month >= 8:
                            academic_start_year = report_now.year
                        else:
                            academic_start_year = report_now.year - 1

                        report_academic_year = (
                            f"{academic_start_year}-{academic_start_year + 1}"
                        )
                        safe_skills = []
                        for _, row in report_skills.sort_values(
                            "متوسط_الإتقان"
                        ).iterrows():
                            skill_name = html.escape(str(row["skill"]))
                            mastery_value = float(row["متوسط_الإتقان"])
                            record_count = int(row["عدد_السجلات"])

                            safe_skills.append(
                                "<tr><td>" + skill_name + "</td>"
                                + f"<td>{mastery_value:.1f}%</td>"
                                + f"<td>{record_count}</td></tr>"
                            )

                        if report_avg >= threshold:
                            executive_summary = (
                                "بلغ متوسط الإتقان العام الهدف المحدد أو تجاوزه. "
                                "يوصى بالمحافظة على نقاط القوة ومعالجة المهارات "
                                "التي ما زالت دون المستوى المستهدف."
                            )
                        else:
                            executive_summary = (
                                f"بلغ متوسط الإتقان {report_avg:.1f}%، "
                                f"وهو أقل من الهدف المحدد البالغ {threshold}%. "
                                "تُعطى الأولوية للمهارات الأقل إتقانًا، "
                                "مع تنفيذ أنشطة علاجية وتقييم لاحق."
                            )

                        safe_summary = html.escape(executive_summary)

                        if baseline_mean is not None:
                            baseline_text = f"{baseline_mean:.1f}%"
                        else:
                            baseline_text = "لا توجد بيانات"

                        if followup_mean is not None:
                            followup_text = f"{followup_mean:.1f}%"
                        else:
                            followup_text = "لا توجد بيانات"

                        report_html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>التقرير التنفيذي الذكي - MUEEN AI</title>
<style>
:root {{
    --navy: #10243A;
    --teal: #087E8B;
    --gold: #D9A441;
    --bg: #F3F6FA;
    --text: #263445;
    --muted: #64748B;
}}
* {{ box-sizing: border-box; }}
body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: Tahoma, Arial, sans-serif;
    line-height: 1.85;
}}
.page {{
    max-width: 1000px;
    margin: 28px auto;
    padding: 30px;
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 5px 24px rgba(16,36,58,.08);
}}
.hero {{
    padding: 28px;
    border-radius: 13px;
    color: white;
    background: linear-gradient(120deg, var(--navy), #17465B, var(--teal));
    border-bottom: 5px solid var(--gold);
}}
.brand {{
    color: #F1CB72;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: .5px;
}}
h1 {{ margin: 8px 0; font-size: 27px; }}
.subtitle {{ color: #E4EDF4; margin: 4px 0; }}
.meta {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin: 18px 0;
}}
.meta div, .metric {{
    padding: 14px;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    background: #F8FAFC;
}}
.label {{ color: var(--muted); font-size: 13px; }}
.value {{ color: var(--navy); font-weight: bold; }}
.metrics {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin: 18px 0;
}}
.metric {{ border-top: 4px solid var(--teal); }}
.metric strong {{
    display: block;
    color: var(--navy);
    font-size: 25px;
}}
h2 {{
    color: var(--navy);
    font-size: 19px;
    border-right: 4px solid var(--gold);
    padding-right: 10px;
    margin-top: 28px;
}}
.summary {{
    background: #EDF8F8;
    border: 1px solid #B9E0E1;
    border-radius: 10px;
    padding: 16px;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 12px;
}}
th, td {{
    border: 1px solid #DCE4EC;
    padding: 10px;
    text-align: right;
}}
th {{ background: var(--navy); color: white; }}
tbody tr:nth-child(even) {{ background: #F3F6FA; }}
.note {{
    margin-top: 22px;
    padding: 12px;
    color: #526174;
    background: #F8FAFC;
    border-radius: 8px;
    font-size: 12px;
}}
.actions {{
    display: flex;
    gap: 10px;
    margin: 20px 0;
}}
button {{
    border: 0;
    border-radius: 8px;
    padding: 11px 18px;
    color: white;
    background: var(--teal);
    font-size: 15px;
    cursor: pointer;
}}
button.secondary {{ background: var(--navy); }}
.footer {{
    margin-top: 24px;
    padding-top: 12px;
    border-top: 1px solid #DCE4EC;
    color: var(--muted);
    font-size: 12px;
    text-align: center;
}}
@media (max-width: 600px) {{
    .page {{ margin: 0; padding: 16px; border-radius: 0; }}
    .metrics {{ grid-template-columns: 1fr; }}
    .meta {{ grid-template-columns: 1fr; }}
    h1 {{ font-size: 22px; }}
}}
@page {{ size: A4; margin: 12mm; }}
@media print {{
    body {{ background: white; font-size: 11pt; }}
    .page {{
        max-width: none;
        margin: 0;
        padding: 0;
        box-shadow: none;
        border-radius: 0;
    }}
    .actions {{ display: none !important; }}
    .hero, th {{
        print-color-adjust: exact;
        -webkit-print-color-adjust: exact;
    }}
    h2, table, .metrics, .summary {{
        break-inside: avoid;
    }}
}}
</style>
</head>
<body>
<main class="page">
    <header class="hero">
        <div class="brand">MUEEN AI | مُعين</div>
        <h1>التقرير التنفيذي الذكي</h1>
        <p class="subtitle">تقرير متابعة التحصيل الدراسي والإتقان</p>
    </header>

    <section class="meta">
        <div>
            <div class="label">المدرسة النشطة</div>
            <div class="value">{active_school_name}</div>
        </div>
<div>
    <div class="label">السنة الدراسية</div>
    <div class="value">{report_academic_year}</div>
</div>
<div>
    <div class="label">تاريخ إصدار التقرير</div>
    <div class="value">{report_date}</div>
</div>
    </section>

    <div class="actions">
        <button onclick="window.print()">🖨️ طباعة / حفظ PDF</button>
        <button class="secondary" onclick="window.close()">إغلاق</button>
    </div>

    <h2>المؤشرات الرئيسية</h2>
    <section class="metrics">
        <div class="metric">
            <div class="label">متوسط الإتقان العام</div>
            <strong>{report_avg:.1f}%</strong>
        </div>
        <div class="metric">
            <div class="label">حد الإتقان المستهدف</div>
            <strong>{threshold}%</strong>
        </div>
        <div class="metric">
            <div class="label">مهارات دون الحد</div>
            <strong>{len(report_weak)}</strong>
        </div>
    </section>

    <h2>الملخص التنفيذي</h2>
    <div class="summary">{safe_summary}</div>

    <h2>نتائج المهارات</h2>
    <table>
        <thead>
            <tr>
                <th>المهارة</th>
                <th>متوسط الإتقان</th>
                <th>عدد السجلات</th>
            </tr>
        </thead>
        <tbody>
            {"".join(safe_skills)}
        </tbody>
    </table>

    <h2>مؤشرات التقييم القبلي والبعدي</h2>
    <section class="metrics">
        <div class="metric">
            <div class="label">متوسط التقييم القبلي</div>
            <strong>{baseline_text}</strong>
        </div>
        <div class="metric">
            <div class="label">متوسط التقييم البعدي</div>
            <strong>{followup_text}</strong>
        </div>
    </section>

    <h2>التوصية التنفيذية</h2>
    <p>
        توجيه الدعم التعليمي إلى المهارات الأقل إتقانًا، وتنفيذ أنشطة علاجية
        مناسبة، ثم إجراء تقييم لاحق لقياس التقدم. تُراجع النتائج من قبل
        المعلم والإدارة قبل اتخاذ القرارات.
    </p>

    <div class="note">
        يعتمد هذا التقرير على البيانات والفلاتر الحالية. وقد يختلف عدد
        السجلات بين التقييم القبلي والبعدي؛ لذلك لا يثبت اختلاف المتوسطين
        وحده تحسن الطلاب أنفسهم أو العلاقة السببية بين التدخل والنتيجة.
        يجب مراجعة النتائج قبل اتخاذ قرارات تعليمية.
    </div>

    <footer class="footer">
        MUEEN AI | مُعين — أداة مساندة للقرار التعليمي
    </footer>
</main>
</body>
</html>"""


                        st.download_button(
                            "📄 تنزيل التقرير التنفيذي HTML",
                            data=report_html.encode("utf-8"),
                            file_name="mueen_executive_report.html",
                            mime="text/html",
                            key="download_mueen_executive_report",
                        )
                        st.caption(
                            "يمكن فتح ملف HTML في المتصفح ثم اختيار طباعة "
                            "وحفظ بصيغة PDF."
                        )

            with mueen_page(1):
                st.markdown("### 🗂️ أحدث السجلات المحفوظة")
                display_cols = [
                    c for c in [
                        "student_code", "skill", "assessment_type", "score",
                        "max_score", "mastery_pct", "recommendation", "created_at"
                    ] if c in filtered_df.columns
                ]
                st.dataframe(
                    filtered_df.sort_values("created_at", ascending=False)[display_cols].head(200).rename(
                        columns={
                            "student_code": "رمز الطالب/المجموعة",
                            "skill": "المهارة",
                            "assessment_type": "نوع التقييم",
                            "score": "الدرجة",
                            "max_score": "الدرجة الكلية",
                            "mastery_pct": "الإتقان (%)",
                            "recommendation": "التوصية",
                            "created_at": "تاريخ الحفظ",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
                st.download_button(
                    "تنزيل السجلات المصفّاة CSV",
                    filtered_df.to_csv(index=False).encode("utf-8-sig"),
                    "mueen_dashboard_filtered_records.csv",
                    "text/csv",
                )
                if len(dashboard_df) >= 1000:
                    st.caption("تنبيه: عُرضت أحدث 1000 سجل فقط في لوحة المتابعة.")
    except Exception as e:
        st.error("تعذر تحميل لوحة المتابعة من Supabase.")
        st.caption(str(e)[:500])
elif not db_client and st.session_state.get("mueen_active_page") in (1, 2, 3, 4):
    st.info("فعّل اتصال Supabase لعرض لوحة المتابعة المحفوظة.")

# تصميم V3 مدمج ومحصور في بطاقات الخطة العلاجية فقط.
st.markdown("""
<style>
[class*="st-key-mueen_plan_card_"] {
    background:#ffffff !important;
    border:1px solid #d9e5ed !important;
    border-radius:14px !important;
    padding:12px 18px !important;
    box-shadow:0 3px 12px rgba(16,36,58,.045);
    margin-bottom:7px !important;
}
[class*="st-key-mueen_plan_card_"] [data-testid="stVerticalBlock"] {gap:0 !important;}
[class*="st-key-mueen_plan_card_"] .mueen-plan-v2 {
    font-family:'Tajawal','Segoe UI',Arial,sans-serif;
    font-size:18px;line-height:1.8;color:#183248;
    overflow-wrap:break-word;
}
[class*="st-key-mueen_plan_card_"] .mueen-plan-v2-head {
    background:#eff8f9;border-inline-start:4px solid #087e8b;
    border-radius:8px;padding:7px 12px;margin-bottom:9px;
    color:#075e69;font-size:20px;font-weight:800;line-height:1.5;
}
[class*="st-key-mueen_plan_card_"] .mueen-plan-v2-body {padding:0 5px;max-width:1080px;margin-inline:auto;}
[class*="st-key-mueen_plan_card_"] .mueen-plan-v2-body p {
    margin:0 0 8px;font-size:18px;line-height:1.8;
}
[class*="st-key-mueen_plan_card_"] .mueen-plan-v2-body ul,
[class*="st-key-mueen_plan_card_"] .mueen-plan-v2-body ol {
    margin:5px 0 10px;padding-inline-start:28px;list-style-position:outside;
}
[class*="st-key-mueen_plan_card_"] .mueen-plan-v2-body li {
    font-size:18px;line-height:1.8;padding-inline-start:4px;margin-bottom:4px;
}
[class*="st-key-mueen_plan_card_"] .mueen-plan-v2-body li::marker {color:#087e8b;font-weight:800;}
.mueen-plan-v3-metrics {display:flex;gap:10px;flex-wrap:wrap;margin:7px 0 13px;direction:rtl;}
.mueen-plan-v3-metrics span {
    display:inline-block;background:#eaf5f6;color:#075e69;
    border:1px solid #cce5e8;border-radius:9px;
    padding:7px 12px;font-weight:700;font-size:16px;
}
@media(max-width:700px) {
    [class*="st-key-mueen_plan_card_"] {padding:10px 12px !important;}
    [class*="st-key-mueen_plan_card_"] .mueen-plan-v2-head {font-size:18px;}
    [class*="st-key-mueen_plan_card_"] .mueen-plan-v2-body p,
    [class*="st-key-mueen_plan_card_"] .mueen-plan-v2-body li {font-size:16px;}
}
</style>
""", unsafe_allow_html=True)

def render_mueen_plan_body(section_text):
    """تحويل نص الخطة إلى فقرات وقوائم HTML آمنة دون تعديل النص المحفوظ."""
    lines = section_text.splitlines()
    result = []
    list_kind = None
    def close_list():
        nonlocal list_kind
        if list_kind:
            result.append(f"</{list_kind}>")
            list_kind = None
    for raw in lines:
        line = raw.strip()
        if not line:
            close_list()
            continue
        numbered = re.match(r"^(?:\d+|[٠-٩]+)[.)\-]\s+(.+)$", line)
        bullet = re.match(r"^[-•*]\s+(.+)$", line)
        kind = 'ol' if numbered else 'ul' if bullet else None
        if kind:
            if list_kind != kind:
                close_list()
                result.append(f"<{kind}>")
                list_kind = kind
            value = numbered.group(1) if numbered else bullet.group(1)
            result.append(f"<li>{html.escape(value)}</li>")
        else:
            close_list()
            result.append(f"<p>{html.escape(line)}</p>")
    close_list()
    return ''.join(result)


def split_mueen_plan_sections(plan_text, is_arabic=True):
    """قسّم الخطة بصريًا دون تعديل النص الأصلي أو بياناته المحفوظة."""
    headings_ar = [
        ("🔍", "تفسير النتيجة", ("تفسير حذر للنتيجة", "تفسير النتيجة")),
        ("🎯", "الهدف القابل للقياس", ("هدف قابل للقياس", "الهدف القابل للقياس")),
        ("📖", "الشرح المبسط", ("شرح مبسط", "الشرح المبسط")),
        ("💡", "المثال المحلول", ("مثال محلول", "المثال المحلول")),
        ("🧩", "النشاط العلاجي · 10 دقائق", ("نشاط علاجي", "النشاط العلاجي")),
        ("📝", "أسئلة المتابعة والإجابات", ("خمسة أسئلة متابعة", "أسئلة متابعة", "اسئلة متابعة")),
        ("✅", "معيار الإتقان", ("معيار إتقان", "معيار الإتقان")),
        ("🔄", "التدخل البديل", ("بديل إذا لم يتحقق", "التدخل البديل")),
        ("📈", "الخطوة التالية", ("الخطوة التالية بعد التقييم", "الخطوة التالية")),
    ]
    headings_en = [
        ("🔍", "Interpretation", ("interpretation", "interpret the result")),
        ("🎯", "Measurable objective", ("measurable objective", "measurable goal")),
        ("📖", "Simple explanation", ("simple explanation", "simplified explanation")),
        ("💡", "Worked example", ("worked example", "solved example")),
        ("🧩", "10-minute activity", ("remedial activity", "10-minute activity")),
        ("📝", "Follow-up questions", ("follow-up questions", "five questions")),
        ("✅", "Mastery criterion", ("mastery criterion", "mastery criteria")),
        ("🔄", "Alternative support", ("alternative if", "alternative intervention")),
        ("📈", "Next steps", ("next step", "after the follow-up")),
    ]
    headings = headings_ar if is_arabic else headings_en
    sections = []
    current = None
    buffer = []
    for line in plan_text.splitlines():
        normalized = re.sub(r"^[\s#*\-\d٠-٩.)،:]+", "", line.strip()).strip()
        normalized = normalized.rstrip(" :：*#").lower()
        match = None
        # لا تعامل جملة طويلة تحتوي اسم القسم على أنها عنوان.
        if len(normalized) <= 95:
            for index, (icon, title, variants) in enumerate(headings):
                if any(normalized.startswith(v.lower()) for v in variants):
                    match = index
                    break
        if match is not None:
            if buffer and any(x.strip() for x in buffer):
                sections.append((current, "\n".join(buffer).strip()))
            current = match
            buffer = []
        else:
            buffer.append(line)
    if buffer and any(x.strip() for x in buffer):
        sections.append((current, "\n".join(buffer).strip()))
    return headings, sections


with mueen_page(5):
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
        # القيمة الافتراضية، وتُستبدل باختيار الهيكل الأكاديمي عند توفره.
        plan_subject = subject
        plan_grade = grade

        academic_client = get_supabase()
        academic_school_id = get_selected_school_id()

        if academic_client is None or not academic_school_id:
            st.error("تعذر الاتصال بالمدرسة المحددة. سجّل الدخول مجددًا.")
        else:
            try:
                # تحميل الشعب التابعة للمدرسة المحددة
                sections_response = (
                    academic_client.table("academic_sections")
                    .select(
                        "id,grade_level,cycle,track,section_name,academic_year"
                    )
                    .eq("school_id", academic_school_id)
                    .order("grade_level")
                    .order("section_name")
                    .execute()
                )
                academic_sections = sections_response.data or []

                if not academic_sections:
                    st.warning("لا توجد شعب مسجلة في الهيكل الأكاديمي لهذه المدرسة.")
                else:
                    section_options = {}
                    for item in academic_sections:
                        label = (
                            f"الصف {item['grade_level']} - "
                            f"الشعبة {item['section_name']} - "
                            f"{item['academic_year']}"
                        )
                        section_options[label] = item

                    selected_section_label = st.selectbox(
                        "الصف والشعبة",
                        list(section_options.keys()),
                        key="assessment_academic_section",
                    )
                    selected_section = section_options[selected_section_label]

                    # تحميل المواد المرتبطة بالشعبة المختارة فقط
                    links_response = (
                        academic_client.table("section_subjects")
                        .select("subject_id")
                        .eq("school_id", academic_school_id)
                        .eq("section_id", selected_section["id"])
                        .execute()
                    )
                    linked_subject_ids = [
                        item["subject_id"]
                        for item in (links_response.data or [])
                    ]

                    linked_subjects = []
                    if linked_subject_ids:
                        subjects_response = (
                            academic_client.table("academic_subjects")
                            .select(
                                "id,subject_name,grade_level,track,academic_year"
                            )
                            .eq("school_id", academic_school_id)
                            .eq("grade_level", selected_section["grade_level"])
                            .eq("track", selected_section["track"])
                            .eq("academic_year", selected_section["academic_year"])
                            .execute()
                        )
                        linked_subjects = [
                            subject
                            for subject in (subjects_response.data or [])
                            if subject["id"] in linked_subject_ids
                        ]

                    if not linked_subjects:
                        st.warning("لا توجد مواد مرتبطة بهذه الشعبة. أضف الربط من إدارة الهيكل الأكاديمي.")
                    else:
                        subject_options = {
                            subject["subject_name"]: subject
                            for subject in linked_subjects
                        }
                        selected_subject_name = st.selectbox(
                            "المادة",
                            list(subject_options.keys()),
                            key="assessment_academic_subject",
                        )
                        selected_subject = subject_options[selected_subject_name]
                        plan_subject = selected_subject_name
                        plan_grade = str(selected_section["grade_level"])

                        student_code = st.text_input(
                            "رمز الطالب/المجموعة (مجهول الهوية)",
                            value="DEMO-GROUP",
                            help="استخدم رمزًا مستعارًا، ولا تكتب اسم الطالب.",
                        )

                        if st.button(
                            "💾 حفظ نتائج التقييم القبلي في Supabase",
                            use_container_width=True,
                        ):
                            if not student_code.strip():
                                st.error("أدخل رمزًا مجهول الهوية للطالب أو المجموعة.")
                            else:
                                save_student(
                                    student_code.strip(),
                                    str(selected_section["grade_level"]),
                                    str(selected_section["section_name"]),
                                )

                                records = [{
                                    "student_code": student_code.strip(),
                                    "skill": str(row["Skill"]),
                                    "assessment_type": "baseline",
                                    "score": float(row["AverageMastery"]),
                                    "max_score": 100.0,
                                    "recommendation": (
                                        "متوسط الإتقان القبلي للمجموعة؛ الحالة: "
                                        + str(row["Status"])
                                    ),
                                    "section_id": selected_section["id"],
                                    "subject_id": selected_subject["id"],
                                } for _, row in summary.iterrows()]

                                save_assessment_records(records)
                                st.success(
                                    f"تم حفظ {len(records)} سجلًا قبليًا بنجاح."
                                )

            except Exception as e:
                st.error("تعذر تحميل الهيكل الأكاديمي أو حفظ النتائج.")
                st.caption(str(e)[:500])

        weak=summary[summary["AverageMastery"]<threshold]["Skill"].tolist(); options=weak or summary["Skill"].tolist()
        skill=st.selectbox("اختر المهارة المستهدفة",options)
        mastery=float(summary.loc[summary["Skill"]==skill,"AverageMastery"].iloc[0])
        st.metric("متوسط الإتقان القبلي للمهارة",f"{mastery:.1f}%")
        notes=st.text_area("ملاحظات المعلم (اختياري)",placeholder="مثال: يحتاج بعض الطلاب إلى مثال بصري لترتيب الخطوات.")
        group=st.selectbox("الفئة المستهدفة",["مجموعة دعم","مجموعة الصف","مجموعة إثراء"])
        # MUEEN V5 — دورة تدخل ذكي من بيانات التقييم الحالية، دون حفظ تلقائي.
        st.markdown("### 🚀 دورة التدخل الذكي | MUEEN Agent")
        st.caption("يشخّص المهارة الأضعف ويُنشئ الخطة والاختبار للمراجعة؛ لا تُرسل أسماء الطلاب إلى النموذج.")
        agent_weak = summary.sort_values(["AverageMastery", "Skill"], ascending=[True, True]).iloc[0]
        agent_skill = str(agent_weak["Skill"])
        agent_mastery = float(agent_weak["AverageMastery"])
        st.info(
            f"🔎 الأولوية المقترحة: {agent_skill} — متوسط الإتقان {agent_mastery:.1f}% "
            f"(حد الإتقان {threshold}%)."
        )
        current_section_id = selected_section["id"] if "selected_section" in locals() and "selected_subject" in locals() and linked_subjects else None
        current_subject_id = selected_subject["id"] if current_section_id else None
        current_skill_id = None
        if current_subject_id and academic_client is not None:
            try:
                skill_rows = (academic_client.table("learning_skills")
                              .select("id,skill_name")
                              .eq("school_id", academic_school_id)
                              .eq("subject_id", current_subject_id)
                              .eq("skill_name", agent_skill).limit(1).execute().data or [])
                current_skill_id = skill_rows[0]["id"] if skill_rows else None
            except Exception:
                pass
        if st.button("🚀 ابدأ دورة التدخل الذكي", key="mueen_agent_start", use_container_width=True):
            if agent_mastery >= threshold:
                st.warning("جميع المهارات بلغت حد الإتقان؛ لا توجد مهارة متعثرة تستدعي تدخلًا علاجيًا وفق هذه البيانات.")
            elif not get_key():
                st.error("مفتاح OpenAI غير متاح؛ تعذّر بدء الدورة.")
            else:
                # لا نحتفظ بمخرجات دورة قديمة إذا فشل إنشاء إحدى المرحلتين.
                st.session_state.pop("mueen_agent_cycle", None)
                st.session_state.pop("mueen_agent_decision", None)
                st.session_state.pop("mueen_v5_saved_plan", None)
                try:
                    with st.spinner("الوكيل يحلل الأولوية وينشئ الخطة واختبار المتابعة..."):
                        agent_plan = create_plan(
                            model, plan_subject, plan_grade, agent_skill,
                            agent_mastery, output_language, notes, group, threshold
                        )
                        agent_quiz = create_quiz(
                            model, plan_subject, plan_grade, agent_skill, output_language
                        )
                    st.session_state["mueen_agent_cycle"] = {
                        "school_id": get_selected_school_id(),
                        "subject": plan_subject, "grade": plan_grade,
                        "skill": agent_skill, "before": agent_mastery,
                        "threshold": threshold, "plan": agent_plan,
                        "quiz": agent_quiz, "language": output_language,
                        "created_at": datetime.now().isoformat(),
                        "section_id": current_section_id,
                        "subject_id": current_subject_id,
                        "skill_id": current_skill_id,
                        "source_demo": uploaded is None and use_demo,
                        "baseline_rows": data[["Student", "Skill", "Score", "MaxScore"]].to_dict("records"),
                    }
                    st.session_state["last_plan"] = agent_plan
                    st.session_state["last_skill"] = agent_skill
                    st.session_state["last_quiz"] = agent_quiz
                    st.session_state["quiz_skill"] = agent_skill
                    st.success("اكتملت مرحلتا التخطيط وإعداد الاختبار. راجع المخرجات قبل استخدامها.")
                except Exception as e:
                    st.error("لم تكتمل الدورة؛ لم تُحفظ أي سجلات في قاعدة البيانات.")
                    st.caption(str(e)[:500])
        agent_cycle = st.session_state.get("mueen_agent_cycle")
        if agent_cycle and agent_cycle.get("school_id") == get_selected_school_id():
            st.markdown("#### 🧠 ملخص دورة التدخل الذكي")
            st.write(
                f"**المادة:** {agent_cycle['subject']} | **الصف:** {agent_cycle['grade']} | "
                f"**المهارة:** {agent_cycle['skill']} | "
                f"**القبلي:** {agent_cycle['before']:.1f}% | "
                f"**المستهدف:** {agent_cycle['threshold']}%"
            )
            st.caption("المرحلة الحالية: بانتظار تطبيق النشاط وإدخال نتيجة اختبار المتابعة بواسطة المعلم.")
            with st.expander("📘 عرض الخطة التي أنشأها الوكيل"):
                st.markdown(agent_cycle["plan"])
            with st.expander("📝 عرض اختبار المتابعة ومفتاح الإجابة"):
                st.markdown(agent_cycle["quiz"])
            st.download_button("📥 تنزيل خطة الوكيل", agent_cycle["plan"], "mueen_agent_plan.txt", key="mueen_agent_plan_download")
            st.download_button("📥 تنزيل اختبار الوكيل", agent_cycle["quiz"], "mueen_agent_quiz.txt", key="mueen_agent_quiz_download")
            agent_after = st.number_input(
                "نتيجة التقييم البعدي للدورة (%) — بعد تطبيق الاختبار",
                min_value=0.0, max_value=100.0, value=0.0, step=1.0,
                key="mueen_agent_after"
            )
            if st.button("📊 تحليل نتيجة الدورة واقتراح الخطوة التالية", key="mueen_agent_decide"):
                agent_recommendation, agent_delta = decide(
                    agent_cycle["before"], agent_after, agent_cycle["threshold"]
                )
                st.session_state["mueen_agent_decision"] = {
                    "school_id": agent_cycle["school_id"],
                    "cycle_id": agent_cycle["created_at"],
                    "skill": agent_cycle["skill"], "before": agent_cycle["before"],
                    "after": agent_after, "delta": agent_delta,
                    "recommendation": agent_recommendation,
                }
            agent_decision = st.session_state.get("mueen_agent_decision")
            if (agent_decision and agent_decision.get("cycle_id") == agent_cycle["created_at"]
                    and agent_decision["school_id"] == agent_cycle["school_id"]
                    and agent_decision["skill"] == agent_cycle["skill"]
                    and agent_decision["before"] == agent_cycle["before"]):
                st.metric("التغير في الإتقان", f"{agent_decision['delta']:+.1f} نقطة مئوية")
                st.info(agent_decision["recommendation"])
                st.caption("هذه توصية مبدئية وليست قرارًا نهائيًا؛ لا يتم حفظ النتيجة تلقائيًا.")

        # V5 — التحقق من جودة مخرجات الوكيل، ثم حفظها في الجداول الـ16 القائمة.
        if agent_cycle and agent_cycle.get("school_id") == get_selected_school_id():
            st.markdown("### 🧩 MUEEN V5 | الذاكرة والمتابعة والتوسع")
            if agent_cycle.get("source_demo"):
                st.warning("هذه الدورة مستمدة من بيانات نموذجية. يمكن استعراضها، لكن لا يجوز حفظها كدليل على تحسن طلاب حقيقيين.")
            plan_text = agent_cycle["plan"]
            quiz_text = agent_cycle["quiz"]
            required_titles = (["Interpretation", "Measurable objective", "Worked example", "10-minute activity", "Follow-up questions"]
                               if agent_cycle["language"] == "English" else
                               ["تفسير النتيجة", "الهدف القابل للقياس", "المثال المحلول", "النشاط العلاجي", "أسئلة المتابعة"])
            missing_titles = [title for title in required_titles if title not in plan_text]
            quiz_valid = len(quiz_text.strip()) >= 100
            if missing_titles or not quiz_valid:
                st.error("فحص المخرجات: بعض عناصر الخطة أو الاختبار ناقصة. أعد إنشاء الدورة قبل اعتمادها.")
                if missing_titles:
                    st.caption("عناوين ناقصة: " + "، ".join(missing_titles))
            else:
                st.success("اجتازت المخرجات فحص البنية الأولي. ما زالت الدقة العلمية ومفتاح الإجابة بحاجة لمراجعة المعلم.")
            role_v5 = str(st.session_state.get("mueen_school_role", "")).lower()
            can_manage_v5 = role_v5 in ("principal", "coordinator")
            if can_manage_v5:
                try:
                    prior = mueen_v5_prior_interventions(agent_cycle["school_id"], agent_cycle.get("subject_id"), agent_cycle.get("skill_id"))
                    with st.expander("🧠 ذاكرة الوكيل: تدخلات سابقة في المدرسة", expanded=False):
                        if prior:
                            st.dataframe(pd.DataFrame(prior), use_container_width=True, hide_index=True)
                        else:
                            st.info("لا توجد تدخلات سابقة مرئية لهذا النطاق.")
                except Exception as exc:
                    st.warning("تعذر قراءة ذاكرة التدخلات وفق الصلاحيات الحالية.")
                    st.caption(str(exc)[:250])
            else:
                st.info("صلاحيات قاعدة البيانات الحالية تقصر قراءة وحفظ خطط التدخل على المدير والمنسق. يمكن للمعلم إنشاء مقترح للمراجعة.")
            if agent_cycle.get("subject_id") is None:
                st.info("لربط الخطة بالمنهج، اختر شعبة ومادة مرتبطتين من الهيكل الأكاديمي ثم أعد تشغيل الدورة.")
            with st.expander("💾 اعتماد الخطة وحفظها في intervention_plans", expanded=False):
                v5_title = st.text_input("عنوان الخطة", value=f"تدخل {agent_cycle['skill']}", key="mueen_v5_title")
                v5_strategy = st.text_area("استراتيجية التدخل المعتمدة", value=agent_cycle["plan"], height=160, key="mueen_v5_strategy")
                v5_criteria = st.text_input("معيار النجاح", value=f"تحقيق إتقان {agent_cycle['threshold']}% في اختبار متابعة للمهارة", key="mueen_v5_criteria")
                approve_plan = st.checkbox("راجعت الخطة والاختبار وتأكدت من ملاءمتهما", key="mueen_v5_approve_plan")
                if st.button("حفظ الخطة المعتمدة", key="mueen_v5_save_plan", disabled=(not can_manage_v5 or not approve_plan or bool(missing_titles) or not quiz_valid or agent_cycle.get("source_demo") or not agent_cycle.get("subject_id"))):
                    try:
                        saved = mueen_v5_save_plan(agent_cycle, v5_title, v5_strategy, v5_criteria)
                        st.session_state["mueen_v5_saved_plan"] = {"cycle_id": agent_cycle["created_at"], "plan_id": saved["id"]}
                        st.success("حُفظت الخطة في جدول intervention_plans بنجاح.")
                    except Exception as exc:
                        st.error("تعذر حفظ الخطة: " + str(exc)[:400])
            st.markdown("#### 📊 قياس قبلي/بعدي للطلاب أنفسهم")
            post_csv = st.file_uploader("ملف نتائج التقييم البعدي CSV", type=["csv"], key="mueen_v5_post_csv")
            paired_v5 = None
            if post_csv is not None:
                try:
                    paired_v5 = mueen_v5_paired(pd.DataFrame(agent_cycle["baseline_rows"]), pd.read_csv(post_csv), agent_cycle["skill"])
                    st.dataframe(paired_v5, use_container_width=True, hide_index=True)
                    a, b, c = st.columns(3)
                    a.metric("طلاب تمت مطابقتهم", len(paired_v5))
                    b.metric("متوسط التغير", f"{paired_v5['التغير'].mean():+.1f} نقطة")
                    c.metric("بلغوا الإتقان بعديًا", f"{(paired_v5['بعد'] >= agent_cycle['threshold']).mean() * 100:.1f}%")
                    st.download_button("تنزيل المقارنة", paired_v5.to_csv(index=False).encode("utf-8-sig"), "mueen_paired_outcomes.csv", "text/csv", key="mueen_v5_download_paired")
                    st.caption("المقارنة وصفية للطلاب المتطابقين، وليست إثباتًا سببيًا لفاعلية التدخل.")
                except Exception as exc:
                    st.error("تعذرت المطابقة: " + str(exc)[:400])
            saved_plan_v5 = st.session_state.get("mueen_v5_saved_plan", {})
            if saved_plan_v5.get("cycle_id") == agent_cycle["created_at"] and paired_v5 is not None:
                next_mean = float(paired_v5["بعد"].mean())
                advice, change = decide(float(paired_v5["قبل"].mean()), next_mean, agent_cycle["threshold"])
                st.info("قرار الوكيل اعتمادًا على البيانات المطابقة: " + advice)
                v5_teacher_note = st.text_area("ملاحظات المعلم على تنفيذ التدخل", key="mueen_v5_teacher_note")
                confirm_followup = st.checkbox("أؤكد تطبيق الاختبار ومراجعة نتائجه؛ البيانات ليست نموذجية", key="mueen_v5_followup_confirm")
                if st.button("حفظ المتابعة والقرار في intervention_followups", key="mueen_v5_save_followup", disabled=(not confirm_followup or agent_cycle.get("source_demo"))):
                    try:
                        mueen_v5_save_followup(agent_cycle, saved_plan_v5["plan_id"], {"after": next_mean, "recommendation": advice}, v5_teacher_note)
                        st.success("حُفظت المتابعة. يمكن للوكيل الاستفادة منها عند قراءة سجل التدخلات لاحقًا.")
                    except Exception as exc:
                        st.error("تعذر حفظ المتابعة: " + str(exc)[:400])

        st.markdown("### 3) إنشاء خطة علاجية")

        if st.button(
            "✨ إنشاء خطة بالذكاء الاصطناعي",
            type="primary",
            use_container_width=True
        ):
            try:
                with st.spinner("يُعد مُعين الخطة..."):
                    st.session_state["last_plan"] = create_plan(
                        model,
                        plan_subject,
                        plan_grade,
                        skill,
                        mastery,
                        output_language,
                        notes,
                        group,
                        threshold
                    )
                    st.session_state["last_skill"] = skill

            except Exception as e:
                st.error(
                    "تعذر إنشاء الخطة. تحقق من المفتاح والفوترة وإتاحة النموذج."
                )
                st.code(str(e)[:1000])

        # عرض الخطة العلاجية بعد إنشائها
        if st.session_state.get("last_plan"):

            skill_title = st.session_state.get("last_skill", "")
            plan_text = st.session_state["last_plan"]

            st.markdown(
                "#### 📘 الخطة العلاجية: " + skill_title
            )
            # مؤشرات توضيحية فقط؛ حد الإتقان هو إعداد المعلم الحالي.
            st.markdown(
                '<div class="mueen-plan-v3-metrics" dir="rtl">'
                f'<span>📊 الإتقان القبلي: {mastery:.1f}%</span>'
                f'<span>🎯 حد الإتقان: {threshold}%</span>'
                '<span>⏱️ النشاط: 10 دقائق</span>'
                '</div>',
                unsafe_allow_html=True
            )

            # تقسيم الخطة إلى بطاقات مستقلة دون تغيير النص الأصلي للتنزيل.
            plan_is_arabic = st.session_state.get("mueen_output_language", "العربية") == "العربية"
            plan_direction = "rtl" if plan_is_arabic else "ltr"
            plan_headings, plan_sections = split_mueen_plan_sections(plan_text, plan_is_arabic)
            if not plan_sections:
                plan_sections = [(None, plan_text)]

            for card_index, (section_number, section_text) in enumerate(plan_sections):
                if section_number is not None:
                    icon, title, _ = plan_headings[section_number]
                    card_title = f'<div class="mueen-plan-v2-head">{icon} {html.escape(title)}</div>'
                else:
                    card_title = ""
                card_html = (
                    f'<section class="mueen-plan-v2" dir="{plan_direction}">'
                    + card_title
                    + '<div class="mueen-plan-v2-body">'
                    + render_mueen_plan_body(section_text)
                    + '</div></section>'
                )
                with st.container(border=True, key=f"mueen_plan_card_{card_index}"):
                    st.markdown(card_html, unsafe_allow_html=True)

            # تنزيل الخطة
            st.download_button(
                "📥 تنزيل الخطة العلاجية TXT",
                plan_text,
                "mueen_learning_plan.txt",
                "text/plain",
                use_container_width=True
            )

        st.markdown("### 4) إنشاء اختبار متابعة")
        if st.button("📝 إنشاء اختبار متابعة من 5 أسئلة",use_container_width=True):
            try:
                with st.spinner("يُنشئ مُعين الاختبار..."):
                    st.session_state["last_quiz"]=create_quiz(model,plan_subject,plan_grade,skill,output_language)
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
                        "recommendation": (
                            str(result["SuggestedNextStep"])
                            + f" | القبلي: {result['BeforePct']}%"
                            + f" | التغير: {result['ChangePoints']:+.1f} نقطة"
                        ),
                        "section_id": selected_section["id"],
                        "subject_id": selected_subject["id"],
                    }])
                    st.success("تم حفظ نتيجة التقييم البعدي والتوصية في قاعدة البيانات.")
                except Exception as e:
                    st.error("تعذر حفظ النتيجة. تأكد من إعداد Secrets وصلاحية الاتصال.")
                    st.caption(str(e)[:500])

        st.markdown("### 6) سجل المتابعة المحفوظ")
        hist_code = st.text_input("رمز الطالب/المجموعة لعرض السجل", value="", key="history_code", help="أدخل رمز الطالب أو المجموعة الذي تريد عرض سجله.")
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
    2. أضف `SUPABASE_URL` و`SUPABASE_PUBLISHABLE_KEY` إلى Streamlit Secrets.
    3. لا تضع مفتاح Supabase Secret أو أي مفتاح خاص في GitHub أو داخل الواجهة أو في المحادثات.
    4. يعتمد الحفظ على تسجيل دخول المستخدم وسياسات RLS في Supabase؛ يجب اختبارها بحسابات ومدارس مختلفة قبل فتح التطبيق للآخرين.
    5. اختيار المدرسة في الواجهة ليس بديلًا عن RLS؛ قاعدة البيانات هي التي يجب أن تمنع الوصول غير المصرح به.""")
    st.divider()
    st.caption("MUEEN AI V3.1 — عند تفعيل Supabase تُحفظ النتائج القبلية والبعدية وتوصيات المتابعة في قاعدة البيانات. استخدم رموزًا مجهولة الهوية واختبر ببيانات تجريبية أولًا.")
