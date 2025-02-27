import streamlit as st
from streamlit_js_eval import streamlit_js_eval

# def works_inject_js(key: str):
#     """Inject some test JavaScript with a zero height container."""
#     st.markdown(
#         """
#         <style>
#         :root {
#             --st-text-line-height: 1.6;
#             --st-default-font-size: 16px;
#             --base-space: calc(var(--st-text-line-height) * var(--st-default-font-size));
#             /* Fine-tune with an extra 2px */
#             --total-space: calc(var(--base-space) + 7px);  /* 25.6px + 10px = 35.6px */
#         }

#         .stElementContainer:has(iframe) {
#             margin-top: calc(-1 * var(--total-space)) !important;
#             height: 0 !important;
#             min-height: 0 !important;
#             overflow: hidden !important;
#         }

#         .stMarkdown {
#             margin: 0 !important;
#             padding: 0 !important;
#         }
#         </style>
#         """,
#         unsafe_allow_html=True,
#     )

#     js = """
#         <script>
#             console.log("This is a test script");
#         </script>
#         """
#     stcomponents.html(js, height=0)


# def also_works_inject_js(key: str):
#     """Inject some test JavaScript with a zero height container."""
#     # Try to get theme values from session state
#     theme = st.session_state.get("theme", {})
#     base_font_size = theme.get("baseFontSize", "1.666rem")
#     base_spacing_unit = theme.get("spacing", "0.25666rem")
#     print(theme, base_font_size, base_spacing_unit)
#     st.markdown(
#         """
#         <style>
#         :root {
#             /* Use rem for font-size to respect user zoom settings */
#             --st-default-font-size: 1rem;           /* 16px by default */
#             --st-text-line-height: 1.6;             /* Streamlit's line height */
#             --st-base-spacing-unit: 0.25rem;        /* 4px - Streamlit's spacing unit */

#             /* Calculations */
#             --base-space: calc(var(--st-text-line-height) * var(--st-default-font-size));
#             --extra-space: calc(1.75 * var(--st-base-spacing-unit));  /* 7px (1.75 * 4px) */
#             --total-space: calc(var(--base-space) + var(--extra-space));
#         }

#         .stElementContainer:has(iframe) {
#             margin-top: calc(-1 * var(--total-space)) !important;
#             height: 0 !important;
#             min-height: 0 !important;
#             overflow: hidden !important;
#         }

#         .stMarkdown {
#             margin: 0 !important;
#             padding: 0 !important;
#         }
#         </style>
#         """,
#         unsafe_allow_html=True,
#     )

#     js = """
#         <script>
#             console.log("This is a test script");
#         </script>
#         """
#     stcomponents.html(js, height=0)


# def inject_js(
#     js: str,
#     key: str,
#     base_font_size_px: int = 16,
#     line_height_multiplier: float = 1.6,
#     base_spacing_unit: float = 4,
# ):
#     """Inject some test JavaScript with a zero height container.

#     Args:
#         key: Unique key for the component
#         line_height_multiplier: Streamlit's text line height multiplier (default 1.6)
#             This controls the vertical rhythm of text elements.
#             Default value comes from Streamlit's typography system.

#         base_spacing_unit: Base unit for spacing in pixels (default 4)
#             Streamlit uses 0.25rem (4px) as their base spacing unit.
#             Container spacing is calculated as 1.75 * base_spacing_unit.
#     """

#     # Calculate container spacing (1.75 is Streamlit's spacing multiplier)
#     container_spacing = 1.75 * base_spacing_unit  # e.g. 1.75 * 4px = 7px

#     st.markdown(
#         f"""
#         <style>
#         :root {{
#             /* Typography settings from Streamlit's design system */
#             --st-text-line-height: {line_height_multiplier};  /* Default 1.6 */
#             --st-default-font-size: {base_font_size_px}px;                     /* Streamlit base font size */

#             /* Spacing calculations */
#             --base-space: calc(var(--st-text-line-height) * var(--st-default-font-size));
#                 /* e.g. 1.6 * 16px = 25.6px text block height */

#             --container-spacing: {container_spacing}px;
#                 /* Additional space from Streamlit's container:
#                    1.75 * base_spacing_unit (4px) = 7px */

#             --total-space: calc(var(--base-space) + var(--container-spacing));
#                 /* Total = text height + container spacing
#                    e.g. 25.6px + 7px = 32.6px */
#         }}

#         .stElementContainer:has(iframe) {{
#             /* Pull up container by calculated height */
#             margin-top: calc(-1 * var(--total-space)) !important;
#             height: 0 !important;
#             min-height: 0 !important;
#             overflow: hidden !important;
#         }}

#         .stMarkdown {{
#             margin: 0 !important;
#             padding: 0 !important;
#         }}
#         </style>
#         """,
#         unsafe_allow_html=True,
#     )

#     # Wrap user's JavaScript
#     wrapped_js = f"""
#         <script>
#         try {{
#             {js}
#         }} catch (e) {{
#             console.error('Error in zero height container {key}:', e);
#         }}
#         </script>
#     """

#     # Inject the JavaScript
#     stcomponents.html(wrapped_js, height=0)


# def zero_height_container(
#     key: str, js: str, line_height_multiplier: float = 1.6, base_spacing_unit: float = 4
# ):
#     """Create a zero-height container for running custom JavaScript."""

#     # Create container with unique key
#     with st.container(key=f"zhc_{key}"):
#         # Inject CSS with precise spacing
#         st.markdown(
#             """
#             <style>
#             :root {
#                 --st-text-line-height: 1.6;
#                 --st-default-font-size: 16px;
#                 --base-space: calc(var(--st-text-line-height) * var(--st-default-font-size));
#                 /* Original working spacing was base_space + 7px */
#                 --total-space: calc(var(--base-space) + 7px);  /* 25.6px + 7px = 32.6px */
#             }

#             /* Target any iframe container inside this component */
#             .stElementContainer:has(iframe) {
#                 margin-top: calc(-1 * var(--total-space)) !important;
#                 height: 0 !important;
#                 min-height: 0 !important;
#                 overflow: hidden !important;
#             }

#             .stMarkdown {
#                 margin: 0 !important;
#                 padding: 0 !important;
#             }
#             </style>
#             """,
#             unsafe_allow_html=True,
#         )

#         # Wrap user's JavaScript
#         wrapped_js = f"""
#             <script>
#             try {{
#                 {js}
#             }} catch (e) {{
#                 console.error('Error in zero height container {key}:', e);
#             }}
#             </script>
#         """

#         # Inject the JavaScript
#         stcomponents.html(wrapped_js, height=0)


def main():
    st.markdown(
        """
        <style>
            .element-container:has(
                iframe[title="streamlit_js_eval.streamlit_js_eval"]
            ) {
                height: 0 !important;
                display: none;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("Zero Height Container Test")

    # Normal content
    st.write("___________Content before containers")
    st.write("___________Content before containers")

    # First zero height container
    # zero_height_container(key="test1", js="console.log('First container running!');")
    # inject_js(key="test1", js="console.log('First container running!');")

    streamlit_js_eval(
        js_expressions=f"""
    console.log('First container running!');
    """
    )
    # Normal content between
    st.write("______________Content between containers")
    st.write("______________Content between containers")

    # Second zero height container with different JS
    # zero_height_container(
    #     key="test2",
    #     js="""
    #     console.log('Second container running!');
    #     // More complex JS example
    #     const data = { test: 123 };
    #     console.log('Data:', data);
    #     """,
    # )
    streamlit_js_eval(
        js_expressions="""
        console.log('Second container running!');
        // More complex JS example
        const data = { test: 123 };
        console.log('Data:', data);    """
    )
    # Final content
    st.write("_______________Content after containers")
    st.write("_______________Content after containers")


if __name__ == "__main__":
    main()
