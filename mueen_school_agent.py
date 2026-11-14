"""MUEEN school agent: authenticated, persistent, teacher-reviewed school cycles."""
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
    result=[]
    for _,r in summary.iterrows():
        skill=str(r['المهارة']); score=float(r['البعدي %'])
        history=[x for x in prior if x.get('skill')==skill]
        used=[x.get('strategy','') for x in history]
        if score>=threshold:
            proposed='تثبيت وإثراء وتقييم احتفاظ مستقل'
            reason='بلغ متوسط المهارة حد الإتقان؛ تحقق من أداء الأفراد قبل إغلاق الدعم.'
        else:
            stagnated=int(r['عدد بلا تحسن'])
            # Choose a different evidence-aligned modality than the last recorded choice.
            options=STRATEGIES if stagnated else (STRATEGIES[2],STRATEGIES[3],STRATEGIES[0],STRATEGIES[1])
            proposed=next((s for s in options if s not in used), options[len(history)%len(options)])
            reason=('أداء دون حد الإتقان مع حالات ثبات أو تراجع؛ نغيّر أسلوب التدريس.' if stagnated else
                    'تحسن جزئي دون بلوغ حد الإتقان؛ يلزم دعم متدرج وإعادة قياس.')
        affected=paired[(paired['Skill']==skill)&(paired['pct_after']<threshold)]
        result.append({'skill':skill,'baseline_pct':float(r['القبلي %']),'followup_pct':score,
            'delta_pp':float(r['التغير (نقطة)']),'stagnant_count':int(r['عدد بلا تحسن']),
            'priority':'support' if score<threshold else 'maintain','strategy':proposed,
            'reason':reason,'student_codes_for_teacher':[str(s) for s in affected['Student'].tolist()],
            'prior_cycles_consulted':len(history)})
    return result

def make_report(subject,grade,threshold,old_strategy,notes,before,after,history,parent_cycle=None):
    paired,summary=analyze(before,after,threshold)
    prior=[d for c in history for d in (c.get('report') or {}).get('decisions',[])]
    decisions=decide(summary,paired,prior,threshold)
    # Store aggregate results and provenance, not individual assessment rows.
    report={'schema_version':1,'subject':subject.strip(),'grade':int(grade),'threshold':int(threshold),
        'previous_intervention':old_strategy.strip(),'execution_notes':notes.strip(),
        'skill_summary':summary.to_dict('records'),'decisions':decisions,
        'students_count':int(paired['Student'].nunique()),
        'prior_saved_cycles':len(history),
        'parent_cycle_id':str(parent_cycle['id']) if parent_cycle else None,
        'assessment_stage':'followup_next' if parent_cycle else 'initial',
        'limitations':'درجات اختبارين لا تثبت السببية أو أسباب الأخطاء. يلزم اعتماد المعلم وتقييم متابعة مستقل.'}
    # Stable evidence identity: independent of teacher notes and model decisions.
    def evidence_rows(df):
        clean = normalize(df, 'التقييم')
        return sorted([{'Student':str(r['Student']), 'Skill':str(r['Skill']),
                        'Score':float(r['Score']), 'MaxScore':float(r['MaxScore'])}
                       for _,r in clean.iterrows()], key=lambda x:(x['Student'],x['Skill']))
    raw=json.dumps({'subject':subject.strip(),'grade':int(grade),
                    'before':evidence_rows(before),'after':evidence_rows(after)},
                   sort_keys=True,ensure_ascii=False)
    fingerprint=hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return report,fingerprint

def render_school_agent(get_client,get_school,get_user):
    st.markdown('## 🏫 مُعين AI — مساحة عمل المعلم الفعلية')
    st.caption('حفظ دائم في Supabase، ذاكرة للدورات السابقة، وموافقة المعلم؛ لا تنفيذ آلي للتدخل.')
    client=get_client()
    if client is None:
        st.error('سجّل الدخول أولًا.');return
    try:
        school=str(get_school()); user=str(get_user(client))
        membership=(client.table('school_memberships').select('role,is_active')
            .eq('school_id',school).eq('user_id',user).eq('is_active',True).limit(1).execute().data or [])
        if not membership: st.error('ليس لديك عضوية نشطة في المدرسة المحددة.');return
        role=str(membership[0]['role']).lower()
        cycles=(client.table('mueen_school_cycles').select('id,report,status,created_at,created_by,approved_at')
            .eq('school_id',school).order('created_at',desc=True).limit(100).execute().data or [])
    except Exception as exc:
        st.error('تعذر قراءة ذاكرة الوكيل. شغّل ملف SQL المرفق أولًا، ثم راجع صلاحيات RLS. '+str(exc)[:200]);return
    st.metric('الدورات المحفوظة للمدرسة',len(cycles))
    with st.expander('📚 ذاكرة الوكيل — الدورات المحفوظة',expanded=False):
        for c in cycles[:20]:
            rep=c.get('report') or {}
            st.write(f"{c['created_at']} | {rep.get('subject','')} | الصف {rep.get('grade','')} | {c['status']} | {c['id']}")
    with st.form('mueen_real_school_cycle'):
        subject=st.text_input('المادة (أي مادة)',value='الرياضيات')
        grade=st.selectbox('الصف',list(range(5,13)),index=2)
        threshold=st.number_input('حد الإتقان',1,100,80)
        old=st.text_area('التدخل السابق الذي نُفذ فعلًا')
        notes=st.text_area('ملاحظات التنفيذ المؤكدة؛ لا تخترع ملاحظات')
        b=st.file_uploader('التقييم القبلي CSV',type='csv',key='agent_baseline')
        a=st.file_uploader('التقييم البعدي CSV',type='csv',key='agent_followup')
        # The selection is rebuilt for the selected subject/grade on submission.
        link_mode=st.radio('نوع الدورة', ['تقييم أولي مستقل','متابعة جديدة لدورة معتمدة'],
                           index=1 if cycles else 0)
