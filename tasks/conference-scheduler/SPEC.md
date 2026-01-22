# Conference Scheduler Specification

Build a REST API that generates optimal schedules for a tech conference. Given rooms, sessions, speakers, and attendees with various constraints, produce a valid schedule that maximizes attendee satisfaction.

## Overview

The scheduler receives conference data via POST and returns a schedule assigning each session to a room and time slot. The solution must satisfy all **hard constraints** (or be rejected) and is scored on how well it satisfies **soft constraints**.

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
  "time_slots": [...],
  "config": {...}
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
  ],
  "score": 850,
  "score_breakdown": {
    "attendee_satisfaction": 500,
    "speaker_convenience": 200,
    "room_utilization": 150
  }
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
  "amenities": ["array of strings"]
}
```

**Amenities** are arbitrary strings like: `"projector"`, `"whiteboard"`, `"video_recording"`, `"wheelchair_accessible"`, `"natural_light"`.

### Session
```json
{
  "id": "string",
  "title": "string",
  "duration_minutes": "integer (15-480, must align with slot boundaries)",
  "speaker_ids": ["array of speaker IDs (1 or more)"],
  "track": "string or null",
  "required_amenities": ["array of strings"],
  "expected_attendance": "integer (0-10000)",
  "is_keynote": "boolean (default false)"
}
```

### Speaker
```json
{
  "id": "string",
  "name": "string",
  "unavailable_slots": ["array of time slot strings"],
  "preferred_slots": ["array of time slot strings"]
}
```

### Attendee
```json
{
  "id": "string",
  "must_attend": ["array of session IDs (non-negotiable)"],
  "wants_to_attend": ["array of session IDs (preferences, ranked by position)"]
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

### Config
```json
{
  "max_compute_seconds": "integer (default 30)",
  "optimization_level": "string: 'fast' | 'balanced' | 'thorough'"
}
```

---

## Hard Constraints (Must Satisfy)

Violation of ANY hard constraint makes the schedule invalid.

### HC1: No Speaker Conflicts
A speaker cannot be scheduled in overlapping sessions.

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
Sessions in the same track cannot overlap in time.
(Allows attendees to attend all sessions in a track)

### HC9: Keynote Exclusivity
When a keynote is scheduled, no other sessions run in that time slot.
(All attendees should be able to attend keynotes)

### HC10: Attendee Must-Attend
For each attendee, their `must_attend` sessions cannot overlap in time.
If the input has an attendee with conflicting `must_attend` sessions, return `infeasible`.

---

## Soft Constraints (Optimization Scoring)

The schedule is scored on how well it satisfies soft constraints. Higher is better.

### SC1: Attendee Satisfaction (0-1000 points)

For each attendee, calculate how many of their `wants_to_attend` sessions they can actually attend (no overlaps).

```
satisfaction = Σ (attendable_sessions / wanted_sessions) * weight
```

Sessions earlier in `wants_to_attend` list are worth more (position-weighted).

### SC2: Speaker Convenience (0-500 points)

Speakers prefer:
- Sessions in their `preferred_slots` (+20 points each)
- Back-to-back sessions (minimize gaps) (+30 points for each adjacent pair)
- Not having sessions at day boundaries (first/last slot) (+10 points)

### SC3: Room Utilization (0-300 points)

Prefer room sizes close to expected attendance (reduce waste):
```
utilization_score = 1 - (room.capacity - expected_attendance) / room.capacity
```

Penalize putting 20 people in a 500-seat room.

### SC4: Track Cohesion (0-200 points)

Sessions in the same track should ideally:
- Be in the same room (+25 points per track with single room)
- Be scheduled consecutively (+15 points for each consecutive pair)

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
- Attendee's `must_attend` sessions inherently conflict
- More sessions than (rooms × time_slots) [pigeonhole]
- Track has more sessions than time slots

The `reason` should be specific and actionable.

---

## Examples

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
    {"id": "SP1", "name": "Alice", "unavailable_slots": [], "preferred_slots": ["09:00"]},
    {"id": "SP2", "name": "Bob", "unavailable_slots": ["09:00"], "preferred_slots": ["10:00", "11:00"]}
  ],
  "attendees": [
    {"id": "A1", "must_attend": ["S1"], "wants_to_attend": ["S2", "S3"]}
  ],
  "time_slots": [
    {"start": "09:00", "duration_minutes": 60},
    {"start": "10:00", "duration_minutes": 60},
    {"start": "11:00", "duration_minutes": 60}
  ],
  "config": {"max_compute_seconds": 10, "optimization_level": "balanced"}
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
  ],
  "score": 425,
  "score_breakdown": {
    "attendee_satisfaction": 200,
    "speaker_convenience": 150,
    "room_utilization": 75
  }
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
    {"id": "SP1", "name": "Alice", "unavailable_slots": ["11:00"], "preferred_slots": []}
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

## Performance Requirements

- **Small inputs** (≤10 sessions, ≤5 rooms): respond within 5 seconds
- **Medium inputs** (≤50 sessions, ≤15 rooms): respond within 30 seconds
- **Large inputs** (≤200 sessions, ≤30 rooms): respond within `config.max_compute_seconds`

The API should return the best schedule found within the time limit, not necessarily the global optimum.

---

## Implementation Notes

This is a constraint satisfaction + optimization problem (CSP/COP). Approaches include:

- Backtracking with constraint propagation
- Local search (simulated annealing, tabu search)
- Integer linear programming
- Genetic algorithms
- Greedy construction + improvement

The choice of algorithm affects both solution quality and runtime. A good implementation will:

1. Detect infeasibility early (before exhaustive search)
2. Find a valid solution quickly (satisfy hard constraints)
3. Iteratively improve the solution (optimize soft constraints)
4. Respect the time budget and return best-so-far

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
- Soft constraint scoring (compared against baseline threshold)
- Proper infeasibility detection
- Appropriate error messages for bad input
