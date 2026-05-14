import streamlit as st
import api_client


@st.cache_data(ttl=2, show_spinner=False)
def get_creatures(token: str = None):
    return api_client.get_creatures(token)


@st.cache_data(ttl=2, show_spinner=False)
def get_classes():
    return api_client.get_classes()


def clear_cache():
    get_creatures.clear()
    get_classes.clear()
