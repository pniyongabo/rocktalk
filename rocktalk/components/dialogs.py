import streamlit as st


@st.dialog("Upload")
def upload_dialog():
    uploaded_files = st.file_uploader("Choose a file", accept_multiple_files=True)
    if uploaded_files:
        for uploaded_file in uploaded_files:
            # Check if the uploaded file is an image
            if uploaded_file.type.startswith("image"):
                # Display the image
                st.image(
                    uploaded_file,
                    caption="Uploaded Image",
                    width=100,
                )
            else:
                st.error(
                    "Sorry, only image files are supported. Please upload an image file."
                )


@st.dialog("Text box")
def open_text_dialog():

    animal = st.form("my_animal")

    # These methods called on the form container, so they appear inside the form.
    submit = animal.form_submit_button(f"Submit")
    sentence = animal.text_input("Your sentence:")
    if submit:
        print(sentence)
        st.session_state.additional_text = sentence
        st.rerun()
