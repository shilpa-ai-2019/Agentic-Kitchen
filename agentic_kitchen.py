import streamlit as st
from time import sleep
import os
from google import genai
from google.genai import types
from google.genai import errors
from streamlit_scroll_to_top import scroll_to_here
from streamlit.logger import get_logger

logger = get_logger(__name__)

# Function to generate recipes recommendations based on user preferences and inputs using GEMINI API
# 1. Initialize the state variable tracking the button's status
if "btn_disabled" not in st.session_state:
    st.session_state.btn_disabled = False

if "animateText" not in st.session_state:
    st.session_state.animateText = True # Set to True to enable text animation for the first time, False to disable

# 2. Define the callback function to change the state
def generate_recipes_recommendations():
    logger.info("-"*25)
    logger.info('Generate Recipes Button clicked!')
    if st.session_state.userSearchTerm.strip() == "" and st.session_state.userSearchTermType == "Food Dishes":
        show_error_alert_popup("Please enter the dish names (comma separated) and then click 'Generate Recipes'!   \n**Note:** _'Food Dishes'_ is currently selected in the _'What are you looking for?'_ section.")
        # TODO: Limitation: Yet not able to set focus to the input field for better user experience
        return

    if st.session_state.userSearchTerm.strip() == "" and st.session_state.userSearchTermType == "Recipes from Ingredients":
        show_error_alert_popup("Please enter the ingredients you have (comma separated) and then click 'Generate Recipes'!   \n**Note:** _'Recipes from Ingredients'_ is currently selected in the _'What are you looking for?'_ section.")
        # TODO: Limitation: Yet not able to set focus to the input field for better user experience
        return
    st.toast(":rainbow[Generating the recipes tailored for you..] 🍲", icon="⏳", duration=2)
    st.session_state.btn_disabled = True
    userInputDictionary = {
        "nickname": st.session_state.nickname or "User",
        "servings": st.session_state.servings,
        "dietType": st.session_state.dietType or ["Vegetarian"],
        "cuisine_types": st.session_state.cuisine_types or ["multi-cuisine"],
        "userSearchTermType": st.session_state.userSearchTermType or "Just a few easy recipes",
        "recommendations_count": st.session_state.expected_recommendations_count,
        "userSearchTerm": st.session_state.userSearchTerm,
        "language": st.session_state.language or "English",
        "meal_types": st.session_state.meal_types or ["Dinner"],
        "skill_level": st.session_state.skill_level or "Beginner",
        "restrictions": st.session_state.restrictions or ["no restrictions and allergies"],
        "nutritionalLimits": st.session_state.nutritionalLimits or ["calories"],
        "provideTips": st.session_state.provideTips
        }
    generate(userInputDictionary)

def enable_button():
    # print('-- Enable button --')
    st.session_state.btn_disabled = False

# Define the popup structure using the dialog decorator
@st.dialog("Attention❗")
def show_error_alert_popup(message):
    st.write(message)
    # if st.button("OK"): # 
        # st.rerun()  # Programmatically closes the dialog

def generate(userInputDictionary):
    logger.info("Generating recipes based on user preferences and inputs.")
    logger.info(f"User Food choices: {userInputDictionary}")

    user_key = st.session_state.users_gemini_api_key.strip() if st.session_state.users_gemini_api_key else None
    # from streamlit secrets
    paid_key = st.secrets.get("GEMINI_PAID_API_KEY")
    free_key = st.secrets.get("GEMINI_FREE_API_KEY")

    attempt_keys = []
    if user_key:
        attempt_keys.append(("user", user_key))
    else:
        if paid_key:
            attempt_keys.append(("paid", paid_key))
        if free_key:
            attempt_keys.append(("free", free_key))

    if not attempt_keys:
        enable_button()
        scroll_to_here(0, key="scroll_top")
        show_error_alert_popup("No Gemini API key available. Please enter your own GEMINI API key to continue.")
        return

    # for easy to create prompts using f-string templates
    nickname1 = userInputDictionary['nickname']
    servings1 = userInputDictionary['servings']
    dietType1 = ', '.join(userInputDictionary['dietType'])
    cuisine_types1 = ', '.join(userInputDictionary['cuisine_types'])
    userSearchTermType1 = userInputDictionary['userSearchTermType']
    userSearchTerm1 = userInputDictionary['userSearchTerm']
    if userInputDictionary['language'] != "English":
        language1 = userInputDictionary['language'] + " with English translation of recipe name and ingredients for better understanding OR else provide the recipe in English with " + userInputDictionary['language'] + " translation of recipe name and ingredients for better understanding"
    else:
        language1 = "English" 
    
    meal_types1 = ', '.join(userInputDictionary['meal_types'])
    skill_level1 = userInputDictionary['skill_level']
    restrictions1 = ', '.join(userInputDictionary['restrictions'])
    nutritionalLimits1 = ', '.join(userInputDictionary['nutritionalLimits'])
    provideTips1 = userInputDictionary['provideTips']
    updatedSearchTerm1 = f""

    if st.session_state.userSearchTermType == "Food Dishes":
        updatedSearchTerm1 = f" Provide recipes for '{userSearchTerm1}'"
        cuisine_types1 = "multi-cuisine" # Override cuisine type to multi-cuisine when user is looking for specific dishes, as they may belong to different cuisines. This will help the model to not limit the recipe suggestions to a specific cuisine and provide more relevant results.
        dietType1 = "based on asked dish recipes" # Override diet type to any when user is looking for specific dishes, as they may want to see recipes for the specified dishes across different diet types (vegetarian, vegan, non-vegetarian) and not limit the suggestions to a specific diet type. This will help the model to provide more relevant results based on the user's search term.
        meal_types1 = "any meal type" # Override meal type to any when user is looking for specific dishes, as they may want to see recipes for the specified dishes across different meal types and not limit the suggestions to a specific meal type. This will help the model to provide more relevant results based on the user's search term.
    elif st.session_state.userSearchTermType == "Recipes from Ingredients":
        updatedSearchTerm1 = f" Recommend {st.session_state.expected_recommendations_count} recipes based on the ingredients '{userSearchTerm1}'"
        dietType1 = "based on ingredients" # Override diet type to any when user is looking for specific dishes, as they may want to see recipes for the specified dishes across different diet types (vegetarian, vegan, non-vegetarian) and not limit the suggestions to a specific diet type. This will help the model to provide more relevant results based on the user's search term.
    else:   
        updatedSearchTerm1 = f" Recommend {st.session_state.expected_recommendations_count}  easy recipes"

    promptTextTemplate=f"""
    {updatedSearchTerm1} for {nickname1}.  
    {nickname1}'s current food preferences are:
    - Servings: {servings1}
    - Diet Type: {dietType1}
    - Preferred Cuisines: {cuisine_types1}
    - Preferred Recipe Language: {language1}
    - Preferred Meal Type: {meal_types1}
    - Cooking Skill Level: {skill_level1}
    - Dietary Restrictions & Allergies: {restrictions1}
    - Nutritional Limits: {nutritionalLimits1}
    - Provide healthy and hygienic cooking and storage tips: {provideTips1}

    Consider the above preferences as applicable and recommend healthy and easy to make recipes. Provide recipes in clear, step-by-step format, including approximate cooking time and how many people the meal should serve.
    Add emojis related to the recipes and cuisines to make it more visually appealing.
    Provide new recipes every time.
    Provide food recipe's sustainability footprint for each recipe and it's ingredients.
    Include tips on how to make cooking more sustainable and reduce food waste, where relevant.
    Ocassionally, you can also provide short interesting story OR fun fact related to any recipe OR some other engaging content like quotes about cooking, as a suprise element for the user.
    """
    logger.info("Prompt Text Template: " + promptTextTemplate)
    #--- TESTING WITH STATIC CONTENT WITHOUT CALLING THE API TO IMPROVE DEVELOPMENT SPEED AND ITERATE FASTER ON UI/UX AND OTHER NON-API RELATED ASPECTS ---
    # sleep(2) # Adding a short delay before starting the generation to improve user experience and allow the toast message to be visible for a moment before the generation starts.
    # scroll_to_here(0, key="scroll_top")
    # st.toast(f":rainbow[All done with customized cooking ideas for you..] 🍲 ✅", icon="🎉", duration=2)
    # st.session_state.animateText = True
    # st.session_state.recipes_search_result = testRecipeText
    # print("="*25)
    # enable_button()
    # return
    # --- END OF TESTING WITH STATIC CONTENT ---

    model = "gemini-2.5-flash-lite"#"gemini-3-flash-preview"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=promptTextTemplate),
            ],
        ),
    ]
    tools = [
        types.Tool(googleSearch=types.GoogleSearch(
        )),
    ]
    try:
        generate_content_config = types.GenerateContentConfig(
            # thinking_config=types.ThinkingConfig(
            #     thinking_level="HIGH",
            # ),
            tools=tools,
            system_instruction=[
                types.Part.from_text(text="""You are a helpful cooking assistant specialised in multi-cuisine low calorie, healthy recipes. Your task is to suggest recipes based mainly on either ingredients or dish name. User may also ask for any random recipes. User preferences will be provided. Always stick to recipe suggestions and cooking advice. If asked about anything unrelated to cooking and nutrition, politely redirect the conversation back to cooking ideas. Provide recipes in clear, step-by-step format, including approximate cooking time and how many people the meal should serve."""),
            ],
        )

        def run_generation(api_key: str) -> str:
            client = genai.Client(api_key=api_key)
            finalContent = ""
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            ):
                if text := chunk.text:
                    finalContent += text
            return finalContent

        logger.info('-- Generating content --')
        finalContent = ""
        for source, api_key in attempt_keys:
            try:
                if source == "paid":
                    logger.info("Trying GEMINI_PAID_API_KEY first.")
                elif source == "free":
                    logger.info("Retrying with GEMINI_FREE_API_KEY after paid key quota error.")

                finalContent = run_generation(api_key)
                break
            except errors.APIError as e:
                # if source == "paid" '''and e.code == 429''' and free_key:
                if source == "paid" and free_key:
                    logger.info("*** Error {} with Paid Gemini key. Retrying with free key ***".format(e.code))
                    continue
                raise

        logger.info('-- Content generation completed --')
        # print(finalContent)
        scroll_to_here(0, key="scroll_top")
        st.toast(f":rainbow[All done with customized cooking ideas for you..] 🍲 ✅", icon="🎉", duration=2)
        st.session_state.animateText = True
        st.session_state.recipes_search_result = finalContent
        logger.info("-"*25)
        enable_button()
        
    except errors.APIError as e:
        # errors thrown after trying with user entered API key OR retrying with default paid-free keys sequence from above try-catch of above for loop
        
        # 1. Get the HTTP status code (e.g., 400, 403, 404, 500, 503)  and *Notify additional details for 429 RESOURCE_EXHAUSTED error code*
        st.session_state.animateText = False # Disable text animation for subsequent generations after an error occurs, to improve user experience and avoid long animations when the error message is already displayed.
        error_code = e.code
        # 2. Get the human-readable message or JSON error dictionary string
        error_message = e.message.strip().replace("*", "")  # Remove extra whitespace and newlines for better readability in the popup

        if error_code == 429 and not st.session_state.users_gemini_api_key:  # RESOURCE_EXHAUSTED error code, apps default API key quota limits exceeded
            logger.info("*** Error {} with out default Gemini keys ***".format(e.code))
            error_message += "  \n**Note:** _Our default Gemini token hit quota.   \nYou may please try entering your own GEMINI API key in the :color[❮❮]{foreground='#ff00ff'} left panel and then click 'Generate Recipes' button again.  \nIf the issue persists, it is likely due to exceeding the quota limits of either our default GEMINI API key or your own. \nWe apologize for the inconvenience and appreciate your patience and understanding._"
        elif error_code == 429 and st.session_state.users_gemini_api_key: # RESOURCE_EXHAUSTED error code, user's API key quota limits exceeded
            logger.info("*** Error {} with user's Gemini key ***".format(e.code))
            error_message += "  \n**Note:** _Your GEMINI API key has hit its quota limit.   \nPlease check the quota limits, validity and usage of your API key or try a different key.  \nIf you have exceeded the quota limits, you may need to wait for the quota to reset or consider upgrading your plan for higher limits.  \nIf you believe this error is a mistake and you have not exceeded any quota limits, please contact respective support for further assistance._"
        else:
            logger.info("*** Non-429 Google API Error {} occurred ***".format(e.code))
            if st.session_state.users_gemini_api_key:
                error_message += "  \n**Note:** _Error is associated with your own GEMINI API key.   \nPlease check the quota limits, validity and usage of your API key or try a different key._"
            else:
                error_message += "  \n**Note:** _Error is most likely due to our default GEMINI API key.   \nYou may please try entering your own GEMINI API key in the :color[❮❮]{foreground='#ff00ff'} left panel and then click 'Generate Recipes' button again.   \nWe apologize for the inconvenience and appreciate your patience and understanding._"
        
        enable_button()
        scroll_to_here(0, key="scroll_top")
        logger.error(f"Google API Error ({error_code}): {error_message}")
        show_error_alert_popup(f"Google API Error ({error_code}): {error_message}")
    except errors.ServerError as e:
        st.session_state.animateText = False # Disable text animation for subsequent generations after an error occurs, to improve user experience and avoid long animations when the error message is already displayed.
        enable_button()
        scroll_to_here(0, key="scroll_top")
        logger.error(f"Unexpected Server Issue ({e.code}): Google's endpoint failed. Implement a backoff retry.")
        show_error_alert_popup(f"Unexpected Server Issue ({e.code}): Google's endpoint failed. Implement a backoff retry.")
    except Exception as e:
        st.session_state.animateText = False # Disable text animation for subsequent generations after an error occurs, to improve user experience and avoid long animations when the error message is already displayed.
        enable_button()
        scroll_to_here(0, key="scroll_top")
        logger.error(f"Unexpected error occurred: {e}")
        show_error_alert_popup(f"Unexpected error occurred: {e}")

# SIDEBAR - USER INPUTS
@st.fragment # to avoid refreshing the entire sidebar and page on every interaction and only update the relevant components
def sidebarFoodPrefFormControls():
    st.subheader("Your Preferences")
    # Update session state if needed for ALL recipes generations based on user preferences input, to maintain consistency across the app and avoid losing user inputs on re-rendering of the sidebar.
    # nickname
    st.session_state.nickname = st.text_input("Nickname", placeholder = "user name   ₍^. .^₎⟆", max_chars=10)
    # st.session_state.nickname = nickname
    # userSearchTermType and userSearchTerm
    userSearchTermType = st.selectbox("What are you looking for?", ["Just a few easy recipes","Food Dishes", "Recipes from Ingredients"])
    st.session_state.userSearchTermType = userSearchTermType
    if userSearchTermType == "Food Dishes":
        userSearchTerm = st.text_input("Enter the dish names (comma separated) *", placeholder="e.g. Palak Paneer, Batata vada, Veggie Stir Fry, etc.", max_chars=100,)
    elif userSearchTermType == "Recipes from Ingredients":
        userSearchTerm = st.text_input("Enter the ingredients you have (comma separated) *", placeholder="e.g. Paneer, rice, tomatoes, potatoes, etc.", max_chars=100,)
    else:   
        # userSearchTerm = st.sidebar.text_input("Anything", "Few easy recipes", disabled=True)
        userSearchTerm = "Anything, Few easy recipes"

    st.session_state.userSearchTerm = userSearchTerm
    # servings
    servings = st.number_input("Servings", min_value=1, step=1)
    st.session_state.servings = servings
    # dietType
    dietType = st.multiselect("Diet Type", ["Vegetarian", "Vegan", "Non-Vegetarian"], default=["Vegetarian"],max_selections=2,accept_new_options=True,help="_Enter your diet type preference. You can select multiple options or add new ones as per your needs. If you are looking for recipes based on ingredients, the diet type will be automatically set to 'based on ingredients' to provide more relevant results. If you are looking for specific dishes, the diet type will be automatically set to 'based on asked dish recipes' to provide more relevant results based on the specified dishes._")
    st.session_state.dietType = dietType
    # cuisine_types
    cuisine_types = st.multiselect("Cuisine", ["Indian (South Asian)", "Italian (European)", "Mexican (North American)", "Japanese (East Asian)", "Thai (Southeast Asian)"],default=["Indian (South Asian)"], max_selections=3, accept_new_options=True,
    help="_Select your preferred cuisines. You can select multiple options or add new ones as per your needs. If you are looking for specific dishes, the cuisine type will be automatically set to 'multi-cuisine' to provide more relevant results based on the specified dishes which may belong to different cuisines. If you are looking for recipes based on ingredients, the cuisine type will not be overridden and the selected cuisine preferences will be considered for providing the results._")
    st.session_state.cuisine_types = cuisine_types
    # meal_types
    meal_types = st.multiselect("Meal Type", ["Lunch", "Breakfast", "Dinner", "Brunch", "Supper", "Snack", "Dessert"], default=["Dinner"],max_selections=3)
    st.session_state.meal_types = meal_types
    # skill_level
    skill_level = st.selectbox("Skill Level", ["Beginner", "Intermediate", "Advanced", "Any"])
    st.session_state.skill_level = skill_level
    # language
    language = st.selectbox(
        "Preferred Recipe Language",
        ["English", "Arabic", "Bengali", "Chinese (Simplified and Traditional)", "Danish", "Dutch", "French", "German", "Gujarati", "Hindi", "Hungarian", "Indonesian", "Italian", "Japanese", "Kannada", "Latvian", "Lithuanian", "Malayalam", "Marathi", "Norwegian", "Polish", "Portuguese", "Romanian", "Russian", "Slovenian", "Spanish", "Swahili", "Swedish", "Tamil", "Telugu", "Thai", "Turkish", "Ukrainian", "Urdu", "Vietnamese"]
        ,help="_Select your preferred language for the recipes. The recipes could be provided in combination of that language and English. Default is English._"
    )
    st.session_state.language = language
    # recommendations_count
    expected_recommendations_count = 3 # default value
    if userSearchTermType == "Recipes from Ingredients":
        expected_recommendations_count = st.number_input("Number of Recommendations", min_value=1, step=1, max_value=10, value=3)

    st.session_state.expected_recommendations_count = expected_recommendations_count
    # restrictions and allergies
    restrictions = st.multiselect(
        "Restrictions & Allergies:",
        ["nuts", "dairy", "gluten","shellfish","avocado"],
        max_selections=7,
        accept_new_options=True,
        help="_Select any dietary restrictions or allergies you have. You can choose multiple options or add new ones as per your needs._"
    )
    st.session_state.restrictions = restrictions
    # nutritionalLimits
    nutritionalLimits = st.multiselect(
        "Limit:",
        ["calories", "sodium", "sugar", "oil"],
        default=["calories"],
        max_selections=7,
        accept_new_options=True,
        help="_Select any nutritional limits you wish to set. You can choose multiple options or add new ones as per your needs._"
    )
    st.session_state.nutritionalLimits = nutritionalLimits
    # provideTips
    provideTips = st.radio(
        "Should provide tips on healthy, efficient and hygienic cooking and storage?",
        ["Yes", "No"],
        help="_Select whether you want tips on healthy, efficient and hygienic cooking and storage. Default is Yes._"
    )
    st.session_state.provideTips = provideTips
    # gemini API key input
    user_entered_gemini_api_key = st.text_input("GEMINI API Key", type="password", placeholder ="(Optional but recommended) GEMINI API key", max_chars=80, help="_Enter your own GEMINI API key for a seamless experience or leave it blank to use our default key. Follow the instructions at https://ai.google.dev/gemini-api/docs/api-key to create and manage your own API keys in Google AI Studio. Please check the privacy note below for more details on how the GEMINI API key is used in this App._")
    st.session_state.users_gemini_api_key = user_entered_gemini_api_key
# @st.fragment sidebarFoodPrefFormControls() --- END OF FRAGMENT ---

# ---- for Disclaimer and Notes in the sidebar ----
    
def additional_info_with_Feedback_UPIPayPal_PrivacyNote_Disclaimer():
    st.markdown("---")
    with st.expander("⛶ Buy me a cup of tea! ☕️", expanded=True):
        st.caption("If you find this app helpful, consider buying me a cup of tea! ☕️ धन्यवाद!")
        with st.expander("🌏 PayPal", expanded=True):
            # TODO: Limitation: yet not able to hide fullscreen option on hovering the image of st.image, need to find a workaround for that to improve user experience
            st.image("images/paypal_qr.jpg")
        with st.expander("🇮🇳 UPI", expanded=True):
            st.image("images/upi_qr.jpg")
    with st.expander("Feedback ✍️💡", expanded=True):
        st.caption("Got feedback or an idea for a new agentic AI project? We’d love to hear it — just click the feedback button!")
        contact_email = "agentic.swayampakghar@gmail.com"
        subject = "Feedback: Agentic SwayampakGhar(स्वयंपाकघर) App"
        # Construct the mailto URL
        mailto_url = f"mailto:{contact_email}?subject={subject}"
        st.link_button("📧 Feedback", mailto_url)
    with st.expander("🔐 **Privacy Note:**"):
        st.caption("""The GEMINI API key you enter is used solely for making requests to the GEMINI API and the App does not store or share it.   \nPlease check https://streamlit.io/privacy-policy for more details on Streamlit's privacy practices.   \n The app does not store any of your preferences or inputs after the session ends. However, during the session, your inputs are stored in the session state to provide a seamless and interactive experience.   \nBy using the app, you acknowledge and agree to this privacy note.""")
    with st.expander("⚠️ **Disclaimer:**"):
        st.caption("""The recipes and culinary suggestions provided by this AI assistant are generated by artificial intelligence and may include mistakes.   \nWhile we strive to provide accurate and functional recipes, the AI may produce errors.   \nIt is your sole responsibility to verify food safety, proper cooking temperatures, and check for potential allergens.   \nWe are not liable for any adverse reactions, foodborne illnesses, or property damage resulting from the use of these recipes.   \nWe hereby disclaim any responsibility for the AI generated content or external websites linked to or from this App and accept no responsibility whatever should they contain offensive or illegal or inaccurate content of any nature or infringe on any copyright or contravene any national laws.""")

with st.sidebar:
    sidebarFoodPrefFormControls()
    st.button("Generate Recipes", on_click=generate_recipes_recommendations,disabled=st.session_state.btn_disabled, type="primary")
    additional_info_with_Feedback_UPIPayPal_PrivacyNote_Disclaimer()

# STREAMLIT APP MAIN PAGE
st.set_page_config(page_title="🍽 Agentic SwayampakGhar(स्वयंपाकघर)", layout="wide")
logger.info("App loaded successfully.")
st.caption("") # Adding some space between the top of the page and the title for better visibility when scrolled to top.
st.title("🎛️ 🔥 SwayampakGhar(स्वयंपाकघर) - Eat Healthy, Stay Healthy 🍲 🍽")
st.markdown("""
    Welcome to the **Agentic SwayampakGhar(स्वयंपाकघर)**, Your own multicuisine culinary assistant. सुस्वागतम्!  
    Our goal is to help you master meal prep with these tips for planning, cooking, and storing nutritious meals that save time and help you stay on track with your health goals. 🌱  
""")
st.caption("The Marathi word **Swayampak(स्वयंपाक)** originates from Sanskrit and literally translates to **'cooking by oneself'**.  \nIt is formed by combining two root words: 1) Swayam (स्वयं): Meaning 'self' or 'by oneself'. 2) Paka (पाक): Meaning 'cooking' or 'ripening'.  \nIt is a broad term frequently used across Indian culture to refer to traditional home cooking, or the culinary arts.  \n**SwayampakGhar (स्वयंपाकघर)** is a Marathi word that translates to **Kitchen**.  \n However, we offer more than just Indian cuisine with our Agentic SwayampakGhar 😊")
st.caption("© 2026 Shilpa Kulkarni")
st.markdown("📋 Enter your preferences in the :color[❮❮]{foreground='#ff00ff'} left panel and click 'Generate Recipes' button to receive recommendations right away! :rainbow[♨ 𓌉◯𓇋]")
st.divider()
# -------------------------------------------------------------------------------

if "recipes_search_result" not in st.session_state:
    st.session_state.recipes_search_result = ":rainbow[♡𓌉◯𓇋₊˚⊹♡]   The generated recipes and cooking tips will appear here based on your preferences!   :rainbow[♡𓌉◯𓇋₊˚⊹♡]"

resultsMarkdown = st.markdown("")
if st.session_state.animateText:
    resultsMarkdown.markdown("") # Clear the markdown before starting animation
    text = st.session_state.recipes_search_result
    displayed_text = ""
    for char in text:
        displayed_text += char
        resultsMarkdown.markdown(displayed_text)
        # 0.7 milliseconds delay between each character for animation effect, adjust as needed for faster or slower animation. Note that very long texts may take a while to animate with longer delays, so choose the delay value accordingly based on the length of the generated content and desired user experience.
        sleep(0.00065)  # Adjust the speed of animation here, value mentioned is in seconds (0.001 means 1 millisecond delay between each character)
    st.session_state.animateText = False # Reset the animation state after animating the text
else:
    resultsMarkdown.markdown(st.session_state.recipes_search_result)

# Test recipe text for testing with static content without calling the API to improve development speed and iterate faster on UI/UX and other non-API related aspects
testRecipeText = """ 
### Healthy Gulab Jamun (Milk-Based Sweet Dumplings)

Gulab Jamun is a classic Indian dessert. We'll make a healthier version using whole wheat flour and baking instead of frying for a lower-calorie treat.

**Approximate Cooking Time:** 30-40 minutes
**Servings:** 1 (2-3 small gulab jamuns)

**Ingredients:**

**For Gulab Jamun:**
*   2 tablespoons whole wheat flour (atta)
*   1 tablespoon milk powder (optional, for richness)
*   1 tablespoon grated paneer or ricotta cheese (optional, for softness)
*   1/2 teaspoon ghee or unsalted butter
*   A pinch of baking soda
*   Milk, to knead (start with 1-2 tablespoons)
*   Oil or ghee for greasing baking tray

**For Sugar Syrup:**
*   1/2 cup water
*   1/4 cup sugar (you can reduce this further if you prefer less sweet)
*   2-3 green cardamom pods, lightly crushed
*   A few strands of saffron (kesar), optional

**Instructions:**

**1. Prepare the Sugar Syrup:**
    *   In a small saucepan, combine water, sugar, and crushed cardamom pods.
    *   Heat gently, stirring until the sugar dissolves completely.
    *   Bring to a boil and simmer for 2-3 minutes until it becomes slightly sticky (one-string consistency is not required, just a light syrup).
    *   Add saffron (if using) and stir. Keep the syrup warm.

**2. Prepare the Gulab Jamun Dough:**
    *   In a bowl, combine whole wheat flour, milk powder (if using), grated paneer/ricotta (if using), ghee/butter, and baking soda.
    *   Mix well to combine.
    *   Gradually add milk, a tablespoon at a time, and knead into a soft, smooth dough. Do not over-knead. The dough should be pliable and not sticky.

**3. Shape and Bake:**
    *   Grease a baking tray with a little oil or ghee.
    *   Divide the dough into 2-3 small portions.
    *   Shape each portion into small, smooth balls, ensuring there are no cracks.
    *   Place the balls on the greased baking tray.
    *   Preheat your oven or toaster oven to 180°C (350°F).
    *   Bake for 12-15 minutes, or until the gulab jamuns are lightly golden brown. Keep an eye on them to prevent over-browning.

**4. Soak and Serve:**
    *   Carefully remove the baked gulab jamuns from the oven.
    *   Immediately drop them into the warm sugar syrup.
    *   Let them soak for at least 15-20 minutes to absorb the syrup.
    *   Serve warm.

---

### Healthy Cooking & Storage Tips:

**For Chhole Bhature:**
*   **Lowering Calories:** The main calorie contributor is the deep-fried bhatura. Baking or air-frying the bhatura significantly reduces the fat content. You can also use whole wheat flour for the bhature to add fiber.
*   **Flavor Boost:** Use fresh ginger and garlic instead of paste for a more vibrant flavor. A pinch of dried mango powder (amchur) can add a nice tanginess to the chhole.
*   **Storage:** Chhole can be stored in an airtight container in the refrigerator for up to 2-3 days. Reheat gently on the stovetop or in the microwave. Baked bhature are best consumed fresh, but any leftovers can be stored in an airtight container at room temperature for a day and lightly reheated.

**For Gulab Jamun:**
*   **Healthier Sweetening:** Reduce the sugar in the syrup as much as you prefer. You can also explore natural sweeteners like dates or stevia in moderation, but this might alter the traditional taste and texture.
*   **Baking vs. Frying:** Baking is a much healthier alternative to deep-frying Gulab Jamun, cutting down on significant fat and calories.
*   **Texture Tip:** Ensure the dough for Gulab Jamun is soft and smooth. Over-kneading can make them hard.
*   **Storage:** Gulab Jamun soaked in syrup can be stored in an airtight container in the refrigerator for up to 4-5 days. They taste even better the next day as the flavors meld further. Reheat gently before serving.

Enjoy your delicious and healthy homemade meal!

---

**Fun Fact:** Did you know that Gulab Jamun's origin is believed to be Persian? The name "Gulab" comes from the Persian words "gul" (flower) and "ab" (water), referring to the rose-scented syrup, and "Jamun" is the Hindi word for a dark purple, plum-like fruit, which the dessert resembles in shape and color.
"""


    


