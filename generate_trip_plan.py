import google.generativeai as genai

class TripPlannerAI:
    def __init__(self, api_key, model_name, instruction):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name, system_instruction=instruction)
        self.chat = self.model.start_chat()

    def send_message(self, user_message):
        bot_response = self.chat.send_message(user_message)
        return bot_response.text
