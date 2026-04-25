from .base_agent import BaseAgent
import datetime
import json

class BookingAgent(BaseAgent):
    def get_details(self, compressed_draft, trip_summary):
        current_year = datetime.datetime.now().year
        today = datetime.date.today().isoformat()
        dest = trip_summary.get("destination", "the destination")
        requires_flight = trip_summary.get("requires_flight", True)
        travel_dates = trip_summary.get("travel_dates", "")
        duration = trip_summary.get("duration_days", 7)

        if travel_dates:
            date_instruction = f"User's travel period: {travel_dates}. You MUST pick a specific departure date (YYYY-MM-DD) within that period and set the return date = departure date + {duration - 1} days."
        else:
            date_instruction = f"No specific dates provided. Pick a reasonable departure date in {current_year} (at least 2 weeks from today) and set the return date = departure date + {duration - 1} days."

        system_prompt = f"""You are the Booking Agent for DaddiesTrip. Depart from KUL, Malaysia. Today is {today}. {date_instruction} All flight dates MUST be concrete YYYY-MM-DD format — never leave them vague or empty.

Return JSON:
{{
  "destination_currency": "<ISO>",
  "destination_iata": "<IATA>",
  "destination_review": {{"name":"...","rating":"4.x/5","review_count":"...","review_comment":"short line"}},
  "flight_options": [/* 3 if requires_flight, else [] */],
  "itinerary_details": [/* EXACTLY {duration} entries */]
}}

FLIGHTS (if requires_flight=true): 3 options with different airlines (e.g. AirAsia AK, MH, Batik Air OD). "cost_myr"=per-person round-trip. Each flight option MUST follow this exact structure:
{{"airline":"Airline Name","airline_iata":"XX","cost_myr":N,"departure":{{"airport":"KUL","date":"YYYY-MM-DD","time":"HH:MM"}},"return":{{"airport":"<dest IATA>","date":"YYYY-MM-DD","arrival_time":"HH:MM"}}}}
IMPORTANT: "departure.time" and "return.arrival_time" are REQUIRED — never omit them. Use realistic flight times (e.g. "08:30", "14:15", "22:00").

TRANSPORT ACCURACY: When describing airport transfers or transport from/to the airport, you MUST reference the actual airport IATA code from your flight_options (e.g. if flight lands at HND use Haneda transport, if NRT use Narita Express, if HND use Keikyu Line or Tokyo Monorail). Never assume the airport — always check the IATA code in flight_options first.

PER DAY — EXACTLY {duration} days:
- "day": N
- "hotel": {{"name":"<real hotel>","cost_myr":<NEVER 0>,"rating":"4.x/5"}} — every day must have hotel with non-zero cost. Repeat if same hotel.
- "activities": [{{"name":"...","cost_myr":N,"schedule":"HH:MM-HH:MM","rating":"4.x/5","transport_to_next":{{"mode":"...","duration":"...","estimated_cost_myr":N,"notes":"..."}}}}] — include transport_to_next for all activities except last of day.
- "food_recommendations": EXACTLY 3 per day: [{{"name":"...","avg_cost_myr":<NEVER 0>,"type":"breakfast or lunch or dinner","rating":"4.x/5"}}]
- "daily_food_cost_myr": sum of food avg_cost_myr (NEVER 0)

BUDGET: Group budget RM {trip_summary.get('budget_myr', 5000)}. Stay under budget. Prefer cost-effective options. Short responses. Realistic KUL→{dest} costs."""

        user_prompt = f"Trip: {json.dumps(trip_summary, separators=(',', ':'))}\nItinerary: {json.dumps(compressed_draft, separators=(',', ':'))}"
        return self.query(system_prompt, user_prompt, max_tokens=6000)

    def amend_item(self, item_type, current_item, user_preference, trip_summary):
        current_year = datetime.datetime.now().year
        today = datetime.date.today().isoformat()
        dest = trip_summary.get("destination", "the destination")

        if item_type == "hotel":
            schema = '{{"name":"...","cost_myr":N,"rating":"4.x/5"}}'
            instruction = f"Replace the hotel with one matching the user's preference. Return exactly ONE hotel object: {schema}"
        elif item_type == "food":
            schema = '[{{"name":"...","avg_cost_myr":N,"type":"breakfast or lunch or dinner","rating":"4.x/5"}}]'
            instruction = f"Replace the food recommendation(s) with ones matching the user's preference. Return exactly 3 items: {schema}"
        elif item_type == "activity":
            schema = '{{"name":"...","cost_myr":N,"schedule":"HH:MM-HH:MM","rating":"4.x/5","transport_to_next":{{"mode":"...","duration":"...","estimated_cost_myr":N,"notes":"..."}}}}'
            instruction = f"Replace the activity with one matching the user's preference. Return exactly ONE activity object: {schema}"
        else:
            raise ValueError(f"Unknown item_type: {item_type}")

        system_prompt = f"""You are the Booking Agent for DaddiesTrip. Today is {today}. Destination: {dest}. All dates must be {current_year} or later. Budget: RM {trip_summary.get('budget_myr', 5000)}.

{instruction}

Output ONLY valid JSON matching the schema above. No explanation needed."""

        user_prompt = f"Current item: {json.dumps(current_item, separators=(',', ':'))}\nUser wants: {user_preference}"
        return self.query(system_prompt, user_prompt, max_tokens=1000)
