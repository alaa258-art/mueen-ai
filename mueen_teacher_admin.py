"""MUEEN V6.3 school principal membership UI.

Authorization and privileged operations MUST be enforced by the Edge Function.
The Edge Function must explicitly implement the 'set_role' action before role
changes can succeed. Never use a service-role key in Streamlit.
"""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st


ROLES = {'teacher': 'معلم', 'coordinator': 'منسق'}


def _call(action, school_id, token, **payload):
    url = str(st.secrets.get('SUPABASE_URL', '')).rstrip('/')
    anon = str(st.secrets.get('SUPABASE_PUBLISHABLE_KEY', ''))
    if not url.startswith('https://') or not anon or not token:
        raise ValueError('إعدادات الاتصال أو الجلسة غير مكتملة.')
    request = Request(
        url + '/functions/v1/mueen-teacher-admin',
        data=json.dumps({'action': action, 'school_id': school_id, **payload}).encode('utf-8'),
        headers={
            'Authorization': 'Bearer ' + token,
            'apikey': anon,
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.load(response)
    except HTTPError as exc:
        try:
            body = json.loads(exc.read().decode('utf-8'))
            message = body.get('error') or body.get('message') or 'Request failed'
        except Exception:
            message = 'تعذر تنفيذ الطلب.'
        raise ValueError(str(message)) from None
    except URLError:
        raise ValueError('تعذر الاتصال بخدمة إدارة المعلمين.') from None


def _refresh():
    st.session_state.pop('v63_members', None)


def render_teacher_admin(school_id, role):
    if str(role).lower() != 'principal':
        return

    with st.expander('👥 إدارة المعلمين والحسابات | V6.3', expanded=False):
        st.caption('إدارة عضويات المدرسة ودعوات المعلمين. الصلاحيات تُتحقق في الخادم.')
        token = st.session_state.get('mueen_access_token')
        if not token:
            st.warning('سجّل الدخول مجددًا.')
            return

        if st.button('🔄 تحديث قائمة العضويات', key='v63_refresh'):
            _refresh()

        try:
            if st.session_state.get('v63_members_school') != school_id:
                _refresh()
                st.session_state['v63_members_school'] = school_id
            if 'v63_members' not in st.session_state:
                st.session_state['v63_members'] = _call('list', school_id, token).get('members', [])
            members = st.session_state['v63_members']
            if members:
                st.dataframe(
                    [
                        {
                            'البريد': x.get('email', ''),
                            'الدور': x.get('role'),
                            'نشط': x.get('is_active'),
                            'المعرّف': x.get('user_id'),
                        }
                        for x in members
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info('لا توجد عضويات معروضة.')
        except ValueError as exc:
            st.error(str(exc))
            return

        with st.form('v63_invite_form'):
            email = st.text_input('البريد الإلكتروني للمعلم')
            role_choice = st.selectbox('الدور', list(ROLES), format_func=lambda x: ROLES[x])
            submit = st.form_submit_button('📩 إرسال دعوة وربط العضوية')
        if submit:
            try:
                _call('invite', school_id, token, email=email.strip(), role=role_choice)
                st.success('تم قبول طلب الدعوة وربط العضوية. تحقق من وصول البريد الإلكتروني.')
                _refresh()
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

        targets = [m for m in members if m.get('role') in ROLES and m.get('user_id')]
        if not targets:
            return
        options = {str(m['user_id']): m for m in targets}
        format_member = lambda k: f"{options[k].get('email') or k} ({options[k].get('role')})"

        st.markdown('#### 🔁 تغيير دور عضو موجود')
        st.caption('استخدم هذا القسم للحسابات الموجودة؛ لا ترسل دعوة جديدة لتغيير الدور.')
        with st.form('v63_role_form'):
            role_user_id = st.selectbox(
                'العضوية المراد تغيير دورها', list(options),
                format_func=format_member, key='v63_role_user_id',
            )
            old_role = str(options[role_user_id].get('role', ''))
            new_role = st.selectbox(
                'الدور الجديد', list(ROLES),
                index=list(ROLES).index(old_role),
                format_func=lambda x: ROLES[x],
                key='v63_new_role',
            )
            confirm_role = st.checkbox('أؤكد تغيير دور هذه العضوية')
            update_role = st.form_submit_button('💾 حفظ الدور الجديد')
        if update_role:
            if not confirm_role:
                st.warning('يرجى تأكيد تغيير الدور.')
            elif new_role == old_role:
                st.info('الدور الجديد مطابق للدور الحالي؛ لم يُجرَ أي تعديل.')
            else:
                try:
                    _call('set_role', school_id, token, user_id=role_user_id, role=new_role)
                    _refresh()
                    st.success('تم تحديث الدور. يُنصح بإعادة تسجيل الدخول لتحديث الصلاحيات.')
                    st.rerun()
                except ValueError as exc:
                    st.error(f'لم يتم تغيير الدور: {exc}')
                    st.info('تأكد من أن Edge Function تدعم الإجراء set_role وتتحقق من صلاحية المدير.')

        st.markdown('#### تفعيل العضوية أو تعطيلها')
        with st.form('v63_status_form'):
            user_id = st.selectbox(
                'العضوية المراد تعديل حالتها', list(options),
                format_func=format_member, key='v63_status_user_id',
            )
            active = st.checkbox('العضوية نشطة', value=bool(options[user_id].get('is_active')))
            confirm = st.checkbox('أؤكد تغيير حالة العضوية')
            update = st.form_submit_button('حفظ حالة العضوية')
        if update:
            if not confirm:
                st.warning('يرجى تأكيد العملية.')
            else:
                try:
                    _call('set_active', school_id, token, user_id=user_id, is_active=active)
                    _refresh()
                    st.success('تم تحديث العضوية.')
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
