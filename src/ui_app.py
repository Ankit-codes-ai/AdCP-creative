"""
Streamlit UI application for AdCP Agentic Platform.
Provides interface for listing creative formats and previewing creatives.
"""

import streamlit as st
import json
import requests
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add current directory to path for imports when running as script
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from creative_tasks import CreativeTasks, fetch_formats_from_s3
    from utils.logger import get_logger
except ImportError:
    # Fallback for relative imports
    from .creative_tasks import CreativeTasks, fetch_formats_from_s3
    from .utils.logger import get_logger

logger = get_logger()

# Page configuration
st.set_page_config(page_title="AdCP Agentic Platform", layout="wide")

# Initialize session state
if "formats" not in st.session_state:
    st.session_state.formats = []
if "selected_format_id" not in st.session_state:
    st.session_state.selected_format_id = None
if "preview_data" not in st.session_state:
    st.session_state.preview_data = None
if "agent_url" not in st.session_state:
    st.session_state.agent_url = "https://adzymic-exercise.s3.ap-southeast-1.amazonaws.com/adcp"


def display_preview(preview_data: Dict[str, Any]):
    """
    Display creative preview based on type.
    
    Args:
        preview_data: Preview data dictionary
    """
    preview_type = preview_data.get("type", "").lower()
    preview_url = preview_data.get("url", "")
    preview_html = preview_data.get("html", "")

    if preview_type == "image" or preview_url.endswith(
        (".jpg", ".jpeg", ".png", ".gif", ".webp")):
        st.image(preview_url,
                 caption="Creative Preview",
                 use_container_width=True)

    elif preview_type == "video" or preview_url.endswith(
        (".mp4", ".webm", ".ogg")):
        st.video(preview_url)

    elif preview_type == "html" or preview_html:
        st.components.v1.html(preview_html, height=600, scrolling=True)

    else:
        # Try to display as image first
        if preview_url:
            try:
                st.image(preview_url,
                         caption="Creative Preview",
                         use_container_width=True)
            except:
                # If image fails, try HTML
                if preview_html:
                    st.components.v1.html(preview_html,
                                          height=600,
                                          scrolling=True)
                else:
                    st.json(preview_data)


def main():
    """Main Streamlit application."""

    st.title("AdCP Agentic Platform")
    st.markdown(
        "Interact with AdCP Creative Agent to list formats and preview creatives."
    )

    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        agent_url = st.text_input("Creative Agent URL",
                                  value=st.session_state.agent_url,
                                  help="Base URL of the Creative Agent")
        st.session_state.agent_url = agent_url

        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        This platform allows you to:
        - List all available creative formats
        - Preview creatives by FormatID
        
        Uses MCP protocol for communication.
        """)

    # Main content area
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("Creative Formats")

        # Button to list formats
        if st.button("List Creative Formats",
                     type="primary",
                     use_container_width=True):
            with st.spinner("Fetching creative formats..."):
                try:
                    # Try MCP first
                    tasks = CreativeTasks(agent_url=agent_url)
                    formats = tasks.get_creative_formats()

                    if not formats:
                        # Fallback to S3
                        st.info("MCP not available, fetching from S3...")
                        formats = fetch_formats_from_s3()
                        # Add agent_url prefix to FormatID
                        for fmt in formats:
                            if not fmt.get("FormatID", "").startswith("http"):
                                fmt["FormatID"] = f"{agent_url}/{fmt.get('id', '')}"

                    st.session_state.formats = formats
                    st.success(f"Retrieved {len(formats)} creative formats!")

                except Exception as e:
                    st.error(f"Error fetching formats: {str(e)}")
                    logger.log_error(f"UI Error: {str(e)}")
                    # Try fallback
                    try:
                        formats = fetch_formats_from_s3()
                        for fmt in formats:
                            if not fmt.get("FormatID", "").startswith("http"):
                                fmt["FormatID"] = f"{agent_url}/{fmt.get('id', '')}"
                        st.session_state.formats = formats
                        st.success(
                            f"Retrieved {len(formats)} formats from S3!")
                    except:
                        st.session_state.formats = []

        # Display formats
        if st.session_state.formats:
            st.markdown(f"### Found {len(st.session_state.formats)} formats")

            # Create format selection
            format_options = {
                f"{fmt.get('name', 'Unknown')} ({fmt.get('FormatID', 'N/A')})":
                fmt.get("FormatID")
                for fmt in st.session_state.formats
            }

            selected_format_name = st.selectbox(
                "Select a FormatID to preview:",
                options=list(format_options.keys()),
                key="format_selector")

            if selected_format_name:
                st.session_state.selected_format_id = format_options[
                    selected_format_name]

            # Display formats table
            with st.expander("View All Formats", expanded=False):
                format_data = []
                for fmt in st.session_state.formats:
                    format_data.append({
                        "Name": fmt.get("name", "N/A"),
                        "Type": fmt.get("type", "N/A"),
                        "FormatID": fmt.get("FormatID", "N/A"),
                        "ID": fmt.get("id", "N/A")
                    })
                st.dataframe(format_data, use_container_width=True)
        else:
            st.info(
                "Click 'List Creative Formats' to fetch available formats.")

    with col2:
        st.header("Creative Preview")

        if st.session_state.selected_format_id:
            st.info(
                f"Selected FormatID: `{st.session_state.selected_format_id}`")

            if st.button("Preview Creative",
                         type="primary",
                         use_container_width=True):
                with st.spinner("Loading preview..."):
                    try:
                        tasks = CreativeTasks(agent_url=agent_url)
                        preview_data = tasks.get_creative_preview(
                            st.session_state.selected_format_id)
                        st.session_state.preview_data = preview_data
                        st.success("Preview loaded!")

                    except Exception as e:
                        st.error(f"Error loading preview: {str(e)}")
                        logger.log_error(f"Preview Error: {str(e)}")

                        # Try direct S3 preview
                        try:
                            format_id = st.session_state.selected_format_id
                            # Extract ID from FormatID
                            if "/" in format_id:
                                format_id = format_id.split("/")[-1]

                            preview_base = "https://adzymic-exercise.s3.ap-southeast-1.amazonaws.com/adcp/previews/"
                            preview_url = f"{preview_base}{format_id}"

                            # Try to fetch preview
                            response = requests.head(preview_url, timeout=5)
                            if response.status_code == 200:
                                preview_data = {
                                    "type": "image",
                                    "url": preview_url
                                }
                                st.session_state.preview_data = preview_data
                                st.success("Preview loaded from S3!")
                            else:
                                st.warning(
                                    "Preview not available at expected URL.")
                        except Exception as e2:
                            st.error(f"Fallback also failed: {str(e2)}")

            # Display preview
            if st.session_state.preview_data:
                st.markdown("### Preview")
                display_preview(st.session_state.preview_data)

                with st.expander("Preview Data (JSON)", expanded=False):
                    st.json(st.session_state.preview_data)
        else:
            st.info("Select a FormatID from the left to preview.")

    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: gray;'>
        <small>AdCP Agentic Platform | MCP Protocol | Streamlit UI</small>
        </div>
        """,
                unsafe_allow_html=True)


if __name__ == "__main__":
    main()
