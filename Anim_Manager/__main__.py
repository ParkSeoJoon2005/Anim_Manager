import importlib
import re
import json
import requests
from typing import Optional, List
from parsel import Selector
from urllib.request import urlopen

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import Unauthorized, BadRequest, TimedOut, NetworkError, ChatMigrated, TelegramError
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from telegram.ext.dispatcher import run_async, DispatcherHandlerStop
from telegram.utils.helpers import escape_markdown

from Anim_Manager import dispatcher, updater, TOKEN, WEBHOOK, OWNER_ID, CERT_PATH, PORT, URL, LOGGER, \
    ALLOW_EXCL
# needed to dynamically load modules
# NOTE: Module order is not guaranteed, specify that in the config file!
from Anim_Manager.modules import ALL_MODULES
from Anim_Manager import dispatcher
from Anim_Manager.modules.disable import DisableAbleCommandHandler
from Anim_Manager.modules.helper_funcs.chat_status import is_user_admin
from Anim_Manager.modules.helper_funcs.misc import paginate_modules



PM_START_TEXT = """
**𝐇𝐞𝐥𝐥𝐨 {}, 𝐌𝐲 𝐍𝐚𝐦𝐞 𝐢𝐬 {}!** 

𝐈 𝐚𝐦 𝐚𝐧 𝐚𝐝𝐯𝐚𝐧𝐜𝐞𝐝 𝐠𝐫𝐨𝐮𝐩 𝐦𝐚𝐧𝐚𝐠𝐞𝐦𝐞𝐧𝐭 𝐛𝐨𝐭 𝐛𝐲 @𝐬𝐞𝐧𝐮𝐢𝐧𝐟𝐢𝐧𝐢𝐭𝐲.💫
𝐈 𝐜𝐚𝐧 𝐦𝐚𝐧𝐚𝐠𝐞 𝐲𝐨𝐮𝐫 𝐠𝐫𝐨𝐮𝐩 𝐯𝐞𝐫𝐲 𝐞𝐚𝐬𝐢𝐥𝐲 & 𝐬𝐚𝐟𝐞𝐥𝐲. 𝐘𝐨𝐮 𝐜𝐚𝐧 𝐤𝐞𝐞𝐩 𝐭𝐫𝐮𝐬𝐭 𝐨𝐧 𝐦𝐞 𝐰𝐢𝐭𝐡𝐨𝐮𝐭 𝐚𝐧𝐲 𝐝𝐨𝐮𝐛𝐭. 𝐈 𝐚𝐦 𝐥𝐢𝐤𝐞 𝐚 𝐩𝐮𝐛𝐥𝐢𝐜 𝐮𝐬𝐞𝐫𝐛𝐨𝐭.🔥
𝐓𝐫𝐲 𝐮𝐬𝐢𝐧𝐠 𝐦𝐞!⚡️

/𝐡𝐞𝐥𝐩 𝐔𝐬𝐞 𝐅𝐨𝐫 𝐆𝐞𝐭 𝐂𝐨𝐦𝐦𝐚𝐧𝐝

"""

HELP_STRINGS = """

👋𝐇𝐞𝐥𝐥𝐨! 𝐦𝐲 𝐧𝐚𝐦𝐞 *{}*.

𝐓𝐡𝐞 𝐛𝐞𝐬𝐭 𝐠𝐫𝐨𝐮𝐩 𝐦𝐚𝐧𝐚𝐠𝐞𝐫 𝐛𝐨𝐭 𝐭𝐨 𝐦𝐚𝐧𝐚𝐠𝐞 𝐲𝐨𝐮𝐫 𝐠𝐫𝐨𝐮𝐩𝐬.⚙️
𝐓𝐡𝐢𝐬 𝐢𝐬 𝐭𝐡𝐞 𝐡𝐞𝐥𝐩 𝐬𝐞𝐜𝐭𝐢𝐨𝐧 𝐰𝐡𝐞𝐫𝐞 𝐲𝐨𝐮 𝐜𝐚𝐧 𝐥𝐞𝐚𝐫𝐧 𝐭𝐨 𝐮𝐬𝐞 𝐦𝐞. "𝐲𝐚𝐲!🥳"

*𝐌𝐚𝐢𝐧* 𝐜𝐨𝐦𝐦𝐚𝐧𝐝𝐬 𝐚𝐫𝐞 𝐦𝐞𝐧𝐭𝐢𝐨𝐧𝐞𝐝 𝐛𝐞𝐥𝐨𝐰.
👇👇👇👇👇👇👇👇👇👇👇👇

𝐌𝐚𝐢𝐧 𝐜𝐨𝐦𝐦𝐚𝐧𝐝𝐬 𝐚𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞:
 💠 - /𝐬𝐭𝐚𝐫𝐭: 𝐬𝐭𝐚𝐫𝐭 𝐭𝐡𝐞 𝐛𝐨𝐭
 💠 - /𝐡𝐞𝐥𝐩: 𝐏𝐌'𝐬 𝐲𝐨𝐮 𝐭𝐡𝐢𝐬 𝐦𝐞𝐬𝐬𝐚𝐠𝐞.
 💠 - /𝐡𝐞𝐥𝐩 <𝐦𝐨𝐝𝐮𝐥𝐞 𝐧𝐚𝐦𝐞>: 𝐏𝐌'𝐬 𝐲𝐨𝐮 𝐢𝐧𝐟𝐨 𝐚𝐛𝐨𝐮𝐭 𝐭𝐡𝐚𝐭 𝐦𝐨𝐝𝐮𝐥𝐞.
 💠 - /𝐬𝐞𝐭𝐭𝐢𝐧𝐠𝐬:
    🔹- 𝐢𝐧 𝐏𝐌: 𝐰𝐢𝐥𝐥 𝐬𝐞𝐧𝐝 𝐲𝐨𝐮 𝐲𝐨𝐮𝐫 𝐬𝐞𝐭𝐭𝐢𝐧𝐠𝐬 𝐟𝐨𝐫 𝐚𝐥𝐥 𝐬𝐮𝐩𝐩𝐨𝐫𝐭𝐞𝐝 𝐦𝐨𝐝𝐮𝐥𝐞𝐬.
    🔹- 𝐢𝐧 𝐚 𝐠𝐫𝐨𝐮𝐩: 𝐰𝐢𝐥𝐥 𝐫𝐞𝐝𝐢𝐫𝐞𝐜𝐭 𝐲𝐨𝐮 𝐭𝐨 𝐩𝐦, 𝐰𝐢𝐭𝐡 𝐚𝐥𝐥 𝐭𝐡𝐚𝐭 𝐜𝐡𝐚𝐭'𝐬 𝐬𝐞𝐭𝐭𝐢𝐧𝐠𝐬.


𝐀𝐥𝐥 𝐜𝐨𝐦𝐦𝐚𝐧𝐝𝐬 𝐜𝐚𝐧 𝐞𝐢𝐭𝐡𝐞𝐫 𝐛𝐞 𝐮𝐬𝐞𝐝 𝐰𝐢𝐭𝐡 / 𝐨𝐫 !.

𝐀𝐧𝐝 𝐭𝐡𝐞 𝐟𝐨𝐥𝐥𝐨𝐰𝐢𝐧𝐠:
""".format(dispatcher.bot.first_name, "" if not ALLOW_EXCL else "\nAll commands can either be used with / or !.\n")

TECHNO_IMG = "https://telegra.ph/file/6d31bc8d4cb688a44726d.jpg"
IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
DATA_IMPORT = []
DATA_EXPORT = []

CHAT_SETTINGS = {}
USER_SETTINGS = {}

for module_name in ALL_MODULES:
    imported_module = importlib.import_module("Anim_Manager.modules." + module_name)
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if not imported_module.__mod_name__.lower() in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception("Can't have two modules with the same name! Please change one 😅")

    if hasattr(imported_module, "__help__") and imported_module.__help__:
        HELPABLE[imported_module.__mod_name__.lower()] = imported_module

    # Chats to migrate on chat_migrated events
    if hasattr(imported_module, "__migrate__"):
        MIGRATEABLE.append(imported_module)

    if hasattr(imported_module, "__stats__"):
        STATS.append(imported_module)

    if hasattr(imported_module, "__user_info__"):
        USER_INFO.append(imported_module)

    if hasattr(imported_module, "__import_data__"):
        DATA_IMPORT.append(imported_module)

    if hasattr(imported_module, "__export_data__"):
        DATA_EXPORT.append(imported_module)

    if hasattr(imported_module, "__chat_settings__"):
        CHAT_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__user_settings__"):
        USER_SETTINGS[imported_module.__mod_name__.lower()] = imported_module


# do not async
def send_help(chat_id, text, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    dispatcher.bot.send_message(chat_id=chat_id,
                                text=text,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=keyboard)


@run_async
def test(bot: Bot, update: Update):
    # pprint(eval(str(update)))
    # update.effective_message.reply_text("Hola tester! _I_ *have* `markdown`", parse_mode=ParseMode.MARKDOWN)
    update.effective_message.reply_text("This person edited a message 😐")
    print(update.effective_message)

@run_async
def start(bot: Bot, update: Update, args: List[str]):
    if update.effective_chat.type == "private":
        if len(args) >= 1:
            if args[0].lower() == "help":
                send_help(update.effective_chat.id, HELP_STRINGS)
            elif args[0].lower() == "disasters":
                IMPORTED["disasters"].send_disasters(update)
            elif args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", args[0].lower())
                chat = dispatcher.bot.getChat(match.group(1))

                if is_user_admin(chat, update.effective_user.id):
                    send_settings(match.group(1), update.effective_user.id, False)
                else:
                    send_settings(match.group(1), update.effective_user.id, True)

            elif args[0][1:].isdigit() and "rules" in IMPORTED:
                IMPORTED["rules"].send_rules(update, args[0], from_pm=True)

        else:
            first_name = update.effective_user.first_name
            update.effective_message.reply_photo(
                TECHNO_IMG,
                PM_START_TEXT.format(escape_markdown(first_name), escape_markdown(bot.first_name), OWNER_ID),
                parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="❓ Help ❓",
                                                                       callback_data="help_back".format(bot.username)),
                                                                                   InlineKeyboardButton(text="My 𝙽𝚎𝚠𝚜 🙋",
                                                                       url="https://t.me/senuinfinity")],
                                                                                   [InlineKeyboardButton(text="➕ Add To Group ➕",
                                                                       url="t.me/{}?startgroup=true".format(bot.username)),
                                                                                   InlineKeyboardButton(text="𝚂𝚞𝚙𝚙𝚘𝚛𝚝 💬",
                                                                       url="https://t.me/senuinfinitygroup")
                                                                                 ]]))

    else:
        update.effective_message.reply_text("👋𝓱𝓲, 𝓘 𝓪𝓶 𝓷𝓸𝔀 𝓞𝓷𝓵𝓲𝓷𝓮, 𝔂𝓪𝔂!🥳")


def send_start(bot, update):
    #Try to remove old message
    try:
        query = update.callback_query
        query.message.delete()
    except:
        Pass


# for test purposes
def error_callback(bot, update, error):
    try:
        raise error
    except Unauthorized:
        print("no nono1")
        print(error)
        # remove update.message.chat_id from conversation list
    except BadRequest:
        print("no nono2")
        print("BadRequest caught")
        print(error)

        # handle malformed requests - read more below!
    except TimedOut:
        print("no nono3")
        # handle slow connection problems
    except NetworkError:
        print("no nono4")
        # handle other connection problems
    except ChatMigrated as err:
        print("no nono5")
        print(err)
        # the chat_id of a group has changed, use e.new_chat_id instead
    except TelegramError:
        print(error)
        # handle all other telegram related errors


@run_async
def help_button(bot: Bot, update: Update):
    query = update.callback_query
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)
    try:
        if mod_match:
            module = mod_match.group(1)
            text = "Here is the help for the *{}* module:\n".format(HELPABLE[module].__mod_name__) \
                   + HELPABLE[module].__help__
            query.message.reply_text(text=text,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         [[InlineKeyboardButton(text="Back", callback_data="help_back")]]))

        elif prev_match:
            curr_page = int(prev_match.group(1))
            query.message.reply_text(HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(curr_page - 1, HELPABLE, "help")))

        elif next_match:
            next_page = int(next_match.group(1))
            query.message.reply_text(HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(next_page + 1, HELPABLE, "help")))

        elif back_match:
            query.message.reply_text(text=HELP_STRINGS,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help")))

        # ensure no spinny white circle
        bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            LOGGER.exception("Exception in help buttons. %s", str(query.data))


@run_async
def get_help(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    args = update.effective_message.text.split(None, 1)

    # ONLY send help in PM
    if chat.type != chat.PRIVATE:

        update.effective_message.reply_text("👋 Hi,Contact me in Direct Message to get the help 😏.",
                                            reply_markup=InlineKeyboardMarkup(
                                                [[InlineKeyboardButton(text="Help 💬",
                                                                       url="t.me/{}?start=help".format(
                                                                           bot.username))]]))
        return

    elif len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
        module = args[1].lower()
        text = "Here is the available help for the *{}* module:\n".format(HELPABLE[module].__mod_name__) \
               + HELPABLE[module].__help__
        send_help(chat.id, text, InlineKeyboardMarkup([[InlineKeyboardButton(text="BACK", callback_data="help_back")]]))

    else:
        send_help(chat.id, HELP_STRINGS)

def imdb_searchdata(bot: Bot, update: Update):
    query_raw = update.callback_query
    query = query_raw.data.split('$')
    print(query)
    if query[1] != query_raw.from_user.username:
        return
    title = ''
    rating = ''
    date = ''
    synopsis = ''
    url_sel = 'https://www.imdb.com/title/%s/' % (query[0])
    text_sel = requests.get(url_sel).text
    selector_global = Selector(text = text_sel)
    title = selector_global.xpath('//div[@class="title_wrapper"]/h1/text()').get().strip()
    try:
        rating = selector_global.xpath('//div[@class="ratingValue"]/strong/span/text()').get().strip()
    except:
        rating = '-'
    try:
        date = '(' + selector_global.xpath('//div[@class="title_wrapper"]/h1/span/a/text()').getall()[-1].strip() + ')'
    except:
        date = selector_global.xpath('//div[@class="subtext"]/a/text()').getall()[-1].strip()
    try:
        synopsis_list = selector_global.xpath('//div[@class="summary_text"]/text()').getall()
        synopsis = re.sub(' +',' ', re.sub(r'\([^)]*\)', '', ''.join(sentence.strip() for sentence in synopsis_list)))
    except:
        synopsis = '_No synopsis available._'
    movie_data = '*%s*, _%s_\n★ *%s*\n\n%s' % (title, date, rating, synopsis)
    query_raw.edit_message_text(
        movie_data, 
        parse_mode=ParseMode.MARKDOWN
    )

@run_async
def imdb(bot: Bot, update: Update, args):
    message = update.effective_message
    query = ''.join([arg + '_' for arg in args]).lower()
    if not query:
        bot.send_message(
            message.chat.id,
            'You need to specify a movie/show name!'
        )
        return
    url_suggs = 'https://v2.sg.media-imdb.com/suggests/%s/%s.json' % (query[0], query)
    json_url = urlopen(url_suggs)
    suggs_raw = ''
    for line in json_url:
        suggs_raw = line
    skip_chars = 6 + len(query)
    suggs_dict = json.loads(suggs_raw[skip_chars:][:-1])
    if suggs_dict:
        button_list = [[
                InlineKeyboardButton(
                    text = str(sugg['l'] + ' (' + str(sugg['y']) + ')'), 
                    callback_data = str(sugg['id']) + '$' + str(message.from_user.username)
                )] for sugg in suggs_dict['d'] if 'y' in sugg
        ]
        reply_markup = InlineKeyboardMarkup(button_list)
        bot.send_message(
            message.chat.id,
            'Which one? ',
            reply_markup = reply_markup
        )
    else:
        pass


def send_settings(chat_id, user_id, user=False):
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                "*{}*:\n{}".format(mod.__mod_name__, mod.__user_settings__(user_id)) for mod in USER_SETTINGS.values())
            dispatcher.bot.send_message(user_id, "These are your current settings:" + "\n\n" + settings,
                                        parse_mode=ParseMode.MARKDOWN)

        else:
            dispatcher.bot.send_message(user_id, "Seems like there aren't any user specific settings available :'(",
                                        parse_mode=ParseMode.MARKDOWN)

    else:
        if CHAT_SETTINGS:
            chat_name = dispatcher.bot.getChat(chat_id).title
            dispatcher.bot.send_message(user_id,
                                        text="Which module would you like to check {}'s settings for?".format(
                                            chat_name),
                                        reply_markup=InlineKeyboardMarkup(
                                            paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)))
        else:
            dispatcher.bot.send_message(user_id, "Seems like there aren't any chat settings available :'(\nSend this "
                                                 "in a group chat you're admin in to find its current settings!",
                                        parse_mode=ParseMode.MARKDOWN)


@run_async
def settings_button(bot: Bot, update: Update):
    query = update.callback_query
    user = update.effective_user
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = bot.get_chat(chat_id)
            text = "*{}* has the following settings for the *{}* module:\n\n".format(escape_markdown(chat.title),
                                                                                     CHAT_SETTINGS[module].__mod_name__) + \
                   CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)
            query.message.reply_text(text=text,
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(
                                         [[InlineKeyboardButton(text="Back",
                                                                callback_data="stngs_back({})".format(chat_id))]]))

        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text("Hi there! There are quite a few settings for {} - go ahead and pick what "
                                     "you're interested in.".format(chat.title),
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(curr_page - 1, CHAT_SETTINGS, "stngs",
                                                          chat=chat_id)))

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text("Hi there! There are quite a few settings for {} - go ahead and pick what "
                                     "you're interested in.".format(chat.title),
                                     reply_markup=InlineKeyboardMarkup(
                                         paginate_modules(next_page + 1, CHAT_SETTINGS, "stngs",
                                                          chat=chat_id)))

        elif back_match:
            chat_id = back_match.group(1)
            chat = bot.get_chat(chat_id)
            query.message.reply_text(text="Hi there! There are quite a few settings for {} - go ahead and pick what "
                                          "you're interested in.".format(escape_markdown(chat.title)),
                                     parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=InlineKeyboardMarkup(paginate_modules(0, CHAT_SETTINGS, "stngs",
                                                                                        chat=chat_id)))

        # ensure no spinny white circle
        bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            LOGGER.exception("Exception in settings buttons. %s", str(query.data))


@run_async
def get_settings(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = msg.text.split(None, 1)

    # ONLY send settings in PM
    if chat.type != chat.PRIVATE:
        if is_user_admin(chat, user.id):
            text = "Click here to get this chat's settings, as well as yours."
            msg.reply_text(text,
                           reply_markup=InlineKeyboardMarkup(
                               [[InlineKeyboardButton(text="Settings",
                                                      url="t.me/{}?start=stngs_{}".format(
                                                          bot.username, chat.id))]]))
        else:
            text = "Click here to check your settings 😁."

    else:
        send_settings(chat.id, user.id, True)



def migrate_chats(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    if msg.migrate_to_chat_id:
        old_chat = update.effective_chat.id
        new_chat = msg.migrate_to_chat_id
    elif msg.migrate_from_chat_id:
        old_chat = msg.migrate_from_chat_id
        new_chat = update.effective_chat.id
    else:
        return

    LOGGER.info("Migrating from %s, to %s", str(old_chat), str(new_chat))
    for mod in MIGRATEABLE:
        mod.__migrate__(old_chat, new_chat)

    LOGGER.info("Successfully migrated!")
    raise DispatcherHandlerStop


def main():
    test_handler = CommandHandler("test", test)
    start_handler = CommandHandler("start", start, pass_args=True)

    start_callback_handler = CallbackQueryHandler(send_start, pattern=r"bot_start")
    

    help_handler = CommandHandler("help", get_help)
    help_callback_handler = CallbackQueryHandler(help_button, pattern=r"help_")
    
    IMDB_HANDLER = CommandHandler("imdb", imdb, pass_args=True)
    IMDB_SEARCHDATA_HANDLER = CallbackQueryHandler(imdb_searchdata)
    settings_handler = CommandHandler("settings", get_settings)
    settings_callback_handler = CallbackQueryHandler(settings_button, pattern=r"stngs_")

   
    migrate_handler = MessageHandler(Filters.status_update.migrate, migrate_chats)

    # dispatcher.add_handler(test_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(settings_handler)
    dispatcher.add_handler(help_callback_handler)
    dispatcher.add_handler(settings_callback_handler)
    dispatcher.add_handler(migrate_handler)
    dispatcher.add_handler(start_callback_handler)
    dispatcher.add_handler(IMDB_HANDLER)
    dispatcher.add_handler(IMDB_SEARCHDATA_HANDLER)
    # dispatcher.add_error_handler(error_callback)

    if WEBHOOK:
        LOGGER.info("Using webhooks.")
        updater.start_webhook(listen="127.0.0.1",
                              port=PORT,
                              url_path=TOKEN)

        if CERT_PATH:
            updater.bot.set_webhook(url=URL + TOKEN,
                                    certificate=open(CERT_PATH, 'rb'))
        else:
            updater.bot.set_webhook(url=URL + TOKEN)

    else:
        LOGGER.info("Using long polling.")
        updater.start_polling(timeout=15, read_latency=4)

    updater.idle()


if __name__ == '__main__':
    LOGGER.info("Successfully loaded modules: " + str(ALL_MODULES))
    main()
