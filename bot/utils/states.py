from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_partner_invite = State()
    
    waiting_for_new_admin_id = State()
    waiting_for_new_admin_role = State()
    waiting_for_remove_admin = State()
    waiting_for_change_role_id = State()
    waiting_for_change_role_new = State()
    
    waiting_for_notify_day = State()
    waiting_for_notify_time = State()
    
    waiting_for_file = State()
    waiting_for_search_text = State()
    
    waiting_for_event_title = State()
    waiting_for_event_description = State()
    waiting_for_event_location = State()
    waiting_for_event_date = State()
    waiting_for_event_url = State()
    
    waiting_for_edit_event_title = State()
    waiting_for_edit_event_desc = State()
    waiting_for_edit_event_location = State()
    waiting_for_edit_event_date = State()
    waiting_for_edit_event_url = State()
    
    waiting_for_new_user_role = State()
    
    waiting_for_parsing_criteria = State()
    
    waiting_for_source_name = State()
    waiting_for_source_url = State()
    waiting_for_delete_source_id = State()
    
    waiting_for_edit_user_name = State()
    waiting_for_edit_user_email = State()
    waiting_for_edit_user_pos = State()

class UserStates(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_email = State()
    waiting_for_phone = State()
    waiting_for_position = State()
    waiting_for_search_text = State()