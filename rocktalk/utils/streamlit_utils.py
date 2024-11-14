import streamlit.components.v1 as components


def close_dialog() -> None:
    components.html(
        """\
            <script>
            parent.document.querySelector('div[data-baseweb="modal"]').remove();
            </script>
            """,
        height=0,
        scrolling=False,
    )
