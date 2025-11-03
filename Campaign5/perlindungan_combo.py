from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple, Union
import logging
import json
import asyncio
from datetime import datetime, date
import sys
from pathlib import Path

# Add parent directory to path to access main.py
sys.path.append(str(Path(__file__).parent.parent))

# Configure module logger once
logger = logging.getLogger(__name__)
if not logger.handlers:
    # Basic configuration only if no handlers exist (won't override app-level config)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Try to import Google Sheets helper (it's optional for tests)
try:
    from Google_Sheet import append_row_to_sheet
except Exception as e:
    append_row_to_sheet = None
    logger.warning("Google_Sheet.append_row_to_sheet not available: %s", e)

# Import active_conversations from main if available
try:
    from main import active_conversations
except Exception:
    active_conversations = {}
    logger.warning("Could not import active_conversations from main")


def format_currency(amount: float) -> str:
    try:
        return f"RM {float(amount):,.2f}"
    except Exception:
        return f"RM {amount}"


@dataclass
class CampaignState:
    """State management for Perlindungan Combo campaign."""
    current_step: str = "welcome"
    user_data: Dict[str, Any] = field(default_factory=dict)
    age: Optional[int] = None
    package_tier: Optional[int] = None


class PerlindunganComboCampaign:
    """Main handler for Perlindungan Combo campaign."""

    _instance = None

    # Standardized button configurations
    BUTTONS = {
        'welcome': [
            {"label": "📚 Learn More", "value": "learn_more"},
            {"label": "❌ Not Now", "value": "not_now"}
        ],
        'package_selection': [
            {"label": "1️⃣ Silver - Essential Protection", "value": "1"},
            {"label": "2️⃣ Gold - Balanced Protection", "value": "2"},
            {"label": "3️⃣ Platinum - Comprehensive Protection", "value": "3"}
        ],
        'confirmation': [
            {"label": "✅ Yes, Proceed", "value": "yes"},
            {"label": "❌ No, Choose Another Package", "value": "no"}
        ],
        'agent_contact': [
            {"label": "✅ Yes, Contact Me", "value": "yes"},
            {"label": "❌ No Thanks", "value": "no"}
        ],
        'navigation': [
            {"label": "🏠 Main Menu", "value": "main_menu"}
        ]
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def get_buttons(self, button_type: str) -> List[Dict[str, str]]:
        """Get standardized button configuration by type."""
        return self.BUTTONS.get(button_type, [])

    def create_button_response(self, message: str, button_type: str, **kwargs) -> Dict[str, Any]:
        """Create a standardized button response."""
        response = {
            "type": "buttons",
            "response": message,
            "content": message,
            "buttons": self.get_buttons(button_type)
        }
        response.update(kwargs)
        logger.info("[create_button_response] Created response with buttons: %s", button_type)
        logger.debug("[create_button_response] Full response: %s", json.dumps(response, indent=2, default=str))
        return response

    def __init__(self):
        if not getattr(self, 'initialized', False):
            self.states: Dict[str, CampaignState] = {}
            self.last_active: Dict[str, float] = {}
            self.name = "Perlindungan Combo"
            self.description = "A comprehensive protection plan combining life, medical, and critical illness coverage"
            self.initialized = True

            # Package details
            self.package_names = {
                1: "Silver - Essential Protection",
                2: "Gold - Balanced Protection",
                3: "Platinum - Comprehensive Protection"
            }

    def get_state(self, user_id: str) -> CampaignState:
        """Get or create state for a user."""
        if user_id not in self.states:
            self.states[user_id] = CampaignState()
        self.last_active[user_id] = datetime.now().timestamp()
        return self.states[user_id]

    def calculate_combo_tier(self, age: int, package_tier: int) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """
        Calculates premium based on a pre-defined package tier and age band.

        Returns:
            tuple: (annual_premium, monthly_premium, error_message)
        """
        package_bands = {
            1: {  # Silver - Essential Protection
                '18-25': 2400,
                '26-35': 2800,
                '36-44': 3600,
                '45-54': 4000
            },
            2: {    # Gold - Balanced Protection
                '18-25': 3500,
                '26-35': 3600,
                '36-44': 4200,
                '45-54': 5000
            },
            3: {  # Platinum - Comprehensive Protection
                '18-25': 4000,
                '26-35': 5400,
                '36-44': 6300,
                '45-54': 8400
            }
        }

        try:
            if package_tier not in package_bands:
                return None, None, "Invalid package tier. Please choose 1, 2, or 3."

            if 18 <= age <= 25:
                age_band = '18-25'
            elif 26 <= age <= 35:
                age_band = '26-35'
            elif 36 <= age <= 44:
                age_band = '36-44'
            elif 45 <= age <= 54:
                age_band = '45-54'
            else:
                return None, None, "Combo plans are typically for ages 18-54. Please consult our advisor for alternative options."

            annual_premium = package_bands[package_tier][age_band]
            monthly_premium = round(annual_premium / 12.0, 2)
            return float(annual_premium), float(monthly_premium), None

        except Exception as e:
            logger.error("Error in calculate_combo_tier: %s", e, exc_info=True)
            return None, None, f"An error occurred while calculating your premium: {str(e)}"

    async def send_message(self, message: str, ws: Any = None) -> str:
        """Helper to send text through WebSocket if available."""
        if not message or not isinstance(message, str):
            logger.warning("Attempted to send empty or invalid message")
            return ""

        logger.info("[PerlindunganCombo] Sending message: %.100s", message)
        if ws:
            try:
                # Some WebSocket libs use send_text, others use send; handle both gracefully
                send_func = getattr(ws, "send_text", None) or getattr(ws, "send", None)
                if send_func:
                    await send_func(json.dumps({
                        "type": "message",
                        "content": message,
                        "is_user": False
                    }))
            except Exception as e:
                logger.error("Error sending message: %s", e, exc_info=True)
        return message

    async def send_buttons(self, text: str, buttons: List[Dict[str, str]], ws: Any = None) -> str:
        """Send buttons through WebSocket if available, fallback to text."""
        if not text or not isinstance(text, str):
            logger.warning("Attempted to send buttons with empty or invalid message")
            text = "Please select an option:"

        if not buttons or not isinstance(buttons, list):
            logger.warning("No valid buttons provided, sending as text")
            return await self.send_message(text, ws)

        logger.info("[PerlindunganCombo] Sending buttons: %.100s", text)

        valid_buttons = []
        for btn in buttons:
            if not isinstance(btn, dict) or 'label' not in btn or 'value' not in btn:
                logger.warning("Skipping invalid button: %s", btn)
                continue
            valid_buttons.append({
                'label': str(btn['label']),
                'value': str(btn['value'])
            })

        if not valid_buttons:
            logger.warning("No valid buttons to send")
            return await self.send_message(text, ws)

        fallback = f"{text}\n" + "\n".join(
            f"{i + 1}. {btn.get('label', 'Option')}"
            for i, btn in enumerate(valid_buttons)
        )

        if ws:
            try:
                send_func = getattr(ws, "send_text", None) or getattr(ws, "send", None)
                if send_func:
                    await send_func(json.dumps({
                        "type": "buttons",
                        "content": text,
                        "buttons": valid_buttons,
                        "is_user": False
                    }))
                    return text
            except Exception as e:
                logger.error("Error sending buttons: %s", e, exc_info=True)
                return await self.send_message(fallback, ws)

        return await self.send_message(fallback, ws)

    def _create_response(self, response_type: str, message: str, buttons: Optional[List[Dict[str, str]]] = None,
                         next_step: Optional[str] = None, campaign_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a standardized response dictionary."""
        if campaign_data is None:
            campaign_data = {}

        response = {
            "type": response_type,
            "response": message,
            "content": message,
            "campaign_data": campaign_data
        }

        if buttons is not None:
            response["buttons"] = buttons
        if next_step is not None:
            response["next_step"] = next_step

        return response

    def _get_welcome_response(self) -> Dict[str, Any]:
        """Helper method to get welcome message and buttons."""
        welcome_msg = self.get_welcome_message()
        return self.create_button_response(
            message=welcome_msg,
            button_type='welcome',
            next_step='after_welcome'
        )

    def _get_plan_explanation_response(self) -> Dict[str, Any]:
        """Helper method to get plan explanation and next steps."""
        return self._create_response(
            response_type="buttons",
            message=self.get_plan_explanation(),
            buttons=self.get_buttons('package_selection'),
            next_step="after_explanation"
        )

    def _get_plan_estimate_message(self, age: int, package_tier: int) -> Tuple[str, float, float, str]:
        """Generate the plan estimate message and return it along with premium details."""
        coverage_details = {
            1: "Life: RM 100,000 \n Critical Illness: RM 50,000 \n Medical Card: RM 180,000",
            2: "Life: RM 150,000 \n  Critical Illness: RM 75,000 \n Medical Card: RM 180,000",
            3: "Life: RM 200,000 \n Critical Illness: RM 100,000 \n Medical Card: RM 1,000,000"
        }
        annual_premium, monthly_premium, error = self.calculate_combo_tier(age, package_tier)
        if error:
            raise ValueError(error)

        response_msg = (
            f"🔍 *Your Combo Plan Estimate*\n"
            f"• Package: {self.package_names.get(package_tier, 'Unknown')}\n"
            f"• Age: {age} years old\n"
            f"• Annual Premium: {format_currency(annual_premium)}\n"
            f"• Monthly Premium: {format_currency(monthly_premium)}\n\n"
            f"Includes: \n {coverage_details.get(package_tier, '')}\n\n"
            "💡 This is a rough estimate. Your final premium depends on your health assessment and exact coverage amounts.\n\n"
            "Would you like our agent to contact you for a more detailed discussion about your protection needs?"
        )

        if age < 18 or age > 60:
            response_msg += "\n\n⚠️ **Note:** Combo plans are typically for ages 18-60. Our advisor will explain all available options for you."

        return response_msg, annual_premium, monthly_premium, self.package_names.get(package_tier, 'Unknown')

    def calculate_age_from_dob(self, dob_str: str) -> Optional[int]:
        """Calculate age from date of birth string (DD/MM/YYYY format)."""
        try:
            parts = dob_str.strip().split('/')
            if len(parts) != 3:
                return None
            day, month, year = map(int, parts)
            dob = date(year, month, day)
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            return age if age >= 0 else None
        except (ValueError, AttributeError, IndexError) as e:
            logger.warning("Error calculating age from DOB '%s': %s", dob_str, e)
            return None

    def _append_to_google_sheet(self, state: CampaignState, user_id: str, package_tier: int, contact_requested: bool = False) -> bool:
        """Helper to append user data to Google Sheet. Returns True if successful."""
        try:
            if append_row_to_sheet is None:
                logger.warning("[PERLINDUNGAN_COMBO] append_row_to_sheet is not configured.")
                return False

            user_data = state.user_data
            if not user_data.get('name') or not user_data.get('email'):
                logger.warning("[PERLINDUNGAN_COMBO] Missing required data for sheet append (user: %s)", user_id)
                return False

            name = user_data.get("name", "N/A")
            dob = user_data.get("dob", "")
            email = user_data.get("email", "")
            primary_concern = user_data.get("primary_concern", "")
            life_stage = user_data.get("life_stage", "")
            dependents = user_data.get("dependents", "")
            existing_coverage = user_data.get("existing_coverage", "")
            premium_budget = user_data.get("premium_budget", "")
            selected_plan = "perlindungan_combo"
            package_tier_str = str(package_tier)

            contact_status = "Yes, Contact Requested" if contact_requested else "No, Contact Declined"

            row_data = [
                name, dob, email, primary_concern, life_stage, dependents,
                existing_coverage, premium_budget, selected_plan, None, None, None,
                None, None, None, package_tier_str, contact_status
            ]
            append_row_to_sheet(row_data)
            logger.info("[PERLINDUNGAN_COMBO] Data inserted to Google Sheet for user %s | Package Tier=%s | Contact=%s", user_id, package_tier_str, contact_status)
            return True
        except Exception as sheet_error:
            logger.error("[PERLINDUNGAN_COMBO] Error inserting data to Google Sheet: %s", sheet_error, exc_info=True)
            return False

    async def process_message(
        self,
        user_id: str,
        message: Union[str, dict],
        ws: Any = None,
        user_data: Optional[Dict[str, Any]] = None
    ) -> dict:
        """Process incoming message and return response. Refactored into a clean state machine."""
        logger.info("[PerlindunganCombo] Processing message for user %s: %s", user_id, str(message)[:200])

        state = self.get_state(user_id)

        # Update state with provided user_data (from main conversation)
        if user_data:
            logger.info("[PerlindunganCombo] Updating user data: %s", user_data)
            state.user_data.update(user_data)
            if 'age' in user_data and user_data['age']:
                try:
                    state.age = int(user_data['age'])
                    state.user_data['age'] = state.age
                    logger.info("[PerlindunganCombo] Updated age: %s", state.age)
                except (ValueError, TypeError) as e:
                    logger.warning("[PerlindunganCombo] Invalid age in user_data: %s", e)
            if 'name' in user_data and user_data['name']:
                state.user_data['name'] = user_data['name']

        # Extract and normalize message content
        message_content = ""
        if isinstance(message, dict):
            # prefer explicit 'value' from button payload, then 'text'
            message_content = message.get('value') or message.get('text') or ""
        else:
            message_content = str(message)

        normalized_msg = message_content.lower().strip() if isinstance(message_content, str) else ''

        # Handle navigation commands first (always available)
        if normalized_msg == "main_menu":
            logger.info("Returning to main menu for user: %s", user_id)
            self.states[user_id] = CampaignState(current_step="welcome")
            return {
                "type": "reset_to_main",
                "response": "Welcome back to the main menu! What's your name?",
                "content": "Welcome back to the main menu! What's your name?",
                "next_step": "get_name",
            }

        try:
            # Onboarding integration: Handle name/DOB/email/age collection if coming from main
            if 'next_step' in state.user_data:
                next_step = state.user_data['next_step']
                if next_step == 'get_name':
                    state.user_data['name'] = message_content
                    state.user_data['next_step'] = 'get_dob'
                    state.current_step = "get_dob"
                    return {
                        "type": "message",
                        "response": f"Hi {state.user_data['name']}! What is your date of birth? (DD/MM/YYYY)",
                        "content": f"Hi {state.user_data['name']}! What is your date of birth? (DD/MM/YYYY)",
                        "next_step": "get_dob",
                        "campaign_data": state.user_data
                    }
                elif next_step == 'get_dob':
                    state.user_data['dob'] = message_content
                    calculated_age = self.calculate_age_from_dob(message_content)
                    if calculated_age is not None:
                        state.age = calculated_age
                        state.user_data['age'] = calculated_age
                        # Automatic under-18 detection: block and return to main menu
                        if calculated_age < 18:
                            state.current_step = "welcome"
                            return self.create_button_response(
                                message="Sorry, combo plans are only available for users aged 18 and above. Returning to main menu.",
                                button_type='navigation',
                                campaign_data=state.user_data,
                                next_step='end_conversation'
                            )
                    state.user_data['next_step'] = 'get_email'
                    state.current_step = "get_email"
                    return {
                        "type": "message",
                        "response": "What is your email address?",
                        "content": "What is your email address?",
                        "next_step": "get_email",
                        "campaign_data": state.user_data
                    }
                elif next_step == 'get_email':
                    state.user_data['email'] = message_content
                    state.user_data['next_step'] = 'get_age'
                    state.current_step = "get_age"
                    return {
                        "type": "message",
                        "response": "How old are you? (Or confirm if we calculated it from your DOB.)",
                        "content": "How old are you? (Or confirm if we calculated it from your DOB.)",
                        "next_step": "get_age",
                        "campaign_data": state.user_data
                    }
                elif next_step == 'get_age':
                    try:
                        age = int(message_content)
                        if age < 18:
                            # Underage: show error and provide a button to return to main menu
                            state.current_step = "welcome"
                            return self.create_button_response(
                                message="Sorry, combo plans are only available for users aged 18 and above. Returning to main menu.",
                                button_type='navigation',
                                campaign_data=state.user_data,
                                next_step='end_conversation'
                            )
                        elif 18 <= age <= 60:
                            state.age = age
                            state.user_data['age'] = age
                            state.user_data.pop('next_step', None)
                            state.current_step = "after_onboarding"
                            return self._get_welcome_response()
                        else:
                            return {
                                "type": "message",
                                "response": "Age must be between 18-60 for combo plans. Please enter a valid age:",
                                "content": "Age must be between 18-60 for combo plans. Please enter a valid age:",
                                "next_step": "get_age",
                                "campaign_data": state.user_data
                            }
                    except ValueError:
                        return {
                            "type": "message",
                            "response": "Please enter a valid number for your age (18-60):",
                            "content": "Please enter a valid number for your age (18-60):",
                            "next_step": "get_age",
                            "campaign_data": state.user_data
                        }

            # State machine: Handle each step
            if state.current_step == "welcome" or normalized_msg in ['start', 'begin']:
                # Show welcome if no onboarding in progress
                if not state.user_data.get('name'):
                    state.user_data['next_step'] = 'get_name'
                    return {
                        "type": "message",
                        "response": "Welcome! Let's start. What is your name?",
                        "content": "Welcome! Let's start. What is your name?",
                        "next_step": "get_name",
                        "campaign_data": state.user_data
                    }
                state.current_step = "after_welcome"
                return self._get_welcome_response()

            elif state.current_step == "after_welcome":
                if normalized_msg in ['learn_more', 'show_benefits', 'benefits', 'yes']:
                    benefits_msg = self.get_benefits_message()
                    state.current_step = "show_benefits_response"
                    return {
                        "type": "buttons",
                        "response": benefits_msg,
                        "content": benefits_msg,
                        "buttons": [
                            {"label": "✅ Yes, Show My Estimate", "value": "show_estimate"},
                            {"label": "❌ No Thanks", "value": "not_now"}
                        ],
                        "next_step": "show_benefits_response",
                        "campaign_data": state.user_data
                    }
                elif normalized_msg in ['not_now', 'no', 'later']:
                    state.current_step = "end_conversation"
                    return self.create_button_response(
                        message="Understood. Feel free to ask later. Would you like to return to the main menu?",
                        button_type='navigation',
                        campaign_data=state.user_data,
                        next_step='end_conversation'
                    )
                else:
                    return self._get_welcome_response()

            elif state.current_step == "show_benefits_response":
                if normalized_msg == "show_estimate":
                    age = state.age or state.user_data.get('age')
                    # If age exists and is under 18, block immediately and provide main-menu button
                    if age is not None and isinstance(age, int) and age < 18:
                        state.current_step = "welcome"
                        return self.create_button_response(
                            message="Sorry, combo plans are only available for users aged 18 and above. Returning to main menu.",
                            button_type='navigation',
                            campaign_data=state.user_data,
                            next_step='end_conversation'
                        )
                    if not age or not (18 <= age <= 60):
                        state.current_step = "get_age_manually"
                        return {
                            "type": "message",
                            "response": "To show your estimate, please enter your age (18-60):",
                            "content": "To show your estimate, please enter your age (18-60):",
                            "next_step": "get_age_manually",
                            "campaign_data": state.user_data
                        }
                    state.current_step = "get_package"
                    return {
                        "type": "buttons",
                        "response": f"Great! Based on your age ({age}), please select a protection package:",
                        "content": f"Great! Based on your age ({age}), please select a protection package:",
                        "buttons": self.get_buttons('package_selection'),
                        "next_step": "get_package",
                        "campaign_data": state.user_data
                    }
                elif normalized_msg == "not_now":
                    state.current_step = "end_conversation"
                    return self.create_button_response(
                        message="Understood. Would you like to return to the main menu?",
                        button_type='navigation',
                        campaign_data=state.user_data,
                        next_step='end_conversation'
                    )
                else:
                    return {
                        "type": "buttons",
                        "response": self.get_benefits_message(),
                        "content": self.get_benefits_message(),
                        "buttons": [
                            {"label": "✅ Yes, Show My Estimate", "value": "show_estimate"},
                            {"label": "❌ No Thanks", "value": "not_now"}
                        ],
                        "next_step": "show_benefits_response",
                        "campaign_data": state.user_data
                    }

            elif state.current_step == "get_age_manually":
                try:
                    age = int(normalized_msg)
                    if age < 18:
                        # Underage: show error and provide a button to return to main menu
                        state.current_step = "welcome"
                        return self.create_button_response(
                            message="Sorry, combo plans are only available for users aged 18 and above. Returning to main menu.",
                            button_type='navigation',
                            campaign_data=state.user_data,
                            next_step='end_conversation'
                        )
                    elif 18 <= age <= 60:
                        state.age = age
                        state.user_data['age'] = age
                        state.current_step = "get_package"
                        return {
                            "type": "buttons",
                            "response": f"Great! You are {age} years old.\n\nPlease select a protection package:",
                            "content": f"Great! You are {age} years old.\n\nPlease select a protection package:",
                            "buttons": self.get_buttons('package_selection'),
                            "next_step": "get_package",
                            "campaign_data": state.user_data
                        }
                    else:
                        return {
                            "type": "message",
                            "response": "Age must be 18-60. Please enter a valid age:",
                            "next_step": "get_age_manually",
                            "campaign_data": state.user_data
                        }
                except ValueError:
                    return {
                        "type": "message",
                        "response": "Please enter a valid number (18-60):",
                        "next_step": "get_age_manually",
                        "campaign_data": state.user_data
                    }

            elif state.current_step == "get_package":
                # normalized_msg could be '1', '2', '3' from the button value
                # If age present but under 18, block before allowing package selection
                age_check = state.age or state.user_data.get('age')
                if age_check is not None and isinstance(age_check, int) and age_check < 18:
                    state.current_step = "welcome"
                    return self.create_button_response(
                        message="Sorry, combo plans are only available for users aged 18 and above. Returning to main menu.",
                        button_type='navigation',
                        campaign_data=state.user_data,
                        next_step='end_conversation'
                    )
                if normalized_msg.isdigit() and int(normalized_msg) in [1, 2, 3]:
                    package_tier = int(normalized_msg)
                    state.package_tier = package_tier
                    state.user_data['package_tier'] = package_tier
                    age = state.age or state.user_data.get('age')
                    if not age:
                        state.current_step = "get_age_manually"
                        return {
                            "type": "message",
                            "response": "Please enter your age first (18-60):",
                            "next_step": "get_age_manually",
                            "campaign_data": state.user_data
                        }

                    annual_premium, monthly_premium, error = self.calculate_combo_tier(age, package_tier)
                    if error:
                        return {
                            "type": "message",
                            "response": f"Error: {error}. Please try again.",
                            "next_step": "get_package",
                            "campaign_data": state.user_data
                        }

                    package_name = self.package_names.get(package_tier, f"Package {package_tier}")
                    state.user_data.update({
                        "package_choice": package_tier,
                        "package_name": package_name,
                        "annual_premium": annual_premium,
                        "monthly_premium": monthly_premium
                    })

                    state.current_step = "confirm_package"
                    estimate_msg, _, _, _ = self._get_plan_estimate_message(age, package_tier)
                    return self.create_button_response(
                        message=f"{estimate_msg}\n\nWould you like to proceed with this plan?",
                        button_type='confirmation',
                        campaign_data=state.user_data,
                        next_step='confirm_package'
                    )
                else:
                    return {
                        "type": "buttons",
                        "response": "Please select a package (1-3):",
                        "content": "Please select a package (1-3):",
                        "buttons": self.get_buttons('package_selection'),
                        "next_step": "get_package",
                        "campaign_data": state.user_data
                    }

            elif state.current_step == "confirm_package":
                if normalized_msg in ['yes', 'proceed', 'y']:
                    state.current_step = "follow_up_contact"
                    package_name = state.user_data.get('package_name', 'your plan')
                    annual_premium = state.user_data.get('annual_premium', 0)
                    monthly_premium = state.user_data.get('monthly_premium', 0)
                    response_msg = (
                        f"Excellent choice! Your {package_name} plan:\n"
                        f"• Annual: {format_currency(annual_premium)}\n"
                        f"• Monthly: {format_currency(monthly_premium)}\n\n"
                        "Would you like an agent to contact you for more details?"
                    )
                    return self.create_button_response(
                        message=response_msg,
                        button_type='agent_contact',
                        campaign_data=state.user_data,
                        next_step='follow_up_contact'
                    )
                elif normalized_msg in ['no', 'change', 'n']:
                    state.current_step = "get_package"
                    return {
                        "type": "buttons",
                        "response": "No problem! Please select another package:",
                        "content": "No problem! Please select another package:",
                        "buttons": self.get_buttons('package_selection'),
                        "next_step": "get_package",
                        "campaign_data": state.user_data
                    }
                else:
                    age = state.age or state.user_data.get('age')
                    package_tier = state.package_tier or state.user_data.get('package_tier')
                    if age and package_tier:
                        estimate_msg, _, _, _ = self._get_plan_estimate_message(age, package_tier)
                        return self.create_button_response(
                            message=f"{estimate_msg}\n\nWould you like to proceed?",
                            button_type='confirmation',
                            campaign_data=state.user_data,
                            next_step='confirm_package'
                        )
                    else:
                        state.current_step = "get_package"
                        return {
                            "type": "buttons",
                            "response": "Please select a package first:",
                            "buttons": self.get_buttons('package_selection'),
                            "next_step": "get_package",
                            "campaign_data": state.user_data
                        }

            elif state.current_step == "follow_up_contact":
                package_tier = state.user_data.get('package_tier')
                if not package_tier:
                    logger.warning("No package_tier in user_data for %s", user_id)
                    state.current_step = "end_conversation"
                    return self.create_button_response(
                        message="Something went wrong. Would you like to start over?",
                        button_type='navigation',
                        campaign_data=state.user_data,
                        next_step='end_conversation'
                    )

                if normalized_msg in ['yes', 'contact', 'y', 'contact me']:
                    # Attempt to append to Google Sheet; pass contact_requested=True
                    sheet_success = self._append_to_google_sheet(state, user_id, package_tier, contact_requested=True)
                    if sheet_success:
                        state.user_data['contact_requested'] = True
                        response_msg = "Thank you! One of our agents will contact you shortly via email with more details on your plan."
                    else:
                        response_msg = "Thank you for your interest! We'll follow up soon. (Note: System issue logged.)"
                    state.current_step = "end_conversation"
                    return self.create_button_response(
                        message=response_msg,
                        button_type='navigation',
                        campaign_data=state.user_data,
                        next_step='end_conversation'
                    )
                elif normalized_msg in ['no', 'no thanks', 'n']:
                    self._append_to_google_sheet(state,user_id, package_tier, contact_requested=False)
                    state.current_step = "end_conversation"
                    return self.create_button_response(
                        message="No problem! If you change your mind, feel free to ask. Would you like to return to the main menu?",
                        button_type='navigation',
                        campaign_data=state.user_data,
                        next_step='end_conversation'
                    )
                else:
                    package_name = state.user_data.get('package_name', 'your plan')
                    response_msg = f"Regarding your {package_name} plan, would you like an agent to contact you?"
                    return self.create_button_response(
                        message=response_msg,
                        button_type='agent_contact',
                        campaign_data=state.user_data,
                        next_step='follow_up_contact'
                    )

            elif state.current_step == "end_conversation":
                return self.create_button_response(
                    message="Thanks for chatting! What would you like to do next?",
                    button_type='navigation',
                    campaign_data=state.user_data,
                    next_step='end_conversation'
                )

            logger.warning("[PerlindunganCombo] Unknown state '%s' or input '%s' for %s", state.current_step, normalized_msg, user_id)
            state.current_step = "welcome"
            return self._get_welcome_response()

        except Exception as e:
            logger.error("Error in process_message for %s: %s", user_id, e, exc_info=True)
            return {
                "type": "message",
                "response": "Sorry, an error occurred. Type 'main_menu' to restart.",
                "content": "Sorry, an error occurred. Type 'main_menu' to restart.",
                "campaign_data": state.user_data,
                "next_step": "welcome"
            }

    async def show_premium_estimate(self, state: CampaignState, user_id: str) -> dict:
        """Show premium estimate based on user data (legacy method, now integrated into process_message)."""
        age = state.user_data.get('age')
        package_tier = state.user_data.get('package_tier')

        if not age or not package_tier:
            return {
                "type": "message",
                "response": "❌ Missing age or package info. Please start over.",
                "content": "❌ Missing age or package info. Please start over.",
                "next_step": "welcome",
                "campaign_data": state.user_data
            }

        state.current_step = "confirm_package"
        # Simulate confirmation flow — return the response from process_message for consistency
        return await self.process_message(user_id, {"value": "yes"}, user_data=state.user_data)

    def get_welcome_message(self) -> str:
        """Return the welcome message for this campaign."""
        return """*🛡️ Welcome to Perlindungan Combo - Your Complete Protection Solution*

I can help you find the perfect protection plan that combines:
• Life Insurance
• Critical Illness Coverage
• Medical Protection
• Accident Coverage

All in one simple, affordable package. Would you like to learn more about the benefits?"""

    def get_benefits_message(self) -> str:
        """Return the benefits message for this campaign."""
        return """💎 *Benefits of Combo Protection:*

• All-in-one coverage: Life, Medical, Critical Illness, Accident
• Single premium payment - simpler to manage
• Better value than buying separate policies
• No coverage gaps - complete protection
• Guaranteed insurability for all coverage types

Would you like to get a quick estimate of your premium based on your age and desired coverage?"""

    def get_plan_explanation(self) -> str:
        """Return the explanation of the combo protection plan."""
        return (
            "💎 *Benefits of Combo Protection:*\n\n"
            "• **All-in-one coverage:** Life, Medical, Critical Illness, Accident\n"
            "• **Single premium payment** - simpler to manage\n"
            "• **Better value** than buying separate policies\n"
            "• **No coverage gaps** - complete protection\n"
            "• **Guaranteed insurability** for all coverage types\n\n"
            "Would you like to get a quick estimate of your premium based on your age and desired coverage?"
        )

    def get_initial_message(self, user_id: str) -> dict:
        """Get the initial welcome message with buttons."""
        state = self.get_state(user_id)
        state.current_step = "welcome"
        welcome_response = self._get_welcome_response()
        welcome_response.update({
            "message": welcome_response["response"],
            "text": welcome_response["response"],
            "is_user": False,
            "timestamp": datetime.now().isoformat()
        })
        return welcome_response

    async def _handle_agent_contact(self, state: CampaignState, user_id: str, message: str) -> Dict[str, Any]:
        """Handle agent contact preference (fallback for old calls)."""
        normalized_msg = message.lower().strip()
        package_tier = state.user_data.get('package_tier')
        if not package_tier:
            return {
                "type": "message",
                "response": "Something went wrong. Please select a package first.",
                "content": "Something went wrong. Please select a package first.",
                "next_step": "get_package",
                "campaign_data": state.user_data
            }

        if normalized_msg in ['yes', 'contact', 'y']:
            sheet_success = self._append_to_google_sheet(state, user_id, package_tier)
            response_msg = "Thank you! An agent will contact you soon." if sheet_success else "Thank you! We'll follow up soon."
            state.current_step = "end_conversation"
            return self.create_button_response(
                message=response_msg,
                button_type='navigation',
                campaign_data=state.user_data,
                next_step='end_conversation'
            )
        else:
            state.current_step = "end_conversation"
            return self.create_button_response(
                message="No problem! Feel free to ask later.",
                button_type='navigation',
                campaign_data=state.user_data,
                next_step='end_conversation'
            )


# Create a singleton instance
perlindungan_combo_campaign = PerlindunganComboCampaign()
perlindungan_combo_campaign_instance = perlindungan_combo_campaign


# If run as script, run small tests (non-exhaustive)
if __name__ == "__main__":
    import asyncio
    from unittest.mock import patch, MagicMock

    async def test_campaign():
        campaign = perlindungan_combo_campaign
        user_id = "test_user"

        if user_id in campaign.states:
            del campaign.states[user_id]

        print("=== Initial welcome ===")
        welcome = campaign.get_initial_message(user_id)
        print(welcome['response'][:200])

        # simulate onboarding coming from main
        state = campaign.get_state(user_id)
        state.user_data = {'name': 'Test User', 'email': 'test@example.com', 'age': 30}
        response1 = await campaign.process_message(user_id, "learn_more")
        print("learn_more ->", response1['response'][:200])

        response2 = await campaign.process_message(user_id, "show_estimate")
        print("show_estimate ->", response2['response'][:200])

        print("=== package selection flow (mocking sheet append) ===")
        # When append_row_to_sheet is present, patch that reference on this module for tests
        if append_row_to_sheet is not None:
            target = __name__ + ".append_row_to_sheet"
        else:
            # if append_row_to_sheet is not available, patch the method on the object that calls it
            target = __name__ + "._append_to_google_sheet"

        with patch(target) as mock_append:
            # If append_row_to_sheet exists, the patch will replace it; else we patch the wrapper.
            mock_append.return_value = None

            response3 = await campaign.process_message(user_id, "1")
            print("select 1 ->", response3['response'][:200])

            response4 = await campaign.process_message(user_id, "yes")
            print("confirm yes ->", response4['response'][:200])

            response5 = await campaign.process_message(user_id, "yes")
            print("agent yes ->", response5['response'][:200])
            # We won't assert here in script mode, but user tests can assert as needed.

        response6 = await campaign.process_message(user_id, "main_menu")
        print("main_menu ->", response6['response'])

        # invalid age
        state.current_step = "get_age_manually"
        response7 = await campaign.process_message(user_id, "70")
        print("invalid age ->", response7['response'])

        print("✅ Script tests finished.")

    asyncio.run(test_campaign())
