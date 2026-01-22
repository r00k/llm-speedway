# Conference Scheduler Specification

Build a REST API that generates valid schedules for a tech conference. Given rooms, sessions, speakers, and attendees with various constraints, produce a schedule that satisfies all constraints.

## Overview

The scheduler receives conference data via POST and returns a schedule assigning each session to a room and time slot. The solution must satisfy all **hard constraints** or be rejected as infeasible.

---

## API Endpoints

### POST /schedule

Generate a schedule for the given conference data.

**Request Body:**
```json
{
  "rooms": [...],
  "sessions": [...],
  "speakers": [...],
  "attendees": [...],
  "time_slots": [...]
}
```

**Response 200:** Valid schedule generated.
```json
{
  "status": "success",
  "schedule": [
    {"session_id": "S1", "room_id": "R1", "time_slot": "09:00"},
    {"session_id": "S2", "room_id": "R2", "time_slot": "09:00"},
    ...
  ]
}
```

**Response 200:** No valid schedule possible.
```json
{
  "status": "infeasible",
  "reason": "Speaker alice has 3 sessions but only 2 available time slots"
}
```

**Response 400:** Invalid input data.
```json
{
  "error": "Invalid input",
  "details": ["Room R1 has negative capacity", "Unknown speaker referenced in session S3"]
}
```

---

### GET /healthz

Health check endpoint.

**Response 200:**
```json
{"status": "ok"}
```

---

## Data Models

### Room
```json
{
  "id": "string",
  "name": "string",
  "capacity": "integer (1-10000)",
  "amenities": ["array of strings (default: [])"]
}
```

**Amenities** are arbitrary strings like: `"projector"`, `"whiteboard"`, `"video_recording"`, `"wheelchair_accessible"`, `"natural_light"`.

### Session
```json
{
  "id": "string",
  "title": "string",
  "duration_minutes": "integer (15-480)",
  "speaker_ids": ["array of speaker IDs (1 or more)"],
  "track": "string or null (default: null)",
  "required_amenities": ["array of strings (default: [])"],
  "expected_attendance": "integer (0-10000)",
  "is_keynote": "boolean (default: false)"
}
```

### Speaker
```json
{
  "id": "string",
  "name": "string",
  "unavailable_slots": ["array of time slot strings (default: [])"],
  "preferred_slots": ["array of time slot strings (default: [], unused for constraint checking)"]
}
```

### Attendee
```json
{
  "id": "string",
  "must_attend": ["array of session IDs (default: [])"],
  "wants_to_attend": ["array of session IDs (default: [], unused for constraint checking)"]
}
```

### TimeSlot
```json
{
  "start": "string (HH:MM, 24-hour format)",
  "duration_minutes": "integer"
}
```

Example time slots for a day:
```json
[
  {"start": "09:00", "duration_minutes": 60},
  {"start": "10:00", "duration_minutes": 60},
  {"start": "11:00", "duration_minutes": 60},
  {"start": "12:00", "duration_minutes": 60},
  {"start": "14:00", "duration_minutes": 60},
  {"start": "15:00", "duration_minutes": 60},
  {"start": "16:00", "duration_minutes": 60}
]
```

---

## Hard Constraints (Must Satisfy)

Violation of ANY hard constraint makes the schedule invalid.

**Note on time slots:** Time slots are discrete scheduling units. A session assigned to a slot **occupies the entire slot** for all conflict constraints, regardless of its `duration_minutes`. Session duration is only used to ensure the session fits (`HC6`); the scheduler does not pack multiple sessions within a single slot. Two sessions "overlap" if and only if they are assigned to the same time slot.

### HC1: No Speaker Conflicts
A speaker cannot be in two sessions scheduled for the same time slot.

### HC2: Room Capacity
`room.capacity >= session.expected_attendance`

### HC3: Room Amenities
Room must have ALL amenities required by the session:
`session.required_amenities ⊆ room.amenities`

### HC4: Speaker Availability
Sessions cannot be scheduled when ANY of their speakers are unavailable:
`session.time_slot ∉ speaker.unavailable_slots` for all speakers

### HC5: No Room Double-Booking
A room can only host one session per time slot.

### HC6: Session Fits Time Slot
`session.duration_minutes <= time_slot.duration_minutes`

### HC7: All Sessions Scheduled
Every session must be assigned exactly one room and time slot.

### HC8: Track Non-Overlap
Sessions in the same track cannot be in the same time slot.
(Allows attendees to attend all sessions in a track)

### HC9: Keynote Exclusivity
When a keynote is scheduled, no other sessions run in that time slot.
(All attendees should be able to attend keynotes)

### HC10: Attendee Must-Attend
For each attendee, their `must_attend` sessions cannot be in the same time slot.
If the input makes this impossible, return `infeasible`.

---

## Input Validation

Return 400 with descriptive errors for:

- Missing required fields
- Invalid field types or ranges
- Negative capacities or durations
- References to non-existent IDs (speaker in session that doesn't exist)
- Duplicate IDs within a category
- Time slots that overlap
- Sessions with zero speakers
- Duration longer than any available time slot

---

## Infeasibility Detection

Return `status: "infeasible"` with a `reason` when:

- Speaker has more sessions than available time slots
- A session requires amenities no room has
- A session's expected attendance exceeds all room capacities
- Attendee's `must_attend` sessions cannot all be in different time slots
- More sessions than (rooms × time_slots) [pigeonhole]
- Track has more sessions than time slots

The `reason` should be specific and actionable.

---

## Examples

### Minimal Example (Golden Test)

The simplest possible valid input and its exact expected output:

**Request:**
```json
{
  "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
  "sessions": [{"id": "S1", "title": "Talk", "duration_minutes": 60, "speaker_ids": ["SP1"], "expected_attendance": 50}],
  "speakers": [{"id": "SP1", "name": "Alice"}],
  "attendees": [],
  "time_slots": [{"start": "09:00", "duration_minutes": 60}]
}
```

**Response:**
```json
{
  "status": "success",
  "schedule": [{"session_id": "S1", "room_id": "R1", "time_slot": "09:00"}]
}
```

### Example 1: Simple Valid Input

**Request:**
```json
{
  "rooms": [
    {"id": "R1", "name": "Main Hall", "capacity": 200, "amenities": ["projector", "mic"]},
    {"id": "R2", "name": "Room A", "capacity": 50, "amenities": ["projector", "whiteboard"]}
  ],
  "sessions": [
    {"id": "S1", "title": "Opening Keynote", "duration_minutes": 60, "speaker_ids": ["SP1"], "track": null, "required_amenities": ["projector", "mic"], "expected_attendance": 180, "is_keynote": true},
    {"id": "S2", "title": "Intro to Rust", "duration_minutes": 60, "speaker_ids": ["SP2"], "track": "languages", "required_amenities": ["projector"], "expected_attendance": 40, "is_keynote": false},
    {"id": "S3", "title": "Advanced Rust", "duration_minutes": 60, "speaker_ids": ["SP2"], "track": "languages", "required_amenities": ["projector"], "expected_attendance": 30, "is_keynote": false}
  ],
  "speakers": [
    {"id": "SP1", "name": "Alice", "unavailable_slots": []},
    {"id": "SP2", "name": "Bob", "unavailable_slots": ["09:00"]}
  ],
  "attendees": [
    {"id": "A1", "must_attend": ["S1"]}
  ],
  "time_slots": [
    {"start": "09:00", "duration_minutes": 60},
    {"start": "10:00", "duration_minutes": 60},
    {"start": "11:00", "duration_minutes": 60}
  ]
}
```

**Valid Response:**
```json
{
  "status": "success",
  "schedule": [
    {"session_id": "S1", "room_id": "R1", "time_slot": "09:00"},
    {"session_id": "S2", "room_id": "R2", "time_slot": "10:00"},
    {"session_id": "S3", "room_id": "R2", "time_slot": "11:00"}
  ]
}
```

### Example 2: Infeasible Input

**Request:** (Speaker has 3 sessions but only 2 available slots)
```json
{
  "rooms": [{"id": "R1", "name": "Room", "capacity": 100, "amenities": []}],
  "sessions": [
    {"id": "S1", "title": "Talk 1", "duration_minutes": 60, "speaker_ids": ["SP1"], ...},
    {"id": "S2", "title": "Talk 2", "duration_minutes": 60, "speaker_ids": ["SP1"], ...},
    {"id": "S3", "title": "Talk 3", "duration_minutes": 60, "speaker_ids": ["SP1"], ...}
  ],
  "speakers": [
    {"id": "SP1", "name": "Alice", "unavailable_slots": ["11:00"]}
  ],
  "time_slots": [
    {"start": "09:00", "duration_minutes": 60},
    {"start": "10:00", "duration_minutes": 60},
    {"start": "11:00", "duration_minutes": 60}
  ],
  ...
}
```

**Response:**
```json
{
  "status": "infeasible",
  "reason": "Speaker 'Alice' has 3 sessions but only 2 available time slots"
}
```

---

## Implementation Notes

This is a constraint satisfaction problem (CSP). Approaches include:

- Backtracking with constraint propagation
- Local search
- Integer linear programming
- Greedy construction

A good implementation will:

1. Detect infeasibility early (before exhaustive search)
2. Find a valid solution that satisfies all hard constraints

---

## Validation Test Structure

Tests are organized by complexity:

1. **Trivial**: 2-3 sessions, 1-2 rooms, obvious solution
2. **Basic**: 5-10 sessions, 2-3 rooms, some constraints active
3. **Intermediate**: 15-25 sessions, 5-8 rooms, multiple constraint types
4. **Complex**: 40-60 sessions, 10-15 rooms, tight constraints
5. **Stress**: 100+ sessions, edge cases, near-infeasible
6. **Infeasible**: Various unsatisfiable configurations
7. **Validation**: Bad input detection

Each test provides input and validates:
- Hard constraint satisfaction (binary pass/fail)
- Proper infeasibility detection
- Appropriate error messages for bad input
