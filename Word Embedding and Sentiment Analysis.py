"""## Load Package

"""
import torch
import torch.nn as nn
import torch.nn.functional as F

from collections import Counter, OrderedDict
from torchtext.vocab import Vocab, vocab
from torchtext.vocab import build_vocab_from_iterator

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.model_selection import GridSearchCV
from bs4 import BeautifulSoup
import numpy as np
import spacy
from spacy.matcher import Matcher
from spacy.tokens import Token
import re
from pathlib import Path
import textwrap as tw
from nltk.stem.porter import PorterStemmer

import pandas as pd
import gensim
import gensim.downloader as loader
from gensim.models.fasttext import FastText
import random
from gensim.models import Word2Vec
from gensim.models import KeyedVectors
import gc
from nltk.util import ngrams
import nltk
import matplotlib.pyplot as plt

from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer

nltk.download('punkt')
nltk.download('vader_lexicon')

# load spacy model
model = 'en_core_web_lg'
nlp = spacy.load(model)

from google.colab import drive
drive.mount('/content/drive')

data_folder = Path('/content/drive/MyDrive/Data/')

"""## Custom Spacy Model"""

#Custom my stop word
nlp.Defaults.stop_words |= {"ritz","carlton","half","moon","bay","hotel","day","night","experience","property","time","stay", "$", 'san', 'francisco'}

class SpacyPreprocessor(BaseEstimator, TransformerMixin):
    np.random.seed(0)
    def __init__(self, lammetize=True, lower=True, remove_stop=True, 
                 remove_punct=True, remove_email=True, remove_url=True, remove_num=False, stemming = False,
                 add_user_mention_prefix=True, remove_hashtag_prefix=False):
        self.remove_stop = remove_stop
        self.remove_punct = remove_punct
        self.remove_num = remove_num
        self.remove_url = remove_url
        self.remove_email = remove_email
        self.lammetize = lammetize
        self.lower = lower
        self.stemming = stemming
        self.add_user_mention_prefix = add_user_mention_prefix
        self.remove_hashtag_prefix = remove_hashtag_prefix    

 # helpfer functions for basic cleaning 

    def basic_clean(self, text):
        if (bool(BeautifulSoup(text, "html.parser").find())==True):         
            soup = BeautifulSoup(text, "html.parser")
            text = soup.get_text()
        else:
            pass
        return re.sub(r'[\n\r]',' ', text) 

    # helper function for pre-processing with spacy and Porter Stemmer
    
    def spacy_preprocessor(self,texts):

        final_result = []
        nlp = spacy.load(model, disable=['parser','ner'])
        
        ## Add @ as a prefix so that we can separate the word from its token
        prefixes = list(nlp.Defaults.prefixes)

        if self.add_user_mention_prefix:
            prefixes += ['@']

        ## Remove # as a prefix so that we can keep hashtags and words together
        if self.remove_hashtag_prefix:
            prefixes.remove(r'#')

        prefix_regex = spacy.util.compile_prefix_regex(prefixes)
        nlp.tokenizer.prefix_search = prefix_regex.search

        matcher = Matcher(nlp.vocab)
        if self.remove_stop:
            matcher.add("stop_words", [[{"is_stop" : True}]])
        if self.remove_punct:
            matcher.add("punctuation",[ [{"is_punct": True}]])
        if self.remove_num:
            matcher.add("numbers", [[{"like_num": True}]])
        if self.remove_url:
            matcher.add("urls", [[{"like_url": True}]])
        if self.remove_email:
            matcher.add("emails", [[{"like_email": True}]])
            
        Token.set_extension('is_remove', default=False, force=True)

        cleaned_text = []
        for doc in nlp.pipe(texts,batch_size=64,disable=['parser','ner']):
            matches = matcher(doc)
            for _, start, end in matches:
                for token in doc[start:end]:
                    token._.is_remove =True
                    
            if self.lammetize:              
                text = ' '.join(token.lemma_ for token in doc if (token._.is_remove==False))
            elif self.stemming:
                text = ' '.join(PorterStemmer().stem(token.text) for token in doc if (token._.is_remove==False))
            else:
                text = ' '.join(token.text for token in doc if (token._.is_remove==False))
                                   
            if self.lower:
                text=text.lower()
            cleaned_text.append(text)
        return cleaned_text

    def fit(self, X,y=None):
        return self

    def transform(self, X, y=None):
        try:
            if str(type(X)) not in ["<class 'list'>","<class 'numpy.ndarray'>"]:
                raise Exception('Expected list or numpy array got {}'.format(type(X)))
            x_clean = [self.basic_clean(text) for text in X]
            x_clean_final = self.spacy_preprocessor(x_clean)
            return x_clean_final
        except Exception as error:
            print('An exception occured: ' + repr(error))

"""# Load the Dataset"""

TripAdvisor = pd.read_csv (data_folder/r'TripAdvisor.csv', encoding = 'unicode_escape')
Yelp = pd.read_csv (data_folder/r'Yelp.csv', encoding = 'unicode_escape')
full_reviews = pd.read_csv (data_folder/r'rating_reviews.csv', encoding = 'unicode_escape')

low_ratings = full_reviews.loc[full_reviews['Ratings'].isin([1, 2, 3])]
low_ratings.shape

high_ratings = full_reviews.loc[full_reviews['Ratings'].isin([5])]
high_ratings.shape
#imbalanced

# Printing shape of dataframe
TripAdvisor.shape

Yelp.shape

# diaplay first three rows
TripAdvisor.head(3)

Yelp.head(3)

"""## Merge Content

"""

text = pd.DataFrame.to_numpy(TripAdvisor['Contents'].append(Yelp['Contents']))
text_TripAdvisor = pd.DataFrame.to_numpy(TripAdvisor['Contents'])
text_Yelp = pd.DataFrame.to_numpy(Yelp['Contents'])
lowrating_corpus = pd.DataFrame.to_numpy(low_ratings['Contents'])
highrating_corpus = pd.DataFrame.to_numpy(high_ratings['Contents'])

text[1]

"""## Data Preprocessing"""

preprocessor = SpacyPreprocessor(lammetize=True, lower=True, remove_stop=True, 
                 remove_punct=True, remove_email=True, remove_url=True, remove_num=False, stemming = True,
                 add_user_mention_prefix=True, remove_hashtag_prefix=True)
cleaned_text = preprocessor.fit_transform(text)
cleaned_TripAdvisor = preprocessor.fit_transform(text_TripAdvisor)
cleaned_Yelp = preprocessor.fit_transform(text_Yelp)
cleaned_lowrating = preprocessor.fit_transform(lowrating_corpus)
cleaned_highrating = preprocessor.fit_transform(highrating_corpus)

lowrating_text = ''.join(cleaned_lowrating)
high_rating_text = ''.join(cleaned_highrating)
Corpus = [lowrating_text, high_rating_text]

cleaned_text[1]

"""# Exploratory Analysis"""

counter_tripadvisor = Counter() #Counting several repeated objects
counter_tripadvisor.update(str(cleaned_TripAdvisor).split())
sorted_by_freq_tuples = sorted(counter_tripadvisor.items(), key=lambda x: x[1], reverse=True)
sorted_by_freq_tuples[0:20]

counter_yelp = Counter() #Counting several repeated objects
counter_yelp.update(str(cleaned_Yelp).split())
sorted_by_freq_tuples = sorted(counter_yelp.items(), key=lambda x: x[1], reverse=True)
sorted_by_freq_tuples[0:20]

"""## N- gram"""

TripAdvisor_ngram = " ".join(cleaned_TripAdvisor)
Yelp_ngram = " ".join(cleaned_Yelp)
text_ngram = " ".join(cleaned_text)

TripAdvisor_tokens = [token for token in TripAdvisor_ngram.split(" ") if token != ""]
TripAdvisor_bigram = list(ngrams(TripAdvisor_tokens, 2))
TripAdvisor_bigram[2]

counter_TripAdvisor_bigram=Counter(TripAdvisor_bigram) 
TripAdvisor_bi = sorted(counter_TripAdvisor_bigram.items(), key=lambda x: x[1], reverse=True)
TripAdvisor_bi[0:20]

Yelp_tokens = [token for token in Yelp_ngram.split(" ") if token != ""]
Yelp_bigram = list(ngrams(Yelp_tokens, 2))
counter_Yelp_bigram=Counter(Yelp_bigram) 
Yelp_bi = sorted(counter_Yelp_bigram.items(), key=lambda x: x[1], reverse=True)
Yelp_bi[0:20]

Text_tokens = [token for token in text_ngram.split(" ") if token != ""]
Text_bigram = list(ngrams(Text_tokens, 2))
counter_Text_bigram=Counter(Text_bigram) 
Text_bi = sorted(counter_Text_bigram.items(), key=lambda x: x[1], reverse=True)
Text_bi[0:20]

"""# Negative Review Analysis

use tfidf instead of count vectorization
to find high frequent words that only unique to negative value
"""

tfidf_vectorizer = TfidfVectorizer()
tfidf_vectors = tfidf_vectorizer.fit_transform(Corpus)
print(f'tfidf vectors in array (dense) format\n') 
print(tfidf_vectors.toarray())  #to check the dense ventor
print(f'\nThe shape of the tfidf vectors is : {tfidf_vectors.toarray().shape}')

first_document_tfidf = tfidf_vectors[0].toarray().ravel()
feature_names_tfidf = tfidf_vectorizer.get_feature_names()
df_tfidf = pd.DataFrame({'features':feature_names_tfidf , 
                         'norm_tfidf':first_document_tfidf})

# combine dataframes
df_tfidf.sort_values(by=["norm_tfidf"],ascending=False, inplace = True)
df_tfidf.sort_values('norm_tfidf',ascending = False).head(20)

"""## Similarity Analysis """

preprocessor2 = SpacyPreprocessor(lammetize=True, lower=True, remove_stop=False, 
                 remove_punct=True, remove_email=True, remove_url=True, remove_num=False, stemming = True,
                 add_user_mention_prefix=True, remove_hashtag_prefix=True)
cleaned_lowrating2 = preprocessor2.fit_transform(lowrating_corpus)

token_text=[x.split() for x in cleaned_lowrating2]

model0 = Word2Vec(token_text, epochs=14, vector_size=50, window=8, min_count=1, sg=0)
model0.wv.most_similar("valet", topn=15)

"""## Tensor Board Visualization

"""

import numpy as np
import tensorflow.compat.v1 as tf
import tensorflow_probability as tfp
import datetime, os
from tensorboard.plugins import projector

log_dir = Path('/content/drive/MyDrive/Data/model_dir')

embeddings = dict(zip(model0.wv.index_to_key, model0.wv.vectors))
#https://github.com/RaRe-Technologies/gensim/wiki/Migrating-from-Gensim-3.x-to-4

embeddings_vectors = np.stack(list(embeddings.values()), axis=0)
embeddings_vectors.shape

# Create some variables.
emb = tf.Variable(embeddings_vectors, name='word_embeddings')

# Add an op to initialize the variable.
tf.disable_eager_execution()

tfd = tfp.distributions

init_op = tf.global_variables_initializer()

# Add ops to save and restore all the variables.
saver = tf.train.Saver()

# Later, launch the model, initialize the variables and save the
# variables to disk.
with tf.Session() as sess:
   sess.run(init_op)

# Save the variables to disk.
   save_path = saver.save(sess, '/content/drive/MyDrive/Data/model_dir/model.ckpt')
   print("Model saved in path: %s" % save_path)

words = '\n'.join(list(embeddings.keys()))

with open(os.path.join(log_dir, 'metadata.tsv'), 'w', encoding='utf-8') as f:
   f.write(words)

# Commented out IPython magic to ensure Python compatibility.
#%load_ext tensorboard
# %load_ext tensorboard
#%tensorboard --logdir model_dir/
# %tensorboard --logdir='/content/drive/MyDrive/Data/model_dir/'

"""## Custom Word Pairs for model evaluation"""

# how to choose different vector size and window size
model1 = Word2Vec(token_text, epochs=14, vector_size=50, window=10, min_count=1, workers = 8, sg=0)
model2 = Word2Vec(token_text, epochs=14, vector_size=50, window=15, min_count=1, workers = 8, sg=0)
model3 = Word2Vec(token_text, epochs=14, vector_size=100, window=8, min_count=1, workers = 8, sg=0)
model4 = Word2Vec(token_text, epochs=14, vector_size=100, window=10, min_count=1, workers = 8, sg=0)
model5 = Word2Vec(token_text, epochs=14, vector_size=100, window=15, min_count=1, workers = 8, sg=0)
model6 = Word2Vec(token_text, epochs=14, vector_size=50, window=10, min_count=1, workers = 8, sg=1)
model7 = Word2Vec(token_text, epochs=14, vector_size=50, window=15, min_count=1, workers = 8, sg=1)
model8 = Word2Vec(token_text, epochs=14, vector_size=100, window=10, min_count=1, workers = 8, sg=1)
model9 = Word2Vec(token_text, epochs=14, vector_size=100, window=15, min_count=1, workers = 8, sg=1)
model10 = Word2Vec(token_text, epochs=14, vector_size=100, window=20, min_count=1, workers = 8, sg=1)
model11 = Word2Vec(token_text, epochs=14, vector_size=200, window=8, min_count=1, workers = 8, sg=1)
model12 = Word2Vec(token_text, epochs=14, vector_size=200, window=10, min_count=1, workers = 8, sg=1)
model13 = Word2Vec(token_text, epochs=14, vector_size=200, window=15, min_count=1, workers = 8, sg=1)

model1.wv['room']

list1 = ['poor', 'outstanding', 'excellent', 'bad', 'expensive', 'overcharge', 'valet', 'hotel', 'fire']
list2 = ['horrible', 'wonderful', 'incredible', 'terrible', 'overpriced', 'bill', 'parking', 'property','pit']

models = [model0, model1, model2, model3, model4, model5, model6, model7, model8, model9, model10, model11, model12, model13]
for model in models:
  loss = sum(model.wv[i]@ model.wv[j] for (i, j) in zip(list1, list2))
  print(model, loss)
# model 11 perform the best

# save the best model
model12.save('word2vec.negative_review_model')

# load the model
Word2Vec_model = Word2Vec.load("word2vec.negative_review_model")

Word2Vec_model.wv['room']

"""## Fasttext"""

# use skip-gram
model1 = FastText(token_text, epochs=14, vector_size=50, window=10, sample=1e-2, min_count=1, workers = 8, sg=1)
model2 = FastText(token_text, epochs=14, vector_size=50, window=15, sample=1e-2, min_count=1, workers = 8, sg=1)
model3 = FastText(token_text, epochs=14, vector_size=100, window=10, sample=1e-2, min_count=1, workers = 8, sg=1)
model4 = FastText(token_text, epochs=14, vector_size=100, window=15, sample=1e-2, min_count=1, workers = 8, sg=1)
model5 = FastText(token_text, epochs=14, vector_size=100, window=20, sample=1e-2, min_count=1, workers = 8, sg=1)
model6 = FastText(token_text, epochs=14, vector_size=200, window=8, sample=1e-2, min_count=1, workers = 8, sg=1)
model7 = FastText(token_text, epochs=14, vector_size=200, window=10, sample=1e-2, min_count=1, workers = 8, sg=1)
model8 = FastText(token_text, epochs=14, vector_size=200, window=15, sample=1e-2, min_count=1, workers = 8, sg=1)

models = [model1, model2, model3, model4, model5, model6, model7, model8]
for model in models:
  loss = sum(model.wv[i]@ model.wv[j] for (i, j) in zip(list1, list2))
  print(model, loss)

"""Word2Vec take shorter time to train and have higher accuracy

# special Occasion

## Customer Segmentation
"""

preprocessor3 = SpacyPreprocessor(lammetize=False, lower=True, remove_stop=False, 
                 remove_punct=False, remove_email=True, remove_url=True, remove_num=False, stemming = False,
                 add_user_mention_prefix=True, remove_hashtag_prefix=True)
cleaned_text3 = preprocessor3.fit_transform(text)

token_text2=[x.split() for x in cleaned_text3]

model = Word2Vec(token_text2, epochs=14, vector_size=14, window=15, min_count=5, workers = 8, sg=0)
model.wv.most_similar("anniversary", topn=15)

search_special_occasion=['birthday', 'celebrate', 'babymoon', 'photograph', 'photo', 'flower', '25th', 
                         '5th', '30th','balloon', 'celebrating', 'celebration', 'occasion''proposal', 
                         'engagement', 'anniversary', '10th', 'bday', 'shoot']

special_occasion = [
    sentence for sentence in cleaned_text3 if any(
        keyword in sentence for keyword in search_special_occasion)]

special_occasion[1]

len(special_occasion)

"""## Aspect Grouping"""

preprocessor4 = SpacyPreprocessor(lammetize=True, lower=True, remove_stop=True, 
                 remove_punct=True, remove_email=True, remove_url=True, remove_num=False, stemming = True,
                 add_user_mention_prefix=True, remove_hashtag_prefix=True)
special_occasion_text = preprocessor4.fit_transform(special_occasion)

counter_so = Counter() #Counting several repeated objects
counter_so.update(str(special_occasion_text).split())
sorted_by_freq_tuples = sorted(counter_so.items(), key=lambda x: x[1], reverse=True)
sorted_by_freq_tuples[0:20]

special_occasion_text_ngram = " ".join(special_occasion_text)
so_tokens = [token for token in special_occasion_text_ngram.split(" ") if token != ""]
so_bigram = list(ngrams(so_tokens, 2))
counter_so_bigram=Counter(so_bigram) 
so_bi = sorted(counter_so_bigram.items(), key=lambda x: x[1], reverse=True)
so_bi[0:20]

text_sentences = " ".join(special_occasion).split(".")
def aspect_grouping(searchwords, lookup_sentences, return_sentence):
  for sentence in lookup_sentences:
    if any(keyword in sentence for keyword in searchwords):
      return_sentence.append(sentence)
  return len(return_sentence)

search_club=['club', 'lounge']
club_lounge=[]
aspect_grouping(search_club, text_sentences, club_lounge)

search_upgrade=['upgrade']
upgrade=[]
aspect_grouping(search_upgrade, text_sentences, upgrade)

search_firepit=['fire', 'pit', 'firepit']
firepit=[]
aspect_grouping(search_firepit, text_sentences, firepit)

search_frontdesk=['front', 'desk', 'frontdesk']
frontdesk=[]
aspect_grouping(search_frontdesk, text_sentences, frontdesk)

search_view=['ocean', 'view', 'oceanview']
ocean_view=[]
aspect_grouping(search_view, text_sentences, ocean_view)

search_wine=['wine', 'glass', 'bottle']
wine=[]
aspect_grouping(search_wine, text_sentences, wine)

"""## Test VADER, TextBlob, Flair

Test VADER, TextBlob, Flair

VADER, TextBlob: 
*   As sentences get longer, more neutral words exist, and therefore, the overall score tends to normalize more towards neutral 

Flair: 
*   Embedding based model, trained on IMDB dataset, not generalize well on other dataset
*   tends to be slower than its rule-based counterparts but comes at the advantage of being a trained NLP model instead of a rule-based model, which, if done well comes with added performance.
"""

sentences = ['Best nights sleep- beds so comfy.',                                                          # positive
            'The place is worth the money for the location and room view. ',                               # positive
            'We visited the RC HMB this weekend.',                                                         # neural
            'Visited here for a company sponsored event.',                                                 # neural     
            'Beautiful location and hotel but poor planning and customer service.',                        # negative   
            'I think I learned my lesson when it comes to Ritz spas (this is my 3rd spa experience at a Ritz): over priced and extremely poor service.'] # negative

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
analyzer = SentimentIntensityAnalyzer()
for sentence in sentences:
  vs = analyzer.polarity_scores(sentence)
  print(str(vs))

from textblob import TextBlob

for sentence in sentences:
  testimonial = TextBlob(sentence)
  print(testimonial.sentiment)
#not very accurate

from flair.models import TextClassifier
from flair.data import Sentence

classifier = TextClassifier.load('en-sentiment')
for sentence in sentences:
  sentence = Sentence(sentence)
  classifier.predict(sentence)
  print(sentence.labels)
# no nerual result

"""## Sentiment Analysis"""

def sentiment_analyzer_scores(sentences, categorylist):  
  for sentence in sentences:
    score = analyzer.polarity_scores(sentence)
    categorylist.append(score.get('compound'))

club_lounge_score = []
sentiment_analyzer_scores(club_lounge, club_lounge_score)

print(club_lounge_score)

upgrade_score = []
sentiment_analyzer_scores(upgrade, upgrade_score)
firepit_score = []
sentiment_analyzer_scores(firepit, firepit_score)
front_desk_score = []
sentiment_analyzer_scores(frontdesk, front_desk_score)
ocean_view_score = []
sentiment_analyzer_scores(ocean_view, ocean_view_score)
wine_score = []
sentiment_analyzer_scores(wine, wine_score)

data=[club_lounge_score, upgrade_score, firepit_score, front_desk_score, ocean_view_score, wine_score]

num1 = []
for category in data:
  num1.append(len(category))
print(num1)

fig, ax = plt.subplots()
fig.suptitle('Speical Occation Segment - Sentiment Analysis', fontsize=14, fontweight='bold')
xlabel=['Club Lounge', 'Upgrade', 'Fire Pit', 'Front Desk', 'Ocean View', 'Wine']
ax.set_xticklabels(xlabel) 
fig.autofmt_xdate(rotation=45)
ax.set_xlabel('Service Category Group')
ax.set_ylabel('Sentence Sentiment Score')
bp = ax.boxplot(data)

#plt.rcParams["figure.figsize"] = [7.50, 4.50]
#plt.rcParams["figure.autolayout"] = True

for i, line in enumerate(bp['medians']):
    x, y = line.get_xydata()[1]
    text = 'n={:.0f}'.format(num1[i])
    ax.annotate(text, xy=(x, y))
