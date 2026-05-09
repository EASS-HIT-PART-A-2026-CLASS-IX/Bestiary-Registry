import base64
import json
import streamlit as st
import api_client


def _decode_token_payload(token: str) -> dict:
    try:
        payload_part = token.split(".")[1]
        padding = 4 - len(payload_part) % 4
        if padding != 4:
            payload_part += "=" * padding
        return json.loads(base64.urlsafe_b64decode(payload_part))
    except Exception:
        return {}


def show_auth_page():
    st.markdown(
        '<h1 style="text-align:center; font-size:36px; font-weight:800; margin-bottom:8px;">Bestiary Registry</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="text-align:center; color:#ad92c9; margin-bottom:32px;">Enter the realm to manage mythical entities.</p>',
        unsafe_allow_html=True,
    )

    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button(
            "Log In", type="primary", use_container_width=True, key="login_btn"
        ):
            if not username or not password:
                st.error("Username and password are required.")
            else:
                try:
                    data = api_client.login(username, password)
                    token = data["access_token"]
                    payload = _decode_token_payload(token)
                    st.session_state["token"] = token
                    st.session_state["username"] = payload.get("sub", username)
                    st.session_state["role"] = payload.get("role", "viewer")
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")

    with register_tab:
        new_username = st.text_input("Username", key="reg_username")
        new_password = st.text_input("Password", type="password", key="reg_password")
        role = st.selectbox("Role", ["viewer", "admin"], key="reg_role")

        if st.button(
            "Register", type="primary", use_container_width=True, key="reg_btn"
        ):
            if not new_username or not new_password:
                st.error("Username and password are required.")
            else:
                try:
                    api_client.register(new_username, new_password, role)
                    st.success("Account created! You can now log in.")
                except Exception as e:
                    st.error(f"Registration failed: {e}")
