'previous_intervention':old_strategy.strip(),'execution_notes':notes.strip(),
        'skill_summary':summary.to_dict('records'),'decisions':decisions,
        'decision_quality':evaluate_decisions(decisions,threshold),
        'tools_used':['normalize','analyze','decide','evaluate_decisions'],
        'students_count':int(paired['Student'].nunique()),
        'cohort_fingerprint': cohort_fingerprint(paired),
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
        st.error('تعذر قراءة ذاكرة الوكيل. تحقق من اتصال Supabase وسياسات RLS.');return
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
        previous_id=st.selectbox('الدورة السابقة (للمتابعة الجديدة)',
                                 options=['']+[str(c['id']) for c in cycles if c['status']=='approved'],
                                 format_func=lambda v: 'اختر دورة معتمدة' if not v else v,
                                 disabled=link_mode!='متابعة جديدة لدورة معتمدة')
        submitted=st.form_submit_button('تحليل وإعداد قرار جديد')
    if submitted:
        try:
            if not subject.strip(): raise ValueError('المادة مطلوبة')
            if link_mode=='متابعة جديدة لدورة معتمدة' and not old.strip():
                raise ValueError('وصف التدخل السابق مطلوب عند تسجيل متابعة')
            if b is None or a is None:raise ValueError('ارفع ملفي CSV')
            before=pd.read_csv(b,dtype={'Student':'string','Skill':'string'})
            after=pd.read_csv(a,dtype={'Student':'string','Skill':'string'})
            same=[c for c in cycles if (c.get('report') or {}).get('subject')==subject.strip() and (c.get('report') or {}).get('grade')==grade and c['status']=='approved']
            parent=None
            if link_mode=='متابعة جديدة لدورة معتمدة':
                parent=next((c for c in same if str(c['id'])==previous_id),None)
                if parent is None:
                    raise ValueError('اختر دورة سابقة معتمدة للمادة والصف نفسيهما.')
                prior_summary=(parent.get('report') or {}).get('skill_summary') or []
                prev={str(x['المهارة']):float(x['البعدي %']) for x in prior_summary}
                current_before=normalize(before,'قبلي المتابعة')
                skills=set(current_before['Skill'].astype(str))
                if skills!=set(prev):
                    raise ValueError('مهارات قبلي المتابعة لا تطابق مهارات البعدي للدورة السابقة.')
                # Compare using the same weighted-by-score approach as analyze().
                actual={str(k):round(100*g['Score'].sum()/g['MaxScore'].sum(),2)
                        for k,g in current_before.groupby('Skill')}
                if any(abs(actual[k]-prev[k])>0.02 for k in prev):
                    raise ValueError('ملف القبلي للمتابعة لا يطابق نتائج البعدي السابق. ارفع ملف البعدي الأول نفسه بوصفه قبلي المتابعة.')
                if current_before['Student'].nunique() != int(parent['report'].get('students_count') or 0):
                    raise ValueError('عدد الطلاب لا يطابق الدورة السابقة؛ يلزم توثيق اختلاف العينة قبل الربط.')
                previous_fingerprint = parent['report'].get('cohort_fingerprint')
                if not previous_fingerprint:
                    raise ValueError('الدورة السابقة لا تحتوي على بصمة المجموعة؛ لا يمكن ربطها تلقائيًا.')
                current_fingerprint = cohort_fingerprint(current_before)
                if current_fingerprint != previous_fingerprint:
                    raise ValueError('مجموعة الطلاب والمهارات لا تطابق الدورة السابقة.')

            report,hashval=make_report(subject,grade,threshold,old,notes,before,after,same,parent)
            # Do not save an identical pair of skill summaries as a new progress stage.
            new_summary=report['skill_summary']
            def skill_key(rows):
                return sorted((str(x['المهارة']),round(float(x['القبلي %']),2),round(float(x['البعدي %']),2)) for x in rows)
            if any(skill_key((c.get('report') or {}).get('skill_summary') or [])==skill_key(new_summary) for c in same):
                raise ValueError('نتائج المهارات مطابقة لدورة معتمدة سابقة؛ لا تُسجل كتدخل جديد.')
            st.session_state['mueen_agent_preview']={'school':school,'user':user,'report':report,'hash':hashval}
        except ValueError as exc: st.error('تعذر التحليل: '+str(exc)[:350])
        except Exception: st.error('حدث خطأ غير متوقع أثناء التحليل. راجع سجلات الخادم.')
    preview=st.session_state.get('mueen_agent_preview')
    if preview and preview['school']==school and preview['user']==user:
        report=preview['report']
        st.subheader('نتائج التحليل وقرارات الوكيل')
        st.dataframe(pd.DataFrame(report['skill_summary']),hide_index=True,use_container_width=True)
        st.dataframe(pd.DataFrame(report['decisions'])[['skill','followup_pct','strategy','reason','prior_cycles_consulted']],hide_index=True,use_container_width=True)
        st.warning(report['limitations'])
        st.info('المرحلة: '+('متابعة جديدة مرتبطة بدورة معتمدة' if report.get('parent_cycle_id') else 'تقييم أولي مستقل')+
                ' | هذه النتائج لم تُحفظ بعد. احفظها ثم اعتمدها من حساب المعلم.')
        if st.button('💾 حفظ القرار للمراجعة في قاعدة البيانات',key='agent_save'):
            try:
                existing=(client.table('mueen_school_cycles').select('id').eq('school_id',school)
                    .eq('evidence_hash',preview['hash']).limit(1).execute().data or [])
                if existing:st.warning('هذه الأدلة محفوظة بالفعل؛ لن ننشئ دورة مكررة.')
                else:
                    client.table('mueen_school_cycles').insert({'school_id':school,'created_by':user,
                        'evidence_hash':preview['hash'],'report':report,'status':'pending'}).execute()
                    st.success('حُفظ القرار مع سجل تدقيق.');st.session_state.pop('mueen_agent_preview',None)
                    st.rerun()
            except Exception: st.error('فشل الحفظ. تحقق من الاتصال والصلاحيات.')
    pending=[c for c in cycles if c['status']=='pending' and str(c['created_by'])==user]
    if pending:
        st.subheader('✍️ مراجعة المعلم واعتماد القرار')
        selected=st.selectbox('الدورة المراد مراجعتها',[c['id'] for c in pending])
        decision=next(c for c in pending if c['id']==selected)
