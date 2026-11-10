"""MUEEN AI school pilot: subject-neutral, read-only, teacher-reviewed adaptation."""
import json
from datetime import datetime, timezone
import pandas as pd
import streamlit as st

REQUIRED = ('Student','Skill','Score','MaxScore')

def normalize(df, label):
    missing = set(REQUIRED)-set(df.columns)
    if missing: raise ValueError(f'{label}: أعمدة ناقصة: {sorted(missing)}')
    data = df[list(REQUIRED)].copy()
    data['Student'] = data['Student'].astype('string').str.strip()
    data['Skill'] = data['Skill'].astype('string').str.strip()
    if data[['Student','Skill']].isna().any().any() or (data[['Student','Skill']]=='').any().any():
        raise ValueError(f'{label}: رمز الطالب والمهارة مطلوبان')
    for c in ('Score','MaxScore'):
        data[c]=pd.to_numeric(data[c],errors='coerce')
    if data[['Score','MaxScore']].isna().any().any() or (data['MaxScore']<=0).any() or (data['Score']<0).any() or (data['Score']>data['MaxScore']).any():
        raise ValueError(f'{label}: درجات غير صالحة')
    if data.duplicated(['Student','Skill']).any():
        raise ValueError(f'{label}: تكرار طالب ومهارة؛ يجب تحديد تقييم واحد لكل دورة')
    data['pct']=data['Score']/data['MaxScore']*100
    return data

def analyze(before, after, threshold=80):
    b=normalize(before,'القبلي'); a=normalize(after,'البعدي الأول')
    joined=b.merge(a,on=['Student','Skill'],how='outer',suffixes=('_before','_after'),indicator=True,validate='one_to_one')
    if (joined['_merge']!='both').any():
        raise ValueError('المهارات والطلاب غير متطابقين بين الاختبارين؛ لا يجوز إسقاط سجلات بصمت')
    joined['delta']=joined['pct_after']-joined['pct_before']
    rows=[]
    for skill,group in joined.groupby('Skill',sort=True):
        prior=100*group['Score_before'].sum()/group['MaxScore_before'].sum()
        current=100*group['Score_after'].sum()/group['MaxScore_after'].sum()
        stagnant=int((group['delta']<=0).sum())
        rows.append({'المهارة':skill,'القبلي %':round(prior,2),'البعدي %':round(current,2),
                     'التغير (نقطة)':round(current-prior,2),'عدد بلا تحسن':stagnant,
                     'أقل من الهدف':current<threshold})
    summary=pd.DataFrame(rows).sort_values(['البعدي %','التغير (نقطة)']).reset_index(drop=True)
    joined['القرار الفردي']=joined.apply(lambda r: 'إثراء وتثبيت' if r['pct_after']>=threshold else ('تغيير الاستراتيجية والتحقق من الخطأ' if r['delta']<=0 else 'دعم موجه وإعادة قياس'),axis=1)
    return joined,summary

def strategy(row, subject):
    skill=str(row['المهارة'])
    if row['عدد بلا تحسن']:
        return f'تحليل أخطاء الطلبة غير المتحسنين في «{skill}»، ثم نموذج محلول وتدريب موجه بمثال جديد مناسب لمادة «{subject}»'
    return f'تدريب متدرج مع تغذية راجعة وتقييم مستقل لمهارة «{skill}» في «{subject}»'

def render_school_pilot():
    st.markdown('## 🏫 مُعين AI — تجربة المعلم لجميع المواد (V6.2 Preview)')
    st.info('هذه مساحة تحليل وقرار تكيفي أولي للمعلم. لا تكتب في Supabase، ولا تُرسل بيانات الطلبة إلى نموذج ذكاء اصطناعي.')
    with st.form('school_pilot_context'):
        subject=st.text_input('المادة الدراسية (أي مادة)',value='الرياضيات')
        grade=st.selectbox('الصف',list(range(5,13)),index=2)
        threshold=st.number_input('حد الإتقان %',min_value=1,max_value=100,value=80)
        old_strategy=st.text_area('وصف التدخل الأول المنفذ (لذاكرة القرار)',placeholder='ما الاستراتيجية التي نُفذت بالفعل؟')
        execution=st.text_area('ملاحظات التنفيذ الفعلية',placeholder='ما الذي لاحظه المعلم؟ وما الذي يحتاج إلى تحقق؟')
        bfile=st.file_uploader('ملف CSV للتقييم القبلي',type='csv',key='pilot_before')
        afile=st.file_uploader('ملف CSV للتقييم البعدي الأول',type='csv',key='pilot_after')
        run=st.form_submit_button('تحليل المهارات وإعداد التدخل الثاني',use_container_width=True)
    st.caption('الأعمدة المطلوبة في كل ملف: Student, Skill, Score, MaxScore. استخدم رموزًا مستعارة للطلبة، لا أسماءهم.')
    if run:
        try:
            if not subject.strip(): raise ValueError('أدخل اسم المادة')
            if bfile is None or afile is None: raise ValueError('ارفع الملفين أولًا')
            before=pd.read_csv(bfile,dtype={'Student':'string','Skill':'string'})
            after=pd.read_csv(afile,dtype={'Student':'string','Skill':'string'})
            paired,summary=analyze(before,after,threshold)
            st.session_state['pilot_report']={'subject':subject.strip(),'grade':grade,'threshold':threshold,
                'old_strategy':old_strategy,'execution':execution,'paired':paired,'summary':summary}
            st.session_state.pop('pilot_approved',None)
        except Exception as e: st.error(str(e))
    report=st.session_state.get('pilot_report')
    if not report:return
    summary=report['summary']; paired=report['paired']
    st.subheader('مقارنة المهارات')
    st.dataframe(summary,use_container_width=True,hide_index=True)
    st.subheader('الفروق الفردية: نفس الطالب ونفس المهارة')
    st.dataframe(paired[['Student','Skill','pct_before','pct_after','delta','القرار الفردي']].rename(columns={'pct_before':'قبلي %','pct_after':'بعدي %','delta':'التغير'}),use_container_width=True,hide_index=True)
    weak=summary[summary['أقل من الهدف']]
    if weak.empty:
        st.success('جميع متوسطات المهارات بلغت الحد المستهدف؛ يوصى بالإثراء واختبار الاحتفاظ.')
        priority=[]
    else:
        priority=[{'skill':r['المهارة'],'before_pct':r['القبلي %'],'after_pct':r['البعدي %'],
                   'delta_pp':r['التغير (نقطة)'],'stagnant_students':int(r['عدد بلا تحسن']),
                   'proposed_strategy':strategy(r,report['subject'])} for _,r in weak.iterrows()]
        st.subheader('قرار التكيف الثاني المقترح — يحتاج اعتماد المعلم')
        for i,item in enumerate(priority,1):
            st.markdown(f"**{i}. {item['skill']}** — {item['after_pct']}% بعدي؛ التغير {item['delta_pp']:+g} نقطة؛ {item['stagnant_students']} دون تحسن.  ")
            st.write(item['proposed_strategy'])
    st.warning('هذه توصية أولية مستندة إلى الدرجات فقط. لا تثبت سبب التعثر أو الأثر السببي للتدخل. راجع أوراق الطلبة وجودة الاختبار قبل الاعتماد.')
    teacher=st.text_input('اسم المعلم المراجع (للتقرير المحلي فقط)',key='pilot_teacher')
    approved=st.checkbox('راجعتُ النتائج والخطة، وأوافق على اعتمادها كتوصية للتطبيق',key='pilot_approve_checkbox')
    if st.button('اعتماد محلي للتقرير',disabled=not (approved and teacher.strip()),key='pilot_approve_btn'):
        st.session_state['pilot_approved']={'teacher':teacher.strip(),'at':datetime.now(timezone.utc).isoformat()}
    approval=st.session_state.get('pilot_approved')
    payload={'release':'V6.2-preview','source':'teacher-uploaded CSV','subject':report['subject'],'grade':report['grade'],
        'threshold_pct':report['threshold'],'previous_intervention':report['old_strategy'],
        'teacher_execution_notes':report['execution'],'skill_comparison':summary.to_dict('records'),
        'adaptive_decisions':priority,'review':approval or {'status':'pending'},
        'limitations':['read-only preview','not saved to Supabase','second posttest not yet conducted']}
    st.download_button('📥 تنزيل سجل القرار والأدلة JSON',json.dumps(payload,ensure_ascii=False,indent=2).encode('utf-8'),
        'MUEEN_School_Pilot_Decision.json',mime='application/json',key='pilot_download')
    st.caption('اعتماد محلي داخل جلسة Streamlit فقط؛ لا يُعد توقيعًا رسميًا أو سجل تدقيق محفوظًا في قاعدة البيانات.')
