from pathlib import Path
from datetime import date
from pydantic import BaseModel
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client


# --------------------------------------------------
# SETUP
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

app = FastAPI()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("SUPABASE URL:", SUPABASE_URL)
print("SUPABASE KEY LOADED:", bool(SUPABASE_KEY))


# Separate clients
supabase_auth = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

supabase_db = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Nowshera Events API is connected!"
    }

class LoginData(BaseModel):
    email: str
    password: str

# --------------------------------------------------
# SIGNUP
# --------------------------------------------------

from fastapi import Request

@app.post("/signup")
async def signup(request: Request):
    try:
        # Try JSON body first
        try:
            data = await request.json()
            name = data.get("name")
            email = data.get("email")
            password = data.get("password")
        except:
            data = {}

        # If website sends query parameters
        if not name:
            name = request.query_params.get("name")

        if not email:
            email = request.query_params.get("email")

        if not password:
            password = request.query_params.get("password")

        if not name or not email or not password:
            return {
                "error": "Name, email and password are required"
            }

        response = supabase_auth.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "name": name
                }
            }
        })

        return {
            "message": "Signup successful",
            "user": response.user
        }

    except Exception as e:
        print("SIGNUP ERROR:", repr(e))
        return {
            "error": str(e)
        }


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

from fastapi import Request

@app.post("/login")
async def login(request: Request):
    try:
        # Try JSON body
        try:
            data = await request.json()
            email = data.get("email")
            password = data.get("password")
        except:
            email = None
            password = None

        # Also accept query parameters
        if not email:
            email = request.query_params.get("email")

        if not password:
            password = request.query_params.get("password")

        if not email or not password:
            return {
                "error": "Email and password are required"
            }

        response = supabase_auth.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        user = response.user

        role = "attendee"

        profile_response = (
            supabase_db
            .table("profiles")
            .select("role")
            .eq("id", user.id)
            .execute()
        )

        if profile_response.data:
            role = profile_response.data[0].get(
                "role",
                "attendee"
            )

        return {
            "message": "Login successful",
            "user_id": user.id,
            "email": user.email,
            "role": role
        }

    except Exception as e:
        print("LOGIN ERROR:", repr(e))
        return {
            "error": str(e)
        }

# --------------------------------------------------
# ADMIN CHECK
# --------------------------------------------------

def check_admin(user_id: str):
    try:
        response = (
            supabase_db
            .table("profiles")
            .select("role")
            .eq("id", user_id)
            .single()
            .execute()
        )

        if not response.data:
            return False

        return response.data.get("role") == "admin"

    except Exception as e:
        print("ADMIN CHECK ERROR:", repr(e))
        return False


# --------------------------------------------------
# GET ALL EVENTS
# --------------------------------------------------

@app.get("/events")
def get_events():
    try:
        response = (
            supabase_db
            .table("events")
            .select("*")
            .order("date")
            .execute()
        )

        return response.data

    except Exception as e:
        print("GET EVENTS ERROR:", repr(e))
        return {
            "error": str(e)
        }


# --------------------------------------------------
# GET AVAILABLE EVENTS
# --------------------------------------------------

@app.get("/available-events")
def get_available_events():
    try:
        response = (
            supabase_db
            .table("events")
            .select("*, registrations(id, status)")
            .eq("status", "published")
            .order("date")
            .execute()
        )

        available_events = []

        for event in response.data:

            active_registrations = [
                registration
                for registration in event.get(
                    "registrations",
                    []
                )
                if registration.get("status") == "active"
            ]

            registered_count = len(
                active_registrations
            )

            event.pop("registrations", None)

            if (
                registered_count < event["capacity"]
                and event["date"] >= str(date.today())
            ):
                event["registered_count"] = registered_count
                event["places_left"] = (
                    event["capacity"] - registered_count
                )

                available_events.append(event)

        return {
            "events": available_events
        }

    except Exception as e:
        print(
            "AVAILABLE EVENTS ERROR:",
            repr(e)
        )

        return {
            "error": str(e)
        }


# --------------------------------------------------
# REGISTER FOR EVENT
# --------------------------------------------------

@app.post("/register-event")
def register_event(
    user_id: str,
    event_id: str
):
    try:

        # 1. Get event
        event_response = (
            supabase_db
            .table("events")
            .select("*")
            .eq("id", event_id)
            .single()
            .execute()
        )

        event = event_response.data

        if not event:
            return {
                "error": "Event not found"
            }

        # 2. Event must be published
        if event["status"] != "published":
            return {
                "error": "This event is not available for registration"
            }

        # 3. Event cannot be in the past
        if event["date"] < str(date.today()):
            return {
                "error": "This event has already passed"
            }

        # 4. Check active duplicate
        existing = (
            supabase_db
            .table("registrations")
            .select("id")
            .eq("user_id", user_id)
            .eq("event_id", event_id)
            .eq("status", "active")
            .execute()
        )

        if existing.data:
            return {
                "error": "You are already registered"
            }

        # 5. Count active registrations
        registrations = (
            supabase_db
            .table("registrations")
            .select("id")
            .eq("event_id", event_id)
            .eq("status", "active")
            .execute()
        )

        registered_count = len(registrations.data)

        # 6. Check capacity
        if registered_count >= event["capacity"]:
            return {
                "error": "Event is full"
            }

        # 7. Check if user previously cancelled
        cancelled = (
            supabase_db
            .table("registrations")
            .select("id")
            .eq("user_id", user_id)
            .eq("event_id", event_id)
            .eq("status", "cancelled")
            .execute()
        )

        # 8. Re-activate cancelled registration
        if cancelled.data:

            response = (
                supabase_db
                .table("registrations")
                .update({
                    "status": "active"
                })
                .eq("id", cancelled.data[0]["id"])
                .execute()
            )

            return {
                "message": "Registration successful",
                "status": "active"
            }

        # 9. Create new registration
        response = (
            supabase_db
            .table("registrations")
            .insert({
                "user_id": user_id,
                "event_id": event_id,
                "status": "active"
            })
            .execute()
        )

        return {
            "message": "Registration successful",
            "status": "active"
        }

    except Exception as e:
        return {
            "error": "Unable to complete registration. Please try again."
        }
# --------------------------------------------------
# CREATE EVENT - ADMIN
# --------------------------------------------------

@app.post("/admin/events")
async def create_event(request: Request):
    try:
        # Read JSON body
        try:
            data = await request.json()
        except:
            data = {}

        user_id = data.get("user_id")
        title = data.get("title")
        description = data.get("description")
        event_date = data.get("date")
        event_time = data.get("time")
        location = data.get("location")
        capacity = data.get("capacity")

        # Also allow query parameters
        if not user_id:
            user_id = request.query_params.get("user_id")
        if not title:
            title = request.query_params.get("title")
        if not description:
            description = request.query_params.get("description")
        if not event_date:
            event_date = request.query_params.get("date")
        if not event_time:
            event_time = request.query_params.get("time")
        if not location:
            location = request.query_params.get("location")
        if capacity is None:
            capacity = request.query_params.get("capacity")

        # Required fields
        if not user_id:
            return {"error": "user_id is required"}

        if not title:
            return {"error": "title is required"}

        if not description:
            return {"error": "description is required"}

        if not event_date:
            return {"error": "date is required"}

        if not event_time:
            return {"error": "time is required"}

        if not location:
            return {"error": "location is required"}

        if capacity is None:
            return {"error": "capacity is required"}

        # Convert capacity to number
        try:
            capacity = int(capacity)
        except:
            return {"error": "Capacity must be a number"}

        # Admin check
        if not check_admin(user_id):
            return {"error": "Admin access required"}

        # Capacity validation
        if capacity <= 0:
            return {
                "error": "Capacity must be greater than 0"
            }

        # Create event as draft
        response = (
            supabase_db
            .table("events")
            .insert({
                "title": title,
                "description": description,
                "date": event_date,
                "time": event_time,
                "location": location,
                "status": "draft",
                "capacity": capacity
            })
            .execute()
        )

        return {
            "message": "Event created successfully",
            "event": response.data
        }

    except Exception as e:
        print(
            "CREATE EVENT ERROR:",
            repr(e)
        )

        return {
            "error": str(e)
        }

# --------------------------------------------------
# UPDATE EVENT - ADMIN
# --------------------------------------------------

@app.put("/admin/events/{event_id}")
async def update_event(event_id: str, request: Request):
    try:

        # Try JSON body first
        try:
            data = await request.json()
        except:
            data = {}

        # Accept JSON OR query parameters
        user_id = data.get("user_id")
        if not user_id:
            user_id = request.query_params.get("user_id")

        title = data.get("title")
        if not title:
            title = request.query_params.get("title")

        description = data.get("description")
        if not description:
            description = request.query_params.get("description")

        event_date = data.get("date")
        if not event_date:
            event_date = request.query_params.get("date")

        event_time = data.get("time")
        if not event_time:
            event_time = request.query_params.get("time")

        location = data.get("location")
        if not location:
            location = request.query_params.get("location")

        capacity = data.get("capacity")
        if capacity is None:
            capacity = request.query_params.get("capacity")

        status = data.get("status")
        if not status:
            status = request.query_params.get("status")

        # Check required fields
        if not user_id:
            return {"error": "user_id is required"}

        if not title:
            return {"error": "title is required"}

        if not description:
            return {"error": "description is required"}

        if not event_date:
            return {"error": "date is required"}

        if not event_time:
            return {"error": "time is required"}

        if not location:
            return {"error": "location is required"}

        if capacity is None:
            return {"error": "capacity is required"}

        if not status:
            return {"error": "status is required"}

        # Convert capacity to integer
        try:
            capacity = int(capacity)
        except:
            return {"error": "Capacity must be a number"}

        # Admin check
        if not check_admin(user_id):
            return {
                "error": "Admin access required"
            }

        # Capacity validation
        if capacity <= 0:
            return {
                "error": "Capacity must be greater than 0"
            }

        # Allowed statuses
        allowed_statuses = [
            "draft",
            "published",
            "completed",
            "cancelled"
        ]

        if status not in allowed_statuses:
            return {
                "error": "Invalid event status"
            }

        # Count active registrations
        registrations = (
            supabase_db
            .table("registrations")
            .select("id")
            .eq("event_id", event_id)
            .eq("status", "active")
            .execute()
        )

        active_count = len(registrations.data)

        # Capacity cannot be below active registrations
        if capacity < active_count:
            return {
                "error":
                "Capacity cannot be below active registrations"
            }

        # Update event
        response = (
            supabase_db
            .table("events")
            .update({
                "title": title,
                "description": description,
                "date": event_date,
                "time": event_time,
                "location": location,
                "capacity": capacity,
                "status": status
            })
            .eq("id", event_id)
            .execute()
        )

        if not response.data:
            return {
                "error": "Event not found"
            }

        return {
            "message": "Event updated successfully",
            "event": response.data
        }

    except Exception as e:
        print(
            "UPDATE EVENT ERROR:",
            repr(e)
        )

        return {
            "error": str(e)
        }

# --------------------------------------------------
# CANCEL EVENT - ADMIN
# --------------------------------------------------

@app.delete("/admin/events/{event_id}")
async def cancel_event(event_id: str, request: Request):
    try:
        # Try to get user_id from JSON body
        try:
            data = await request.json()
        except:
            data = {}

        user_id = data.get("user_id")

        # If not in body, try query parameter
        if not user_id:
            user_id = request.query_params.get("user_id")

        if not user_id:
            return {
                "error": "user_id is required"
            }

        # Admin check
        if not check_admin(user_id):
            return {
                "error": "Admin access required"
            }

        response = (
            supabase_db
            .table("events")
            .update({
                "status": "cancelled"
            })
            .eq("id", event_id)
            .execute()
        )

        if not response.data:
            return {
                "error": "Event not found"
            }

        return {
            "message": "Event cancelled successfully",
            "event": response.data
        }

    except Exception as e:
        print("CANCEL EVENT ERROR:", repr(e))

        return {
            "error": str(e)
        }

# --------------------------------------------------
# ADMIN REGISTRATIONS
# --------------------------------------------------

@app.get("/admin/registrations")
def get_registrations(
    user_id: str
):
    try:

        # Admin check
        if not check_admin(user_id):
            return {
                "error":
                "Admin access required"
            }

        response = (
            supabase_db
            .table("registrations")
            .select("*")
            .eq("status", "active")
            .execute()
        )

        return {
            "registrations":
            response.data,
            "total":
            len(response.data)
        }

    except Exception as e:
        print(
            "GET REGISTRATIONS ERROR:",
            repr(e)
        )

        return {
            "error": str(e)
        }


# --------------------------------------------------
# MY REGISTRATIONS
# --------------------------------------------------

@app.get("/my-registrations")
def my_registrations(
    user_id: str
):
    try:

        response = (
            supabase_db
            .table("registrations")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )

        return {
            "registrations":
            response.data
        }

    except Exception as e:
        print(
            "MY REGISTRATIONS ERROR:",
            repr(e)
        )

        return {
            "error": str(e)
        }


# --------------------------------------------------
# GET ONE REGISTRATION
# --------------------------------------------------

@app.get("/registrations/{registration_id}")
def get_registration(
    registration_id: str,
    user_id: str
):
    try:

        response = (
            supabase_db
            .table("registrations")
            .select("*")
            .eq("id", registration_id)
            .single()
            .execute()
        )

        registration = response.data

        if not registration:
            return {
                "error":
                "Registration not found"
            }

        # User can only access their own registration
        if registration["user_id"] != user_id:

            # Admin can access registrations
            if not check_admin(user_id):
                return {
                    "error":
                    "Access denied"
                }

        return {
            "registration":
            registration
        }

    except Exception as e:
        print(
            "GET REGISTRATION ERROR:",
            repr(e)
        )

        return {
            "error": str(e)
        }


# --------------------------------------------------
# CANCEL REGISTRATION
# --------------------------------------------------

@app.put("/cancel-registration")
def cancel_registration(
    user_id: str,
    registration_id: str
):
    try:

        response = (
            supabase_db
            .table("registrations")
            .update({
                "status": "cancelled"
            })
            .eq("id", registration_id)
            .eq("user_id", user_id)
            .eq("status", "active")
            .execute()
        )

        if not response.data:
            return {
                "error":
                "Active registration not found"
            }

        return {
            "message":
            "Registration cancelled successfully",
            "registration":
            response.data
        }

    except Exception as e:
        print(
            "CANCEL REGISTRATION ERROR:",
            repr(e)
        )

        return {
            "error": str(e)
        }