"""MUEEN AI V7.3: read-only, school-scoped agent evidence panel."""
import streamlit as st
import pandas as pd

def _num(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def render_agent_intelligence_center(get_client, get_school):
    st.markdown("### 🧠 مركز ذكاء مُعين | Agent Intelligence Center")
    st.caption("أدلة مستمدة من دورات المدرسة المحفوظة؛ لا يتم إنشاء أو تعديل أي سجلات.")
    client = get_client()
    if client is None:
        st.info("لا توجد جلسة موثقة لعرض أدلة الوكيل.")
        return
    try:
        school_id = get_school()
        cycles = (client.table("mueen_school_cycles")
                  .select("id,status,created_at,approved_at,report")
                  .eq("school_id", school_id)
                  .order("created_at", desc=True).limit(100).execute().data or [])
    except Exception:
        st.warning("تعذر قراءة دورات الوكيل. تحقق من صلاحيات القراءة والاتصال بقاعدة البيانات.")
        return

    approved = [c for c in cycles if c.get("status") == "approved"]
    reports = [c for c in approved if isinstance(c.get("report"), dict)]
    decision_total = sum(len(c["report"].get("decisions") or [])
                         for c in reports if isinstance(c["report"].get("decisions"), list))
    linked = [c for c in reports if c["report"].get("parent_cycle_id")]
    consulted = sum(1 for c in reports if any(
        (_num(d.get("prior_cycles_consulted")) or 0) > 0
        for d in (c["report"].get("decisions") or [])
        if isinstance(d, dict)))
    c1,c2,c3,c4=st.columns(4)
    c1.metric("الدورات المعتمدة",len(approved))
    c2.metric("القرارات المحفوظة",decision_total)
    c3.metric("دورات مرتبطة بسابقتها",len(linked))
    c4.metric("تقارير تشير لاستشارة ذاكرة",consulted)
    st.caption("العدادات تشمل أحدث 100 دورة في المدرسة فقط؛ الإشارة لاستشارة الذاكرة لا تثبت وحدها أثر التكيف.")

    if not reports:
        st.info("لا توجد دورات معتمدة قابلة للعرض حاليًا.")
        return
    options = {str(i): c for i,c in enumerate(reports)}
    def title(i):
        c=options[i]; r=c["report"]
        return f"{r.get('subject','مادة غير محددة')} · الصف {r.get('grade','—')} · {str(c.get('created_at',''))[:10]}"
    choice=st.selectbox("اختر دورة معتمدة لعرض أدلتها",options=list(options),format_func=title,
                        key="mueen_intelligence_selected")
    selected=options[choice]
    report=selected["report"]
    st.caption(f"تاريخ الحفظ: {str(selected.get('created_at',''))[:19]} · حالة الدورة: معتمدة")
    skills=report.get("skill_summary") or []
    if isinstance(skills,list) and skills:
        st.markdown("**نتائج المهارات المحفوظة**")
        safe_skills=[]
        for item in skills:
            if isinstance(item,dict):
                safe_skills.append({k:item.get(k) for k in
                    ("المهارة","القبلي %","البعدي %","التغير (نقطة)","أقل من الهدف")
                    if k in item})
        if safe_skills:
            st.dataframe(pd.DataFrame(safe_skills),hide_index=True,use_container_width=True)
    decisions=report.get("decisions") or []
    if isinstance(decisions,list) and decisions:
        st.markdown("**أدلة القرارات التعليمية**")
        rows=[]
        for d in decisions:
            if not isinstance(d,dict): continue
            rows.append({
                "المهارة":d.get("skill","—"),
                "الأولوية":d.get("priority","—"),
                "الاستراتيجية":d.get("strategy","—"),
                "سبب القرار":d.get("reason","—"),
                "دورات سابقة مستشارة":d.get("prior_cycles_consulted",0),
            })
        if rows: st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    st.markdown("**مؤشرات الذاكرة والتكيف**")
    prev=report.get("previous_intervention")
    parent=report.get("parent_cycle_id")
    prior=report.get("prior_saved_cycles",0)
    st.write(f"التدخل السابق: {str(prev)[:350] if prev else 'غير مسجل'}")
    st.write(f"عدد الدورات السابقة المذكورة في التقرير: {prior}")
    st.write("الارتباط بدورة سابقة: " + ("موجود" if parent else "غير مسجل"))
    if not parent and not consulted:
        st.info("هذه البيانات لا تثبت بمفردها استخدام ذاكرة تكيفية؛ يلزم الرجوع إلى أدلة دورات مترابطة عند توفرها.")
    st.caption("البيانات التجريبية لا تمثل أثرًا تعليميًا ميدانيًا مثبتًا. راجع القرارات قبل التطبيق.")
