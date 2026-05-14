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
        "<style>"
        '[data-testid="InputInstructions"] { display: none !important; }'
        'div[data-testid="stTextInput"] label { color: #ffffff !important; }'
        "</style>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<h1 style="text-align:center; font-size:36px; font-weight:800; margin-bottom:8px;">Bestiary Registry</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="text-align:center; color:#ad92c9; margin-bottom:32px;">Enter the realm to manage mythical entities.</p>',
        unsafe_allow_html=True,
    )

    _, col2, _ = st.columns([1, 2, 1])

    with col2:
        login_tab, register_tab = st.tabs(["Login", "Register"])

        with login_tab:
            with st.form("login_form"):
                username = st.text_input("Username", key="login_username")
                password = st.text_input(
                    "Password", type="password", key="login_password"
                )
                submitted = st.form_submit_button(
                    "Log In", type="primary", use_container_width=True
                )
            if submitted:
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
                        st.query_params["token"] = token
                        try:
                            me = api_client.get_me(token)
                            if me.get("avatar"):
                                st.session_state["avatar"] = me["avatar"]
                        except Exception:
                            pass
                        st.rerun()
                    except Exception:
                        st.error("Incorrect username or password.")

        with register_tab:
            new_username = st.text_input("Username", key="reg_username")
            new_password = st.text_input(
                "Password", type="password", key="reg_password"
            )

            if st.button(
                "Register", type="primary", use_container_width=True, key="reg_btn"
            ):
                if not new_username or not new_password:
                    st.error("Username and password are required.")
                else:
                    try:
                        api_client.register(new_username, new_password, "admin")
                        st.success("Account created! You can now log in.")
                    except Exception as e:
                        st.error(f"Registration failed: {e}")
