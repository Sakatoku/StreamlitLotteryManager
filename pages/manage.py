import streamlit as st
import mysql.connector
import pandas as pd
import time

# タイトル
st.title('管理コンソール')

# Connect to TiDB
@st.cache_resource(ttl=600)
def connect_to_tidb(autocommit=True):
    connection = mysql.connector.connect(
        host = st.secrets.tidb.host,
        port = st.secrets.tidb.port,
        user = st.secrets.tidb.user,
        password = st.secrets.tidb.password,
        database = st.secrets.tidb.database,
        autocommit = autocommit,
        use_pure = True
    )
    return connection

# 在庫数を更新する
def update_stock(item_name, new_stock, df=None):
    # itemsテーブルを更新
    connection = connect_to_tidb()
    cursor = connection.cursor()
    cursor.execute("START TRANSACTION;")
    cursor.execute(f"UPDATE items SET item_stock = {new_stock} WHERE item_name = '{item_name}';")
    cursor.execute("COMMIT;")

    # データフレームが与えられている場合はログを出力する
    if df is not None:
        item_key = df[df['item_name'] == item_name]['item_key'].values[0]
        item_stock_before = df[df['item_name'] == item_name]['item_stock'].values[0]
        item_stock_after = new_stock
    cursor.execute(f"INSERT INTO lot_logs (lot_time, item_key, item_stock_before, item_stock_after) VALUES (NOW(), {item_key}, {item_stock_before}, {item_stock_after});")

st.subheader('在庫確認')

# itemsテーブルをすべて取得してデータフレームに格納
connection = connect_to_tidb()
cursor = connection.cursor()
cursor.execute("SELECT * FROM items;")
items = cursor.fetchall()
df = pd.DataFrame(items, columns=['item_key', 'item_name', 'item_stock'])
# データフレームを表示
st.dataframe(df)

st.subheader('抽選ログ')

with st.expander('抽選ログを表示'):
    # lot_logsテーブルを新しい方から20件取得してデータフレームに格納
    cursor.execute("SELECT * FROM lot_logs ORDER BY lot_time DESC LIMIT 20;")
    lot_logs = cursor.fetchall()
    df_logs = pd.DataFrame(lot_logs, columns=['lot_time', 'item_key', 'item_stock_before', 'item_stock_after'])
    # データフレームを表示
    st.dataframe(df_logs)

st.subheader('在庫更新')

# 在庫更新フォーム
selected_item = st.selectbox('アイテムを選択', ['', 'socks', 'backpack'])
if selected_item == 'socks':
    default_value = df[df['item_name'] == 'socks']['item_stock'].values[0]
    max_value = 500
elif selected_item == 'backpack':
    default_value = df[df['item_name'] == 'backpack']['item_stock'].values[0]
    max_value = 10
else:
    st.stop()
new_stock = st.slider(selected_item, 0, max_value, default_value)

# 更新にパスワードを要求する
password = st.text_input('パスワードを入力', type='password')
if st.button('更新'):
    if password == st.secrets.manage.password:
        # 在庫数を更新
        update_stock(selected_item, new_stock, df)
        st.success('更新が完了しました。5秒後にリロードされます。')
        time.sleep(5)
        st.rerun()
    else:
        st.error('パスワードが違います')
