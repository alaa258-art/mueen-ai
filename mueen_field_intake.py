"""MUEEN field-pilot intake: in-memory, read-only; no Supabase writes."""
import io
import re
import pandas as pd

PHASES = ('baseline', 'followup_1', 'followup_2')
COLUMNS = ['student_code', 'skill', 'assessment_type', 'score', 'max_score', 'assessed_at', 'intervention_id', 'teacher_approved']


def template_csv():
    rows = []
    for i in range(1, 9):
        rows.append(dict(student_code=f'FIELD-MATH-{i:02}', skill='ترتيب خطوات الحل',
                         assessment_type='baseline', score='', max_score=20,
                         assessed_at='', intervention_id='', teacher_approved=''))
    return pd.DataFrame(rows, columns=COLUMNS).to_csv(index=False).encode('utf-8-sig')


def validate(csv_bytes):
    errors, warnings = [], []
    if len(csv_bytes) > 1024 * 1024:
        return None, ['الملف أكبر من 1 ميغابايت.'], warnings
    try:
        df = pd.read_csv(io.BytesIO(csv_bytes), dtype=str, keep_default_na=False, encoding='utf-8-sig')
    except Exception as exc:
        return None, [f'تعذر قراءة CSV: {type(exc).__name__}'], warnings
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        return None, ['أعمدة مفقودة: ' + ', '.join(missing)], warnings
    if len(df) == 0 or len(df) > 30:
        errors.append('يجب أن يحتوي الملف على 1–30 سجلًا (حتى 10 طلبة × 3 تقييمات).')
    if any(x in df.columns for x in ('name', 'student_name', 'email', 'phone', 'national_id', 'emirates_id')):
        errors.append('يحتوي الملف على عمود بيانات شخصية؛ احذفه قبل الرفع.')
    for col in ('student_code', 'skill', 'assessment_type'):
        df[col] = df[col].astype(str).str.strip()
    if not df['student_code'].map(lambda x: bool(re.fullmatch(r'FIELD-[A-Z]+-[0-9]{2}', x))).all():
        errors.append('رموز الطلبة يجب أن تكون مثل FIELD-MATH-01 دون أسماء.')
    if df['student_code'].nunique() > 10:
        errors.append('الحد الأقصى 10 طلبة في التجربة.')
    if not df['assessment_type'].isin(PHASES).all():
        errors.append('نوع التقييم يجب أن يكون baseline أو followup_1 أو followup_2.')
    if df[['student_code','skill','assessment_type']].duplicated().any():
        errors.append('يوجد تقييم مكرر لنفس الطالب والمهارة والمرحلة.')
    for col in ('score','max_score'):
        df[col] = pd.to_numeric(df[col], errors='coerce')
    if df['score'].isna().any() or df['max_score'].isna().any():
        errors.append('يجب إدخال جميع الدرجات والدرجات العظمى كأرقام.')
    else:
        if (df['max_score'] != 20).any():
            errors.append('النموذج الحالي يعتمد درجة عظمى 20 لكل تقييم.')
        if ((df['score'] < 0) | (df['score'] > df['max_score'])).any():
            errors.append('توجد درجة خارج المجال 0–20.')
    dates = pd.to_datetime(df['assessed_at'], errors='coerce', utc=True)
    if dates.isna().any():
        errors.append('كل تقييم يحتاج تاريخًا صحيحًا بصيغة YYYY-MM-DD.')
    df['parsed_date'] = dates
    for (code, skill), group in df.groupby(['student_code','skill']):
        by_phase = {r['assessment_type']: r for _,r in group.iterrows()}
        for later, earlier in [('followup_1','baseline'), ('followup_2','followup_1')]:
            if later in by_phase and earlier not in by_phase:
                errors.append(f'{code}: {later} يحتاج {earlier} قبله.')
            if later in by_phase and earlier in by_phase:
                a, b = by_phase[earlier], by_phase[later]
                if pd.notna(a['parsed_date']) and pd.notna(b['parsed_date']) and b['parsed_date'] <= a['parsed_date']:
                    errors.append(f'{code}: ترتيب تواريخ التقييمات غير صحيح.')
        for phase in ('followup_1','followup_2'):
            if phase in by_phase:
                row = by_phase[phase]
                if not str(row['intervention_id']).strip():
                    errors.append(f'{code}: {phase} يحتاج رمز التدخل المنفذ.')
                if str(row['teacher_approved']).strip().lower() not in ('yes','true','1'):
                    errors.append(f'{code}: {phase} يحتاج توثيق موافقة المعلم (yes).')
        if len(by_phase) < 3:
            warnings.append(f'{code}: الدورة غير مكتملة بعد؛ التحليل جزئي.')
    if not errors:
        df['mastery_pct'] = df['score'] / df['max_score'] * 100
    return df, list(dict.fromkeys(errors)), list(dict.fromkeys(warnings))


def render():
    import streamlit as st
    st.markdown('### 🧪 وحدة التجربة الميدانية — استقبال النتائج الحقيقية')
    st.caption('مرحلة معاينة وتدقيق فقط: لا يتم حفظ أي سجل في Supabase، ولا تُرسل البيانات إلى نموذج ذكاء اصطناعي.')
    st.download_button('📄 تنزيل قالب CSV للطلبة الثمانية', template_csv(),
                       file_name='MUEEN_Field_Results_Template.csv', mime='text/csv', key='field_template')
    uploaded = st.file_uploader('رفع نتائج التجربة (CSV، رموز مستعارة فقط)', type=['csv'], key='field_upload')
    if uploaded is None:
        st.info('ابدأ بتعبئة التقييم القبلي في القالب. أضف صفًا مستقلًا لكل تقييم لاحق، بعد تنفيذ التدخل واعتماد المعلم.')
        return
    df, errors, warnings = validate(uploaded.getvalue())
    if errors:
        st.error('لا يمكن اعتماد الملف قبل تصحيح الأخطاء:')
        for item in errors: st.write('• ' + item)
        return
    for item in warnings: st.warning(item)
    st.success('اجتاز الملف فحوص الصيغة والاتساق الأساسية. لم يتم حفظه في قاعدة البيانات.')
    display = df[['student_code','skill','assessment_type','score','max_score','mastery_pct']].copy()
    st.dataframe(display, use_container_width=True, hide_index=True)
    summary = (df.groupby('assessment_type').agg(students=('student_code','nunique'),
                records=('student_code','size'), mean_pct=('mastery_pct','mean')).reset_index())
    st.dataframe(summary, use_container_width=True, hide_index=True)
    piv = df.pivot_table(index=['student_code','skill'],columns='assessment_type',values='mastery_pct',aggfunc='first').reset_index()
    for phase in PHASES:
        if phase not in piv.columns: piv[phase] = float('nan')
    piv['change_cycle_1_pp'] = piv['followup_1'] - piv['baseline']
    piv['change_cycle_2_pp'] = piv['followup_2'] - piv['followup_1']
    st.markdown('**التغير الفردي بالنقاط المئوية (لا تحسب الفروق للقياسات المفقودة)**')
    st.dataframe(piv, use_container_width=True, hide_index=True)
    st.download_button('📥 تنزيل تحليل المعاينة CSV', piv.to_csv(index=False).encode('utf-8-sig'),
                       file_name='MUEEN_Field_Preview.csv', mime='text/csv', key='field_preview')
    st.info('الخطوة اللاحقة: اعتماد سياسة الحفظ والصلاحيات وسجل الأدلة قبل تفعيل الكتابة إلى قاعدة البيانات.')
