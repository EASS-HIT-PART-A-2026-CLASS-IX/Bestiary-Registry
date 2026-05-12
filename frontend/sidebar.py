import api_client
import streamlit as st


def render_sidebar(current_view: str):
    token = st.session_state.get("token")
    if token and "avatar" not in st.session_state:
        try:
            me = api_client.get_me(token)
            if me.get("avatar"):
                st.session_state["avatar"] = me["avatar"]
        except Exception:
            pass

    username = st.session_state.get("username", "Guest")
    role = st.session_state.get("role", "viewer")
    avatar_b64 = st.session_state.get("avatar")
    if avatar_b64:
        avatar_url = f"data:image/png;base64,{avatar_b64}"
    else:
        avatar_url = f"https://api.dicebear.com/7.x/identicon/svg?seed={username}"

    st.sidebar.markdown(
        f"""
        <div style="margin-bottom: 2rem;">
            <div style="display: flex; align-items: center; gap: 12px; padding: 8px 0;">
                <div style="width: 48px; height: 48px; border-radius: 50%; border: 2px solid #7f13ec; background-image: url('{avatar_url}'); background-size: cover; background-position: center;"></div>
                <div>
                    <div style="font-weight: 700; color: white; font-size: 15px;">{username}</div>
                    <div style="font-size: 13px; color: #ad92c9;">{role.capitalize()}</div>
                </div>
            </div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # Navigation Buttons

    # Callback to update view
    def set_view(v):
        st.query_params["view"] = v  # Sync URL for bookmarking
        # App will rerun automatically on button click

    # Registry Button
    if st.sidebar.button(
        "Bestiary Registry",
        key="nav_registry",
        use_container_width=True,
        type="primary" if current_view == "registry" else "secondary",
    ):
        set_view("registry")
        st.rerun()

    # Map Button
    if st.sidebar.button(
        "Realm Map",
        key="nav_map",
        use_container_width=True,
        type="primary" if current_view == "map" else "secondary",
    ):
        set_view("map")
        st.rerun()

    st.sidebar.markdown(
        '<div style="flex-grow: 1; height: 100px;"></div>', unsafe_allow_html=True
    )  # Spacer

    st.sidebar.markdown(
        """
    <div style="border-top: 1px solid #4d3267; margin-top: auto; padding-top: 1rem;"></div>
    """,
        unsafe_allow_html=True,
    )

    if st.sidebar.button(
        "Settings",
        key="nav_settings",
        use_container_width=True,
        type="primary" if current_view == "settings" else "secondary",
    ):
        set_view("settings")
        st.rerun()

    if st.sidebar.button("Log Out", key="logout", use_container_width=True):
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()
