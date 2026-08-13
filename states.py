from aiogram.fsm.state import State, StatesGroup


class TicketForm(StatesGroup):
    category    = State()
    enddesk     = State()
    description = State()
    contact_tt  = State()
    photo       = State()
    confirm     = State()


class AdminForm(StatesGroup):
    waiting_user_id    = State()
    waiting_new_secret = State()


class JournalForm(StatesGroup):
    browsing        = State()
    ticket_detail   = State()


class CleanupForm(StatesGroup):
    choose_method   = State()
    waiting_id      = State()
    waiting_date    = State()
    confirm_delete  = State()


class ReOpenForm(StatesGroup):
    waiting_ticket_id = State()
