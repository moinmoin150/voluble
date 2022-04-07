import streamlit as st
import pandas as pd
import streamlit.components as stc
import base64
import time
import datetime
import requests

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

# request access token
params = {
"password":st.secrets["password"]
}
url = 'https://api.brandwatch.com/oauth/token?username=tzhu@gbexpertsgroup.com&grant_type=api-password&client_id=brandwatch-api-client'
r = requests.get(url, params=params).json()
access_token = r['access_token']
h = {
"Authorization":f"Bearer {access_token}"
}

# request query list
url = 'https://api.brandwatch.com/projects/1998290339/queries'
r = requests.get(url, headers=h).json()
queries = [i['name'] for i in r['results']]

# user input query name
st.markdown("# Download Tweets From Brandwatch")
query = st.selectbox("Select the query", queries)
_id = [i['id'] for i in r['results'] if i['name']==query][0]
if st.checkbox('Query Quick Look'):
    st.subheader('Query:')
    st.write([i['booleanQuery'] for i in r['results'] if i['name']==query][0])
    st.subheader('Since:')
    st.write([i['startDate'] for i in r['results'] if i['name']==query][0])
    st.subheader('Content Sources:')
    st.write([i['contentSources'] for i in r['results'] if i['name']==query][0])
    st.subheader('Location Filter:')
    st.write([i['locationFilter'] for i in r['results'] if i['name']==query][0])
	
# user select date range
start_date = st.date_input("Select start date")
end_date = st.date_input("Select end date")
start = start_date.strftime("%Y-%m-%d")
end = end_date.strftime("%Y-%m-%d")

# preview the number of data points to download
search_btn = st.button("Search")
if st.session_state.get('button') != True:
    st.session_state['button'] = search_btn
if st.session_state['button'] == True:
    url = f"https://api.brandwatch.com/projects/1998290339/data/mentions/count?queryId%5B%5D={_id}&startDate={start}&endDate={end}"
    r = requests.get(url, headers=h).json()
    st.write(f"Ready to collect {r['mentionsCount']} data points")

# start downloading
    proceed = st.checkbox("Proceed?")
    if proceed:
        url = f"https://api.brandwatch.com/projects/1998290339/data/mentions?queryId={_id}&startDate={start}&endDate={end}&pageSize=5000&orderBy=date&orderDirection=asc"
        r = requests.get(url, headers=h).json()
        ids = [i['guid'] for i in r['results']]
        st.write('Data processing in process...')
        while 'nextCursor' in r:
            cursor = r['nextCursor']
            url = f"https://api.brandwatch.com/projects/1998290339/data/mentions?queryId={_id}&startDate={start}&endDate={end}&pageSize=5000&orderBy=date&orderDirection=asc&cursor={cursor}"
            r = requests.get(url, headers=h).json()
            ids += [i['guid'] for i in r['results']]
            st.write(f"Collected {len(ids)} IDs")

        df = pd.DataFrame({
        'ID':ids,
        'ID_string':[str(i) for i in ids]
        })
        st.subheader("Preview first 50 rows:")
        st.dataframe(df.head(50))
        download = FileDownloader(df.to_csv(),file_ext='csv').download_id()

        twi_btn = st.button(f"Collect these {len(ids)} tweets via Twitter API?")
        if twi_btn:
            st.write("it works!")
            st.session_state['button'] = False
