import streamlit as st

if not st.experimental_user.is_logged_in:
    if st.button("Log in"):
        foo = st.login()
        print(foo)
else:
    if st.button("Log out"):
        st.logout()
    st.write(f"Hello, {st.experimental_user.name}!")
    st.write(st.experimental_user)
