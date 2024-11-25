# First import standard library modules
import logging
import sys
import os
import time
import threading
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

# Then import third-party modules
import streamlit as st
from PIL import Image
import numpy as np
from dotenv import load_dotenv
import json

# Finally import your local modules
from feature_extractor import FeatureExtractor
from wardrobe_tracker import WardrobeTracker
from wardrobe_notifier import EmailNotifier
from decider import decide_preference
from event_loop import background_loop
from email_settings import initialize_email_settings
from market_place_manager import Marketplace
from decide_match import decide_match

from dotenv import load_dotenv
from SambaFit import *
from style_advisor import StyleAdvisor
from preferences_tab import preferences_tab
from edit_wardrobe_tab import edit_wardrobe_tab
from capture_tab import capture_tab
from notifications_tab import notifications_tab
from marketplace_tab import marketplace_tab
from style_advisor_tab import style_advisor_tab
from developer_assistant import developer_assistant
from fashion_agent import fashion_agent


# Load environment variables
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
SAMBANOVA_API_KEY = os.environ["SAMBANOVA_API_KEY"]
best = [
{ "type": "blazer", "material": "polyester blend", "color": { "primary": "beige", "secondary": [] }, "fit_and_style": { "fit": "slightly relaxed", "style": "contemporary" }, "design_features": { "closure": "single-breasted with single button", "lapel": "notched", "sleeves": "long, cuffless" }, "condition": "new or like-new", "brand": "unknown", "season": "all-season", "use_case": ["professional settings", "casual outings"], "size": "unknown" }
]

worst = [
    { "type": "sweatshirt", "material": "cotton blend", "color": { "primary": "dark navy blue", "secondary": ["white graphic"] }, "fit_and_style": { "fit": "relaxed", "style": "casual" }, "design_features": { "collar": "hooded", "closures": ["drawstring"], "embellishments": ["graphic print"], "logo": "none" }, "condition": "new", "brand": "unknown", "season": "all-season", "use_case": ["travel", "casual outings"], "size": "unknown" }
]
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
def inject_css():
    st.markdown("""
        <style>
        /* Main camera container */
        [data-testid="stCamera"] {
            background-color: #1E1E1E !important;
            border-radius: 10px !important;
            padding: 0 !important;
            margin: 0 auto !important; /* Center the camera */
            width: 480px !important; /* Adjusted for vertical layout */
            height: 640px !important; /* Adjusted for vertical layout */
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
        }
        
        /* Video feed */
        [data-testid="stCamera"] > video {
            transform: rotate(90deg) !important; /* Rotate video feed */
            width: 100% !important;
            height: 100% !important;
            object-fit: cover !important;
        }
        
        /* Captured image */
        [data-testid="stCamera"] > img {
            width: 100% !important;
            height: 100% !important;
            object-fit: contain !important;
            background-color: #1E1E1E !important;
        }
        
        /* Clear photo button section */
        [data-testid="stCamera"] > div {
            position: absolute !important;
            bottom: 0 !important;
            width: 100% !important;
            background-color: rgba(0,0,0,0.7) !important;
            padding: 8px !important;
            border-radius: 0 0 10px 10px !important;
        }

        /* Center the camera in the page */
        [data-testid="stHorizontalBlock"] {
            justify-content: center !important;
            background-color: transparent !important;
        }

        /* Remove any extra padding/margin */
        .stApp {
            margin: 0 auto !important;
        }
        </style>
    """, unsafe_allow_html=True)



def initialize_database():
    """Initialize the database file if it doesn't exist or is empty"""
    database_path = 'clothing_database.json'
    initial_data = {
        "items": [],
        "outfits": [],
        "listings": []
    }
    
    try:
        if not os.path.exists(database_path):
            with open(database_path, 'w') as file:
                json.dump(initial_data, file)
        else:
            # Try to load existing database
            try:
                with open(database_path, 'r') as file:
                    data = json.load(file)
                    if not isinstance(data, dict) or not all(key in data for key in initial_data.keys()):
                        raise ValueError("Invalid database structure")
            except (json.JSONDecodeError, ValueError):
                # If file is corrupt, reinitialize it
                with open(database_path, 'w') as file:
                    json.dump(initial_data, file)
    except Exception as e:
        st.error(f"Error initializing database: {str(e)}")
        # Ensure we have a valid database even if something goes wrong
        with open(database_path, 'w') as file:
            json.dump(initial_data, file)
   
def initialize_notification_state():
    if 'notification_state' not in st.session_state:
        st.session_state.notification_state = {
            'unworn_items': None,
            'show_send_button': False,
            'sending_email': False
        }
def initialize_camera_state():
    if 'camera_initialized' not in st.session_state:
        st.session_state.camera_initialized = False
    if 'current_image' not in st.session_state:
        st.session_state.current_image = None
    if 'first_run' not in st.session_state:
        st.session_state.first_run = True
    if 'image_processed' not in st.session_state:
        st.session_state['image_processed'] = False
    
    inject_css()


def main():
    inject_css()
    initialize_email_settings()
    initialize_notification_state()
    initialize_camera_state()  # Add this line
    initialize_database()
    st.title("VESTIQUE - Smart Wardrobe Assistant")
    
    feature_extractor = FeatureExtractor()
    tracker = WardrobeTracker(feature_extractor)
    email_notifier = EmailNotifier()
    if 'style_advisor' not in st.session_state:
        st.session_state.style_advisor = StyleAdvisor(SAMBANOVA_API_KEY)
    # Initialize dev mode in session state if not exists
    if 'dev_mode' not in st.session_state:
        st.session_state.dev_mode = False   
    if 'last_mode' not in st.session_state:
        st.session_state.last_mode = False
    # Sidebar controls
    with st.sidebar:
        st.subheader("Settings")
        mode = st.radio(
            "Capture Mode",
            ["Single Item", "Full Outfit"],
            help="Choose whether to capture a single clothing item or a full outfit"
        )
        
        if st.button("Load Demo Data"):
            tracker.add_demo_data()
        
        debug_mode = st.checkbox("Debug Mode")
        st.session_state['debug_mode'] = debug_mode
        
        # Developer Mode toggle
        st.divider()
        st.subheader("👨‍💻 Developer Tools")
        dev_mode = st.checkbox('Developer Assistant', value=st.session_state.dev_mode, help="Switch to Developer Assistant mode")
        st.session_state.dev_mode = dev_mode

        # Email Settings in Sidebar
        st.divider()
        st.subheader("📧 Email Settings")
        with st.expander("Configure Email"):
            sender_email = st.text_input(
                "Gmail Address", 
                value=st.session_state.sender_email,
                help="Enter the Gmail address you want to send notifications from"
            )
            
            email_password = st.text_input(
                "App Password", 
                type="password",
                value=st.session_state.email_password,
                help="Enter your Gmail App Password (Not your regular Gmail password). Get it from Google Account -> Security -> 2-Step Verification -> App passwords"
            )
            
            if st.button("Save Email Settings"):
                if '@gmail.com' not in sender_email:
                    st.error("Please enter a valid Gmail address")
                elif len(email_password) != 16:
                    st.error("App Password should be 16 characters. Please check your Google App Password")
                else:
                    st.session_state.sender_email = sender_email
                    st.session_state.email_password = email_password
                    st.session_state.email_configured = True
                    st.success("✅ Email settings saved!")

        # Default reset period
        st.divider()
        st.subheader("Default Reset Period")
        new_reset_period = st.number_input(
            "Days until reset for new items", 
            min_value=1, 
            max_value=30, 
            value=tracker.reset_period
        )
        if new_reset_period != tracker.reset_period:
            tracker.reset_period = new_reset_period
            st.success(f"Default reset period updated to {new_reset_period} days!")
     # Check if mode changed and reapply CSS
    if st.session_state.last_mode != st.session_state.dev_mode:
        inject_css()
        st.session_state.last_mode = st.session_state.dev_mode
    # Main content - conditional rendering based on dev_mode
    if st.session_state.dev_mode:
        inject_css()
        developer_assistant()
    else:
        

        # Regular app tabs
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "Capture", "My Wardrobe", "Edit Wardrobe", 
            "Notifications", "Preferences", "Marketplace", "Style Advisor", "SambaFit"
        ])
        
        with tab1:
            
            capture_tab(mode, tracker, debug_mode)
        
        with tab2:
            tracker.display_wardrobe_grid()
            
        with tab3:
            edit_wardrobe_tab(tracker)

        with tab4:
            notifications_tab(tracker, email_notifier)

        with tab5:
            preferences_tab()

        with tab6:
            marketplace_tab(tracker, email_notifier)

        with tab7:
            style_advisor_tab(tracker)

        with tab8:
            fashion_agent(tracker)
            
    
if __name__ == "__main__":
    main()