"""Approved-cycle executive view. Reads only school-scoped Supabase rows."""
import html
import json
import math
import pandas as pd
import streamlit as st


def _skills(report):
    rows = {}
    for item in report.get('skill_summary', []):
        try:
            name = str(item['المهارة']).strip()
            before, after = float(item['القبلي %']), float(item['البعدي %'])
            if not name or not all(math.isfinite(x) and 0 <= x <= 100 for x in (before, after)):
                return {}
            if name in rows:
                return {}
            rows[name] = (before, after)
        except (ValueError, TypeError, KeyError):
            return {}
    return rows


def _signature(report):
    return (str(report.get('subject', '')).strip(), str(report.get('grade', '')),
            json.dumps(_skills(report), ensure_ascii=False, sort_keys=True))


def _table_html(rows):
    if not rows:
        return '<p>لا توجد بيانات.</p>'
    cols = list(rows[0])
    header = ''.join('<th>' + html.escape(str(k)) + '</th>' for k in cols)
    body = ''.join('<tr>' + ''.join('<td>' + html.escape(str(r.get(k, ''))) + '</td>' for k in cols) + '</tr>' for r in rows)
    return '<table><thead><tr>' + header + '</tr></thead><tbody>' + body + '</tbody></table>'


def render_executive_report(get_client, get_school, get_user, school_name):
    st.markdown('## 🏫 التقرير التنفيذي الموحد لمدير المدرسة')
    st.caption('المصدر الرسمي: دورات مُعين المعتمدة في المدرسة النشطة. لا تُضم السجلات التجريبية القديمة إلى المؤشرات.')
    try:
        client = get_client()
        if client is None:
            raise ValueError('جلسة Supabase غير متاحة')
        school = str(get_school())
        user = str(get_user(client))
        memberships = (client.table('school_memberships').select('role').eq('school_id', school)
                       .eq('user_id', user).eq('is_active', True).limit(1).execute().data or [])
        if not memberships:
            st.error('لا توجد عضوية نشطة في المدرسة المختارة.'); return
        cycles = (client.table('mueen_school_cycles')
                  .select('id,school_id,status,created_at,approved_at,report')
                  .eq('school_id', school).eq('status', 'approved')
                  .order('created_at', desc=False).limit(500).execute().data or [])
    except Exception as exc:
        st.error('تعذر قراءة الدورات المعتمدة. تحقق من صلاحيات القراءة وسياسات RLS.')
        st.caption(type(exc).__name__)
        return

    valid = [c for c in cycles if isinstance(c.get('report'), dict) and _skills(c['report'])]
    if not valid:
        st.info('لا توجد دورات معتمدة ذات نتائج مهارات صالحة لهذه المدرسة.'); return
    options = sorted({(str(c['report'].get('subject', '')).strip(), str(c['report'].get('grade', ''))) for c in valid})
    selected = st.selectbox('نطاق التقرير: المادة والصف', options,
                            format_func=lambda x: f'{x[0]} — الصف {x[1]}', key='mueen_exec_scope')
    scoped = [c for c in valid if (str(c['report'].get('subject', '')).strip(), str(c['report'].get('grade', ''))) == selected]
    distinct = []
    signatures = set()
    canonical_by_signature = {}
    for c in scoped:
        sig = _signature(c['report'])
        if sig not in signatures:
            signatures.add(sig)
            distinct.append(c)
            canonical_by_signature[sig] = c
    st.caption(f'الدورات المعتمدة في النطاق: {len(scoped)}؛ مجموعات نتائج مختلفة: {len(distinct)}. التطابق لا يثبت تكرار بيانات الأفراد، لكنه يمنع العد المزدوج في الملخص.')

    by_id = {str(c['id']): c for c in distinct}
    # A follow-up is a verified stage only if it links to an approved prior cycle
    # and its baseline equals the prior cycle's follow-up for each skill.
    verified_edges = {}
    for c in distinct:
        rep = c['report']
        original_parent = next((x for x in scoped if str(x['id']) == str(rep.get('parent_cycle_id') or '')), None)
        parent = canonical_by_signature.get(_signature(original_parent['report'])) if original_parent else None
        if not parent:
            continue
        a, b = _skills(parent['report']), _skills(rep)
        if (a.keys() == b.keys() and
            all(abs(a[k][1] - b[k][0]) <= 0.02 for k in a) and
            int(parent['report'].get('students_count') or 0) == int(rep.get('students_count') or 0)):
            verified_edges[str(c['id'])] = str(parent['id'])

    latest = distinct[-1]
    lineage = [latest]
    seen = {str(latest['id'])}
    while str(lineage[-1]['id']) in verified_edges:
        parent_id = verified_edges[str(lineage[-1]['id'])]
        if parent_id in seen:
            break
        lineage.append(by_id[parent_id]); seen.add(parent_id)
    lineage.reverse()
    # If newest approved cycle is not linked, prefer a longer verified chain.
    for tip in distinct:
        chain = [tip]; visited = {str(tip['id'])}
        while str(chain[-1]['id']) in verified_edges:
            pid = verified_edges[str(chain[-1]['id'])]
            if pid in visited: break
            chain.append(by_id[pid]); visited.add(pid)
        chain.reverse()
        if len(chain) > len(lineage) or (len(chain) == len(lineage) and str(chain[-1].get('approved_at') or '') > str(lineage[-1].get('approved_at') or '')):
            lineage = chain

    def mean(vals): return round(sum(vals) / len(vals), 2)
    initial = _skills(lineage[0]['report'])
    current = _skills(lineage[-1]['report'])
    initial_before = mean([v[0] for v in initial.values()])
    first_after = mean([v[1] for v in initial.values()])
    current_after = mean([v[1] for v in current.values()])
    st.markdown(f'**{school_name}** — {selected[0]} — الصف {selected[1]}')
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('الطلاب وفق التقرير', str(lineage[-1]['report'].get('students_count', '—')))
    c2.metric('المهارات', len(current))
    c3.metric('قبلي أول دورة معتمدة', f'{initial_before:.2f}%')
    c4.metric('آخر بعدي معتمد', f'{current_after:.2f}%', delta=f'{current_after - initial_before:+.2f} نقطة')
    if len(lineage) == 1:
        st.info('المحفوظ حاليًا مرحلة تقييم معتمدة واحدة فقط. لا توجد متابعة ثانية موثقة ومرتبطة بها بعد.')
    else:
        st.success(f'تم التحقق من ارتباط {len(lineage)} مراحل تقييم معتمدة، مع تطابق متوسطات المهارات بين كل بعدي وقبلي تالٍ.')

    stages = [{'المرحلة': 'القبلي الأول', 'الإتقان %': initial_before}]
    for i, c in enumerate(lineage, 1):
        stages.append({'المرحلة': f'البعدي {i}', 'الإتقان %': mean([x[1] for x in _skills(c['report']).values()])})
    st.markdown('### تطور الإتقان المعتمد')
    st.dataframe(pd.DataFrame(stages), use_container_width=True, hide_index=True)
    rows = []
    threshold = float(lineage[-1]['report'].get('threshold') or 80)
    for skill, (before, _) in initial.items():
        if skill not in current: continue
        after = current[skill][1]
        rows.append({'المهارة': skill, 'القبلي الأول %': before, 'آخر بعدي معتمد %': after,
                     'التغير (نقطة)': round(after - before, 2),
                     'الأولوية': 'دعم ومتابعة' if after < threshold else 'تثبيت وإثراء'})
    st.markdown('### المهارات والأولويات')
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    decisions = lineage[-1]['report'].get('decisions') or []
    recommendations = []
    for d in decisions:
        if isinstance(d, dict):
            recommendations.append({'المهارة': str(d.get('skill') or ''),
                                    'الاستراتيجية المقترحة': str(d.get('strategy') or ''),
                                    'التبرير': str(d.get('reason') or '')})
    if recommendations:
        st.markdown('### توصيات الوكيل المعتمدة للمراجعة الإدارية')
        st.dataframe(pd.DataFrame(recommendations), hide_index=True, use_container_width=True)
    st.caption('المتوسطات متساوية الوزن بين المهارات كما وردت في تقارير الدورات؛ ليست متوسطات مرجحة بدرجات جميع الطلاب. لا تثبت النتائج السببية. التقييم المحلي غير المحفوظ لا يظهر.')
    st.caption('الاختيار الجانبي للمادة والصف يخص لوحة التحليل العامة؛ نطاق هذا التقرير يُحدد من قائمة المادة والصف أعلاه.')
    doc = ('<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>تقرير مُعين التنفيذي</title>'
           '<style>body{font-family:Tahoma,Arial;margin:25px;color:#10243a}table{border-collapse:collapse;width:100%;margin:16px 0}'
           'td,th{border:1px solid #ddd;padding:8px;text-align:right}th{background:#e6f3f4}</style></head><body>'
           '<h1>التقرير التنفيذي الموحد — مُعين AI</h1>'
           f'<p>{html.escape(str(school_name))} — {html.escape(selected[0])} — الصف {html.escape(selected[1])}</p>'
           f'<p>عدد الطلاب: {html.escape(str(lineage[-1]["report"].get("students_count", "—")))}؛ حد الإتقان: {threshold:g}%</p>'
           '<h2>مراحل الإتقان المعتمدة</h2>' + _table_html(stages)
           + '<h2>المهارات والأولويات</h2>' + _table_html(rows)
           + '<h2>توصيات المعلم والوكيل</h2>' + _table_html(recommendations)
           + '<p>المتوسطات متساوية الوزن بين المهارات، ولا تثبت السببية. تُعرض المراحل المرتبطة فقط.</p>'
           + '</body></html>')
    st.download_button('📄 تنزيل التقرير التنفيذي الموحد HTML', doc.encode('utf-8'),
                       file_name='MUEEN_Executive_Approved.html', mime='text/html', key='mueen_unified_exec_html')
    with st.expander('📂 سجل الدورات المعتمدة والقيود', expanded=False):
        st.dataframe(pd.DataFrame([{'المعرف': str(c['id']), 'تاريخ الاعتماد': str(c.get('approved_at') or ''),
                                   'الارتباط بالسابقة': str(c['report'].get('parent_cycle_id') or '—')}
                                  for c in scoped]), hide_index=True, use_container_width=True)
        st.warning('الدورات المتطابقة تُعرض في سجل التدقيق، لكن لا تُجمع كتحسن مستقل. الدورات غير المرتبطة لا تُدمج في سلسلة التحسن.')
