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
        self.conversation_score = self.__score_conversation()

    def __score_tweets(self):
        scores = []
        for tweet in self.tweets:
            scores.append(self.sid.polarity_scores(tweet)["compound"])

        return scores

    def __score_conversation(self):
        score = 0
        for i in range(1, self.number_of_turns()):
            diff = self.sentiment_scores[i-1] - self.sentiment_scores[i]
            if diff > 0.02:
                score -= 1
            elif diff < -0.02:
                score += 1

        return (score / (self.number_of_turns()-1))

    def unique_participants(self):
        return len(set(self.authors))

    def number_of_turns(self):
        return len(self.tweets)

    def lowest_sentiment_score(self):
        return min(self.sentiment_scores)

    def highest_sentiment_score(self):
        return max(self.sentiment_scores)


class ConversationDisplay(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent)
        self.conversations = []

    def load_file(self):
        path = fd.askopenfilename(parent=self,
                                  filetypes=(("JSON files", "*.json"),
                                             ("All files", "*")))
        with open(path) as f:
            json_convos = json.load(f)["conversations"]

        self.conversations = [Conversation(convo) for convo in json_convos]

        for c in self.conversations:
            print(c.tweets)
            print(c.sentiment_scores)
            print(c.conversation_sentiment())
            print()


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
