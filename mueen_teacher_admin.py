"""MUEEN V6.3 school principal teacher membership UI.

All authorization and privileged operations are enforced by the Edge Function.
"""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import streamlit as st


def _call(action, school_id, token, **payload):
    url = str(st.secrets.get('SUPABASE_URL', '')).rstrip('/')
    anon = str(st.secrets.get('SUPABASE_PUBLISHABLE_KEY', ''))
    if not url.startswith('https://') or not anon or not token:
        raise ValueError('إعدادات الاتصال أو الجلسة غير مكتملة.')
    request = Request(
        url + '/functions/v1/mueen-teacher-admin',
        data=json.dumps({'action': action, 'school_id': school_id, **payload}).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + token, 'apikey': anon,
                 'Content-Type': 'application/json'}, method='POST')
    try:
        with urlopen(request, timeout=20) as response:
            return json.load(response)
    except HTTPError as exc:
        try:
            message = json.loads(exc.read().decode('utf-8')).get('error', 'Request failed')
        except Exception:
            message = 'تعذر تنفيذ الطلب.'
        raise ValueError(message) from None
    except URLError:
        raise ValueError('تعذر الاتصال بخدمة إدارة المعلمين.') from None


def render_teacher_admin(school_id, role):
    if str(role).lower() != 'principal':
        return
    with st.expander('👥 إدارة المعلمين والحسابات | V6.3', expanded=False):
        st.caption('دعوات المعلمين وإدارة عضويات المدرسة. لا تُعرض هذه الواجهة للمنسق أو المعلم.')
        token = st.session_state.get('mueen_access_token')
        if not token:
            st.warning('سجّل الدخول مجددًا.')
            return
        if st.button('🔄 تحديث قائمة العضويات', key='v63_refresh'):
            st.session_state.pop('v63_members', None)
        try:
            if st.session_state.get('v63_members_school') != school_id:
                st.session_state.pop('v63_members', None)
                st.session_state['v63_members_school'] = school_id
            if 'v63_members' not in st.session_state:
                st.session_state['v63_members'] = _call('list', school_id, token).get('members', [])
            members = st.session_state['v63_members']
            if members:
                st.dataframe([{'البريد': x.get('email', ''), 'الدور': x.get('role'),
                               'نشط': x.get('is_active'), 'المعرّف': x.get('user_id')}
                              for x in members], hide_index=True, use_container_width=True)
            else:
                st.info('لا توجد عضويات معروضة.')
        except ValueError as exc:
            st.error(str(exc))
            return
        with st.form('v63_invite_form'):
            email = st.text_input('البريد الإلكتروني للمعلم')
            role_choice = st.selectbox('الدور', ['teacher', 'coordinator'],
                                       format_func=lambda x: {'teacher':'معلم', 'coordinator':'منسق'}[x])
            submit = st.form_submit_button('📩 إرسال دعوة وربط العضوية')
        if submit:
            try:
                _call('invite', school_id, token, email=email.strip(), role=role_choice)
                st.success('تم قبول طلب الدعوة وربط العضوية. تحقق من وصول البريد الإلكتروني.')
                st.session_state.pop('v63_members', None)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        targets = [m for m in members if m.get('role') in ('teacher', 'coordinator')]
        if targets:
            with st.form('v63_status_form'):
                options = {str(m['user_id']): m for m in targets}
                user_id = st.selectbox('العضوية المراد تعديلها', list(options),
                    format_func=lambda k: f"{options[k].get('email') or k} ({options[k].get('role')})")
                active = st.checkbox('العضوية نشطة', value=bool(options[user_id].get('is_active')))
                confirm = st.checkbox('أؤكد تغيير حالة العضوية')
                update = st.form_submit_button('حفظ حالة العضوية')
            if update:
                if not confirm:
                    st.warning('يرجى تأكيد العملية.')
                else:
                    try:
                        _call('set_active', school_id, token, user_id=user_id, is_active=active)
                        st.session_state.pop('v63_members', None)
                        st.success('تم تحديث العضوية.')
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
