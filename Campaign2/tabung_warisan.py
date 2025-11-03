from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
import logging
from datetime import datetime
import asyncio
from Google_Sheet import append_row_to_sheet

logger = logging.getLogger(__name__)

def format_currency(amount: float) -> str:
    try:
        return f"RM {float(amount):,.2f}"
    except (ValueError, TypeError):
        return "RM 0.00"

@dataclass
class TabungWarisanState:
    """State management for Tabung Warisan campaign."""
    current_step: str = "welcome"
    user_data: Dict[str, Any] = field(default_factory=dict)
    user_name: Optional[str] = None
    user_age: Optional[int] = None
    desired_legacy: Optional[float] = None
    welcome_shown: bool = False

    def reset(self):
        self.current_step = "welcome"
        self.user_data.clear()
        self.user_name = None
        self.user_age = None
        self.desired_legacy = None
        self.welcome_shown = False

    def calculate_warisan_premium_estimation(self, legacy_amount: float, age: int) -> float:
        try:
            legacy_amount = float(legacy_amount)
        except (ValueError, TypeError):
            legacy_amount = 0.0

        if age <= 35:
            base_factor = 4.8
        elif age <= 45:
            base_factor = 9
        else:
            base_factor = 17
        return (legacy_amount / 1000) * base_factor


class TabungWarisanCampaign:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if not self.initialized:
            self.states: Dict[str, TabungWarisanState] = {}
            self.last_active: Dict[str, float] = {}
            self.name = "Tabung Warisan"
            self.description = "Legacy planning to secure your family's future"
            self.initialized = True

    def get_state(self, user_id: str) -> TabungWarisanState:
        if user_id not in self.states:
            self.states[user_id] = TabungWarisanState()
        self.last_active[user_id] = datetime.now().timestamp()
        return self.states[user_id]

    def get_welcome_message(self) -> str:
        return (
            "🌟 *Welcome to Tabung Warisan!* 🌟\n\n"
            "Protect your family's future with our legacy planning solution. "
            "With Tabung Warisan, you can ensure your loved ones are taken care of "
            "with guaranteed financial protection and wealth accumulation options."
        )

    def get_benefits(self) -> List[Dict[str, Any]]:
        return [
            {
                "title": "LIFETIME PROTECTION",
                "description": "Your legacy is protected for life.",
                "points": [
                    "Guaranteed payout to your beneficiaries",
                    "Coverage that lasts your entire lifetime",
                    "Financial security for your loved ones"
                ]
            },
            {
                "title": "WEALTH ACCUMULATION",
                "description": "Grow your wealth over time.",
                "points": [
                    "Cash value that grows tax-deferred",
                    "Potential for long-term growth",
                    "Flexible premium payment options"
                ]
            },
            {
                "title": "PEACE OF MIND",
                "description": "Know your family is taken care of.",
                "points": [
                    "Financial protection for your loved ones",
                    "No medical check-up required",
                    "Guaranteed acceptance"
                ]
            }
        ]

    def _format_benefits(self, benefits: List[Dict[str, Any]]) -> str:
        formatted = []
        for benefit in benefits:
            formatted.append(f"*{benefit['title']}*")
            formatted.append(f"{benefit['description']}")
            for point in benefit['points']:
                formatted.append(f"• {point}")
            formatted.append("")
        return "\n".join(formatted)

    def _get_welcome_response(self) -> Dict[str, Any]:
        welcome_message = self.get_welcome_message()
        return {
            "type": "message",
            "text": welcome_message + "\n\nWould you like to learn more about the benefits?",
            "content": welcome_message + "\n\nWould you like to learn more about the benefits?",
            "buttons": [
                {"label": "✅ Yes, tell me more", "value": "yes_benefits"},
                {"label": "❌ Not now, thanks", "value": "no_thanks"}
            ],
            "next_step": "handle_welcome_response"
        }

    def _get_benefits_response(self) -> Dict[str, Any]:
        benefits_text = self._format_benefits(self.get_benefits())
        question = "\n\nWould you like to see how much coverage you can get?"
        full_message = benefits_text + question
        return {
            "type": "buttons",
            "text": full_message,
            "content": full_message,
            "buttons": [
                {"label": "✅ Yes, show me", "value": "yes_coverage"},
                {"label": "❌ Maybe later", "value": "no_thanks"},
            ],
            "next_step": "handle_benefits_response"
        }

    async def _handle_legacy_amount(self, state: TabungWarisanState, message: Union[str, dict]) -> Dict[str, Any]:
        try:
            if isinstance(message, dict):
                message_text = message.get('value') or message.get('text') or str(message)
            else:
                message_text = str(message)

            if message_text.lower() in ["other", "other amount", "other_amount"]:
                state.current_step = "get_custom_legacy_amount"
                return {
                    "type": "message",
                    "content": "Please enter your desired legacy amount (minimum RM 1,000):",
                    "next_step": "get_custom_legacy_amount"
                }

            amount = float(''.join(c for c in message_text if c.isdigit() or c == '.'))
            if amount < 1000:
                return {
                    "type": "buttons",
                    "text": "The minimum legacy amount is RM 1,000. Please select an amount:",
                    "content": "The minimum legacy amount is RM 1,000. Please select an amount:",
                    "buttons": [
                        {"label": "RM 500,000", "value": "500000"},
                        {"label": "RM 1,000,000", "value": "1000000"},
                        {"label": "RM 1,500,000", "value": "1500000"},
                        {"label": "RM 2,000,000", "value": "2000000"},
                        {"label": "Other Amount", "value": "other_amount"}
                    ],
                    "next_step": "get_legacy_amount"
                }

            state.desired_legacy = amount

            if state.user_age:
                if state.user_age < 18:
                    state.current_step = "main_menu"
                    return {
                        "type": "buttons",
                        "content": (
                            "Sorry, Tabung Warisan is only available for users aged 18 and above.\n"
                            "Please return to the main menu."
                        ),
                        "buttons": [
                            {"label": "🏠 Return to Main Menu", "value": "main_menu"}
                        ],
                        "next_step": "main_menu"
                    }
                if state.user_age > 70:
                    state.current_step = "get_age"
                    return {
                        "type": "message",
                        "content": "Please enter a valid age between 18 and 70.",
                        "next_step": "get_age"
                    }
                premium = state.calculate_warisan_premium_estimation(amount, state.user_age)
                monthly_premium = premium / 12
                state.current_step = "offer_agent_contact"
                return {
                    "type": "buttons",
                    "content": (
                        f"Great! I see you are {state.user_age} years old and want to leave {format_currency(amount)} as a legacy.\n\n"
                        f"Your estimated premium would be:\n"
                        f"- Annual: *{format_currency(premium)}*\n"
                        f"- Monthly: *{format_currency(monthly_premium)}*\n\n"
                        "Would you like an agent to contact you to further discuss the plan?"
                    ),
                    "next_step": "offer_agent_contact",
                    "buttons": [
                        {"label": "✅ Yes, contact me", "value": "contact_agent"},
                        {"label": "❌ No thanks", "value": "no_contact"}
                    ]
                }
            else:
                state.current_step = "get_age"
                return {
                    "type": "message",
                    "content": (
                        f"Great! You want to leave {format_currency(amount)} as a legacy.\n\n"
                        "Now, may I know your current age? (18-70 years)"
                    ),
                    "next_step": "get_age"
                }
        except (ValueError, TypeError):
            return {
                "type": "buttons",
                "text": "Please select a valid legacy amount:",
                "content": "Please select a valid legacy amount:",
                "buttons": [
                    {"label": "RM 500,000", "value": "500000"},
                    {"label": "RM 1,000,000", "value": "1000000"},
                    {"label": "RM 1,500,000", "value": "1500000"},
                    {"label": "RM 2,000,000", "value": "2000000"},
                    {"label": "Other Amount", "value": "other_amount"}
                ],
                "next_step": "get_legacy_amount"
            }

    async def _handle_age(self, state: TabungWarisanState, message: Union[str, dict]) -> Dict[str, Any]:
        try:
            if isinstance(message, dict):
                message_text = message.get('value') or message.get('text') or str(message)
            else:
                message_text = str(message)

            age = int(''.join(c for c in message_text if c.isdigit()))
            if age < 18:
                # User is under 18, show error and main menu button
                state.current_step = "main_menu"
                return {
                    "type": "buttons",
                    "content": (
                        "Sorry, Tabung Warisan is only available for users aged 18 and above.\n"
                        "Please return to the main menu."
                    ),
                    "buttons": [
                        {"label": "🏠 Return to Main Menu", "value": "main_menu"}
                    ],
                    "next_step": "main_menu"
                }
            if age > 70:
                return {
                    "type": "message",
                    "content": "Please enter a valid age between 18 and 70.",
                    "next_step": "get_age"
                }

            state.user_age = age
            premium = state.calculate_warisan_premium_estimation(state.desired_legacy or 0, age)
            monthly_premium = premium / 12
            state.current_step = "offer_agent_contact"
            return {
                "type": "buttons",
                "content": (
                    f"Based on your age of {age} and desired legacy of {format_currency(state.desired_legacy or 0)}, "
                    f"your estimated premium would be:\n"
                    f"- Annual: *{format_currency(premium)}*\n"
                    f"- Monthly: *{format_currency(monthly_premium)}*\n\n"
                    "Would you like an agent to contact you to further discuss the plan?"
                ),
                "next_step": "offer_agent_contact",
                "buttons": [
                    {"label": "✅ Yes, contact me", "value": "contact_agent"},
                    {"label": "❌ No thanks", "value": "no_contact"}
                ]
            }
        except (ValueError, TypeError):
            return {
                "type": "message",
                "content": "Please enter a valid age between 18 and 70.",
                "next_step": "get_age"
            }

    def _handle_agent_contact(self, state: TabungWarisanState, message: Union[str, dict]) -> Dict[str, Any]:
        try:
            if isinstance(message, dict):
                message_value = (message.get('value') or message.get('text') or str(message)).lower().strip()
            else:
                message_value = str(message).lower().strip()

            if message_value == "contact_agent":
                # Prepare data for Google Sheet
                try:
                    name = state.user_data.get("name") or state.user_name or "N/A"
                    dob = state.user_data.get("dob", "")
                    email = state.user_data.get("email", "")
                    primary_concern = state.user_data.get("primary_concern", "")
                    life_stage = state.user_data.get("life_stage", "")
                    dependents = state.user_data.get("dependents", "")
                    existing_coverage = state.user_data.get("existing_coverage", "")
                    premium_budget = state.user_data.get("premium_budget", "")
                    selected_plan = "tabung_warisan"
                    legacy_amount_str = format_currency(state.desired_legacy or 0)
                    

                    row_data = [
                        name, dob, email, primary_concern, life_stage, dependents,
                        existing_coverage, premium_budget, selected_plan,
                        None, None, legacy_amount_str, None, None,None,None,"Yes, Contact Requested"]

                    append_row_to_sheet(row_data)
                    logger.info(
                        f"[TABUNG_WARISAN] Data inserted to Google Sheet: Name={name}, Legacy={legacy_amount_str}, "
                        f"Email={email}"
                    )
                except Exception as e:
                    logger.error(f"[TABUNG_WARISAN] Failed to append to Google Sheet: {e}")

                state.current_step = "main_menu"
                return {
                    "type": "buttons",
                    "content": "Thank you for your interest in Tabung Warisan! If you wish to return to the main menu, click below.",
                    "next_step": "main_menu",
                    "buttons": [
                        {"label": "🏠 Return to Main Menu", "value": "main_menu"}
                    ]
                }

            if message_value == "no_contact":
                try:
                    name = state.user_data.get("name") or state.user_name or "N/A"
                    dob = state.user_data.get("dob", "")
                    email = state.user_data.get("email", "")
                    primary_concern = state.user_data.get("primary_concern", "")
                    life_stage = state.user_data.get("life_stage", "")
                    dependents = state.user_data.get("dependents", "")
                    existing_coverage = state.user_data.get("existing_coverage", "")
                    premium_budget = state.user_data.get("premium_budget", "")
                    selected_plan = "tabung_warisan"
                    legacy_amount_str = format_currency(state.desired_legacy or 0)

                    row_data =[
                        name, dob, email, primary_concern, life_stage, dependents,
                    existing_coverage, premium_budget, selected_plan,
                    None, None, legacy_amount_str, None, None, None, None, "No, Contact Declined"
                    ]

                    append_row_to_sheet(row_data)
                    logger.info(
                        f"[TABUNG_WARISAN]Data inserted to Google Sheet: Name={name}, Legacy={legacy_amount_str}, Email={email}, Contact=No"
                    )
                except Exception as e:
                    logger.error(f"[TABUNG_WARISAN] Failed to append to Google Sheet (No Contact): {e}")

                state.current_step = "main_menu"
                return {
                    "type": "buttons",
                    "content": "Thank you for your interest! You may return to the main menu below.",
                    "buttons": [
                        {"label": "🏠 Return to Main Menu", "value": "main_menu"}
                    ],
                    "next_step": "main_menu"
                }

            if message_value in ["main_menu", "restart"]:
                state.reset()
                return {
                    "type": "reset_to_main",
                    "response": "Returning to main menu...",
                    "content": "Returning to main menu...",
                    "reset_to_main": True
                }

            # Default fallback
            return {
                "type": "buttons",
                "text": "Would you like an agent to contact you to further discuss the plan?",
                "content": "Would you like an agent to contact you to further discuss the plan?",
                "next_step": "offer_agent_contact",
                "buttons": [
                    {"label": "✅ Yes, contact me", "value": "contact_agent"},
                    {"label": "❌ No thanks", "value": "no_contact"}
                ]
            }

        except Exception as e:
            logger.error(f"Error in _handle_agent_contact: {e}")
            return {
                "type": "message",
                "content": "I'm sorry, something went wrong. Let's try that again.",
                "next_step": "offer_agent_contact"
            }

    async def process_message(self, user_id: str, message: Union[str, dict], ws: Any = None, user_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            state = self.get_state(user_id)
            logger.info(f"[TabungWarisan] Processing message for user_id={user_id}: {message}")

            # Merge incoming user_data (if provided)
            if user_data:
                state.user_data.update(user_data)
                if 'age' in user_data and user_data['age']:
                    try:
                        state.user_age = int(user_data['age'])
                        logger.info(f"[TabungWarisan] Updated age from main conversation: {state.user_age}")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"[TabungWarisan] Invalid age in user_data: {user_data['age']}. Error: {e}")
                if 'name' in user_data and user_data['name']:
                    state.user_name = user_data.get('name')
                    logger.info(f"[TabungWarisan] Updated name from main conversation: {state.user_name}")

            # Extract message text
            if isinstance(message, dict):
                msg_payload = message.get('value') or message.get('text') or str(message)
            else:
                msg_payload = str(message)

            msg_lower = msg_payload.lower().strip()

            # Global commands
            if msg_lower in ["main_menu", "restart", "start"]:
                state.reset()
                return {
                    "type": "reset_to_main",
                    "content": "Returning to main menu. Let's start again! What's your name?"
                }

            # Show welcome if not yet shown
            if state.current_step in ["", "welcome"] or not state.welcome_shown:
                state.current_step = "handle_welcome_response"
                state.welcome_shown = True
                return self._get_welcome_response()

            # Handle welcome response
            if state.current_step == "handle_welcome_response":
                if msg_lower in ["yes", "yes_benefits", "yes, tell me more"]:
                    state.current_step = "handle_benefits_response"
                    return self._get_benefits_response()
                elif msg_lower in ["no", "no_thanks", "maybe later", "later"]:
                    return {
                        "type": "buttons",
                        "content": "No problem! If you wish to return to the main menu and restart the bot, click below.",
                        "buttons": [
                            {"label": "🏠 Return to Main Menu", "value": "main_menu"}
                        ]
                    }
                else:
                    return self._get_welcome_response()

            # Handle benefits response
            if state.current_step == "handle_benefits_response":
                if msg_lower in ["yes", "yes_coverage", "yes, show me"]:
                    # Check age restriction before proceeding
                    if state.user_age and state.user_age < 18:
                        state.current_step = "main_menu"
                        return {
                            "type": "buttons",
                            "content": (
                                "Sorry, Tabung Warisan is only available for users aged 18 and above.\n"
                                "Please return to the main menu."
                            ),
                            "buttons": [
                                {"label": "🏠 Return to Main Menu", "value": "main_menu"}
                            ],
                            "next_step": "main_menu"
                        }
                    
                    state.current_step = "get_legacy_amount"
                    return {
                        "type": "buttons",
                        "text": "Great! To calculate your coverage, I'll need a few details.\n\n"
                               "How much would you like to leave as a legacy for your loved ones?",
                        "content": "Great! To calculate your coverage, I'll need a few details.\n\n"
                                   "How much would you like to leave as a legacy for your loved ones?",
                        "buttons": [
                            {"label": "RM 500,000", "value": "500000"},
                            {"label": "RM 1,000,000", "value": "1000000"},
                            {"label": "RM 1,500,000", "value": "1500000"},
                            {"label": "RM 2,000,000", "value": "2000000"},
                            {"label": "Other Amount", "value": "other_amount"}
                        ],
                        "next_step": "get_legacy_amount"
                    }
                elif msg_lower in ["no", "no_thanks", "maybe later", "later"]:
                                        return {
                        "type": "buttons",
                        "content": "Thank you for your interest in Tabung Warisan! If you wish to return to the main menu, click below.",
                        "buttons": [
                            {"label": "🏠 Return to Main Menu", "value": "main_menu"}
                        ]
                    }
                else:
                    return self._get_benefits_response()

            # Legacy amount step
            if state.current_step == "get_legacy_amount":
                return await self._handle_legacy_amount(state, msg_payload)

            # Custom legacy amount step
            if state.current_step == "get_custom_legacy_amount":
                try:
                    amount_text = msg_payload if not isinstance(msg_payload, dict) else (msg_payload.get('value') or msg_payload.get('text') or str(msg_payload))
                    amount = float(''.join(c for c in str(amount_text) if c.isdigit() or c == '.'))
                    if amount < 1000:
                        return {
                            "type": "message",
                            "content": "The minimum legacy amount is RM 1,000. Please enter a higher amount:",
                            "next_step": "get_custom_legacy_amount"
                        }
                    state.desired_legacy = amount
                    if state.user_age and 18 <= state.user_age <= 70:
                        premium = state.calculate_warisan_premium_estimation(amount, state.user_age)
                        monthly_premium = premium / 12
                        state.current_step = "offer_agent_contact"
                        return {
                            "type": "buttons",
                            "content": (
                                f"Great! I see you are {state.user_age} years old and want to leave {format_currency(amount)} as a legacy.\n\n"
                                f"Your estimated premium would be:\n"
                                f"- Annual: *{format_currency(premium)}*\n"
                                f"- Monthly: *{format_currency(monthly_premium)}*\n\n"
                                "Would you like an agent to contact you to further discuss the plan?"
                            ),
                            "next_step": "offer_agent_contact",
                            "buttons": [
                                {"label": "✅ Yes, contact me", "value": "contact_agent"},
                                {"label": "❌ No thanks", "value": "no_contact"}
                            ]
                        }
                    else:
                        state.current_step = "get_age"
                        return {
                            "type": "message",
                            "content": (
                                f"Great! You want to leave {format_currency(amount)} as a legacy.\n\n"
                                "Now, may I know your current age? (18-70 years)"
                            ),
                            "next_step": "get_age"
                        }
                except (ValueError, TypeError):
                    return {
                        "type": "message",
                        "content": "Please enter a valid amount (e.g., 100000 or 100,000):",
                        "next_step": "get_custom_legacy_amount"
                    }

            # Age step
            if state.current_step == "get_age":
                return await self._handle_age(state, msg_payload)

            # Offer agent contact step
            if state.current_step == "offer_agent_contact":
                return self._handle_agent_contact(state, message)

            # Main menu / after contact
            if state.current_step == "main_menu":
                if msg_lower == "main_menu":
                    state.reset()
                    return {
                        "type": "reset_to_main",
                        "content": "Returning to main menu. Let's start again! What's your name?"
                    }
                return {
                    "type": "buttons",
                    "content": "Thank you for your interest! You may return to the main menu below.",
                    "buttons": [
                        {"label": "🏠 Return to Main Menu", "value": "main_menu"}
                    ],
                    "next_step": "main_menu"
                }

            # Fallback: reset and start over
            logger.warning(f"[TabungWarisan] Unhandled step '{state.current_step}' for user {user_id}. Resetting.")
            state.reset()
            return {
                "type": "reset_to_main",
                "response": "Returning to main menu...",
                "content": "Returning to main menu...",
                "reset_to_main": True
            }

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"[TabungWarisan] Error in process_message: {e}\n{error_details}")
            return {
                "type": "message",
                "content": "I'm sorry, something went wrong. The error has been logged. Let's start over.",
                "next_step": "welcome"
            }


# Create the campaign instance with the exact name expected by main.py
tabung_warisan_campaign_instance = TabungWarisanCampaign()

# Alias for backward compatibility
tabung_warisan_campaign = tabung_warisan_campaign_instance
