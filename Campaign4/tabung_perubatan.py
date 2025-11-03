from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
import logging
import asyncio
from datetime import datetime
from Google_Sheet import append_row_to_sheet

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(ch)


def format_currency(amount: float) -> str:
    return f"RM {amount:,.2f}"


@dataclass
class TabungPerubatanState:
    """State management for Tabung Perubatan campaign."""
    current_step: str = "welcome"
    user_data: Dict[str, Any] = field(default_factory=dict)
    age: Optional[int] = None
    coverage_level: Optional[int] = None
    name: Optional[str] = None


class TabungPerubatanCampaign:
    """Main handler for Tabung Perubatan campaign."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if not self.initialized:
            self.states: Dict[str, TabungPerubatanState] = {}
            self.last_active: Dict[str, float] = {}
            self.name = "Tabung Perubatan"
            self.description = "Comprehensive medical coverage with cashless hospital admissions and extensive benefits"
            self.initialized = True

    def get_state(self, user_id: str) -> TabungPerubatanState:
        """Get or create state for a user."""
        if user_id not in self.states:
            self.states[user_id] = TabungPerubatanState()
        self.last_active[user_id] = datetime.now().timestamp()
        return self.states[user_id]

    def _clear_state(self, user_id: str) -> None:
        """Helper to fully clear a user's state and activity timestamps."""
        if user_id in self.states:
            del self.states[user_id]
        if user_id in self.last_active:
            del self.last_active[user_id]
        logger.info(f"[TabungPerubatan] Cleared state for user {user_id}")

    def get_welcome_message(self) -> str:
        """Return the welcome message for the campaign."""
        return (
            "🏥 *Welcome to Tabung Perubatan!* 🏥\n\n"
            "Let's talk about something important: your health and your savings.\n\n"
            "A single hospital stay can cost tens of thousands of Ringgit. "
            "This plan is a 'Medical Fund' that protects your life savings from "
            "being wiped out by unexpected medical bills."
        )

    def get_plan_explanation(self) -> str:
        """Return the explanation of the medical plan."""
        return (
            "🌟 *What is Tabung Perubatan?*\n\n"
            "It's your personal financial safety net for healthcare. Think of it as a "
            '"Medical Card" that gives you:\n\n'
            "• **Cashless Hospital Admission:** Walk into any of our panel hospitals, focus on getting better. "
            "We settle the bill directly. No large upfront payments.\n"
            "• **High Annual Limit:** Coverage from RM 180,000 to over RM 1,000,000 per year "
            "for surgeries, ICU, room & board, and medication.\n"
            "• **Protection for Your Savings:** Shields your family's finances from the shock "
            "of a major medical event. Your savings remain for your dreams, not hospital bills."
        )

    def estimate_medical_premium(self, age: Optional[int], coverage_level: int) -> tuple[float, str]:
        """Estimate medical premium based on age and coverage level."""
        try:
            # Validate age
            if age is None:
                return 0.0, "Age is required to estimate premium."
            if age < 18:
                return 0.0, "Sorry, age must be at least 18 to apply for this plan. Umur tidak mencukupi untuk memohon."
            if age > 64:
                return 0.0, "Age must be between 18 and 64 for this plan"

            # Annual premiums for ages 34-64 (for basic coverage)
            age_annual_premiums = {
                34: 1833.30,
                35: 1854.40,
                36: 1896.90,
                37: 1931.00,
                38: 1952.10,
                39: 1969.20,
                40: 2015.10,
                41: 2156.00,
                42: 2231.00,
                43: 2294.00,
                44: 2383.60,
                45: 2405.60,
                46: 2580.00,
                47: 2656.00,
                48: 2800.00,
                49: 2862.00,
                50: 3002.30,
                51: 3328.60,
                52: 3605.70,
                53: 3774.00,
                54: 3951.20,
                55: 3951.20,  # Assumed same as 54
                56: 3951.20,  # Assumed same as 54
                57: 3951.20,  # Assumed same as 54
                58: 4711.60,
                59: 5136.20,
                60: 5136.20,  # Assumed same as 59
                61: 5136.20,  # Assumed same as 59
                62: 5136.20,  # Assumed same as 59
                63: 7976.00,
                64: 9232.60
            }

            # Fixed monthly premiums for younger ages (for basic coverage)
            if 18 <= age <= 21:
                base_monthly = 113.0
            elif 22 <= age <= 25:
                base_monthly = 123.0
            elif 26 <= age <= 30:
                base_monthly = 133.0
            elif 31 <= age <= 33:
                base_monthly = 143.0
            else:  # 34-64
                annual = age_annual_premiums.get(age, 3951.20)  # Default to 54's if missing
                base_monthly = annual / 12

            # Adjust by coverage level
            if coverage_level == 1:  # Basic
                # Total contribution = base_monthly * 12
                # Monthly = (Total contribution / 12) - 20
                premium = base_monthly - 20
            elif coverage_level == 3:  # Comprehensive
                # Total contribution = base_monthly * 12
                # Monthly = Total contribution / 12
                premium = base_monthly
            else:
                return 0.0, "Invalid coverage level"

            return round(premium, 2), ""

        except Exception as e:
            logger.error(f"Error calculating premium: {str(e)}", exc_info=True)
            return 0.0, "Unable to calculate premium at this time"

    def _get_welcome_response(self) -> Dict[str, Any]:
        """Helper method to get welcome message and buttons."""
        welcome_message = self.get_welcome_message()
        return {
            "type": "message",
            "text": welcome_message + "\n\nWould you like to know more about this medical coverage plan?",
            "content": welcome_message + "\n\nWould you like to know more about this medical coverage plan?",
            "buttons": [
                {"label": "✅ Yes, tell me more", "value": "yes"},
                {"label": "❌ Not now, thanks", "value": "no"},
            ],
            "next_step": "check_interest_response"
        }

    def _get_estimation_question(self, state: TabungPerubatanState) -> Dict[str, Any]:
        """Helper method to get estimation question with buttons."""
        question = "Would you like to see an estimation of the coverage you can receive?"
        state.current_step = "handle_estimation_response"
        return {
            "type": "buttons",
            "text": question,
            "content": question,
            "buttons": [
                {"label": "✅ Yes, show me an estimate", "value": "yes_estimate"},
                {"label": "❌ Not now, thanks", "value": "no"}
            ]
        }

    async def process_message(
        self,
        user_id: str,
        message: Union[str, dict],
        ws: Any = None,
        user_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process incoming message and return response.

        Args:
            user_id: Unique identifier for the user
            message: The message from the user, can be string or dict
            ws: Optional WebSocket connection for sending messages
            user_data: Optional dictionary containing user data from main conversation

        Returns:
            dict: Response containing message and next steps
        """
        try:
            logger.info(f"[TabungPerubatan] Processing raw message: {repr(message)} for user {user_id}")
            state = self.get_state(user_id)

            # Merge provided user_data into state.user_data and update age/name if available
            if user_data:
                state.user_data.update(user_data)
                if 'age' in user_data and user_data['age']:
                    try:
                        state.age = int(user_data['age'])
                        logger.info(f"[TabungPerubatan] Updated age from main conversation: {state.age}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"[TabungPerubatan] Invalid age in user_data: {user_data.get('age')}. Error: {e}")
                if 'name' in user_data and user_data['name']:
                    state.name = user_data['name']
                    logger.info(f"[TabungPerubatan] Updated name from main conversation: {state.name}")

            # Normalize message text safely (message can be dict from some platforms)
            if isinstance(message, dict):
                message_text = str(message.get('text', '') or "").strip()
            else:
                message_text = str(message or "").strip()

            message_lower = message_text.lower()

            logger.info(f"[TabungPerubatan] Current step: {state.current_step}")
            logger.info(f"[TabungPerubatan] Message text normalized: '{message_lower}'")

            # Handle immediate global commands (restart/main_menu) BEFORE other logic
            if message_lower in ["restart", "main_menu"]:
                self._clear_state(user_id)
                return {
                    "type": "reset_to_main",
                    "response": "Returning to main menu...",
                    "content": "Returning to main menu...",
                    "reset_to_main": True
                }

            # Default response skeleton
            response: Dict[str, Any] = {
                "type": "message",
                "response": "",
                "content": "",
                "campaign_data": state.user_data,
                "next_step": state.current_step
            }

            # Welcome flow
            if state.current_step == "welcome" or not state.current_step:
                welcome_response = self._get_welcome_response()
                state.current_step = welcome_response.get("next_step", "check_interest_response")
                return welcome_response

            # Handle interest check response
            elif state.current_step == "check_interest_response":
                if any(word in message_lower for word in ['yes', 'y', 'ya', 'yeah', 'sure', 'ok']) and not any(word in message_lower for word in ['no', 'n', 'not now', 'later']):
                    explanation = self.get_plan_explanation()
                    state.current_step = "handle_estimation_response"
                    combined_text = f"{explanation}\n\nWould you like to see an estimation of the coverage you can receive?"
                    return {
                        "type": "buttons",
                        "text": combined_text,
                        "content": combined_text,
                        "buttons": [
                            {"label": "✅ Yes, show me an estimate", "value": "yes_estimate"},
                            {"label": "❌ Not now, thanks", "value": "no"}
                        ],
                        "next_step": "handle_estimation_response"
                    }
                elif "estimate" in message_lower:
                    state.current_step = "get_coverage_level"
                    age_info = f"I see you're {state.age} years old. " if state.age else ""
                    return {
                        "type": "buttons",
                        "content": f"{age_info}Please select your desired coverage level:",
                        "next_step": "get_coverage_level",
                        "buttons": [
                            {"label": "Basic (RM180k/year)", "value": "1"},
                            {"label": "Comprehensive (RM1M+/year)", "value": "3"}
                        ]
                    }
                elif any(word in message_lower for word in ['no', 'n', 'not now', 'later']):
                    state.current_step = "end_conversation"
                    return {
                        "type": "buttons",
                        "content": "Understood. If you have any questions about medical coverage in the future, feel free to ask. Stay healthy!",
                        "next_step": "end_conversation",
                        "buttons": [
                            {"label": "🏠 Return to Main Menu", "value": "main_menu"}
                        ]
                    }
                else:
                    return self._get_welcome_response()

            # Redundant protection (shouldn't be reached often)
            elif state.current_step == "ask_estimation":
                state.current_step = "welcome"
                return self._get_welcome_response()

            # Handle estimation response
            elif state.current_step == "handle_estimation_response":
                if any(token in message_lower for token in ["yes_estimate", "estimate", "yes", "y", "ya", "sure", "ok"]) and not any(no in message_lower for no in ["no", "n", "not now"]):
                    logger.info("[TabungPerubatan] User requested estimate. Checking age restriction first.")
                    
                    # Check age restriction before showing coverage options
                    if state.age is not None and state.age < 18:
                        state.current_step = "end_conversation"
                        return {
                            "type": "buttons",
                            "content": "Sorry,Tabung Perubatan is only available for users aged 18 and above.\nYou cannot continue with this campaign.",
                            "next_step": "end_conversation",
                            "buttons": [
                                {"label": "🏠 Return to Main Menu", "value": "main_menu"}
                            ]
                        }
                    
                    # If age is valid or not yet known, proceed to coverage selection
                    state.current_step = "get_coverage_level"
                    age_info = f"I see you're {state.age} years old. " if state.age else ""
                    return {
                        "type": "buttons",
                        "content": f"{age_info}Please select your desired coverage level:",
                        "next_step": "get_coverage_level",
                        "buttons": [
                            {"label": "🏥 Basic (RM180k/year)", "value": "1"},
                            {"label": "🏥🏥🏥 Comprehensive (RM1M+/year)", "value": "3"}
                        ]
                    }
                elif any(no in message_lower for no in ["no", "n", "not now", "later"]):
                    state.current_step = "end_conversation"
                    return {
                        "type": "buttons",
                        "content": "Understood. If you have any questions about medical coverage in the future, feel free to ask. Stay healthy!",
                        "next_step": "end_conversation",
                        "buttons": [
                            {"label": "🏠 Return to Main Menu", "value": "main_menu"}
                        ]
                    }
                else:
                    return self._get_estimation_question(state)

            # Get coverage level and estimate premium
            elif state.current_step == "get_coverage_level":
                try:
                    coverage_level = None
                    # allow direct digit or keyword matches
                    if message_lower.isdigit():
                        coverage_level = int(message_lower)
                    elif any(k in message_lower for k in ['basic', '180k']):
                        coverage_level = 1
                    elif any(k in message_lower for k in ['comprehensive', '1m', '1m+']):
                        coverage_level = 3

                    if coverage_level not in [1, 3]:
                        raise ValueError("Please select a valid coverage level")

                    state.coverage_level = coverage_level

                    premium, error = self.estimate_medical_premium(state.age, coverage_level)
                    if error:
                        return {
                            "type": "buttons",
                            "content": f"Sorry, there was an error calculating your premium: {error}",
                            "buttons": [{"label": "🏠 Return to Main Menu", "value": "main_menu"}],
                            "next_step": "end_conversation"
                        }

                    formatted_premium = format_currency(premium)
                    coverage_level_names = {1: "Basic", 3: "Comprehensive"}
                    coverage_amounts = {1: "RM180,000", 3: "RM1,000,000"}

                    response_msg = (
                        f"Based on your age ({state.age}) and selected coverage level ({coverage_level_names[coverage_level]}):\n\n"
                        f"• Estimated Monthly Premium: {formatted_premium}\n"
                        f"• Annual Coverage: {coverage_amounts[coverage_level]}"
                    )

                    if state.age and state.age >= 61:
                        response_msg += (
                            "\n\n⚠️ **Note for Senior Applicants:**\n"
                            "Medical insurance for seniors may have certain conditions. "
                            "Our advisor will explain all details and available options."
                        )

                    state.current_step = "offer_agent_contact"

                    return {
                        "type": "buttons",
                        "content": f"{response_msg}\n\nWould you like an agent to contact you to further discuss the plan?",
                        "next_step": "offer_agent_contact",
                        "buttons": [
                            {"label": "✅ Yes, contact me", "value": "contact_agent"},
                            {"label": "❌ No thanks", "value": "no_contact"},
                        ]
                    }

                except ValueError:
                    buttons = [
                        {"label": "Basic (RM180k/year)", "value": "1"},
                        {"label": "Comprehensive (RM1M+/year)", "value": "3"},
                    ]
                    return {
                        "type": "buttons",
                        "content": "Please select a valid coverage level.\n\n" + "\n".join([f"{i}. {b['label']}" for i, b in enumerate(buttons, 1)]),
                        "buttons": buttons,
                        "next_step": "get_coverage_level"
                    }

            # Offer agent contact and handle user's preference
            elif state.current_step == "offer_agent_contact":
                # use message_lower already computed
                if "contact_agent" in message_lower or "contact me" in message_lower or "yes" in message_lower:
                    # Insert data into Google Sheet (best-effort)
                    try:
                        name = state.user_data.get("name", state.name or "N/A")
                        dob = state.user_data.get("dob", "")
                        email = state.user_data.get("email", "")
                        primary_concern = state.user_data.get("primary_concern", "")
                        life_stage = state.user_data.get("life_stage", "")
                        dependents = state.user_data.get("dependents", "")
                        existing_coverage = state.user_data.get("existing_coverage", "")
                        premium_budget = state.user_data.get("premium_budget", "")
                        selected_plan = "tabung_perubatan"
                        coverage_level_str = str(state.coverage_level or "")

                        row_data = [
                            name, dob, email, primary_concern, life_stage, dependents,
                            existing_coverage, premium_budget, selected_plan,
                            None, None, None, None, None,  # SKIP 6 LAJUR after selected_plan
                            coverage_level_str, None, "Yes, Contact Requested"
                        ]

                        append_row_to_sheet(row_data)
                        logger.info(f"[TABUNG_PERUBATAN] Data inserted to Google Sheet: Coverage Level={coverage_level_str} for user {user_id}")

                    except Exception as sheet_error:
                        logger.error(f"[TABUNG_PERUBATAN] Error inserting to Google Sheet: {sheet_error}", exc_info=True)

                    state.current_step = "contact_confirmed"
                    return {
                        "type": "buttons",
                        "content": "Great! Our agent will contact you soon. You will also receive an email about further information on the plans we offer.",
                        "next_step": "contact_confirmed",
                        "buttons": [
                            {"label": "🏠 Main Menu", "value": "main_menu"}
                        ]
                    }

                elif "no_contact" in message_lower or any(phrase in message_lower for phrase in ["no thanks", "no thank you", "no"]):
                    try:
                        name = state.user_data.get("name", state.name or "N/A")
                        dob = state.user_data.get("dob", "")
                        email = state.user_data.get("email", "")
                        primary_concern = state.user_data.get("primary_concern", "")
                        life_stage = state.user_data.get("life_stage", "")
                        dependents = state.user_data.get("dependents", "")
                        existing_coverage = state.user_data.get("existing_coverage", "")
                        premium_budget = state.user_data.get("premium_budget", "")
                        selected_plan = "tabung_perubatan"
                        coverage_level_str = str(state.coverage_level or "")

                        row_data = [
                            name, dob, email, primary_concern, life_stage, dependents,
                            existing_coverage, premium_budget, selected_plan,
                            None, None, None, None, None,  # SKIP 6 LAJUR after selected_plan
                            coverage_level_str, None, "No, Contact Declined"
                        ]

                        append_row_to_sheet(row_data)
                        logger.info(f"[TABUNG_PERUBATAN] Inserted row for no contact: Coverage Level={coverage_level_str} for user {user_id}")

                    except Exception as sheet_error:
                        logger.error(f"[TABUNG_PERUBATAN] Error inserting 'no contact' to Google Sheet: {sheet_error}", exc_info=True)

                    state.current_step = "end_options"
                    return {
                        "type": "buttons",
                        "content": "Thank you for your interest in Tabung Perubatan! If you wish to return to the main menu, click below.",
                        "next_step": "end_options",
                        "buttons": [
                            {"label": "🏠 Main Menu", "value": "main_menu"}
                        ]
                    }

                elif "other_plans" in message_lower or "other" in message_lower:
                    state.current_step = "show_plans"
                    return {
                        "type": "buttons",
                        "content": "Here are our other available plans that might interest you:",
                        "next_step": "show_plans",
                        "buttons": [
                            {"label": "💰 Tabung Warisan", "value": "tabung_warisan"},
                            {"label": "👨‍👩‍👧‍👦 Masa Depan Anak Kita", "value": "masa_depan_anak_kita"},
                            {"label": "💼 Satu Gaji Satu Harapan", "value": "satu_gaji"},
                            {"label": "🏠 Main Menu", "value": "main_menu"}
                        ]
                    }

                elif message_lower in ["main_menu", "restart"]:
                    # Fully reset conversation state and data
                    self._clear_state(user_id)
                    return {
                        "type": "reset_to_main",
                        "response": "Returning to main menu...",
                        "content": "Returning to main menu...",
                        "reset_to_main": True
                    }

                else:
                    # If unclear, prompt again
                    return {
                        "type": "buttons",
                        "content": "Would you like an agent to contact you to further discuss the plan?",
                        "next_step": "offer_agent_contact",
                        "buttons": [
                            {"label": "✅ Yes, contact me", "value": "contact_agent"},
                            {"label": "❌ No thanks", "value": "no_contact"},
                            {"label": "🏠 Main Menu", "value": "main_menu"}
                        ]
                    }

            # Get contact information (only name, no phone)
            elif state.current_step == "get_contact_info":
                import re
                name = re.sub(r'\d+', '', message_text).strip()
                if not name:
                    return {
                        "type": "message",
                        "content": "Please provide a valid name.",
                        "next_step": "get_contact_info"
                    }
                state.name = name
                state.current_step = "end_conversation"
                logger.info(f"Lead generated: {state.name}, Age: {state.age}, Coverage Level: {state.coverage_level}")
                return {
                    "type": "message",
                    "content": (
                        f"Thank you, {state.name}! Thank you for your interest in Tabung Perubatan! If you wish to return to the main menu, click below. 😊"
                    ),
                    "next_step": "end_conversation"
                }

            # End of conversation
            elif state.current_step == "end_conversation":
                return {
                    "type": "message",
                    "content": "Thank you for your interest in Tabung Perubatan. Have a great day!",
                    "response": "Thank you for your interest in Tabung Perubatan. Have a great day!",
                    "next_step": "end_conversation"
                }

            # Unknown state fallback
            else:
                logger.warning(f"Unknown state encountered: {state.current_step} for user {user_id}. Resetting to welcome.")
                state.current_step = "welcome"
                return await self.process_message(user_id, "start", ws, user_data)

        except Exception as e:
            logger.error(f"Error in process_message: {str(e)}", exc_info=True)
            return {
                "type": "message",
                "content": "Sorry, an error occurred. Let's start over.",
                "response": "Sorry, an error occurred. Let's start over.",
                "campaign_data": {},
                "next_step": "welcome"
            }


# Create a singleton instance
tabung_perubatan_campaign = TabungPerubatanCampaign()
tabung_perubatan_campaign_instance = tabung_perubatan_campaign

# For testing the campaign directly
if __name__ == "__main__":
    class MockWebSocket:
        def __init__(self):
            self.messages = []

        async def send_text(self, message: str):
            self.messages.append(message)
            print(f"BOT: {message}")

    async def test_campaign():
        campaign = TabungPerubatanCampaign()
        ws = MockWebSocket()
        user_id = "test_user"

        # Reset state
        if user_id in campaign.states:
            del campaign.states[user_id]
        campaign.states[user_id] = TabungPerubatanState()

        # Test the conversation flow
        responses = [
            "start",        # Welcome message
            "yes",          # Show me more
            "yes",          # Show me an estimate
            "35",           # Age (we expect external user_data to set age, but testing here)
            "1",            # Coverage level (Basic) - updated to only 1 and 3
            "yes",          # Connect with agent
            "John Doe",     # Name
            "main_menu",    # Return to main menu -> should clear state
            "start",        # Start again should be fresh
        ]

        # Simulate providing age via user_data for testing
        for i, msg in enumerate(responses):
            print(f"\nYOU: {msg}")
            # For testing, inject user_data age before coverage selection
            user_data = None
            if msg == "35":
                # emulate main conversation providing age
                user_data = {"age": 35, "name": "John Doe"}
            response = await campaign.process_message(user_id, msg, ws, user_data=user_data)
            if response:
                await ws.send_text(response.get("response", response.get("content", "No response")))

    asyncio.run(test_campaign())
