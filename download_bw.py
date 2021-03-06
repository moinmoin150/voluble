import streamlit as st
import pandas as pd
import streamlit.components as stc
import base64
import time
import datetime
import requests
import tweepy
import math

timestr = time.strftime("%Y%m%d-%H%M%S")

class FileDownloader(object):
	def __init__(self, data,filename='myfile',file_ext='txt'):
		super(FileDownloader, self).__init__()
		self.data = data
		self.filename = filename
		self.file_ext = file_ext

	def download_id(self):
		b64 = base64.b64encode(self.data.encode()).decode()
		new_filename = "{}_{}_.{}".format(self.filename,timestr,self.file_ext)
		st.markdown("#### Download ID list ###")
		href = f'<a href="data:file/{self.file_ext};base64,{b64}" download="{new_filename}">Click Here</a>'
		st.markdown(href,unsafe_allow_html=True)
		
	def download_dta(self):
		b64 = base64.b64encode(self.data.encode()).decode()
		new_filename = "{}_{}_.{}".format(self.filename,timestr,self.file_ext)
		st.markdown("#### Download Tweets ###")
		href = f'<a href="data:file/{self.file_ext};base64,{b64}" download="{new_filename}">Click Here</a>'
		st.markdown(href,unsafe_allow_html=True)

# request access token
params = {
"password":st.secrets["password"]
}
url1 = 'https://api.brandwatch.com/oauth/token?username=tzhu@gbexpertsgroup.com&grant_type=api-password&client_id=brandwatch-api-client'
r1 = requests.get(url1, params=params).json()
access_token = r1['access_token']
h = {
"Authorization":f"Bearer {access_token}"
}

# request query list
url2 = 'https://api.brandwatch.com/projects/1998290339/queries'
r2 = requests.get(url2, headers=h).json()
queries = [i['name'] for i in r2['results']]

# user input query name
st.markdown("# Download Tweets From Brandwatch")
query = st.selectbox("Select the query", queries)
_id = [i['id'] for i in r2['results'] if i['name']==query][0]
source = [i['contentSources'] for i in r2['results'] if i['name']==query][0]
if ('twitter' not in source)|(len(source)>1):
    st.markdown("##### Please select a Twitter only query!")
if st.checkbox('Query Quick Look'):
    st.subheader('Query:')
    st.write([i['booleanQuery'] for i in r2['results'] if i['name']==query][0])
    st.subheader('Since:')
    st.write([i['startDate'] for i in r2['results'] if i['name']==query][0])
    st.subheader('Content Sources:')
    st.write(source)
    st.subheader('Location Filter:')
    st.write([i['locationFilter'] for i in r2['results'] if i['name']==query][0])

# user select date range
start_date = st.date_input("Select start date")
end_date = st.date_input("Select end date")
start = start_date.strftime("%Y-%m-%d")
end = end_date.strftime("%Y-%m-%d")

# select columns to download
col_list = ['created_at', 'id', 'id_str', 'full_text', 'source', 'in_reply_to_status_id',
'in_reply_to_status_id_str', 'in_reply_to_user_id', 'in_reply_to_user_id_str', 'in_reply_to_screen_name',
'user', 'retweeted_status', 'retweet_count', 'favorite_count', 'lang']
columns_to_download = st.multiselect("Select Columns to Include in Dataset",col_list, default="id")

# preview the number of data points to download
search_btn = st.button("Search", key='search')
if st.session_state.get('button') != True:
    st.session_state['button'] = search_btn
if st.session_state['button'] == True:
    url4 = f"https://api.brandwatch.com/projects/1998290339/data/mentions/count?queryId%5B%5D={_id}&startDate={start}&endDate={end}"
    r4 = requests.get(url4, headers=h).json()
    st.write(f"Ready to collect {r4['mentionsCount']} data points")

# start downloading
    download_btn = st.button("Download", key='download')
    if download_btn:
        url3 = f"https://api.brandwatch.com/projects/1998290339/data/mentions?queryId={_id}&startDate={start}&endDate={end}&pageSize=5000&orderBy=date&orderDirection=asc"
        r3 = requests.get(url3, headers=h).json()
        ids = [i['guid'] for i in r3['results']]
        st.write('Getting ids...')
        while 'nextCursor' in r3:
            cursor = r3['nextCursor']
            url3 = f"https://api.brandwatch.com/projects/1998290339/data/mentions?queryId={_id}&startDate={start}&endDate={end}&pageSize=5000&orderBy=date&orderDirection=asc&cursor={cursor}"
            r3 = requests.get(url3, headers=h).json()
            ids += [i['guid'] for i in r3['results']]
            st.write(f"Collected {len(ids)} IDs")

        df = pd.DataFrame({
        'ID':ids,
        'ID_string':[str(i) for i in ids]
        })
        st.subheader("Preview first 50 rows:")
        st.dataframe(df.head(50))
        download = FileDownloader(df.to_csv(),file_ext='csv').download_id()

        with st.spinner('Download in process...'):
            auth = tweepy.OAuthHandler(st.secrets["CONSUMER_KEY"], st.secrets["CONSUMER_SECRET"])
            auth.set_access_token(st.secrets["OAUTH_TOKEN"], st.secrets["OAUTH_TOKEN_SECRET"])
            api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

            out = []
            for i in range(math.floor(len(ids)/100)+1):
                seq = ids[i*100:(i+1)*100]
                tweets = api.statuses_lookup(seq,tweet_mode='extended')
                for tweet in tweets:
                    out.append(tweet._json)
        st.write(f"Complete! Total Number: {len(out)}")

        dta = {}
        for c in columns_to_download:
            if c == 'user':
                dta[c] = []
                for i in out:
                    try:
                        dta[c].append(i[c]['screen_name'])
                    except:
                        dta[c].append('None')
            elif c == 'retweeted_status':
                dta[c] = []
                for i in out:
                    try:
                        dta[c].append(i[c]['id_str'])
                    except:
                        dta[c].append('None')
            else:
                dta[c] = []
                for i in out:
                    try:
                        dta[c].append(i[c])
                    except:
                        dta[c].append('None')
        twi_df = pd.DataFrame(dta)
        download2 = FileDownloader(twi_df.to_csv(),file_ext='csv').download_dta()
        st.session_state['button'] = False
