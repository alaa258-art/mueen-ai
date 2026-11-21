"""MUEEN V6.3 school principal membership UI.

Authorization and privileged operations MUST be enforced by the Edge Function.
The Edge Function must explicitly implement the 'set_role' action before role
changes can succeed. Never use a service-role key in Streamlit.
"""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st


ROLES = {'teacher': 'معلم', 'coordinator': 'منسق', 'principal': 'مدير المدرسة'}


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
        st.caption('إدارة عضويات المدرسة ودعوات المعلمين والمنسقين والمديرين. جميع الصلاحيات الحساسة يتحقق منها الخادم.')
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
            email = st.text_input('البريد الإلكتروني للعضو')
            role_choice = st.selectbox('الدور', list(ROLES), format_func=lambda x: ROLES[x])
            submit = st.form_submit_button('📩 إرسال دعوة وربط العضوية')
        if submit:
            try:
                _call('invite', school_id, token, email=email.strip(), role=role_choice)
                st.success('قبل الخادم طلب الدعوة وربط العضوية. تحقق من وصول البريد الإلكتروني.')
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
        st.caption('استخدم هذا القسم للحسابات الموجودة؛ يدعم تغيير دور المدير فقط إذا سمحت وظيفة Supabase بذلك. يجب حماية آخر مدير على الخادم.')
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
                    st.info('يتطلب تغيير الأدوار دعم إجراء set_role في Edge Function والتحقق من صلاحية المدير.')

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

        st.markdown('#### 🛡️ إزالة عضو من المدرسة')
        st.caption('الإزالة هنا تعني تعطيل العضوية في المدرسة فقط؛ لا تحذف حساب Supabase أو سجلات الطالب أو التقييمات.')
        active_targets = {uid: m for uid, m in options.items() if bool(m.get('is_active'))}
        if active_targets:
            with st.form('v63_revoke_membership_form'):
                revoke_uid = st.selectbox(
                    'العضو المراد سحب صلاحياته', list(active_targets),
                    format_func=lambda uid: f"{active_targets[uid].get('email') or uid} ({ROLES.get(active_targets[uid].get('role'), active_targets[uid].get('role'))})",
                    key='v63_revoke_user_id',
                )
                st.warning('بعد التعطيل لن يتمكن العضو من الوصول إلى بيانات هذه المدرسة عند التحقق من العضوية مجددًا.')
                revoke_confirm = st.checkbox('أؤكد سحب عضوية هذا الحساب من المدرسة')
                revoke_submit = st.form_submit_button('🚫 إزالة العضوية من المدرسة')
            if revoke_submit:
                if not revoke_confirm:
                    st.warning('يرجى تأكيد إزالة العضوية.')
                else:
                    # Protect own membership on the client; server must independently
                    # prevent self-removal and removal of the final active principal.
                    try:
                        from supabase import create_client
                        auth_client = create_client(
                            str(st.secrets['SUPABASE_URL']),
                            str(st.secrets['SUPABASE_PUBLISHABLE_KEY']),
                        )
                        current_user = auth_client.auth.get_user(token).user
                        current_uid = str(current_user.id) if current_user else ''
                    except Exception:
                        current_uid = ''
                    principals = [m for m in members if m.get('role') == 'principal' and m.get('is_active')]
                    if not current_uid:
                        st.error('تعذر التحقق من هوية المدير الحالي. أعد تسجيل الدخول.')
                    elif revoke_uid == current_uid:
                        st.error('لا يمكن للمدير إزالة عضويته الشخصية.')
                    elif active_targets[revoke_uid].get('role') == 'principal' and len(principals) <= 1:
                        st.error('لا يمكن إزالة آخر مدير نشط في المدرسة.')
                    else:
                        try:
                            _call('set_active', school_id, token, user_id=revoke_uid, is_active=False)
                            _refresh()
                            st.success('تم تعطيل عضوية المستخدم في هذه المدرسة. لم يُحذف حسابه.')
                            st.rerun()
                        except ValueError as exc:
                            st.error(f'تعذر إزالة العضوية: {exc}')
