import os
from botbuilder.core import TurnContext, MessageFactory, MemoryStorage, UserState, ConversationState
from botbuilder.schema import HeroCard, CardAction, ActionTypes, Attachment, SuggestedActions, CardImage
from botbuilder.dialogs import DialogSet, TextPrompt, WaterfallDialog, WaterfallStepContext, DialogTurnResult, PromptOptions
from convert import convert_image_to_base64
import openai
import aiohttp
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
import logging
class EchoBot:
    def __init__(self, openai_api_key, openai_endpoint, openai_deployment, api_version):
        # Initialize memory storage and state
        self.memory_storage = MemoryStorage()
        self.user_state = UserState(self.memory_storage)
        self.conversation_state = ConversationState(self.memory_storage)
        self.openai_api_key=openai_api_key
        self.openai_endpoint= openai_endpoint
        self.api_version=api_version
        # Set up Azure OpenAI client
        openai.api_key = openai_api_key
        openai.api_base = openai_endpoint
        openai.api_version = api_version
        self.api_key = openai_api_key
        self.deployment = openai_deployment
        self.openai_deployment = openai_deployment
        self.client = AzureOpenAI(
            azure_endpoint=openai_endpoint,
            api_key= openai_api_key,
            api_version=api_version
        )
        self.api_key = openai_api_key
        self.deployment = openai_deployment
        # Create dialog state and set up DialogSet
        self.dialog_state = self.conversation_state.create_property("DialogState")
        self.dialogs = DialogSet(self.dialog_state)
        
        # Add dialogs to the DialogSet
        self.dialogs.add(TextPrompt("text_prompt"))
        self.dialogs.add(WaterfallDialog("waterfall_dialog", [
            self.prompt_for_name,
            self.prompt_for_email,
            self.prompt_for_phone,
            self.final_step
        ]))
        
        # Track welcomed users and initialized conversations
        self.welcomed_users = set()
        self.conversations_initialized = set()
        
        # Load text content from files
        self.text_content = self.load_text_files('./Data')

    def load_text_files(self, folder_path):
        text_data = ""
        for filename in os.listdir(folder_path):
            if filename.endswith(".txt"):
                file_path = os.path.join(folder_path, filename)
                with open(file_path, 'r', encoding='utf-8') as file:
                    text_data += file.read() + "\n"
        return text_data

    async def on_turn(self, turn_context: TurnContext):
        # Create a dialog context
        dialog_context = await self.dialogs.create_context(turn_context)

        if turn_context.activity.type == "conversationUpdate":
            if turn_context.activity.members_added:
                for member in turn_context.activity.members_added:
                    if member.id != turn_context.activity.service_url:
                        conversation_id = turn_context.activity.conversation.id
                        if conversation_id not in self.conversations_initialized:
                            self.conversations_initialized.add(conversation_id)
                            await self.send_welcome_message(turn_context)

        elif turn_context.activity.type == "message":
            if dialog_context.active_dialog:
                await dialog_context.continue_dialog()
            else:
                user_id = turn_context.activity.from_property.id
                user_message = turn_context.activity.text.lower()

                if user_id not in self.welcomed_users:
                    self.welcomed_users.add(user_id)
                    if turn_context.activity.conversation.id not in self.conversations_initialized:
                        await self.send_welcome_message(turn_context)
                    await self.handle_user_response(turn_context, user_message, dialog_context)
                else:
                    await self.handle_user_response(turn_context, user_message, dialog_context)

        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)

    async def handle_user_response(self, turn_context: TurnContext, user_message: str, dialog_context):
        if user_message == "yes":
            await self.send_hero_cards(turn_context)
        elif user_message == "no":
            await turn_context.send_activity("How can I help you?")
        elif user_message == "register_now":
            await dialog_context.begin_dialog("waterfall_dialog")
        else:
            if dialog_context.active_dialog:
                await dialog_context.continue_dialog()
            else:
                # Call Azure OpenAI GPT-4 with file content as context
                response = self.call_openai_gpt4(user_message)
                if response == "Answer not found":
                    await turn_context.send_activity(
                        "Answer not found. Please provide your information so we can have someone reach out for further inquiries."
                    )
                    await dialog_context.begin_dialog("waterfall_dialog")
                else:
                    await turn_context.send_activity(response)



    def call_openai_gpt4(self, user_message: str) -> str:
        try:
            # Combine the text content from files with the user's message
            combined_context = self.text_content + "\n\nUser Message: " + user_message
            
            # Create a chat completion request
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that is anwering questions based off of text given if info not available return not found in the response"},
                    {"role": "user", "content": combined_context}
                ],
                max_tokens=900,  # Adjust as needed
                temperature=0.7
            )
            
            logging.info(f"Response JSON: {response}")

            # Check if the response indicates that the answer was not found
            reply = response.choices[0].message.content.strip()
            if "not found" in reply.lower():
                return "Answer not found"
            return reply

        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return "An unexpected error occurred while calling the Azure OpenAI service."

    async def prompt_for_name(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        return await step_context.prompt("text_prompt", PromptOptions(prompt=MessageFactory.text("What is your name?")))

    async def prompt_for_email(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        step_context.values["name"] = step_context.result
        return await step_context.prompt("text_prompt", PromptOptions(prompt=MessageFactory.text("What is your email address?")))

    async def prompt_for_phone(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        step_context.values["email"] = step_context.result
        return await step_context.prompt("text_prompt", PromptOptions(prompt=MessageFactory.text("What is your phone number?")))

    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        step_context.values["phone"] = step_context.result
        name = step_context.values["name"]
        email = step_context.values["email"]
        phone = step_context.values["phone"]
        await step_context.context.send_activity(MessageFactory.text(f"Thank you for registering, {name}! We will contact you at {email} or {phone}."))
        return await step_context.end_dialog()

    async def send_welcome_message(self, turn_context: TurnContext):
        welcome_message = MessageFactory.text("Welcome to our Charity Bot! Are you interested in learning about upcoming charity events?")
        welcome_message.suggested_actions = SuggestedActions(
            actions=[
                CardAction(
                    title="Yes",
                    type=ActionTypes.im_back,
                    value="yes"
                ),
                CardAction(
                    title="No",
                    type=ActionTypes.im_back,
                    value="no"
                )
            ]
        )
        await turn_context.send_activity(welcome_message)

    async def send_hero_cards(self, turn_context: TurnContext):
        base64_hope_horizon_logo = convert_image_to_base64("./Data/Hope.jpeg")
        base64_bright_futures_logo = convert_image_to_base64("./Data/Bright.jpeg")
        base64_skyward_scholars_logo = convert_image_to_base64("./Data/Skyward.jpeg")

        hope_horizon_card = HeroCard(
            title="Hope Horizon Foundation",
            subtitle="Transforming lives through storytelling and creative arts",
            text="Programs include Story Seeds Initiative, Art for All, Imagination Station, and Dreamscapes Grants.",
            images=[CardImage(url=base64_hope_horizon_logo)],
            buttons=[
                CardAction(type=ActionTypes.open_url, title="Learn More", value="http://www.hopehorizonfoundation.org"),
                CardAction(type=ActionTypes.im_back, title="Register Now", value="register_now")
            ]
        )

        bright_futures_card = HeroCard(
            title="Bright Futures Farmstead Initiative",
            subtitle="Nurturing communities through sustainable agriculture",
            text="Programs include Harvest Education Workshops, Farm-to-Table Outreach, Green Spaces Initiative, and Wellness Retreats.",
            images=[CardImage(url=base64_bright_futures_logo)],
            buttons=[
                CardAction(type=ActionTypes.open_url, title="Learn More", value="http://www.brightfuturesfarmstead.org"),
                CardAction(type=ActionTypes.im_back, title="Register Now", value="register_now")
            ]
        )

        skyward_scholars_card = HeroCard(
            title="Skyward Scholars Network",
            subtitle="Expanding educational opportunities and fostering leadership",
            text="Programs include Mentorship Match, Scholarship Fund, Leadership Labs, and College Prep Bootcamps.",
            images=[CardImage(url=base64_skyward_scholars_logo)],
            buttons=[
                CardAction(type=ActionTypes.open_url, title="Learn More", value="http://www.skywardscholars.org"),
                CardAction(type=ActionTypes.im_back, title="Register Now", value="register_now")
            ]
        )

        attachments = [
            Attachment(content_type="application/vnd.microsoft.card.hero", content=hope_horizon_card),
            Attachment(content_type="application/vnd.microsoft.card.hero", content=bright_futures_card),
            Attachment(content_type="application/vnd.microsoft.card.hero", content=skyward_scholars_card)
        ]

        carousel_message = MessageFactory.carousel(attachments)
        await turn_context.send_activity(carousel_message)