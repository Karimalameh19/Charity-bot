from botbuilder.core import TurnContext, MessageFactory
from botbuilder.schema import HeroCard, CardAction, ActionTypes, Attachment, SuggestedActions, CardImage
from convert import convert_image_to_base64

class EchoBot:
    def __init__(self):
        self.welcomed_users = set()  # Track welcomed users to avoid multiple welcome messages

    async def on_turn(self, turn_context: TurnContext):
        # Check if the incoming activity is a message
        if turn_context.activity.type == "message":
            user_id = turn_context.activity.from_property.id

            # If the user hasn't been welcomed, send a welcome message with options
            if user_id not in self.welcomed_users:
                self.welcomed_users.add(user_id)
                await self.send_welcome_message_with_options(turn_context)
            else:
                user_message = turn_context.activity.text.lower()

                # Handle user response based on the option selected
                if user_message == "yes":
                    await self.send_hero_cards(turn_context)
                elif user_message == "no":
                    await turn_context.send_activity("How can I help you?")
                else:
                    await turn_context.send_activity(f"You said: {turn_context.activity.text}")

    async def send_welcome_message_with_options(self, turn_context: TurnContext):
        # Create a welcome message with suggested actions (buttons)
        welcome_message = MessageFactory.text("Welcome to our Charity Bot! Are you interested in learning about upcoming charity events?")
        welcome_message.suggested_actions = SuggestedActions(
            actions=[
                CardAction(
                    title="Yes",
                    type=ActionTypes.im_back,
                    value="Yes"
                ),
                CardAction(
                    title="No",
                    type=ActionTypes.im_back,
                    value="No"
                )
            ]
        )
        await turn_context.send_activity(welcome_message)

    async def send_hero_cards(self, turn_context: TurnContext):
        # Convert local images to base64 (check if this method works as expected)
        base64_hope_horizon_logo = convert_image_to_base64("./Data/Hope.jpeg")
        base64_bright_futures_logo = convert_image_to_base64("./Data/Bright.jpeg")
        base64_skyward_scholars_logo = convert_image_to_base64("./Data/Skyward.jpeg")

        # Check if base64 images are correctly converted
        print(base64_hope_horizon_logo)  # For debugging purposes
        print(base64_bright_futures_logo)
        print(base64_skyward_scholars_logo)

        # Create Hero Cards
        hope_horizon_card = HeroCard(
            title="Hope Horizon Foundation",
            subtitle="Transforming lives through storytelling and creative arts",
            text="Programs include Story Seeds Initiative, Art for All, Imagination Station, and Dreamscapes Grants.",
            images=[CardImage(url=base64_hope_horizon_logo)],
            buttons=[CardAction(type=ActionTypes.open_url, title="Learn More", value="http://www.hopehorizonfoundation.org")]
        )

        bright_futures_card = HeroCard(
            title="Bright Futures Farmstead Initiative",
            subtitle="Nurturing communities through sustainable agriculture",
            text="Programs include Harvest Education Workshops, Farm-to-Table Outreach, Green Spaces Initiative, and Wellness Retreats.",
            images=[CardImage(url=base64_bright_futures_logo)],
            buttons=[CardAction(type=ActionTypes.open_url, title="Learn More", value="http://www.brightfuturesfarmstead.org")]
        )

        skyward_scholars_card = HeroCard(
            title="Skyward Scholars Network",
            subtitle="Expanding educational opportunities and fostering leadership",
            text="Programs include Mentorship Match, Scholarship Fund, Leadership Labs, and College Prep Bootcamps.",
            images=[CardImage(url=base64_skyward_scholars_logo)],
            buttons=[CardAction(type=ActionTypes.open_url, title="Learn More", value="http://www.skywardscholars.org")]
        )

        # Create a list of Hero Card attachments
        hero_cards = [
            Attachment(content_type="application/vnd.microsoft.card.hero", content=hope_horizon_card),
            Attachment(content_type="application/vnd.microsoft.card.hero", content=bright_futures_card),
            Attachment(content_type="application/vnd.microsoft.card.hero", content=skyward_scholars_card)
        ]

        # Send Hero Cards as a carousel
        await turn_context.send_activity(MessageFactory.attachment(hero_cards))
