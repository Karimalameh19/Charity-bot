from botbuilder.core import TurnContext, MessageFactory, MemoryStorage, UserState, ConversationState
from botbuilder.schema import HeroCard, CardAction, ActionTypes, Attachment, SuggestedActions, CardImage
from botbuilder.dialogs import DialogSet, TextPrompt, WaterfallDialog, WaterfallStepContext, DialogTurnResult, PromptOptions, DialogState
from convert import convert_image_to_base64

class EchoBot:
    def __init__(self):
        # Initialize memory storage and state
        self.memory_storage = MemoryStorage()
        self.user_state = UserState(self.memory_storage)
        self.conversation_state = ConversationState(self.memory_storage)
        
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

    async def on_turn(self, turn_context: TurnContext):
        # Create a dialog context
        dialog_context = await self.dialogs.create_context(turn_context)

        if turn_context.activity.type == "conversationUpdate":
            # Handle new user joining
            if turn_context.activity.members_added:
                for member in turn_context.activity.members_added:
                    if member.id != turn_context.activity.service_url:  # Check if the member is not the bot itself
                        conversation_id = turn_context.activity.conversation.id
                        if conversation_id not in self.conversations_initialized:
                            self.conversations_initialized.add(conversation_id)
                            # Send the initial welcome message
                            await self.send_welcome_message(turn_context)

        elif turn_context.activity.type == "message":
            # If a dialog is active, continue the dialog
            if dialog_context.active_dialog:
                await dialog_context.continue_dialog()
            else:
                user_id = turn_context.activity.from_property.id
                user_message = turn_context.activity.text.lower()

                if user_id not in self.welcomed_users:
                    self.welcomed_users.add(user_id)
                    # Send the welcome message if not already sent
                    if turn_context.activity.conversation.id not in self.conversations_initialized:
                        await self.send_welcome_message(turn_context)
                    # Handle the user's response immediately after sending the welcome message
                    await self.handle_user_response(turn_context, user_message, dialog_context)
                else:
                    # Handle user response based on the option selected
                    await self.handle_user_response(turn_context, user_message, dialog_context)

        # Save state changes
        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)

    
    async def handle_user_response(self, turn_context: TurnContext, user_message: str, dialog_context):
        if user_message == "yes":
            await self.send_hero_cards(turn_context)
        elif user_message == "no":
            await turn_context.send_activity("How can I help you?")
        elif user_message == "register_now":
            # Start the registration dialog
            await dialog_context.begin_dialog("waterfall_dialog")
        else:
            # If a dialog is active, continue it
            if dialog_context.active_dialog:
                await dialog_context.continue_dialog()
            else:
                # Handle other messages if no dialog is active
                await turn_context.send_activity("Please choose an option from the suggested actions.")

    async def prompt_for_name(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        # Ask the user for their name
        return await step_context.prompt("text_prompt", PromptOptions(prompt=MessageFactory.text("What is your name?")))

    async def prompt_for_email(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        # Save the name and ask for email
        step_context.values["name"] = step_context.result
        return await step_context.prompt("text_prompt", PromptOptions(prompt=MessageFactory.text("What is your email address?")))

    async def prompt_for_phone(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        # Save the email and ask for phone number
        step_context.values["email"] = step_context.result
        return await step_context.prompt("text_prompt", PromptOptions(prompt=MessageFactory.text("What is your phone number?")))

    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        # Save the phone number and complete the registration
        step_context.values["phone"] = step_context.result
        
        name = step_context.values["name"]
        email = step_context.values["email"]
        phone = step_context.values["phone"]
        
        # Send a confirmation message
        await step_context.context.send_activity(MessageFactory.text(f"Thank you for registering, {name}! We will contact you at {email} or {phone}."))
        return await step_context.end_dialog()

    async def send_welcome_message(self, turn_context: TurnContext):
        # Create a welcome message with suggested actions (buttons)
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
        # Convert local images to base64
        base64_hope_horizon_logo = convert_image_to_base64("./Data/Hope.jpeg")
        base64_bright_futures_logo = convert_image_to_base64("./Data/Bright.jpeg")
        base64_skyward_scholars_logo = convert_image_to_base64("./Data/Skyward.jpeg")

        # Create Hero Cards with "Register Now" buttons
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

        # Create a list of attachments
        attachments = [
            Attachment(content_type="application/vnd.microsoft.card.hero", content=hope_horizon_card),
            Attachment(content_type="application/vnd.microsoft.card.hero", content=bright_futures_card),
            Attachment(content_type="application/vnd.microsoft.card.hero", content=skyward_scholars_card)
        ]

        # Create a message activity with the carousel attachments
        carousel_message = MessageFactory.carousel(attachments)

        # Send the carousel message
        await turn_context.send_activity(carousel_message)
