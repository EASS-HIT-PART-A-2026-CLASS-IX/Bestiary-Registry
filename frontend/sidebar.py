import streamlit as st


def render_sidebar(current_view: str):
    username = st.session_state.get("username", "Guest")
    role = st.session_state.get("role", "viewer")
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
        st.markdown(
            """
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: rgba(0,0,0,0.85);
                z-index: 999999;
                display: flex;
                justify-content: center;
                align-items: center;
                flex-direction: column;
                backdrop-filter: blur(8px);
            ">
                <div style="
                    background: #191022;
                    border: 2px solid #ef4444;
                    padding: 60px;
                    border-radius: 24px;
                    text-align: center;
                    box-shadow: 0 0 80px rgba(239, 68, 68, 0.6);
                    max-width: 600px;
                    animation: popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                ">
                    <div style="font-size: 80px; margin-bottom: 24px;">🏰</div>
                    <h1 style="color: white; font-size: 42px; margin: 0 0 16px 0; font-family: 'Space Grotesk', sans-serif;">You go nowhere!</h1>
                    <p style="color: #ef4444; font-size: 24px; margin: 0; font-weight: 500;">Get back to the Realm!</p>
                </div>
                <style>
                    @keyframes popIn {
                        from { transform: scale(0.8); opacity: 0; }
                        to { transform: scale(1); opacity: 1; }
                    }
                </style>
            </div>
        """,
            unsafe_allow_html=True,
        )
        import time

        time.sleep(3)
        st.session_state.clear()
        st.rerun()
