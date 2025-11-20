from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_partner_invite = State()
    waiting_for_new_admin_id = State()
    waiting_for_new_admin_role = State()
    waiting_for_file = State()
    waiting_for_delete_event = State()

class UserStates(StatesGroup):
    waiting_for_search = State()