#!/usr/bin/env python3

import json
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as fd

from nltk.sentiment.vader import SentimentIntensityAnalyzer


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
            return "negative"
        elif all([x < 0 for x in self.sentiment_diffs]):
            return "positive"
        else:
            return "neutral"

    def unique_participants(self):
        return len(set(self.authors))

    def number_of_turns(self):
        return len(self.tweets)

    def lowest_sentiment_diff(self):
        return min([abs(x) for x in self.sentiment_diffs])


class ConversationTreeview(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent)

        self.scrollbar = ttk.Scrollbar(self)
        self.tree = ttk.Treeview(self, columns=('Tweet', 'Author',))
        self.scrollbar.configure(command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        self.tree.column('#1', width=100, stretch=0)
        self.tree.column('#2', width=100, stretch=0)

        self.tree.heading('#0', text='Tweet')
        self.tree.heading('#1', text='Author')
        self.tree.heading('#2', text='Sentiment')

        self.tree.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')

    def __clear(self):
        self.tree.delete(*self.tree.get_children())

    def update(self, conversations):
        self.__clear()

        for convo in conversations:
            root_tw = self.tree.insert('', 'end', text=convo.tweets[0],
                                       values=[convo.authors[0],
                                               convo.conversation_sentiment])
            for i in range(1, convo.number_of_turns()):
                self.tree.insert(root_tw, 'end', text = convo.tweets[i],
                                 values=[convo.authors[i], 
                                         convo.sentiment_scores[i]])


class ConversationDisplay(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent)
        self.conversations = []

        self.view = ConversationTreeview(self)
        self.view.pack(side='right', fill='both', expand=True)


    def load_file(self):
        path = fd.askopenfilename(parent=self,
                                  filetypes=(("JSON files", "*.json"),
                                             ("All files", "*")))
        with open(path) as f:
            json_convos = json.load(f)["conversations"]

        self.conversations = [Conversation(convo) for convo in json_convos]
        self.view.update(self.conversations)


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
