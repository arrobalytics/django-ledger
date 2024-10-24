"""
Django Ledger created by Miguel Sanda <msanda@arrobalytics.com>.
Copyright© EDMA Group Inc licensed under the GPLv3 Agreement.

The signals module provide the means to notify listeners about important events or states in the models,
such as a ledger model being posted or a bill status changing.
"""

from django.dispatch import Signal

# Ledger Model Signals...
ledger_posted = Signal()
ledger_unposted = Signal()
ledger_locked = Signal()
ledger_unlocked = Signal()
ledger_hidden = Signal()
ledger_unhidden = Signal()

# Journal Entry Model Signals...
journal_entry_posted = Signal()
journal_entry_unposted = Signal()
journal_entry_locked = Signal()
journal_entry_unlocked = Signal()

# Bill Model Signals...
bill_status_draft = Signal()
bill_status_in_review = Signal()
bill_status_approved = Signal()
bill_status_paid = Signal()
bill_status_canceled = Signal()
bill_status_void = Signal()

# Invoice Model Signals...
invoice_status_draft = Signal()
invoice_status_in_review = Signal()
invoice_status_approved = Signal()
invoice_status_paid = Signal()
invoice_status_canceled = Signal()
invoice_status_void = Signal()

# PO Model Signals...
po_status_draft = Signal()
po_status_in_review = Signal()
po_status_approved = Signal()
po_status_fulfilled = Signal()
po_status_canceled = Signal()
po_status_void = Signal()

# Estimate Model Signals...
estimate_status_draft = Signal()
estimate_status_in_review = Signal()
estimate_status_approved = Signal()
estimate_status_completed = Signal()
estimate_status_canceled = Signal()
estimate_status_void = Signal()
