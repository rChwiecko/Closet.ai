from ui_components import WardrobeUI 
import json
from datetime import datetime, timedelta
from pathlib import Path
import streamlit as st
import numpy as np
from PIL import Image
import base64
from io import BytesIO
import json
from datetime import datetime, timedelta
from pathlib import Path
import streamlit as st
import numpy as np
from PIL import Image
import base64
from io import BytesIO
import cv2
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
import seaborn as sns
from wardrobe_analysis import WardrobeAnalysis
import asyncio  # Add this
from classifier import classify_outfit  # Add this
from event_loop import background_loop
class WardrobeTracker:
    def __init__(self, feature_extractor):
        self.feature_extractor = feature_extractor
        self.db_path = Path("clothing_database.json")
        self.similarity_threshold = 0.80
        self.reset_period = 7  # Days before an outfit can be worn again
        self.database = self.load_database()
        
        # Define clothing categories with emojis
        self.clothing_categories = {
            "T-Shirt": "👕",
            "Hoodie": "🧥",
            "Jacket": "🧥",
            "Pants": "👖",
            "Shorts": "🩳",
            "Dress": "👗",
            "Skirt": "👗",
            "Shoes": "👟",
            "Hat": "🧢",
            "Accessory": "👔",
            "Full Outfit": "👔"
        }
    def add_new_item_sync(self, image, item_type, is_outfit=False, name=None, existing_id=None, additional_data=None):
        """Synchronous version of add_new_item for fallback"""
        features = self.feature_extractor.extract_features(image, is_full_outfit=is_outfit)
        if features is None:
            return False

        if existing_id is not None:
            # Add new view to existing item
            collection = "outfits" if is_outfit else "items"
            for item in self.database[collection]:
                if item['id'] == existing_id:
                    if 'reference_images' not in item:
                        item['reference_images'] = []
                        item['reference_features'] = []
                        item['reference_images'].append(item['image'])
                        item['reference_features'].append(item['features'])
                    
                    item['reference_images'].append(self.image_to_base64(image))
                    item['reference_features'].append(features.tolist())
                    self.save_database()
                    return True
            return False
        else:
            # Create new item with initial view and wear count
            collection = "outfits" if is_outfit else "items"
            
            # Generate a new unique ID
            new_id = 0
            existing_ids = set()
            for item in self.database[collection]:
                existing_ids.add(item.get('id', 0))
            while new_id in existing_ids:
                new_id += 1
            
            new_item = {
                "id": new_id,
                "type": item_type,
                "name": name or item_type,
                "reference_images": [self.image_to_base64(image)],
                "reference_features": [features.tolist()],
                "last_worn": datetime.now().isoformat(),
                "image": self.image_to_base64(image),
                "features": features.tolist(),
                "reset_period": 7,
                "wear_count": 1
            }
            
            # Add AI analysis and style data if provided
            if additional_data:
                if 'ai_analysis' in additional_data:
                    new_item['ai_analysis'] = additional_data['ai_analysis']
                if 'style_recommendations' in additional_data:
                    new_item['style_recommendations'] = additional_data['style_recommendations']
                if 'style_sources' in additional_data:
                    new_item['style_sources'] = additional_data['style_sources']
            
            self.database[collection].append(new_item)
            self.save_database()
            return True
    def load_database(self):
        default_db = {
            "items": [],
            "outfits": [],
            "listings": []  # Add listings to the default database structure
        }
        
        try:
            if self.db_path.exists():
                with open(self.db_path) as f:
                    db = json.load(f)
                    
                    # Ensure all keys exist in the database
                    if "outfits" not in db:
                        db["outfits"] = []
                    if "items" not in db:
                        db["items"] = []
                    if "listings" not in db:  # Check for the listings key
                        db["listings"] = []
                    
                    return db
            else:
                return default_db
        except Exception as e:
            st.error(f"Error loading database: {str(e)}")
            return default_db


    def visualize_analysis(self, image, features, matching_item=None):
        """Visualize the analysis process in debug mode"""
        WardrobeAnalysis.visualize_analysis(image, features, matching_item, self.base64_to_image)
    def add_new_item(self, image, item_type, is_outfit=False, name=None, existing_id=None):
        """Add new item or add view to existing item with wear count and AI analysis"""
        try:
            features = self.feature_extractor.extract_features(image, is_full_outfit=is_outfit)
            if features is None:
                return False

            if existing_id is not None:
                # Add new view to existing item
                collection = "outfits" if is_outfit else "items"
                for item in self.database[collection]:
                    if item['id'] == existing_id:
                        if 'reference_images' not in item:
                            item['reference_images'] = []
                            item['reference_features'] = []
                            item['reference_images'].append(item['image'])
                            item['reference_features'].append(item['features'])
                        
                        item['reference_images'].append(self.image_to_base64(image))
                        item['reference_features'].append(features.tolist())
                        self.save_database()
                        return True
                return False
            else:
                # Create new item with initial view, wear count, and AI analysis
                collection = "outfits" if is_outfit else "items"
                
                # Generate a new unique ID for the item
                new_id = 0
                existing_ids = set()
                for item in self.database[collection]:
                    existing_ids.add(item.get('id', 0))
                while new_id in existing_ids:
                    new_id += 1
                
                # Convert image to RGB for analysis
                rgb_image = image.convert("RGB")
                
                try:
                    # Import the background_loop from main.py
                    from app import background_loop

                    # Run the async function in the background event loop
                    future = asyncio.run_coroutine_threadsafe(classify_outfit(rgb_image), background_loop)
                    description = future.result()  # This will block until the result is available
                    
                    # Get style recommendations for the item if it exists in session state
                    style_advice = None
                    if 'style_advisor' in st.session_state:
                        with st.spinner("Getting style recommendations..."):
                            style_advice = st.session_state.style_advisor.get_style_advice(description)
                    
                    new_item = {
                        "id": new_id,  # Use the unique ID we generated
                        "type": item_type,
                        "name": name or item_type,
                        "reference_images": [self.image_to_base64(image)],
                        "reference_features": [features.tolist()],
                        "last_worn": datetime.now().isoformat(),
                        "image": self.image_to_base64(image),
                        "features": features.tolist(),
                        "reset_period": 7,
                        "wear_count": 1,
                        "ai_analysis": description,
                        "style_recommendations": style_advice["styling_tips"] if style_advice else None,
                        "style_sources": style_advice["sources"] if style_advice else None
                    }
                    
                    self.database[collection].append(new_item)
                    self.save_database()
                    st.success("✅ Added to wardrobe with AI analysis!")
                    return True
                    
                except Exception as e:
                    st.error(f"Error during AI analysis: {str(e)}")
                    # Still add the item even if AI analysis fails, but use the unique ID
                    new_item = {
                        "id": new_id,  # Use the unique ID here too
                        "type": item_type,
                        "name": name or item_type,
                        "reference_images": [self.image_to_base64(image)],
                        "reference_features": [features.tolist()],
                        "last_worn": datetime.now().isoformat(),
                        "image": self.image_to_base64(image),
                        "features": features.tolist(),
                        "reset_period": 7,
                        "wear_count": 1
                    }
                    
                    self.database[collection].append(new_item)
                    self.save_database()
                    st.warning("⚠️ Added to wardrobe, but AI analysis failed")
                    return True
        except Exception as e:
            st.error(f"Error adding item: {str(e)}")
            if st.session_state.get('debug_mode', False):
                st.write("Error details:", str(e))
            return False
    
        # 4. Similarity Analysis (if there's a match)
        if matching_item is not None:
            st.write("### 🎯 Similarity Matching")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("#### Matched Item")
                if 'image' in matching_item:
                    matched_image = self.base64_to_image(matching_item['image'])
                    if matched_image:
                        st.image(matched_image, use_column_width=True)
                
            with col2:
                st.write("#### Similarity Metrics")
                stored_features = np.array(matching_item["features"])
                
                # Calculate various similarity metrics
                cosine_sim = self.feature_extractor.calculate_similarity(features, stored_features)
                feature_diff = np.abs(features - stored_features[:len(features)])
                diff_mean = feature_diff.mean()
                
                # Display metrics
                metrics = {
                    "Similarity Score": f"{cosine_sim:.3f}",
                    "Feature Match": f"{(1 - diff_mean):.3f}",
                    "Confidence": f"{max(0, min(1, cosine_sim)):.3f}"
                }
                
                for metric, value in metrics.items():
                    st.metric(metric, value)
                
                # Visualize feature differences
                fig, ax = plt.subplots()
                ax.hist(feature_diff, bins=50, color='blue', alpha=0.6)
                ax.set_title("Feature Differences Distribution")
                ax.axvline(diff_mean, color='red', linestyle='--', 
                          label=f'Mean Diff: {diff_mean:.3f}')
                ax.legend()
                st.pyplot(fig)

    def save_database(self):
        try:
            with open(self.db_path, "w") as f:
                json.dump(self.database, f, indent=4)
        except Exception as e:
            st.error(f"Error saving database: {str(e)}")

    def image_to_base64(self, image):
        """Convert PIL Image to base64 string"""
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=85)  # Reduced quality for storage
        return base64.b64encode(buffered.getvalue()).decode()

    def base64_to_image(self, base64_string):
        """Convert base64 string back to PIL Image"""
        try:
            image_data = base64.b64decode(base64_string)
            return Image.open(BytesIO(image_data))
        except Exception as e:
            st.error(f"Error converting image: {str(e)}")
            return None

    def add_demo_data(self):
        """Add demo outfits with specific wear dates, reset periods, and wear counts"""
        sample_colors = [(200, 150, 150), (150, 200, 150), (150, 150, 200)]
        demo_outfits = []
        
        for i, (name, days_ago, reset_period, wear_count) in enumerate([
            ("Casual Friday", 4, 4, 3),
            ("Business Meeting", 6, 4, 2),
            ("Weekend Style", 2, 4, 5)
        ]):
            img = Image.new('RGB', (300, 400), sample_colors[i])
            
            demo_outfits.append({
                "id": i,
                "name": name,
                "type": "Full Outfit",
                "last_worn": (datetime.now() - timedelta(days=days_ago)).isoformat(),
                "features": [0] * 2048,
                "image": self.image_to_base64(img),
                "reset_period": reset_period,
                "wear_count": wear_count  # Add wear count to demo data
            })
        
        self.database["outfits"] = []
        self.database["outfits"].extend(demo_outfits)
        self.save_database()
        st.success("Demo data loaded successfully!")

    def display_wardrobe_grid(self):
        """Display wardrobe items using the UI components"""
        if 'camera_initialized' not in st.session_state:
            st.session_state.camera_initialized = False
        WardrobeUI.inject_vertical_camera_css()
        # Combine items and outfits, include 'collection' key to identify source
        all_items = (
            [{"collection": "items", **item} for item in self.database["items"]] +
            [{"collection": "outfits", **outfit} for outfit in self.database["outfits"]]
        )
        
        def handle_add_view(item_id, collection):
            st.session_state['adding_view_to'] = item_id
            st.session_state['adding_view_collection'] = collection  # 'items' or 'outfits'
        
        def handle_capture(camera):
            image = Image.open(camera)
            existing_id = st.session_state['adding_view_to']
            collection = st.session_state['adding_view_collection']
            is_outfit = (collection == 'outfits')
            
            # Fetch the item from the database
            for item in self.database[collection]:
                if item['id'] == existing_id:
                    item_type = item['type']
                    break
            else:
                st.error("Item not found.")
                return

            success = self.add_new_item_sync(
                image,
                item_type,
                is_outfit=is_outfit,
                existing_id=existing_id
            )
            if success:
                st.success("✅ Added new view!")
                st.session_state.pop('adding_view_to')
                st.session_state.pop('adding_view_collection')
                st.rerun()
        
        # Render the wardrobe grid
        WardrobeUI.render_wardrobe_grid(all_items, self.base64_to_image, handle_add_view)
        
        # Handle view addition modal if needed
        if 'adding_view_to' in st.session_state:
            existing_id = st.session_state['adding_view_to']
            collection = st.session_state['adding_view_collection']
            # Fetch the item from the database
            for item in self.database[collection]:
                if item['id'] == existing_id:
                    WardrobeUI.render_add_view_modal(item, handle_capture)
                    break

    def display_item_card(self, item):
        """Display a single item/outfit card with image and multi-view support"""
        with st.container():
            st.markdown("""
                <style>
                .clothing-card {
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 10px;
                    margin-bottom: 15px;
                }
                </style>
            """, unsafe_allow_html=True)
            
            emoji = self.clothing_categories.get(item.get('type', 'Other'), '👕')
            
            if 'image' in item:
                try:
                    image = self.base64_to_image(item['image'])
                    if image:
                        st.image(image, use_column_width=True)
                except Exception:
                    st.image("placeholder.png", use_column_width=True)
            
            st.markdown(f"### {emoji} {item.get('name', item['type'])}")
            
            # Display wear count
            wear_count = item.get('wear_count', 0)
            st.markdown(f"👕 Worn {wear_count} times")
            
            last_worn = datetime.fromisoformat(item["last_worn"])
            days_since = (datetime.now() - last_worn).days
            days_remaining = max(0, item.get('reset_period', 7) - days_since)
            
            st.warning(f"⏳ {days_remaining} days remaining")
            st.caption(f"Last worn: {last_worn.strftime('%Y-%m-%d')}")
            
            if 'reference_images' in item:
                num_views = len(item['reference_images'])
                st.caption(f"📸 {num_views} views of this item")
            
            # Style recommendations section
            if 'style_recommendations' in item and item['style_recommendations']:
                with st.expander("👔 Style Suggestions"):
                    st.markdown(item['style_recommendations'])
                    if 'style_sources' in item and item['style_sources']:
                        with st.expander("📚 Sources"):
                            for source in item['style_sources']:
                                st.caption(f"- {source}")
            
            # Button to get style advice if not present
            elif 'ai_analysis' in item and 'style_advisor' in st.session_state:
                col3, col4 = st.columns([3, 1])
                with col4:
                    if st.button("Get Style Tips", key=f"get_style_{item['id']}"):
                        with st.spinner("Getting style recommendations..."):
                            style_advice = st.session_state.style_advisor.get_style_advice(item['ai_analysis'])
                            item['style_recommendations'] = style_advice["styling_tips"]
                            item['style_sources'] = style_advice["sources"]
                            self.save_database()
                            st.rerun()

            # Add View button and camera functionality
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("Add View", key=f"add_view_btn_{item['collection']}_{item['id']}"):
                    st.session_state['adding_view_to'] = item['id']
                    st.session_state['adding_view_type'] = 'outfit' if item.get('type') == 'Full Outfit' else 'item'
            
            # Show camera input if Add View was clicked for this item
            if st.session_state.get('adding_view_to') == item['id']:
                camera = st.camera_input(
                    "Take another photo of this item",
                    key=f"camera_view_{item['id']}"
                )
                if camera:
                    image = Image.open(camera)
                    success = self.add_new_item(
                        image,
                        item['type'],
                        is_outfit=(st.session_state['adding_view_type'] == 'outfit'),
                        existing_id=item['id']
                    )
                    if success:
                        st.success("✅ Added new view!")
                        st.session_state.pop('adding_view_to')
                        st.rerun()


    def process_image(self, image, is_outfit=False):
        """Process image with automatic wear count increment for matches"""
        features = self.feature_extractor.extract_features(image, is_full_outfit=is_outfit)
        if features is None:
            return "error", None, 0

        if st.session_state.get('debug_mode', False):
            self.visualize_analysis(image, features)

        # Combine items from wardrobe and listings
        items_to_check = self.database["outfits"] if is_outfit else self.database["items"]
        listings_to_check = self.database.get("listings", [])
        all_items_to_check = items_to_check + listings_to_check

        matching_item = None
        best_similarity = 0
        matching_collection = None

        for item in all_items_to_check:
            try:
                # Use reference_features for matching
                reference_features = [np.array(f) for f in item.get('reference_features', [])]
                if reference_features:
                    similarity = self.feature_extractor.calculate_similarity_multi_view(
                        features,
                        reference_features
                    )
                else:
                    stored_features = np.array(item["features"])
                    similarity = self.feature_extractor.calculate_similarity(features, stored_features)

                if similarity > self.similarity_threshold and similarity > best_similarity:
                    matching_item = item
                    best_similarity = similarity
                    matching_collection = 'listings' if item in listings_to_check else ('outfits' if is_outfit else 'items')
            except Exception as e:
                st.warning(f"Error comparing items: {str(e)}")
                continue

        if matching_item:
            if matching_collection == 'listings':
                # Move the item back to the wardrobe
                self.move_back_from_listings(matching_item['id'])
                st.info(f"Item '{matching_item.get('name', matching_item['type'])}' moved back to wardrobe.")
                # Update the collection to 'items' or 'outfits' as appropriate
                matching_collection = 'outfits' if is_outfit else 'items'

            # Increment wear count
            new_count = self.increment_wear_count(matching_item['id'], matching_collection)
            st.success(f"Updated wear count to {new_count}")
            return "existing", matching_item, best_similarity

        return "new", None, 0

    
    def update_item(self, item_id, collection, new_last_worn, new_wear_count):
        """Update item details only when update button is clicked"""
        try:
            for item in self.database[collection]:
                if item['id'] == item_id:
                    # Update the values only when explicitly called
                    item["last_worn"] = new_last_worn
                    item["wear_count"] = int(new_wear_count)
                    item["reset_period"] = 7
                    self.save_database()
                    return True
            return False
        except Exception as e:
            st.error(f"Error updating item: {str(e)}")
            return False
    def increment_wear_count(self, item_id, collection):
        """Handle wear count increments when matching items"""
        try:
            for item in self.database[collection]:
                if item['id'] == item_id:
                    current_count = item.get("wear_count", 0)
                    item["wear_count"] = current_count + 1
                    item["last_worn"] = datetime.now().isoformat()
                    self.save_database()
                    return item["wear_count"]
            return None
        except Exception as e:
            st.error(f"Error incrementing wear count: {str(e)}")
            return None
    
    def move_to_listings(self, item_id, collection):
        """Move an item to the listings collection."""
        try:
            # First find the item
            item_to_move = None
            for item in self.database[collection]:
                if item["id"] == item_id:
                    item_to_move = item
                    break
            
            if not item_to_move:
                return False
                
            # Check if listings key exists, create if not
            if "listings" not in self.database:
                self.database["listings"] = []
                
            # Check if item is already in listings
            if any(listing["id"] == item_id for listing in self.database["listings"]):
                return False
                
            # Remove the item from the current collection
            self.database[collection] = [
                x for x in self.database[collection] if x["id"] != item_id
            ]

            # Create listing entry
            listing_item = {
                **item_to_move,
                "date_listed": datetime.now().isoformat(),
                "original_collection": collection
            }
            
            # Add to listings
            self.database["listings"].append(listing_item)
            self.save_database()
            return True
            
        except Exception as e:
            st.error(f"Error moving item to listings: {str(e)}")
            return False

    def generate_listing_description(self, item):
        """Generate a listing description for an item."""
        try:
            # Placeholder logic for AI-based generation
            description = f"Check out this amazing {item['type']}! It's perfect for {', '.join(item.get('use_case', ['everyday use']))}."
            return description
        except Exception as e:
            st.error(f"Error generating listing description: {str(e)}")
            return "A wonderful item waiting to find a new home!"
       


    def remove_from_listings(self, item_id):
        """Remove an item from the listings collection."""
        try:
            if "listings" not in self.database:
                return False
                
            # Remove the item from listings
            self.database["listings"] = [
                x for x in self.database["listings"] 
                if x["id"] != item_id
            ]
            
            self.save_database()
            return True
            
        except Exception as e:
            st.error(f"Error removing item from listings: {str(e)}")
            return False

    def get_listings(self):
        """Get all current listings."""
        try:
            if "listings" not in self.database:
                self.database["listings"] = []
                self.save_database()
            return self.database["listings"]
        except Exception as e:
            st.error(f"Error getting listings: {str(e)}")
            return []
    def move_back_from_listings(self, item_id):
        """Move an item from listings back to the appropriate wardrobe collection."""
        try:
            # Find the item in listings
            for item in self.database["listings"]:
                if item["id"] == item_id:
                    # Determine original collection
                    original_collection = item.get("original_collection", "items")
                    # Remove from listings
                    self.database["listings"] = [
                        x for x in self.database["listings"] 
                        if x["id"] != item_id
                    ]
                    # Add back to the wardrobe
                    self.database[original_collection].append(item)
                    self.save_database()
                    return True
            return False
        except Exception as e:
            st.error(f"Error moving item back from listings: {str(e)}")
            return False
