from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_partner_invite = State()
    waiting_for_new_admin_id = State()
    waiting_for_new_admin_role = State()
    waiting_for_file = State()
    waiting_for_delete_event = State()

class UserStates(StatesGroup):
    waiting_for_search = State()
    waiting_for_search_text = State()
    waiting_for_full_name = State()
    waiting_for_email = State()
    waiting_for_phone = State()
    waiting_for_edit_field = State()
    waiting_for_edit_value = State()
    waiting_for_criteria = State()