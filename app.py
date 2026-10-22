import streamlit as st
import pandas as pd
import json
import html
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


def create_achievement_analysis(model, aggregate_json, threshold, language):
    """تحليل تعليمي من بيانات مجمعة فقط؛ لا ترسل رموز الطلاب أو سجلاتهم الفردية."""
    prompt = f"""أنت محلل بيانات تعليمية مساعد للمعلم. حلل مؤشرات التحصيل التالية بحذر وباللغة {language}.
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
                        placeholder="مثال: الرياضيات"
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
                .execute()
            )

            if existing_subject.data:
                st.warning(
                    "هذه المادة مسجلة بالفعل لهذا الصف والمسار. "
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
                            st.error(
                                "تعذر الربط. قد يكون هذا الربط موجودًا مسبقًا."
                            )
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

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("طلاب/مجموعات", students_n)
                m2.metric("السجلات المعروضة", int(len(filtered_df)))
                m3.metric("متوسط جميع السجلات", f"{avg_mastery:.1f}%")
                m4.metric("سجلات دون حد الإتقان", below_threshold_n)

                m5, m6 = st.columns(2)
                m5.metric(
                    "متوسط الإتقان القبلي",
                    f"{baseline_avg:.1f}%" if baseline_avg is not None else "لا توجد بيانات"
                )
                m6.metric(
                    "متوسط الإتقان البعدي",
                    f"{followup_avg:.1f}%" if followup_avg is not None else "لا توجد بيانات"
                )

                if baseline_avg is not None and followup_avg is not None:
                    st.caption(
                        "تنبيه: متوسطا القبلي والبعدي قد يعتمدان على سجلات مختلفة؛ "
                        "لا يُعد الفرق بينهما مقياسًا مؤكدًا للتحسن الفردي."
                    )

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

                baseline_rows = (
                    comparison_source[
                        comparison_source["type_norm"].isin(["baseline", "قبلي"])
                    ]
                    .sort_values("created_at")
                    .drop_duplicates(
                        ["student_code", "skill"], keep="last"
                    )
                    [["student_code", "skill", "mastery_pct"]]
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
                        ["student_code", "skill"], keep="last"
                    )
                    [["student_code", "skill", "mastery_pct"]]
                    .rename(columns={"mastery_pct": "البعدي (%)"})
                )

                comparison = baseline_rows.merge(
                    followup_rows,
                    on=["student_code", "skill"],
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
                if not key:
                    st.info("أضف OPENAI_API_KEY إلى Streamlit Secrets لتفعيل التحليل الذكي.")
                elif st.button("✨ إنشاء تحليل ذكي للمؤشرات الحالية", key="run_achievement_analysis", use_container_width=True):
                    try:
                        aggregate_for_ai = skill_summary[["skill", "assessment_type", "متوسط_الإتقان", "عدد_السجلات"]].copy()
                        aggregate_for_ai["متوسط_الإتقان"] = aggregate_for_ai["متوسط_الإتقان"].round(1)
                        aggregate_json = json.dumps(aggregate_for_ai.to_dict(orient="records"), ensure_ascii=False)
                        with st.spinner("يحلل مُعين المؤشرات المجمعة..."):
                            st.session_state["mueen_achievement_analysis"] = create_achievement_analysis(
                                model, aggregate_json, threshold, language
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

                        # إنشاء تقرير HTML قابل للتنزيل والطباعة إلى PDF
                        safe_skills = []
                        for _, row in report_skills.sort_values(
                            "متوسط_الإتقان"
                        ).iterrows():
                            safe_skills.append(
                                "<tr><td>"
                                + html.escape(str(row["skill"]))
                                + "</td><td>"
                                + f"{row['متوسط_الإتقان']:.1f}%"
                                + "</td><td>"
                                + str(int(row["عدد_السجلات"]))
                                + "</td></tr>"
                            )

                        report_html = (
                            "<!DOCTYPE html><html lang='ar' dir='rtl'><head>"
                            "<meta charset='utf-8'>"
                            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                            "<title>التقرير التنفيذي - MUEEN AI</title>"
                            "<style>"
                            "body{font-family:Arial,sans-serif;margin:36px;line-height:1.8;color:#222}"
                            "h1,h2{color:#174a6e}table{border-collapse:collapse;width:100%}"
                            "th,td{border:1px solid #ccc;padding:9px;text-align:right}"
                            "th{background:#eef3f7}.metric{padding:12px;background:#f5f7f9;"
                            "margin:12px 0;border-radius:8px}"
                            "@media print{body{margin:15mm}}"
                            "</style></head><body>"
                            "<h1>التقرير التنفيذي الذكي لمدير المدرسة</h1>"
                            "<p>منصة MUEEN AI - مُعين</p>"
                            "<div class='metric'><b>متوسط الإتقان العام:</b> "
                            + f"{report_avg:.1f}%"
                            + "<br><b>حد الإتقان المستهدف:</b> "
                            + f"{threshold}%"
                            + "<br><b>عدد المهارات دون الحد:</b> "
                            + str(len(report_weak))
                            + "</div><h2>نتائج المهارات</h2>"
                            "<table><thead><tr><th>المهارة</th>"
                            "<th>متوسط الإتقان</th><th>عدد السجلات</th>"
                            "</tr></thead><tbody>"
                            + "".join(safe_skills)
                            + "</tbody></table><h2>التوصية التنفيذية</h2>"
                            "<p>توجيه الدعم التعليمي إلى المهارات الأقل إتقانًا، "
                            "وتنفيذ أنشطة علاجية مناسبة، ثم متابعة النتائج "
                            "بتقييم لاحق. تُراجع النتائج من قبل المعلم والإدارة "
                            "قبل اتخاذ القرارات.</p>"
                            "<p>هذا التقرير مبني على البيانات والفلاتر الحالية "
                            "ولا يثبت وحده العلاقة السببية بين التدخل والتحسن.</p>"
                            "</body></html>"
                        )

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
