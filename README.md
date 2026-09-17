# Nowshera Events Co.

## Project Overview

Nowshera Events Co. is a full-stack event registration and management system designed to replace manual WhatsApp and spreadsheet-based event registration.

The system allows attendees to discover and register for events while administrators can manage events, registrations, capacities, and attendees from one place.

## Features

### Attendee

* Sign up and log in
* View published events
* Register for available events
* Cancel event registrations
* View registration status
* Prevent duplicate registrations
* Prevent registration when an event is full
* Prevent registration for cancelled or unavailable events

### Admin

* Create events
* Edit events
* Publish events
* Cancel events
* Complete events
* Manage event capacity
* View registered attendees
* View registration totals
* Manage event information

### Security and Validation

* User authentication
* Role-based access
* Server-side validation
* Duplicate registration prevention
* Event capacity validation
* Cancelled-event protection
* Persistent database storage

## Technology Stack

* Frontend: HTML, CSS, JavaScript
* Backend: Python, FastAPI
* Database: Supabase PostgreSQL
* Authentication: Supabase Auth
* API: FastAPI REST API

## Project Structure

The project contains separate frontend and backend components, with the FastAPI backend handling authentication, event management, registrations, and database operations.

## API Features

The backend provides functionality for:

* User signup
* User login
* Event listing
* Event registration
* Registration cancellation
* Duplicate registration prevention
* Capacity checking
* Event status validation
* Registration persistence

## Testing

The system was tested for:

* Attendee registration
* Duplicate registration prevention
* Full-event protection
* Cancelled-event protection
* Registration cancellation
* Published event visibility
* Event status handling
* Registration persistence after refresh
* Admin event management
* Attendee registration tracking

## Security

Sensitive Supabase credentials are stored using environment variables and are not included in the public repository.

## Purpose

This project was developed as a practical full-stack project to demonstrate skills in:

* Python
* FastAPI
* Supabase
* REST APIs
* Authentication
* PostgreSQL
* Backend validation
* Event management systems

## Project Status

Completed and tested according to the project requirements.
