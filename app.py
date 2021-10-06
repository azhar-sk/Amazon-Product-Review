import pandas as pd 
import numpy as np

from bs4 import BeautifulSoup
import requests

import warnings
warnings.filterwarnings('ignore')

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

import string

import spacy
nlp = spacy.load('en_core_web_sm')

import nltk
from nltk import tokenize

from wordcloud import WordCloud
import matplotlib.pyplot as plt

from wordcloud import WordCloud, STOPWORDS

from flask import Flask, redirect, url_for, request,render_template

pd.set_option('display.max_rows',None)
pd.set_option('display.max_colwidth', 80)

import csv

affin = pd.read_csv('Afinn.csv',sep=',',encoding='latin-1')

affinity_scores = affin.set_index('word')['value'].to_dict()

sentiment_lexicon = affinity_scores

def get_url(x):
    template = 'https://www.amazon.in/s?k='
    url = template + x
    return url

def add_page(url,x):
    page_link = url + '&page=' + str(x)
    return page_link

def extract_record(item):
    
    "description and url"
    atag = item.h2.a
    description = atag.text.strip()
    url = 'https://www.amazon.in' + atag.get('href')
    
    "price"
    try:
        price_parent = item.find('span', 'a-price')
        price = price_parent.find('span', 'a-offscreen').text
    except AttributeError:
        return
    
    "rating and review count"
    try:
        rating = item.i.text
        review_count = item.find('span', {'class':'a-size-base'}).text
    except AttributeError:
        rating = ''
        review_count ='' 
    
    result = (description, price, rating, review_count, url)
    
    return result

def main(search_term):
    "Run main program routine"
    
    "starting up the web driver"
    driver = webdriver.Chrome(ChromeDriverManager().install())
    
    records=[]
    
    url = get_url(search_term)
    
    for page in range(1,6):
        
        link = add_page(url,page)
        
        driver.get(link)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        results = soup.find_all('div', {'data-component-type': 's-search-result'})
        
        for item in results:
            record = extract_record(item)
            if record:
                records.append(record)
    driver.close()
    
    "Saving the data in csv"
    with open('search_results.csv','w', newline='',encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Description','Price','Rating','Review_Count','URL'])
        writer.writerows(records)

def get_review(product_page):
    
    driver = webdriver.Chrome(ChromeDriverManager().install())
    
    driver.get(product_page)
    
    soup = BeautifulSoup(driver.page_source,'html.parser')
    review_page = soup.find('a',{'data-hook':'see-all-reviews-link-foot'})
    review_link = review_page.get('href')
    
    template = 'https://amazon.in'
    url = template + review_link
    driver.close()
    new_main(url)
        
    return 

def new_extract_record(item):
    
    'profile name'
    try:
        name = item.find('div',{'class':'a-profile-content'}).text.strip()
    except AttributeError:
        return
    
    'rating'
    try:
        itag = item.i
        rating = itag.text.replace('out of 5 stars','').strip()
    except AttributeError:
        return
    
    'Review title'
    try:
        review_title = item.find('a',{'data-hook':'review-title'}).text.strip()
    except AttributeError:
        return
    
    'Review Body'
    try:
        body = item.find('span',{'data-hook':'review-body'}).text.strip()
    except AttributeError:
        return
    
    result = (name,rating,review_title,body)
    
    return result

def calculate_sentiment(text: str = None):
        sent_score = 0
        if text:
            sentence = nlp(text)
            for word in sentence:
                sent_score += sentiment_lexicon.get(word.lemma_,0)
        return sent_score

def new_main(url):
    
    driver = webdriver.Chrome(ChromeDriverManager().install())
    
    records=[]
    
    url += '&pageNumber={}'
    
    for page in range(1,999999):
        #https://www.amazon.in/New-Apple-iPhone-Pro-128GB/product-reviews/
        #B08L5VZKWT/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews
                
        driver.get(url.format(page))
        
        soup = BeautifulSoup(driver.page_source, 'html.parser') 
        
        results = soup.find_all('div', {'data-hook':'review'})
        
        for item in results:
            record = new_extract_record(item)
            records.append(record)
        
        if not soup.find('li',{'class':'a-disabled a-last'}):
            pass
        else:
            break
    
    driver.close()
    
    
    "Saving the data in csv"
    with open('reviews.csv','w', newline='',encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Name','Rating','Review_Title','Review_Body'])
        writer.writerows(records)

        
app = Flask(__name__)

@app.route('/',methods = ['POST','GET'])
def home_page():
    home = 'home.html'
    return render_template(home)

@app.route('/search_results',methods = ['POST','GET'])
def search_results():
    if request.method == 'POST':
        search_term = str(request.form['search_term'])
        main(search_term)
        data = pd.read_csv('search_results.csv')
        data = data.dropna()
        data = data.reset_index(drop =True)
        for i in range (0,len(data)):
            data.Review_Count[i] = data.Review_Count[i].replace(',','')
        data.Review_Count = pd.to_numeric(data['Review_Count'])
        index_names = data[data['Review_Count'] < 11 ].index
        data.drop(index_names, inplace = True)
        data = data.drop_duplicates(subset=['URL'])
        data = data.drop_duplicates(subset=['Description'])
        data = data.reset_index(drop =True)
        p_data = data.drop(['URL'],axis = 1)
        p_data = p_data.reset_index()
        p_data = p_data.rename(columns={'index':'Item_No.'},inplace=False)
        headings0 = np.array(p_data.columns)
        data0 = np.array(p_data)
    return render_template('search_results.html',search_term = search_term,headings = headings0,data = data0)

@app.route('/search_results/item',methods = ['POST','GET'])
def item_review():
    if request.method == 'POST':
        item_no = int(request.form['index_term'])
        data = pd.read_csv('search_results.csv')
        data = data.dropna()
        data = data.reset_index(drop =True)
        for i in range (0,len(data)):
            data.Review_Count[i] = data.Review_Count[i].replace(',','')
        data.Review_Count = pd.to_numeric(data['Review_Count'])
        index_names = data[data['Review_Count'] < 11 ].index
        data.drop(index_names, inplace = True)
        data = data.drop_duplicates(subset=['URL'])
        data = data.drop_duplicates(subset=['Description'])
        data = data.reset_index(drop =True)
        product_url = data.URL[item_no]
        title = data.Description[item_no]
        get_review(product_url)
        review = pd.read_csv('reviews.csv')
        review['review'] = review['Review_Title'] + ' ' + review['Review_Body']
        df= pd.DataFrame(review.review)
        for i in range (0,len(df)):
            df.review[i] = nltk.sent_tokenize(str(df.review[i]))
        affin = pd.read_csv('Afinn.csv',sep=',',encoding='latin-1')
        affinity_scores = affin.set_index('word')['value'].to_dict()
        sentiment_lexicon = affinity_scores
        df['Sentiment_Value'] = 'nan'
        for i in range(0,len(df)):
            sent_score = 0
            for sent in df['review'][i]:
                sent_score = calculate_sentiment(sent)
            df['Sentiment_Value'][i] = sent_score
        df['Word_Count'] = 'nan'
        for i in range(0,len(df)):
            length = 0
            for sent in df['review'][i]:
                length = length + len(sent.split(' '))
            df['Word_Count'][i] = length
        review = review.drop('review',axis = 1)
        df = df.drop('review',axis = 1)
        ndata = review.join(df)
        ndata.Sentiment_Value = pd.to_numeric(ndata['Sentiment_Value'])
        
        mean = int(ndata.Sentiment_Value.describe()[1])
        t5 = int(ndata.Sentiment_Value.describe()[4])
        f5 = int(ndata.Sentiment_Value.describe()[5])
        s5 = int(ndata.Sentiment_Value.describe()[6])
        r = data.Rating[item_no]
        r = r.replace(' out of 5 stars','')
        rat = float(r)
        ndata = ndata.drop(['Sentiment_Value','Word_Count'],axis=1)
        
        if (mean >= 0 and t5 >= 0 and f5 >= 0 and s5 >= 0 and rat >= 4):
            sent_val = 'The product is very good.'
            #print(sent_val)
        elif (mean >= 0 and t5 <= 0 and f5 >= 0 and s5 >= 0 and rat >= 3):
            sent_val = 'The product is good.'
            #print(sent_val)
        elif (mean >= 0 and t5 <= 0 and f5 >= 0 and s5 >= 0 and rat >= 2.5):
            sent_val = 'The product is average.'
            #print(sent_val)
        elif (mean <= 0 and t5 <= 0 and s5 >= 0 and rat >= 2):
            sent_val = 'The product is below average.'
            #print(sent_val)
        elif (mean <= 0 and t5 < 0 and f5 <= 0 and rat < 2):
            sent_val = 'This is a bad product.'
            #print(sent_val)
        #else:
            #sent_val = 'This is a bad product.'
        headings0 = np.array(ndata.columns)
        data0 = np.array(ndata)
        #Rating = ndata.Rating.describe()[5]
    return render_template('item_review.html',title=title,sentiment = sent_val,rating = rat,headings = headings0,data = data0)


if __name__ == '__main__':
    app.run()        