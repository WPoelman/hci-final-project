#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
File name:  feed.py
Authors:    Erwin Meijerhof (S2377012)
            Wessel Poelman  (S2976129)
Date:       09-04-2021
GitHub:     https://github.com/WPoelman/hci-final-project
Description:
    The first part of Assignment 3 of the course Human Computer Interaction.
    This frame allows the user to specify filters for fetching a specific
    Twitter conversation. This conversation is also shown.
Usage:
    python feed.py
"""

import datetime
import json
import queue
import textwrap
import threading
import time
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.ttk as ttk
from enum import Enum
from os.path import isfile
from tkinter import scrolledtext as st
from tkinter.font import Font

import tweepy
from geopy import Nominatim
from nltk import download
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Downloads the required nltk corpus if it is not installed already
download('vader_lexicon')


class Conversation:
    sid = SentimentIntensityAnalyzer()

    def __init__(self, data):
        self.tweets = [tweet["text"] for tweet in data[::-1]]
        self.authors = [tweet["user"]["name"] for tweet in data[::-1]]
        self.sentiment_scores = self.__score_tweets()
        self.sentiment_diffs = self.__sent_diffs()
        self.conversation_sentiment = self.__conv_sent()

    def __score_tweets(self):
        scores = []
        for tweet in self.tweets:
            scores.append(self.sid.polarity_scores(tweet)["compound"])

        return scores

    def __sent_diffs(self):
        diffs = []
        for i in range(1, self.number_of_turns()):
            diff = self.sentiment_scores[i-1] - self.sentiment_scores[i]
            diffs.append(diff)

        return diffs

    def __conv_sent(self):
        if all([x > 0 for x in self.sentiment_diffs]):
            return "Negative"
        elif all([x < 0 for x in self.sentiment_diffs]):
            return "Positive"
        else:
            return "Neutral"

    def unique_participants(self):
        return len(set(self.authors))

    def number_of_turns(self):
        return len(self.tweets)

    def lowest_sentiment_diff(self):
        return min([abs(x) for x in self.sentiment_diffs])


class ConversationTreeview(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent)

        self.font = Font(font='TkDefaultFont')
        self.font_height = self.font.metrics('linespace')
        self.style = ttk.Style(self)
        self.style.configure('Treeview',
                             rowheight=((self.font_height * 2) + 10))

        self.scrollbar = ttk.Scrollbar(self)
        self.tree = ttk.Treeview(self, columns=('Tweet', 'Author',))
        self.scrollbar.configure(command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.tree.column('#1', width=120, stretch=0)
        self.tree.column('#2', width=120, stretch=0)

        self.tree.heading('#0', text='Tweet')
        self.tree.heading('#1', text='Author')
        self.tree.heading('#2', text='Sentiment')

        self.tree.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')

    def __clear(self):
        self.tree.delete(*self.tree.get_children())

    def wrap_text(self, text):
        text_length = len(text)
        if not text_length > 50:
            return text

        line1 = []
        line2 = []

        for word in text.split():
            if len(' '.join(line1) + ' ' + word) < (text_length/2):
                line1.append(word)
            else:
                line2.append(word)

        return ' '.join(line1) + '\n' + ' '.join(line2)

    def update(self, conversations):
        self.__clear()

        for convo in conversations:
            root_tweet_text = self.wrap_text(convo.tweets[0])
            root_tw = self.tree.insert('', 'end', text=root_tweet_text,
                                       values=[convo.authors[0],
                                               convo.conversation_sentiment])
            for i in range(1, convo.number_of_turns()):
                if convo.sentiment_diffs[i-1] <= 0:
                    sent_diff = '+' + \
                        str(round(abs(convo.sentiment_diffs[i-1]), 5))
                else:
                    sent_diff = '-' + str(round(convo.sentiment_diffs[i-1], 5))
                tweet_text = self.wrap_text(convo.tweets[i])
                self.tree.insert(root_tw, 'end', text=tweet_text,
                                 values=[convo.authors[i], sent_diff])


class ConversationDisplay(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent)
        self.conversations = []

        self.filter_menu = tk.Frame(self)
        self.view = ConversationTreeview(self)

        self.min_part_scale = tk.Scale(self.filter_menu, from_=2, to=10,
                                       label="Min participants:",
                                       orient="horizontal")
        self.min_part_scale.set(2)

        self.max_part_scale = tk.Scale(self.filter_menu, from_=2, to=10,
                                       label="Max participants:",
                                       orient="horizontal")
        self.max_part_scale.set(10)

        self.min_turn_scale = tk.Scale(self.filter_menu, from_=3, to=10,
                                       label="Min length:",
                                       orient="horizontal")
        self.min_turn_scale.set(2)

        self.max_turn_scale = tk.Scale(self.filter_menu, from_=3, to=10,
                                       label="Max length:",
                                       orient="horizontal")
        self.max_turn_scale.set(10)

        self.sent_change_label = tk.Label(self.filter_menu, anchor="w",
                                          text="Change in sentiment:",
                                          padx="7")
        self.option_list = ["All", "Positive", "Negative", "Neutral"]
        self.sent_change_var = tk.StringVar()
        self.sent_change_var.set(self.option_list[0])
        self.sent_change_opt = tk.OptionMenu(self.filter_menu,
                                             self.sent_change_var,
                                             *self.option_list)

        self.sent_thresh_scale = tk.Scale(self.filter_menu, from_=0, to=0.5,
                                          label="Sentiment threshold:",
                                          orient="horizontal",
                                          resolution=0.01)
        self.sent_thresh_scale.set(0)

        self.filter_button = tk.Button(self.filter_menu, text="Filter",
                                       command=self.filter, width=20)

        self.min_part_scale.pack(fill='x')
        self.max_part_scale.pack(fill='x')
        self.min_turn_scale.pack(fill='x')
        self.max_turn_scale.pack(fill='x')
        self.sent_change_label.pack(fill='x')
        self.sent_change_opt.pack(fill='x')
        self.sent_thresh_scale.pack(fill='x')
        self.filter_button.pack(fill='x')

        self.filter_menu.pack(side='left', fill='both')
        self.view.pack(side='right', fill='both', expand=True)

    def __filter_conditions(self, convo):
        min_part = convo.unique_participants() >= self.min_part_scale.get()
        max_part = convo.unique_participants() <= self.max_part_scale.get()
        min_turn = convo.number_of_turns() > self.min_turn_scale.get()
        max_turn = convo.number_of_turns() > self.max_turn_scale.get()
        s_change = (self.sent_change_var.get() == "All" or
                    self.sent_change_var.get() == convo.conversation_sentiment)
        s_thr = convo.lowest_sentiment_diff() >= self.sent_thresh_scale.get()

        return (min_part and max_part and min_turn and
                max_turn and s_change and s_thr)

    def load_file(self):
        path = fd.askopenfilename(parent=self,
                                  filetypes=(("JSON files", "*.json"),))
        if not path:
            return

        with open(path) as f:
            try:
                json_convos = json.load(f)["conversations"]
                self.conversations = [Conversation(cv) for cv in json_convos]
                self.view.update(self.conversations)
            except:
                tk.messagebox.showerror("Error", "Invalid conversation file." +
                                        " Please try a different document.")
                self.load_file()

    def filter(self):
        filtered_convos = []
        for convo in self.conversations:
            if self.__filter_conditions(convo):
                filtered_convos.append(convo)

        self.view.update(filtered_convos)


class GeneralStatus(Enum):
    ''' Enum used for indicating a status '''
    IDLE = 'idle'
    FETCHING = 'fetching'
    RETRYING = 'retrying'
    PARSING = 'parsing'
    ERROR = 'error'


class TweepyApi:
    def __init__(self, credentials_path='../credentials.txt'):
        self.status = GeneralStatus.IDLE
        self.message = ''

        self.seen_tweet_ids = set()
        self.halt = False

        # Adapted from:
        # https://developer.twitter.com/en/docs/twitter-for-websites/supported-languages
        self.available_languages = {
            'English':                  'en',
            'Arabic':                   'ar',
            'Bengali':                  'bn',
            'Czech':                    'cs',
            'Danish':                   'da',
            'German':                   'de',
            'Greek':                    'el',
            'Spanish':                  'es',
            'Persian':                  'fa',
            'Finnish':                  'fi',
            'Filipino':                 'fil',
            'French':                   'fr',
            'Hebrew':                   'he',
            'Hindi':                    'hi',
            'Hungarian':                'hu',
            'Indonesian':               'id',
            'Italian':                  'it',
            'Japanese':                 'ja',
            'Korean':                   'ko',
            'Malay':                    'msa',
            'Dutch':                    'nl',
            'Norwegian':                'no',
            'Polish':                   'pl',
            'Portuguese':               'pt',
            'Romanian':                 'ro',
            'Russian':                  'ru',
            'Swedish':                  'sv',
            'Thai':                     'th',
            'Turkish':                  'tr',
            'Ukrainian':                'uk',
            'Urdu':                     'ur',
            'Vietnamese':               'vi',
            'Chinese (Simplified)':     'zh-cn',
            'Chinese (Traditional)':    'zh-tw',
        }

        self.default_language = 'English'
        self.min_conv_len = 3
        self.max_conv_len = 10

        # These are the fields that get extracted from the individual tweets
        # based on their keys.
        self.wanted_keys = {
            "created_at",
            "id",
            "text",
            "in_reply_to_user_id",
            "in_reply_to_status_id",
            "in_reply_to_screen_name",
            "user",
        }

        self.credentials = self.__read_in_credentials(credentials_path)
        self.api = None

        # This happens when someone does not have a valid credentials.txt file
        # in their root directory of the program.
        if self.credentials:
            self.api = self.__create_api()

    def set_status(self, status):
        ''' Sets the status of the api '''
        print(f'New status api: {status}')
        self.status = status

    def set_message(self, message):
        ''' Sets an message message '''
        print(f'New message api: {message}')
        self.message = message

    def get_status(self):
        ''' Returns the status of the api '''
        return self.status.value

    def get_message(self):
        ''' Returns the latest message of the api '''
        return self.message

    def __read_in_credentials(self, path):
        ''' Reads in twitter api credentials from the given path '''
        if not isfile(path):
            self.set_status(GeneralStatus.ERROR)
            self.set_message('Path to credentials file does not exist.')

            return None

        with open(path, 'r') as f:
            credentials = {}
            for line in f.readlines():
                # Bit ugly, be we have no idea what files the user provides.
                if '=' in line:
                    items = line.strip().split('=')
                    if len(items) == 2:
                        credentials[items[0]] = items[1]

        required_keys = {'API_KEY', 'API_SECRET',
                         'ACCESS_TOKEN', 'ACCESS_SECRET'}

        if required_keys != credentials.keys():
            self.set_status(GeneralStatus.ERROR)
            self.set_message(
                'Not all keys are given or the credentials format is wrong.'
            )

            return None

        return credentials

    def is_busy(self):
        ''' Indicates if the api is busy '''
        return (self.status != GeneralStatus.IDLE and
                self.status != GeneralStatus.ERROR)

    def __create_api(self):
        ''' Creates a tweepy api instance '''
        auth = tweepy.OAuthHandler(
            self.credentials['API_KEY'],
            self.credentials['API_SECRET']
        )

        auth.set_access_token(
            self.credentials['ACCESS_TOKEN'],
            self.credentials['ACCESS_SECRET']
        )

        return tweepy.API(auth)

    def __extract_converstation(self, response, acc=None):
        ''' Recursively extracts a conversation '''
        if not acc:
            acc = []

        if self.halt:
            return []

        self.set_status(GeneralStatus.PARSING)

        cleaned_item = {
            key: val
            for key, val in response.items()
            if key in self.wanted_keys
        }

        acc.append(cleaned_item)

        try:
            new = self.api.get_status(
                id=cleaned_item['in_reply_to_status_id']
            )._json
        except (tweepy.error.TweepError, tweepy.error.RateLimitError) as err:
            self.set_status(GeneralStatus.ERROR)
            self.set_message(f'Tweepy error, {err}')
            return []

        # Exit condition is the main 'parent' of the initial tweet or the max
        # number of turns per conversation.
        if not new['in_reply_to_status_id'] or len(acc) == self.max_conv_len:
            self.set_status(GeneralStatus.IDLE)
            return acc

        return self.__extract_converstation(new, acc)

    def get_conversation(self, query=None, language=None, geocode=None):
        ''' Gets a conversation, optionally filtered using the given
            parameters.
                query:      search query
                language:   display name of the available languages, which gets
                            translated into the language code using the
                            'available_language' dictionary
                geocode:    string for only getting tweets from within a
                            certain area, format -> 'lat,long,radius<ml | km>'
        '''
        self.set_status(GeneralStatus.FETCHING)

        if not language:
            language = self.default_language

        print(
            f'''
            Query\t{query}
            Language\t{language}
            Geocode\t{geocode}
            '''
        )

        # This is not a very nice try-except, but the Tweepy package can throw
        # an exception at strange places. For example, initializing the cursor
        # might throw an exception, but not always, calling items() could also
        # do it, and even accessing the _json. The exceptions are all from
        # Tweepy and most of the time they are 400 status errors.
        try:
            cursor = tweepy.Cursor(
                self.api.search,
                q=query,
                lang=self.available_languages[language],
                geocode=geocode
            )

            for status in cursor.items():
                response = status._json

                # Search for a possible conversation candidate.
                if not response['in_reply_to_status_id']:
                    continue

                # Once we have a single conversation, we can extract it and
                # stop searching.
                conversation = self.__extract_converstation(response, [])
                conversation_len = len(conversation)

                # We only want to find conversations with 3-10 turns, as per
                # the assignment instructions. We cannot specify this in
                # calling the Twitter api, so we just have to try again if we
                # do not find it here.
                if (conversation_len >= self.min_conv_len and
                        conversation_len <= self.max_conv_len):

                    ids = {i['id'] for i in conversation}

                    if ids.issubset(self.seen_tweet_ids):
                        self.set_status(GeneralStatus.RETRYING)
                        self.set_message(
                            'Found already existing tweets, trying again...'
                        )
                        continue
                    else:
                        self.seen_tweet_ids.update(ids)
                        break

                if self.halt:
                    break

                self.set_status(GeneralStatus.RETRYING)
                self.set_message((
                    f'Conversation with length {conversation_len}, '
                    'trying again...'
                ))

        except (tweepy.error.TweepError, tweepy.error.RateLimitError) as err:
            self.set_status(GeneralStatus.ERROR)
            self.set_message(f'Tweepy error, {err}')
            return []

        if not conversation:
            self.set_status(GeneralStatus.ERROR)
            self.set_message('No results found or stopped fetching!')
            return []

        self.set_status(GeneralStatus.IDLE)
        self.set_message(
            f'Added new conversation with {len(conversation)} entries'
        )
        return conversation

    def change_credentials(self, filepath):
        ''' Changes the Twitter api credentials with a credentials file from
            the given path.
        '''
        credentials = self.__read_in_credentials(filepath)

        if credentials:
            self.credentials = credentials
            self.api = self.__create_api()
            self.set_status(GeneralStatus.IDLE)
            self.set_message(
                f'Successfully changed credentials using file:\n{filepath}'
            )


class EditableList(tk.Frame):
    ''' Editable list allows text items to be added and removed.

        Adapted from Assignment 1 submission from Wessel.
     '''

    def __init__(self, parent, title, *args, **kwargs):
        super().__init__(parent)
        self.title = title
        self.list_items = []

        self.create_widgets()

    def create_widgets(self):
        ''' Creates the widgets for the EditableList, some of which are stored
            on the object if they are needed again later.
         '''
        # -- Top frame widgets --
        top_frame = tk.Frame(self)
        title_label = ttk.Label(top_frame, text=self.title)
        self.text = st.ScrolledText(top_frame, state='disabled',
                                    wrap=tk.WORD, width=50)
        self.status_text = tk.StringVar(top_frame)
        label = ttk.Label(top_frame, textvariable=self.status_text)

        # -- Bottom frame widgets --
        bottom_frame = tk.Frame(self)
        self.entry = tk.Entry(bottom_frame)
        add_button = tk.Button(bottom_frame, text='add',
                               command=self.add_entry)
        clear_button = tk.Button(bottom_frame, text='clear',
                                 command=self.clear_entries)

        tk.Grid.rowconfigure(self, 0, weight=1)
        tk.Grid.columnconfigure(self, 0, weight=1)

        tk.Grid.rowconfigure(top_frame, 0, weight=1)
        tk.Grid.columnconfigure(top_frame, 0, weight=1)

        tk.Grid.rowconfigure(bottom_frame, 0, weight=1)
        tk.Grid.columnconfigure(bottom_frame, 0, weight=1)

        # -- Top frame grid --
        top_frame.grid(row=0, column=0)
        title_label.grid(row=0, column=0)
        label.grid(row=1, column=0)
        self.text.grid(row=2, column=0)

        # -- Bottom frame grid --
        bottom_frame.grid(row=1, column=0, sticky='s')
        self.entry.grid(row=0, column=1, sticky='s')
        add_button.grid(row=0, column=2, sticky='e')
        clear_button.grid(row=0, column=0, sticky='w')

        self.grid(row=0, column=0, sticky='nsew')

    def add_entry(self):
        ''' Checks if the query exists and adds it to the list if it does '''
        entry = self.entry.get().strip()

        if not entry:
            self.status_text.set('Cannot add empty term')
            return

        self.text.configure(state='normal')
        self.text.insert(tk.END, f'{entry}\n')
        self.text.configure(state='disabled')
        self.list_items.append(entry)
        self.entry.delete(0, tk.END)
        self.status_text.set(f'Search term \'{entry}\' added.')

    def get_entries(self):
        ''' Returns all items currently in the list '''
        return self.list_items

    def clear_entries(self):
        ''' Clears all list fields '''
        self.text.configure(state='normal')
        self.text.delete(1.0, tk.END)
        self.text.configure(state='disabled')
        self.list_items = []
        self.entry.delete(0, tk.END)
        self.status_text.set('')


class Feed(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent)
        self.clean_up_parent = parent.destroy

        # -- Api for retrieving conversations --
        self.api = TweepyApi()

        # -- Status indicator if the frame is busy --
        self.status = GeneralStatus.IDLE
        self.message = ''

        self.status_text = tk.StringVar(self)
        self.status_label = ttk.Label(self, textvariable=self.status_text)

        self.paused = True

        self.textwrapper = textwrap.TextWrapper(60).fill
        self.status_textwrapper = textwrap.TextWrapper(30).fill

        # -- Tweet queue with parsed conversations --
        self.tweet_queue = queue.Queue()

        # --
        #   List with fetched conversations, used to export to file.
        #   Consists of tuples: (list of conversation, search parameters)
        # --
        self.conversation_list = []

        # -- List of search terms --
        self.search_terms_list = EditableList(self, 'Search terms')

        # -- Language selector --
        self.language = tk.StringVar(self)
        self.language.set(self.api.default_language)
        self.language_select = tk.OptionMenu(
            self,
            self.language,
            *sorted(list(self.api.available_languages.keys()))
        )

        # -- Location entry fields --
        self.location_entry = tk.Entry(self)
        self.radius_entry = tk.Entry(self)
        self.geocoder = Nominatim(user_agent='hci_final_project')

        # -- Start fetching using the current filters to get conversation --
        self.start_stop_button = tk.Button(self,
                                           text='Start fetching',
                                           command=self.toggle_pause)

        # -- Entry labels --
        langauge_label = tk.Label(self, text="Tweet language")
        location_label = tk.Label(self, text="Address")
        radius_label = tk.Label(self, text="Radius (km)")

        # -- Tweets treeview --
        ttk.Style().configure('Custom.Treeview', rowheight=50)

        # -- Treeview  --
        self.tree = ttk.Treeview(self,
                                 columns=('tweet'),
                                 style='Custom.Treeview')
        self.tree.heading('#0', text='Author')
        self.tree.column('tweet', width=500)
        self.tree.heading('tweet', text='Tweet')
        self.tree.bind("<Double-1>", self.on_tweet_click)

        # -- Treeview scroll --
        scroll = ttk.Scrollbar(self, orient=tk.VERTICAL,
                               command=self.tree.yview)
        self.tree.configure(yscroll=scroll.set)

        # -- Arrange widgets --
        tk.Grid.rowconfigure(self, 0, weight=1)
        tk.Grid.columnconfigure(self, 0, weight=1)

        self.search_terms_list.grid(row=0,
                                    column=0,
                                    columnspan=2,
                                    sticky='nsew')
        self.status_label.grid(row=1, column=0, columnspan=2, sticky='nsew')
        self.language_select.grid(row=2, column=1, sticky='nsew')
        self.location_entry.grid(row=3, column=1, sticky='nsew')
        self.radius_entry.grid(row=4, column=1, sticky='nsew')

        langauge_label.grid(row=2, column=0, sticky='w')
        location_label.grid(row=3, column=0, sticky='w')
        radius_label.grid(row=4, column=0, sticky='w')
        self.start_stop_button.grid(row=5, column=1, sticky='nsew')

        scroll.grid(row=0, column=2, rowspan=6, sticky='ens')
        self.tree.grid(row=0, column=2, rowspan=6, sticky='nsew')

        self.__update_treeview()
        self.__start_poll_system_status()

        self.grid(row=0, column=0, sticky='nsew')

    def on_tweet_click(self, event):
        ''' Dummy method to override with a method to handle double
            clicking a tree item.
        '''
        print(event)
        print("Clicked on: ", self.tree.item(self.tree.selection()[0]))

    def __start_poll_system_status(self):
        ''' Fires off a new thread that polls the status of the system '''
        threading.Thread(target=self.poll_system_status).start()

    def poll_system_status(self):
        ''' Polls the system status and creates a formatted string from it '''
        self.status_text.set((
            f'\nAPI status: {self.api.get_status()}'
            f'\nAPI message: {self.status_textwrapper(self.api.get_message())}\n'
            f'\nWindow status: {self.get_status()}'
            f'\nWindow message: {self.status_textwrapper(self.get_message())}'
        ))

        if (self.api.status == GeneralStatus.ERROR or
                self.status == GeneralStatus.ERROR):
            self.paused = True
            self.start_stop_button['text'] = 'Start fetching'

        self.after(100, self.poll_system_status)

    def toggle_pause(self):
        ''' Switches between fetching and not fetching. Clears the data from
            the previous 'session' to start fresh. When starting, it fires off
            the fetching and parsing of conversations in a new thread.
        '''
        if not self.api:
            self.set_status(GeneralStatus.ERROR)
            self.set_message('No credentials file provided, please add one.')
            return

        if self.paused:
            self.paused = False
            self.api.halt = False
            self.start_stop_button['text'] = 'Stop fetching'

            self.tree.delete(*self.tree.get_children())
            self.conversation_list = []
            self.api.seen_tweet_ids = set()
            self.tweet_queue.queue.clear()

            threading.Thread(target=self.__submit).start()
        else:
            self.paused = True
            self.api.halt = True
            self.start_stop_button['text'] = 'Start fetching'

    def set_status(self, status):
        ''' Sets the frame status '''
        print(f'New status main frame: {status}')
        self.status = status

    def get_status(self):
        ''' Gets the frame status '''
        return self.status.value

    def set_message(self, message):
        ''' Sets the frame message '''
        print(f'New message main frame: {message}')
        self.message = message

    def get_message(self):
        ''' Gets the frame message '''
        return self.message

    def is_busy(self):
        ''' Indicates if the frame is busy '''
        return (self.status != GeneralStatus.IDLE and
                self.status != GeneralStatus.ERROR)

    def __submit(self):
        ''' Submits the current filters and asks the api to start retrieving
            conversations. The filters get validated before sending the request
            to the Twitter api.
         '''
        self.set_status(GeneralStatus.FETCHING)

        location_query = self.location_entry.get()

        # Clean the radius of any non numeric characters and set it back. This
        # is somewhat tolerant for someone typing '20km' by accident for
        # example as it would normalize it to '20' instead of giving an error.
        location_radius = ''.join(
            [c for c in self.radius_entry.get() if c.isdigit()]
        )
        self.radius_entry.delete(0, tk.END)
        self.radius_entry.insert(0, location_radius)

        geo_query = None

        if location_query and location_radius:
            geo = self.geocoder.geocode(location_query)
            if geo:
                geo_query = (
                    f'{geo.latitude},{geo.longitude},{location_radius}km'
                )
            else:
                self.location_entry.delete(0, tk.END)

        language = self.language.get()

        search_terms = self.search_terms_list.get_entries()

        if len(search_terms) == 1:
            search_query = search_terms[0]
        elif len(search_terms) > 1:
            search_query = '&'.join(search_terms)
        else:
            search_query = None

        self.start_fetching(search_query, language, geo_query)

    def start_fetching(self, search_query, language, geo_query):
        ''' Continuosly fetches conversations when the system is not paused '''
        while not self.paused:
            result = self.api.get_conversation(search_query,
                                               language,
                                               geo_query)

            if result:
                formatted_query = (
                    f'{language}'
                    f'{"&" + search_query if search_query else ""}'
                    f'{"&" + geo_query if geo_query else ""}'
                )
                self.conversation_list.append((result, formatted_query))
                self.tweet_queue.put(result)

            time.sleep(0.1)

        self.set_status(GeneralStatus.IDLE)

    def new_credentials(self):
        ''' Asks the user to provide a new credentials file and instructs the
            tweepy api to use the new credentials.
        '''
        self.set_status(GeneralStatus.PARSING)

        filepath = fd.askopenfilename()

        if filepath:
            self.api.change_credentials(filepath)

        self.set_status(GeneralStatus.IDLE)

    def __update_treeview(self):
        ''' Updates the treeview with tweet conversations from the queue '''
        try:
            conversation = self.tweet_queue.get(block=False)

            parent_tweet = conversation.pop()

            if self.tree.exists(parent_tweet['id']):
                self.set_message('Trying to add already existing tweet.')
                raise ValueError('Trying to add already existing tweet.')

            self.tree.insert(
                '',
                tk.END,
                parent_tweet['id'],
                text=parent_tweet['user']['screen_name'],
                values=[self.textwrapper(parent_tweet['text'])],
                open=True
            )

            for tweet in conversation:
                self.tree.insert(
                    parent_tweet['id'],
                    tk.END,
                    tweet['id'],
                    text=tweet['user']['screen_name'],
                    values=[self.textwrapper(tweet['text'])],
                )

        except (queue.Empty, ValueError):
            pass

        self.after(100, self.__update_treeview)

    def save(self):
        ''' Saves the fetched conversations to a json file '''
        self.set_status(GeneralStatus.PARSING)

        if len(self.conversation_list) > 0:
            now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f'{now}-{self.conversation_list[0][1]}.json'

            with open(filename, 'w') as out_file:
                json.dump({
                    'conversations': [conv[0]
                                      for conv in self.conversation_list
                                      if conv[0]]
                }, out_file)

            self.set_status(GeneralStatus.IDLE)
            self.set_message('Conversations were exported')
        else:
            self.set_status(GeneralStatus.ERROR)
            self.set_message('No conversations to export')

    def clean_up(self):
        ''' Waits for all threads from all widgets to close down and closes
            the window main window afterwards.
        '''
        while self.is_busy():
            self.paused = True
            time.sleep(0.1)

        self.clean_up_parent()

        return True


class Notebook(ttk.Notebook):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent)
        self.parent_cleanup = parent.destroy

        self.feed = Feed(self)
        self.cd = ConversationDisplay(self)
        # self.cd.pack(fill='both', expand=True)

        self.add(self.feed, text='Twitter Feed')
        self.add(self.cd, text='Conversation Sentiments')

        self.grid(sticky='nsew')

    def open_file(self):
        self.cd.load_file()
        self.select(self.cd)

    def clean_up(self):
        ''' Calls the cleanup functions on all child widgets '''
        while self.feed.is_busy():
            self.feed.clean_up()
            time.sleep(0.1)

        self.parent_cleanup()


def main():
    root = tk.Tk()
    root.title('HCI - Final Project')

    # This allows for somewhat graceful window resizing
    tk.Grid.rowconfigure(root, 0, weight=1)
    tk.Grid.columnconfigure(root, 0, weight=1)

    notebook = Notebook(root)

    # -- Menu-bar  --
    menu_bar = tk.Menu(root)

    file_menu = tk.Menu(menu_bar, tearoff=0)
    file_menu.add_command(label="Save", command=notebook.feed.save)
    file_menu.add_command(label="Open", command=notebook.open_file)
    file_menu.add_command(label="Exit", command=notebook.clean_up)

    options_menu = tk.Menu(menu_bar, tearoff=0)
    options_menu.add_command(label="Credentials",
                             command=notebook.feed.new_credentials)

    menu_bar.add_cascade(label="File", menu=file_menu)
    menu_bar.add_cascade(label="Options", menu=options_menu)

    root.config(menu=menu_bar)
    root.protocol("WM_DELETE_WINDOW", notebook.clean_up)

    notebook.mainloop()


if __name__ == '__main__':
    main()
