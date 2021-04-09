#!/usr/bin/env python3

import json
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.ttk as ttk
from tkinter.font import Font

from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk import download
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
                    sent_diff = '+' + str(round(abs(convo.sentiment_diffs[i-1]), 5))
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
        self.min_part_scale.bind("<ButtonRelease-1>", self.check_max_part_scale)
        self.min_part_scale.set(2)

        self.max_part_scale = tk.Scale(self.filter_menu, from_=2, to=10,
                                       label="Max participants:",
                                       orient="horizontal")
        self.max_part_scale.bind("<ButtonRelease-1>", self.check_min_part_scale)
        self.max_part_scale.set(10)

        self.min_turn_scale = tk.Scale(self.filter_menu, from_=3, to=10,
                                       label="Min length:",
                                       orient="horizontal")
        self.min_turn_scale.bind("<ButtonRelease-1>", self.check_max_turn_scale)
        self.min_turn_scale.set(2)

        self.max_turn_scale = tk.Scale(self.filter_menu, from_=3, to=10,
                                       label="Max length:",
                                       orient="horizontal")
        self.max_turn_scale.bind("<ButtonRelease-1>", self.check_min_turn_scale)
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
                max_turn and  s_change and s_thr)

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

    def check_max_part_scale(self, event):
        if self.min_part_scale.get() > self.max_part_scale.get():
            self.max_part_scale.set(self.min_part_scale.get())

    def check_min_part_scale(self, event):
        if self.min_part_scale.get() > self.max_part_scale.get():
            self.min_part_scale.set(self.max_part_scale.get())

    def check_max_turn_scale(self, event):
        if self.min_turn_scale.get() > self.max_turn_scale.get():
            self.max_turn_scale.set(self.min_turn_scale.get())

    def check_min_turn_scale(self, event):
        if self.min_turn_scale.get() > self.max_turn_scale.get():
            self.min_turn_scale.set(self.max_turn_scale.get())

    def filter(self):
        filtered_convos = []
        for convo in self.conversations:
            if self.__filter_conditions(convo):
                filtered_convos.append(convo)

        self.view.update(filtered_convos)


if __name__ == '__main__':
    root = tk.Tk()
    root.geometry('640x480')

    cd = ConversationDisplay(root)
    cd.pack(fill='both', expand=True)

    # Menubar
    menubar = tk.Menu(root)

    filemenu = tk.Menu(menubar, tearoff=0)
    filemenu.add_command(label="Open", command=cd.load_file)
    filemenu.add_command(label="Exit", command=root.quit)

    menubar.add_cascade(label="File", menu=filemenu)

    root.config(menu=menubar)

    # Start loop
    root.mainloop()
