"""MUEEN V7.1 staging school cycles: analysis, persistence, teacher approval, memory."""
import hashlib
import json
from datetime import datetime, timezone
import pandas as pd
import streamlit as st
from mueen_school_pilot import analyze, normalize

STRATEGIES = (
    'تمثيل بصري للمعطيات وخريطة حل مع تبرير الخطوات',
    'تحليل خطأ نموذجي ومقارنة حلين مع تغذية راجعة',
    'أمثلة متدرجة مع سحب الدعم ثم تقييم مستقل',
    'تعليم الأقران واسترجاع نشط ثم اختبار احتفاظ',
)

def decide(summary, paired, prior, threshold):
    result = []
    for _, r in summary.iterrows():
        skill = str(r['المهارة'])
        score = float(r['البعدي %'])
        history = [x for x in prior if x.get('skill') == skill]
        used = [x.get('strategy', '') for x in history]
        if score >= threshold:
            proposed = 'تثبيت وإثراء وتقييم احتفاظ مستقل'
            reason = 'بلغ متوسط المهارة حد الإتقان؛ تحقق من أداء الأفراد قبل إغلاق الدعم.'
        else:
            stagnated = int(r['عدد بلا تحسن'])
            options = STRATEGIES if stagnated else (STRATEGIES[2], STRATEGIES[3], STRATEGIES[0], STRATEGIES[1])
            proposed = next((s for s in options if s not in used), options[len(history) % len(options)])
            reason = ('أداء دون حد الإتقان مع حالات ثبات أو تراجع؛ نغيّر أسلوب التدريس.' if stagnated else
                      'تحسن جزئي دون بلوغ حد الإتقان؛ يلزم دعم متدرج وإعادة قياس.')
        result.append({'skill': skill, 'baseline_pct': float(r['القبلي %']),
                       'followup_pct': score, 'delta_pp': float(r['التغير (نقطة)']),
                       'stagnant_count': int(r['عدد بلا تحسن']),
                       'priority': 'support' if score < threshold else 'maintain',
                       'strategy': proposed, 'reason': reason,
                       'prior_cycles_consulted': len(history)})
    return result

def make_report(subject, grade, threshold, old_strategy, notes, before, after, history, parent_cycle=None):
    paired, summary = analyze(before, after, threshold)
    prior = [d for c in history for d in (c.get('report') or {}).get('decisions', [])]
    decisions = decide(summary, paired, prior, threshold)
    report = {'schema_version': 2, 'subject': subject.strip(), 'grade': int(grade),
              'threshold': int(threshold), 'previous_intervention': old_strategy.strip(),
              'execution_notes': notes.strip(), 'skill_summary': summary.to_dict('records'),
              'decisions': decisions, 'students_count': int(paired['Student'].nunique()),
              'prior_saved_cycles': len(history),
              'parent_cycle_id': str(parent_cycle['id']) if parent_cycle else None,
              'assessment_stage': 'followup_next' if parent_cycle else 'initial',
              'limitations': 'درجات اختبارين لا تثبت السببية؛ يلزم اعتماد المعلم وتقييم متابعة مستقل.'}
    def rows(df):
        clean = normalize(df, 'التقييم')
        return sorted([{'Student': str(r['Student']), 'Skill': str(r['Skill']),
                        'Score': float(r['Score']), 'MaxScore': float(r['MaxScore'])}
                       for _, r in clean.iterrows()], key=lambda x: (x['Student'], x['Skill']))
    raw = json.dumps({'school_subject': subject.strip(), 'grade': int(grade),
                      'before': rows(before), 'after': rows(after)}, sort_keys=True, ensure_ascii=False)
    return report, hashlib.sha256(raw.encode('utf-8')).hexdigest(), paired

def render_school_agent(get_client, get_school, get_user):
    st.markdown('## 🏫 مُعين AI — دورة التدخل المدرسي V7.1')
    st.caption('تحليل قبلي/بعدي، ذاكرة دورات معتمدة، حفظ مسودة، واعتماد بشري. لا تنفيذ آلي للتدخل.')
    client = get_client()
    if client is None:
        st.error('سجّل الدخول أولًا.'); return
    try:
        school, user = str(get_school()), str(get_user(client))
        membership = (client.table('school_memberships').select('role,is_active')
                      .eq('school_id', school).eq('user_id', user).eq('is_active', True)
                      .limit(1).execute().data or [])
        if not membership:
            st.error('ليس لديك عضوية نشطة في المدرسة المحددة.'); return
        role = str(membership[0]['role']).lower()
        cycles = (client.table('mueen_school_cycles')
                  .select('id,report,status,created_at,created_by,approved_at,evidence_fingerprint')
                  .eq('school_id', school).order('created_at', desc=True).limit(100).execute().data or [])
    except Exception as exc:
        st.error('تعذر قراءة ذاكرة الوكيل: ' + str(exc)[:350]); return
    st.metric('الدورات المحفوظة للمدرسة', len(cycles))
    with st.expander('📚 الدورات المحفوظة والاعتماد', expanded=False):
        for c in cycles[:30]:
            rep = c.get('report') or {}
            st.write(f"{c['created_at']} | {rep.get('subject','')} | الصف {rep.get('grade','')} | {c['status']} | {c['id']}")
            if c['status'] == 'draft' and str(c['created_by']) == user and role in ('teacher', 'coordinator', 'principal'):
                confirmed = st.checkbox('راجعت نتائج هذه الدورة وأوافق على اعتماد توصياتها', key='confirm_' + str(c['id']))
                if st.button('✅ اعتماد الدورة', key='approve_' + str(c['id']), disabled=not confirmed):
                    try:
                        updated = (client.table('mueen_school_cycles')
                                   .update({'status': 'approved', 'approved_at': datetime.now(timezone.utc).isoformat()})
                                   .eq('id', c['id']).eq('school_id', school).eq('created_by', user)
                                   .eq('status', 'draft').execute().data or [])
                        if not updated: raise RuntimeError('لم يُعتمد السجل؛ تحقق من الصلاحيات والحالة')
                        st.success('تم اعتماد الدورة'); st.rerun()
                    except Exception as exc: st.error('تعذر الاعتماد: ' + str(exc)[:300])
    approved_cycles = [c for c in cycles if c['status'] == 'approved']
    with st.form('mueen_real_school_cycle'):
        subject = st.text_input('المادة الدراسية', value='الرياضيات')
        grade = st.selectbox('الصف', list(range(5, 13)), index=2)
        threshold = st.number_input('حد الإتقان %', min_value=1, max_value=100, value=80)
        old = st.text_area('التدخل السابق المنفذ فعليًا')
        notes = st.text_area('ملاحظات تنفيذ مؤكدة (دون أسماء طلاب)')
        b = st.file_uploader('التقييم القبلي CSV', type='csv', key='agent_baseline')
        a = st.file_uploader('التقييم البعدي CSV', type='csv', key='agent_followup')
        mode = st.radio('نوع الدورة', ['تقييم أولي مستقل', 'متابعة جديدة لدورة معتمدة'])
        run = st.form_submit_button('🧠 تحليل الدورة وإعداد توصيات الوكيل', use_container_width=True)
    st.caption('أعمدة الملفين: Student, Skill, Score, MaxScore. استخدم رموزًا تجريبية أو مستعارة فقط.')
    if run:
        try:
            if not subject.strip(): raise ValueError('المادة مطلوبة')
            if b is None or a is None: raise ValueError('ارفع ملفي التقييم')
            before = pd.read_csv(b, dtype={'Student': 'string', 'Skill': 'string'})
            after = pd.read_csv(a, dtype={'Student': 'string', 'Skill': 'string'})
            history = [c for c in approved_cycles if (c.get('report') or {}).get('subject') == subject.strip()
                       and (c.get('report') or {}).get('grade') == int(grade)]
            parent = history[0] if mode.startswith('متابعة') and history else None
            if mode.startswith('متابعة') and parent is None:
                raise ValueError('لا توجد دورة معتمدة للمادة والصف المحددين؛ أنشئ دورة أولية أولًا')
            report, fingerprint, paired = make_report(subject, grade, threshold, old, notes,
                                                       before, after, history, parent)
            st.session_state['mueen_v71_preview'] = {'school': school, 'user': user,
                'report': report, 'fingerprint': fingerprint,
                'paired': paired[['Student', 'Skill', 'pct_before', 'pct_after', 'delta']].to_dict('records')}
        except Exception as exc:
            st.session_state.pop('mueen_v71_preview', None)
            st.error('تعذر التحليل: ' + str(exc)[:400])
    preview = st.session_state.get('mueen_v71_preview')
    if not preview or preview['school'] != school or preview['user'] != user: return
    report = preview['report']
    st.subheader('📊 مقارنة المهارات')
    st.dataframe(pd.DataFrame(report['skill_summary']), use_container_width=True, hide_index=True)
    st.subheader('🧠 قرارات الوكيل المقترحة')
    for d in report['decisions']:
        st.markdown(f"**{d['skill']}** — {d['followup_pct']:.1f}%، التغير {d['delta_pp']:+.1f} نقطة")
        st.write(d['strategy'] + ' — ' + d['reason'])
    st.warning('المقارنة لا تثبت السببية، والقرار يحتاج مراجعة المعلم. لا تحفظ بيانات طالب حقيقي في تجربة Staging.')
    if role not in ('teacher', 'coordinator', 'principal'):
        st.info('حفظ المسودات يتطلب دور المعلم أو المنسق أو المدير.'); return
    if st.button('💾 حفظ دورة كمسودة للمراجعة', use_container_width=True, key='save_v71'):
        try:
            existing = (client.table('mueen_school_cycles').select('id').eq('school_id', school)
                        .eq('created_by', user).eq('evidence_fingerprint', preview['fingerprint'])
                        .limit(1).execute().data or [])
            if existing: raise ValueError('هذه البيانات محفوظة مسبقًا في دورة: ' + str(existing[0]['id']))
            payload = {'school_id': school, 'created_by': user, 'report': report,
                       'status': 'draft', 'evidence_fingerprint': preview['fingerprint']}
            saved = client.table('mueen_school_cycles').insert(payload).execute().data or []
            if not saved: raise RuntimeError('لم يُرجع Supabase سجلًا محفوظًا')
            st.session_state.pop('mueen_v71_preview', None)
            st.success('حُفظت المسودة؛ افتح ذاكرة الدورات لاعتمادها.'); st.rerun()
        except Exception as exc: st.error('تعذر الحفظ: ' + str(exc)[:350])
