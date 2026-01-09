# Signals disabled - notifications are handled in booking/signals.py
# to prevent duplicate notifications

# The booking.signals module now handles:
# - NEW booking: notifies all available mechanics
# - Status changes: notifies customer
# - Cancellation: notifies mechanic

# WorkQueue-based notifications have been moved to:
# - accept_work_view in views_web.py (notifies other mechanics when job is taken)
