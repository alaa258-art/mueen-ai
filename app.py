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
        .select("student_code,skill,assessment_type,score,max_score,recommendation,created_at")
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

# بوابة تسجيل الدخول إلى مُعين AI
if not st.session_state.get("mueen_access_token"):
    st.title("🔐 تسجيل الدخول | MUEEN AI")
    st.caption("سجّل الدخول بحسابك المعتمد للوصول إلى المنصة.")
    auth_client = get_auth_client()
    if auth_client is None:
        st.error("تعذر إعداد Supabase. تحقق من SUPABASE_URL وSUPABASE_PUBLISHABLE_KEY في Streamlit Secrets.")
        st.stop()

    with st.form("mueen_login_form"):
        email = st.text_input("البريد الإلكتروني")
        password = st.text_input("كلمة المرور", type="password")
        submitted = st.form_submit_button("تسجيل الدخول", use_container_width=True)

    if submitted:
        try:
            result = auth_client.auth.sign_in_with_password({
                "email": email.strip(),
                "password": password,
            })
            if result.session:
                st.session_state["mueen_access_token"] = result.session.access_token
                st.session_state["mueen_refresh_token"] = result.session.refresh_token
                st.rerun()
            else:
                st.error("لم يتم إنشاء جلسة تسجيل دخول.")
        except Exception:
            st.error("تعذر تسجيل الدخول. تحقق من بيانات الحساب وحالة حسابك في Supabase Auth.")
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

selected_school = st.selectbox(
    "🏫 المدرسة النشطة",
    options=user_schools,
    index=next(i for i, school in enumerate(user_schools) if school["id"] == saved_school_id),
    format_func=lambda school: school["name"],
    key="mueen_school_selector",
)
st.session_state["mueen_school_id"] = selected_school["id"]
st.session_state["mueen_school_role"] = selected_school["role"]
st.caption(f"الدور في المدرسة المختارة: {selected_school['role']}")

logout_col, title_col = st.columns([1, 4])
with logout_col:
    if st.button("تسجيل الخروج", key="mueen_logout"):
        try:
            session_client.auth.sign_out()
        except Exception:
            pass
        clear_login()
        st.rerun()
with title_col:
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
    st.sidebar.warning("تعذر الاتصال بقاعدة البيانات عبر جلسة المستخدم. تحقق من SUPABASE_URL وSUPABASE_PUBLISHABLE_KEY.")
if key: st.success("تم العثور على مفتاح API. لن نعرضه داخل التطبيق.")
else: st.info("أضف OPENAI_API_KEY إلى Settings → Secrets في Streamlit لتفعيل ميزات الذكاء الاصطناعي.")

st.markdown("## 📊 لوحة متابعة المعلم")
st.caption("تعرض اللوحة السجلات المحفوظة في Supabase فقط، ولا تخلط بينها وبين البيانات النموذجية غير المحفوظة.")
if db_client:
    if st.button("🔄 تحديث لوحة المتابعة", use_container_width=True):
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

            st.write("عدد السجلات بعد فلتر التاريخ:", len(dashboard_df))
            if not dashboard_df.empty:
                st.write("أقدم سجل:", dashboard_df["created_at"].min())
                st.write("أحدث سجل:", dashboard_df["created_at"].max())
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
            st.write(
                "عدد السجلات القبلية:",
                int(dashboard_df["assessment_type"].str.lower().isin(["baseline", "قبلي"]).sum()),
            )
            st.write(
                "عدد السجلات البعدية:",
                int(dashboard_df["assessment_type"].str.lower().isin(["follow_up", "followup", "بعدي"]).sum()),
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
                below_threshold_n = int((filtered_df["mastery_pct"] < threshold).sum())

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("طلاب/مجموعات", students_n)
                m2.metric("السجلات المعروضة", int(len(filtered_df)))
                m3.metric("متوسط الإتقان", f"{avg_mastery:.1f}%")
                m4.metric("سجلات دون حد الإتقان", below_threshold_n)

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
                            
                            "تنزيل تقرير المقارنة CSV",
                            comparison.to_csv(index=False).encode("utf-8-sig"),
                            "mueen_dashboard_comparison.csv",
                            "text/csv",
                        )
                    else:
                        st.info("توجد سجلات قبلية وبعدية، لكن لا توجد سجلات متطابقة في رمز الطالب/المجموعة والمهارة للمقارنة.")
                else:
                    st.info("لإظهار المقارنة، اختر كل أنواع التقييم أو تأكد من وجود سجلات قبلية وبعدية ضمن التصفية.")

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
else:
    st.info("فعّل اتصال Supabase لعرض لوحة المتابعة المحفوظة.")

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
2. أضف `SUPABASE_URL` و`SUPABASE_PUBLISHABLE_KEY` إلى Streamlit Secrets.
3. لا تضع مفتاح Supabase Secret أو أي مفتاح خاص في GitHub أو داخل الواجهة أو في المحادثات.
4. يعتمد الحفظ على تسجيل دخول المستخدم وسياسات RLS في Supabase؛ يجب اختبارها بحسابات ومدارس مختلفة قبل فتح التطبيق للآخرين.
5. اختيار المدرسة في الواجهة ليس بديلًا عن RLS؛ قاعدة البيانات هي التي يجب أن تمنع الوصول غير المصرح به.""")
st.divider()
st.caption("MUEEN AI V3.1 — عند تفعيل Supabase تُحفظ النتائج القبلية والبعدية وتوصيات المتابعة في قاعدة البيانات. استخدم رموزًا مجهولة الهوية واختبر ببيانات تجريبية أولًا.")
