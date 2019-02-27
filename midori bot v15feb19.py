# -*- coding: utf-8 -*-
"""
Created on Mon Oct 15 21:06:06 2018

@author: andre
"""
###############################################################################
"""
INSTALLATION & SET-UP
Packages used:
    Telegram API ($ pip install python-telegram-bot)
    Firebase ($pip install python-firebase) **note that for now library only works w python 3.6
"""
###############################################################################


from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, Filters
import datetime as dt

AuthKey = '638918174:AAGkR-wBtzVHCiOrDGmtgAsyaHluE7IicDU'                     #real bot Auth Token
#AuthKey = '762472983:AAG47FPX7S84RYAXlXBg3U5NQ01JtsFZcNo'                      #demo bot Auth Token 
from firebase.firebase import FirebaseApplication, FirebaseAuthentication
url = 'https://smufoodchamps.firebaseio.com/'
token = 'CgosBev5DkwojmcMhBh8eIEmMXMoKwzz8T95drKa'                             #Firebase Auth Token
email = 'smugrowmidori@gmail.com'
fb_auth = FirebaseAuthentication(token, email)
fb=FirebaseApplication(url,fb_auth)

# Enable logging
import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

#defining state numbers
FINDING, RPT_BLDG, RPT_AREA, RPT_TYPE, RPT_EXP, RPT_CLR = range(6)

#error logging
def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)
    
#/cancel command
def cancel(bot, update, user_data):
    user_data.clear()
    update.message.reply_text('CANCELLED! Use commands /find or /report to start over.', parse_mode=ParseMode.HTML)
    return ConversationHandler.END

def _check_repeats(bldg, exact_loc):
    active = fb.get('/', bldg)
    valid = True
    if active != None:
        for id_ in active:
            check = active[id_][0] != exact_loc
            valid = valid and check
    return valid

#automated function to clear food when expired/cleared
def _archive(bldg):
    now = dt.datetime.now()
    active = fb.get('/', bldg)
    if active != None:
        for id_ in active:
            exp = str(max(int(active[id_][1]),int(active[id_][2])))
            food = dt.datetime(now.year,now.month,now.day, int(exp[:2]), int(exp[2:]))
            if now-food > dt.timedelta(minutes=5):
                fb.put('/expired/' + bldg, id_, active[id_])
                fb.delete('/' + bldg, id_)

#admin command to force clear all active foods.                
def archive(bot, update, args):
    if len(args) != 1:                     # Feedback if wrong number of arguments
        update.message.reply_text('Sorry, admin access only.')
    elif args[0] != 'smufoodchamps':
        update.message.reply_text("Wrong password!")
    else:
        for bldg in ['LKCSB', 'SOE', 'SIS', 'Admin Bldg']:
            active = fb.get('/', bldg)
            if active != None:
                for id_ in active:
                    fb.put('/expired/' + bldg, id_, active[id_])
                    fb.delete('/' + bldg, id_)
    update.message.reply_text("Successfully archvied all active buffets.")
                  
#/start command when new_users use the bot
def on_start(bot, update):
    update.message.reply_text("Hello!👋🏼 What would you like to do today?"
                              + "\n🍽 To see free food available, please use /find."
                              + "\n📣 To post food to be cleared, please use /report."
                              + "\n\n [This bot is exclusively for the use of SMU students and staff only.]")

#/find command which returns InlineKeyboard with Building options
def find(bot, update):
    keyboard = [[InlineKeyboardButton("All", callback_data=5)],
               [InlineKeyboardButton("LKCSB", callback_data=1), 
               InlineKeyboardButton("SOE", callback_data=2)],
               [InlineKeyboardButton("SIS", callback_data=3),
               InlineKeyboardButton("Admin Bldg", callback_data=4)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please be aware that freshness of food varies, so do exercise your own discretion! 👍')
    update.message.reply_text('Where would you like to find food? 🥧🍜🍱 Please choose:', reply_markup=reply_markup)
    return FINDING
    
#_format_find callbacks for /find command
def _format_find(bot, update, user_data):
    query = update.callback_query
    bot.edit_message_text(text='Searching database.....', chat_id=query.message.chat_id, message_id=query.message.message_id)
    loc_tag = {1:'LKCSB',
            2:'SOE',
            3:'SIS',
            4:'Admin Bldg'}
    string = ''
    if int(query.data) == 5:
        active = {}
        for i in loc_tag:
            _archive(loc_tag[i])
            bldg_dict = fb.get('/', loc_tag[i])
            if bldg_dict == None:
                string += 'No food found at {0}. 😢\n\n'.format(loc_tag[i])
            else:
                active[loc_tag[i]] = bldg_dict
        for bldg in active:
            string += '\n 🍚🍜 FOOD FOUND AT:\n\n'
            for buffet in active[bldg]:
                info = active[bldg][buffet]
                string += '<b>{0}</b> \n[Dietary Req: {3}; Expires:{1}h; Cleared: {2}h]\n'.format(info[0], info[1], info[2], info[3])
    else:
        _archive(loc_tag[int(query.data)])
        bldg_dict = fb.get('/', loc_tag[int(query.data)])
        if bldg_dict == None:
                string += 'No food found at {0}. 😢\n\n'.format(loc_tag[int(query.data)])
        else:
            string += '\n🍚🍜 FOOD FOUND AT:\n\n'
            for buffet in bldg_dict:
                info = bldg_dict[buffet]
                string += '<b>{0}</b> \n[Dietary Req: {3}; Expires:{1}h; Cleared: {2}h]\n'.format(info[0], info[1], info[2], info[3])
    bot.edit_message_text(text=string, chat_id=query.message.chat_id, message_id=query.message.message_id, parse_mode=ParseMode.HTML)
    return ConversationHandler.END

#/report command which returns InlineKeyboard with building options
def report_main(bot, update):               #to activate password protection command, must add "args" to argumnets
    #if len(args) != 1:                     # Feedback if wrong number of arguments
    #    update.message.reply_text('To report food, please key in Admin password one space after command;'
    #                          +'\n i.e. /report <password>')
    
    #if args[0] != 'smufoodchamps':
    #    update.message.reply_text("Wrong password! Please get the correct password from the organiser to proceed.")
        
    #else:  (rmbr to indent below segment)  
    update.message.reply_text(text="Hi there!😊 Please ensure you have obtained <b>permission from event organisers</b> before reporting.\nThank you for doing your part to save food!", parse_mode=ParseMode.HTML)

    keyboard = [[InlineKeyboardButton("LKCSB", callback_data=6), 
               InlineKeyboardButton("SOE", callback_data=7)],
               [InlineKeyboardButton("SIS", callback_data=8),
               InlineKeyboardButton("Admin Bldg", callback_data=9)]]

    update.message.reply_text('Where is the food? 👀')

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose:', reply_markup=reply_markup)
    return RPT_BLDG
        
#CallbackQuery function for /report function & ConversationHandler states
def _log_bldg(bot, update, user_data):
    user_data.clear()
    query = update.callback_query
    num = int(query.data)
    
    loc_tag = {1:'LKCSB',
                2:'SOE',
                3:'SIS',
                4:'Admin Bldg'}
    user_data['bldg'] = loc_tag[num - 5]
    kb_lkcsb = [[InlineKeyboardButton("1A", callback_data=11),
               InlineKeyboardButton("1B", callback_data=12)], 
               [InlineKeyboardButton("2A", callback_data=21), 
               InlineKeyboardButton("2B", callback_data=22),
               InlineKeyboardButton("2C", callback_data=23),
               InlineKeyboardButton("2D", callback_data=24)],
               [InlineKeyboardButton("3A", callback_data=31), 
               InlineKeyboardButton("3B", callback_data=32),
               InlineKeyboardButton("3C", callback_data=33),
               InlineKeyboardButton("3D", callback_data=34)],
               [InlineKeyboardButton("CANCEL", callback_data=0)]]
    kb_soe = [[InlineKeyboardButton("B1A", callback_data=19),
               InlineKeyboardButton("B1B", callback_data=18), 
               InlineKeyboardButton("B1C", callback_data=17)], 
               [InlineKeyboardButton("2A", callback_data=21),
               InlineKeyboardButton("2B", callback_data=22), 
               InlineKeyboardButton("2C", callback_data=23),
               InlineKeyboardButton("2D", callback_data=24),
               InlineKeyboardButton("2E", callback_data=25)],
               [InlineKeyboardButton("3A", callback_data=31),
               InlineKeyboardButton("3B", callback_data=32), 
               InlineKeyboardButton("3C", callback_data=33),
               InlineKeyboardButton("3D", callback_data=34),
               InlineKeyboardButton("3E", callback_data=35),
               InlineKeyboardButton("3F", callback_data=36)],
               [InlineKeyboardButton("4A", callback_data=41),
               InlineKeyboardButton("4B", callback_data=42), 
               InlineKeyboardButton("4C", callback_data=43)],
               [InlineKeyboardButton("CANCEL", callback_data=0)]]
    kb_sis = [[InlineKeyboardButton("2A", callback_data=21),
               InlineKeyboardButton("2B", callback_data=22)], 
               [InlineKeyboardButton("3A", callback_data=31), 
               InlineKeyboardButton("3B", callback_data=32)],
               [InlineKeyboardButton("CANCEL", callback_data=0)]]
    kb_admin = [[InlineKeyboardButton("1", callback_data=41),
               InlineKeyboardButton("2", callback_data=42), 
               InlineKeyboardButton("3", callback_data=43), 
               InlineKeyboardButton("4", callback_data=44),
               InlineKeyboardButton("5", callback_data=45)],
               [InlineKeyboardButton("6", callback_data=46),
               InlineKeyboardButton("7", callback_data=47),
               InlineKeyboardButton("8", callback_data=48),
               InlineKeyboardButton("9", callback_data=49), 
               InlineKeyboardButton("10", callback_data=50)], 
               [InlineKeyboardButton("11", callback_data=51),
               InlineKeyboardButton("12", callback_data=52),
               InlineKeyboardButton("13", callback_data=53),
               InlineKeyboardButton("14", callback_data=54)],
               [InlineKeyboardButton("CANCEL", callback_data=0)]]     
    if num == 9:
        kb = kb_admin
    elif num == 8:
        kb = kb_sis
    elif num == 7:
        kb = kb_soe
    elif num == 6:
        kb = kb_lkcsb
        
    string = user_data['bldg'] + ' selected. Which <b>level/catering area</b> is the food on? \nObtain this information from signage on the wall'
    bot.edit_message_text(text=string, chat_id=query.message.chat_id, message_id=query.message.message_id, parse_mode=ParseMode.HTML)
    bot.send_message(chat_id=query.message.chat_id, text="Please choose:", reply_markup=InlineKeyboardMarkup(kb))
    return RPT_AREA

def _log_area(bot, update, user_data):
    query = update.callback_query
    num = int(query.data)
    if num == 0:
        state = _wrong_input(bot, update, user_data)
    else:
        area_dict = {'1': 'A', '2': 'B', '3': 'C', '4': 'D', '5': 'E', '6': 'F'}
        if num > 40:
            user_data['area'] = "Level " + str(num-40)
        else:
            user_data['area'] = "Level " + str(num)[0] + " Catering Area " + area_dict[str(num)[1]]
        string = user_data['area'] + ' selected. Does the food fulfil any of these <b>dietary requirements</b>?'
        keyboard = [[InlineKeyboardButton("Halal", callback_data=61),
                   InlineKeyboardButton("Vegetarian", callback_data=62), 
                   InlineKeyboardButton("None", callback_data=63)],
                   [InlineKeyboardButton("CANCEL", callback_data=0)]]
        kb = InlineKeyboardMarkup(keyboard)
        bot.edit_message_text(text=string, chat_id=query.message.chat_id, message_id=query.message.message_id, parse_mode=ParseMode.HTML)
        bot.edit_message_reply_markup(chat_id=query.message.chat_id, message_id=query.message.message_id, reply_markup=kb)
        state = RPT_TYPE
    return state

def _log_type(bot, update, user_data):
    query = update.callback_query
    num = int(query.data)
    if num == 0:
        state = _wrong_input(bot, update, user_data)
    else:
        type_dict = {1: 'Halal', 2: 'Vegetarian', 3: 'None'}
        user_data['type'] = type_dict[num - 60]
        string = 'Dietary Requirement: ' + user_data['type'] + ' satisfied. What time does the food <b>expire</b>? Please reply in <i>24hr format</i> ⏳ (e.g. 2359).'
        keyboard = [[InlineKeyboardButton("CANCEL", callback_data=0)]]
        kb = InlineKeyboardMarkup(keyboard)
        bot.edit_message_text(text=string, chat_id=query.message.chat_id, message_id=query.message.message_id, parse_mode=ParseMode.HTML)
        bot.edit_message_reply_markup(chat_id=query.message.chat_id, message_id=query.message.message_id, reply_markup=kb)
        state = RPT_EXP
    return state

#check 24hr format for time
def _check_time_format(string):
    length = len(string) == 4
    if string.isdigit():
        lt_24 = int(string) < 2400
        min_ok = int(string[2:]) <60
        valid = length and lt_24 and min_ok
    else:
        valid = False
    return valid

#check for expiry/cleared
def _check_exp_clr(string):
    now = dt.datetime.now()
    time = dt.datetime(now.year,now.month,now.day, int(string[:2]),int(string[2:]))
    diff = now-time
    max_exp_1hr = diff < dt.timedelta(hours=1)                      #food cannot be expired/cleared <1hr ago
    not_future = -diff < dt.timedelta(hours=10)                     #food cannot be reported in advance
    return (max_exp_1hr and not_future)

def _log_exp(bot, update, user_data):
    text = update.message.text
    if _check_time_format(text) == False:
        state = RPT_EXP
        reply = 'Invalid format. Please reply in <i>24hr format</i> ⏳ (e.g. 2359).'
    elif _check_exp_clr(text) == False:
        state = RPT_EXP
        reply = "Sorry 😔 you can only report food that is currently available! (The food may have already expired or the buffet hasn't started yet!)"
    else:
        state = RPT_CLR
        user_data['exp'] = text
        reply = "Expiry time: " + str(text) + 'h recorded.\nWhat time does the food get <b>cleared</b>? Please reply in <i>24hr format</i> ⏳ (e.g. 2359).'
    keyboard = [[InlineKeyboardButton("CANCEL", callback_data=0)]]
    kb = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(text=reply, reply_markup=kb, parse_mode=ParseMode.HTML)
    return state

def _log_clr(bot, update, user_data):
    text = update.message.text
    now = dt.datetime.now()
    user_data['rpt_time'] = now.strftime('%d%m%y-%H%M%S')
    exact_loc = user_data['bldg'] + ' ' + user_data['area']
    if _check_time_format(text) == False:
        state = RPT_CLR
        reply = 'Invalid format. Please reply in <i>24hr format</i> ⏳ (e.g. 2359).'
    elif _check_exp_clr(text) == False:
        state = RPT_CLR
        reply = "Sorry 😔 you can only report food that is currently available!  (i.e. Buffet hasn't started, or already cleared)"
    elif _check_repeats(user_data['bldg'], exact_loc) == False:
        state = ConversationHandler.END
        reply = "This buffet has already been reported! Use /find to view reported buffets. Thank you! 🙆"
    else:
        _archive(user_data['bldg'])
        state = ConversationHandler.END
        user_data['clr'] = text
        reply = "Clearing time: " + str(text) + 'h recorded.'
        reply += "\nThank you for reporting food with us! Have a great day! 🙆"
        fb.put('/' + user_data['bldg'], user_data['rpt_time'], [exact_loc, user_data['exp'], user_data['clr'], user_data['type']])
        channel_notif = "🍚 New food reported at\n <b>{0}</b> 🍜\n[Dietary Req: {3}; Expiry:{1}h; Cleared: {2}h]".format(exact_loc, user_data['exp'], user_data['clr'], user_data['type'])
        bot.send_message(chat_id="@smufoodchamps", text=channel_notif, reply_markup=None, parse_mode=ParseMode.HTML)        #demo channel chat_id = -1001280645607
    update.message.reply_text(text=reply, parse_mode=ParseMode.HTML)        
    return state

def _wrong_input(bot, update, user_data):
    query = update.callback_query
    num = int(query.data)
    if num != 0:
        pass
    else:
        user_data.clear()
        bot.edit_message_text(text='CANCELLED! Use commands /find or /report to start over.',
                                chat_id=query.message.chat_id, message_id=query.message.message_id, parse_mode=ParseMode.HTML)
    return ConversationHandler.END

def main():
    
    # Create the Updater and pass it your bot's token.
    updater = Updater(AuthKey)
    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", on_start))
    dp.add_handler(CommandHandler("archive", archive, pass_args=True))
    
    # Add conversation handler with the states FINDING, RPT_LVL, RPT_AREA, RPT_EXP_HR, 
                                    #RPT_EXP_MIN, RPT_CLR_HR, RPT_CLR_MIN & DONE
    conv_handler = ConversationHandler(
            entry_points=[CommandHandler("report", report_main),                # must add pass_args=True for password   
                         CommandHandler("find", find)],
            
            states={
                FINDING: [CallbackQueryHandler(_format_find,
                                    pass_user_data=True),
                          CallbackQueryHandler(_wrong_input,
                                  pass_user_data=True)
                          ],
                RPT_BLDG: [CallbackQueryHandler(_log_bldg,
                                    pass_user_data=True),
                          CallbackQueryHandler(_wrong_input,
                                  pass_user_data=True)
                          ],

                RPT_AREA: [CallbackQueryHandler(_log_area,
                                  pass_user_data=True),
                          CallbackQueryHandler(_wrong_input,
                                  pass_user_data=True) 
                          ],
                RPT_TYPE: [CallbackQueryHandler(_log_type,
                                  pass_user_data=True),
                          CallbackQueryHandler(_wrong_input,
                                  pass_user_data=True)
                          ],
                RPT_EXP: [MessageHandler(Filters.text,
                                         _log_exp,
                                  pass_user_data=True),
                          CallbackQueryHandler(_wrong_input,
                                  pass_user_data=True)
                          ],
                RPT_CLR:[MessageHandler(Filters.text,
                                         _log_clr,
                                  pass_user_data=True),
                             CallbackQueryHandler(_wrong_input,
                                  pass_user_data=True)
                            ]
                    },

            fallbacks=[CommandHandler("cancel", cancel,
                                      pass_user_data=True)]
            )

    dp.add_handler(conv_handler)
    # log all errors
    dp.add_error_handler(error)
    
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
