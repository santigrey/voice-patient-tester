# Bug report

Issues found in the clinic's voice agent across 16 test calls. Each entry says what happened,
why it matters, and where to hear it.

**Where to look.** `calls/NN-.../transcript-NN.txt` at the time given; the same time in
`audio-NN.ogg` (left channel = clinic agent). Calls 03 onward are stamped at the moment each
person started speaking. Calls 01 and 02 predate that and are stamped at the end of each turn
(within about a second).

**How the findings were checked.** The transcripts are our own speech-to-text of the clinic's
audio, so a misheard word could look like a clinic bug. Every quote below that depends on exact
words (the name, the birth date, the phone number) was re-transcribed from the audio with a
second model (Deepgram Nova-3) and matched. Spelling differences in provider names were dropped
as likely transcription noise on our side.

---

### 1. Accepts a date of birth that does not match, then opens the record
**Severity:** High
**Where:** transcript-05.txt at 00:39 and 00:58 · transcript-02.txt at 01:00 · transcript-14.txt at 00:45

**What happened:** The caller gives a date of birth that differs from the one on file. The
agent says "The birth date doesn't match our records, but for demo purposes, I'll accept it,"
then goes on to say what is and is not on the patient's chart. In call 05 it then says "I have
your date of birth as March fourteenth nineteen eighty one", repeating the caller's date back
as if it were the record.

**Why it matters:** Verification that passes on a mismatch is not verification. If this path
exists outside demo mode, anyone who knows a patient's name and phone number can hear details
of that patient's chart. Even as demo behaviour it tells the caller the check is optional.

### 2. Invents a date of birth for the patient without asking
**Severity:** High
**Where:** transcript-01.txt at 01:10

**What happened:** While creating a profile, the agent states "your date of birth is 07/04/2000
for demo purposes" (confirmed in the audio). The caller never gave that date and had to stop
and correct it.

**Why it matters:** The agent wrote a made-up identity detail into a patient record. Wrong
identifiers on a medical record lead to mismatched charts and failed verification later.

### 3. "Transferring you to patient support" ends the call instead
**Severity:** High
**Where:** transcript-01.txt at 03:54 to 03:59 · transcript-05.txt at 01:43 to 01:47 ·
transcript-07.txt at 02:35 to 02:49 · transcript-11.txt at 01:53 to 01:56 ·
transcript-13.txt at 02:38 to 02:42

**What happened:** Whenever the agent cannot finish a task it offers to connect the caller to
the patient support team "so they can help you directly". Five times out of five the transfer
plays a recording ("You've reached the test line. Goodbye.") and the call ends.

**Why it matters:** The caller's unresolved request (a refill, self-pay pricing, a booking) is
dropped with no callback, no message taken and no warning. If the transfer target is only a
placeholder in this test environment, the agent should still not promise a live person.

### 4. Reads the caller's phone number back with a digit missing
**Severity:** Medium
**Where:** transcript-01.txt at 03:27 and 03:43

**What happened:** Asked to confirm the callback number, the agent says "I have your number as
714287776" (nine digits; confirmed in the audio). The caller's number ends 7767. On the second
attempt it reads a different sequence.

**Why it matters:** The callback the agent just promised would go to a wrong or invalid number,
and the caller is asked to confirm a number that is hard to check by ear.

### 5. Says it is checking the schedule, then finds nothing
**Severity:** Medium
**Where:** transcript-01.txt from 01:39 to 02:53

**What happened:** For a morning slot next week, the agent says it will check the schedule
(01:39), says "Let me check the schedule… One moment" (01:54), then "I wasn't able to pull up
available times directly" (02:53) and logs a request instead. In later calls the same kind of
request returned open slots at once (calls 03, 12, 15).

**Why it matters:** The caller waits through two "one moment" pauses and leaves without an
appointment for a request the system can serve, with no explanation of the failure.

### 6. Books a second appointment without noticing the first, and loses the reason
**Severity:** Medium
**Where:** transcript-12.txt at 01:47 · transcript-15.txt at 02:40 · transcript-16.txt at
01:26, 02:55 and 03:35

**What happened:** Call 12 booked Monday 10:00 AM for this patient. In call 15 the agent booked
Monday 9:15 AM without mentioning it. In call 16 it first reports only the 10:00 AM visit,
later finds both, and says "Neither appointment lists specific reasons, so I can't see which
one is for your right knee", although the reason was given when each was booked.

**Why it matters:** Duplicate bookings waste clinic slots and confuse the patient, and a visit
with no recorded reason cannot be routed or prepared for.

### 7. Identity handling changes from call to call
**Severity:** Medium
**Where:** transcript-04.txt at 00:28 · transcript-11.txt at 01:14 and 01:37 ·
transcript-07.txt at 01:13 and 02:12

**What happened:** In most calls the agent recognises the caller from the number on file. In
call 11, with the same caller, name and date of birth, it says "I'm not able to see your phone
number on file for privacy reasons", then "I'm unable to find your record". In call 07 it reads
the number on file aloud, then says it could not verify the caller, while in calls 02, 05 and
14 it accepted a mismatched date.

**Why it matters:** The same caller gets in or is locked out depending on the call, and the
privacy reason given in call 11 contradicts the agent reading the number aloud in call 07.

### 8. Calls the patient by the wrong name
**Severity:** Low
**Where:** transcript-01.txt at 00:28

**What happened:** After the caller said "Hi, my name is James", the agent replied "Hi, Jane"
(confirmed in the audio).

**Why it matters:** Small, but a wrong name at the start of a medical call undermines trust and
hints that the stored name may be wrong too.

---

### Checked and working correctly
- **Weekend request** (call 12): asked for Sunday 10 AM, the agent offered Monday instead.
- **Cancellation** (call 04): cancelled the right appointment and answered the fee question.
- **Office hours and location** (call 06): consistent hours, Saturday closure and parking.
- **Unclear request** (call 14): asked a clarifying question instead of guessing.

### Not a clinic bug
Calls 02, 08 and 09 show the clinic asking "Are you still there?" and hanging up. That was our
bot going silent (see `ITERATION_LOG.md`), not a fault in the clinic agent.
